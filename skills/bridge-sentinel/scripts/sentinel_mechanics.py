#!/usr/bin/env python3
"""Read-only byte and Git-tree mechanics for Bridge skills."""

from __future__ import annotations

import argparse
import ast
import base64
import datetime
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from contextlib import ExitStack, contextmanager

# The guard must precede every import that may someday need 3.9+, so a too-old
# interpreter exits with the documented JSON error instead of a traceback.
if sys.version_info < (3, 9):
    print(
        json.dumps(
            {
                "error": "Python %d.%d is too old; sentinel_mechanics.py"
                " requires Python 3.9 or newer" % sys.version_info[:2]
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(2)

from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Optional, get_type_hints


REGULAR_GIT_MODES = {"100644", "100755"}
GIT_TREE_DIRECTIONS = {
    "observe",
    "source-to-projection",
    "projection-to-source",
}
SEGMENT_PATTERN = rb"[A-Za-z0-9._-]+"
UNIT_ID_PATTERN = SEGMENT_PATTERN + rb"(?:/" + SEGMENT_PATTERN + rb")*"
SOURCE_PATH_PATTERN = UNIT_ID_PATTERN
MANAGED_START_PATTERN = re.compile(
    rb"<!-- bridge:managed:start id=("
    + UNIT_ID_PATTERN
    + rb") source=("
    + SOURCE_PATH_PATTERN
    + rb") -->"
)
MANAGED_END = b"<!-- bridge:managed:end -->"
CLAUDE_ONLY_START = b"<!-- bridge:claude-only:start -->"
CLAUDE_ONLY_END = b"<!-- bridge:claude-only:end -->"
LEGACY_MODE_PATTERN = re.compile(
    rb"<!-- bridge:managed:start id="
    + UNIT_ID_PATTERN
    + rb" source="
    + SOURCE_PATH_PATTERN
    + rb" mode=[^ \t]+ -->"
)
FENCE_PATTERN = re.compile(rb" {0,3}(?:```|~~~)")
ACTIVE_IMPORT_PATTERN = re.compile(rb"(?<!\S)@[A-Za-z0-9_./~-]+")
INTENT_PATTERN = re.compile(
    rb"<!-- bridge:intent (\d{4}-\d{2}-\d{2}) (.+) -->"
)
COVENANT_CONTROL = (
    b"<!-- bridge:covenant covenant/v3 source-tree/v5 report/v5 "
    b"reconciliation/v3 sync-plan/v3 -->"
)
PV2_PREFIX = (
    "Applies only while reading or editing files that match at least one "
    "of these source globs: "
)
PV2_SUFFIX = ". (bridge:pv2)"
UNIVERSAL_PATH_PATTERNS = {"**", "**/*"}
ACTIVATION_PROFILE_SPEC = "activation-fixture/v1"
REPORT_SPEC = "report/v5"
FINDINGS_HEADER = (
    "| surface | unit | host | state | suggested action | tier | annotations |"
)
FINDINGS_SEPARATOR = "|---|---|---|---|---|---|---|"
LIVE_ACTIVATION_OBSERVATIONS = {
    "surface-shadowed",
    "codex-activation-unresolved",
    "codex-root-unresolved",
    "fallback-shadow",
    "codex-effective-budget",
    "agents-md-budget-disabled",
    "agents-md-budget-exceeded",
    "agents-md-size",
}
CAPABILITY_OBSERVATIONS = {"mode-limited"}


def normalize_n(data: bytes) -> bytes:
    """Apply the specification's closed normalization set N."""
    normalized = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    lines = [line.rstrip(b" \t") for line in normalized.split(b"\n")]
    while lines and lines[-1] == b"":
        lines.pop()
    if not lines:
        return b""
    return b"\n".join(lines) + b"\n"


def byte_records(data: bytes) -> list[dict[str, Any]]:
    """Split CRLF, LF, and lone-CR lines while retaining exact byte offsets."""

    records: list[dict[str, Any]] = []
    start = 0
    line_number = 1
    index = 0
    while index < len(data):
        value = data[index]
        if value not in (0x0A, 0x0D):
            index += 1
            continue
        if value == 0x0D and index + 1 < len(data) and data[index + 1] == 0x0A:
            end = index + 2
            eol = b"\r\n"
        else:
            end = index + 1
            eol = bytes((value,))
        records.append(
            {
                "line": line_number,
                "start": start,
                "content_end": index,
                "end": end,
                "content": data[start:index],
                "eol": eol,
            }
        )
        start = end
        index = end
        line_number += 1
    if start < len(data):
        records.append(
            {
                "line": line_number,
                "start": start,
                "content_end": len(data),
                "end": len(data),
                "content": data[start:],
                "eol": b"",
            }
        )
    return records


def fence_line(content: bytes) -> bool:
    """Apply the specification's deliberately simple fence toggle rule."""

    return FENCE_PATTERN.match(content) is not None


def expected_source_for_id(
    unit_id: str, *, entry_source: Optional[str]
) -> Optional[str]:
    if unit_id == "entry":
        return entry_source
    if unit_id.startswith("rules/"):
        suffix = unit_id[len("rules/") :]
        return f".claude/rules/{suffix}.md"
    return None


def complement_spans(
    length: int, excluded: Iterable[tuple[int, int]]
) -> list[dict[str, int]]:
    spans: list[dict[str, int]] = []
    cursor = 0
    for start, end in sorted(excluded):
        if start < cursor or end < start or end > length:
            raise ValueError("invalid or overlapping excluded byte spans")
        if cursor < start:
            spans.append({"start": cursor, "end": start})
        cursor = end
    if cursor < length:
        spans.append({"start": cursor, "end": length})
    return spans


def inspect_managed_blocks(
    data: bytes,
    *,
    entry_source: Optional[str] = None,
    owned_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Parse v4 root-AGENTS blocks and return exact structural byte spans."""

    records = byte_records(data)
    blocks: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    active: Optional[dict[str, Any]] = None
    fence_open = False
    seen: dict[str, int] = {}

    for record in records:
        content = record["content"]
        if fence_line(content):
            fence_open = not fence_open
            continue
        if fence_open:
            continue
        legacy = LEGACY_MODE_PATTERN.fullmatch(content)
        if legacy is not None:
            anomalies.append(
                {
                    "kind": "legacy-managed-mode",
                    "line": record["line"],
                    "start": record["start"],
                    "end": record["end"],
                }
            )
            continue
        start_match = MANAGED_START_PATTERN.fullmatch(content)
        if start_match is not None:
            if active is not None:
                anomalies.append(
                    {
                        "kind": "nested-start",
                        "line": record["line"],
                        "start": record["start"],
                        "end": record["end"],
                    }
                )
                continue
            unit_id = start_match.group(1).decode("ascii")
            source = start_match.group(2).decode("ascii")
            active = {
                "id": unit_id,
                "source": source,
                "start_line": record["line"],
                "start": record["start"],
                "marker_end": record["end"],
                "body_start": record["end"],
            }
            continue
        if content != MANAGED_END:
            continue
        if active is None:
            anomalies.append(
                {
                    "kind": "orphan-end",
                    "line": record["line"],
                    "start": record["start"],
                    "end": record["end"],
                }
            )
            continue
        block = dict(active)
        block.update(
            {
                "body_end": record["start"],
                "end_marker_start": record["start"],
                "end_line": record["line"],
                "end": record["end"],
            }
        )
        unit_id = block["id"]
        ordinal = seen.get(unit_id, 0) + 1
        seen[unit_id] = ordinal
        block["ordinal"] = ordinal
        if ordinal > 1:
            anomalies.append(
                {
                    "kind": "duplicate-id",
                    "id": unit_id,
                    "ordinal": ordinal,
                    "line": block["start_line"],
                    "start": block["start"],
                    "end": block["marker_end"],
                }
            )
        expected_source = expected_source_for_id(
            unit_id, entry_source=entry_source
        )
        block["expected_source"] = expected_source
        block["source_matches"] = (
            expected_source is None or expected_source == block["source"]
        )
        if not block["source_matches"]:
            anomalies.append(
                {
                    "kind": "source-mismatch",
                    "id": unit_id,
                    "line": block["start_line"],
                    "start": block["start"],
                    "end": block["marker_end"],
                    "actual": block["source"],
                    "expected": expected_source,
                }
            )
        block["body_sha256"] = hashlib.sha256(
            data[block["body_start"] : block["body_end"]]
        ).hexdigest()
        blocks.append(block)
        active = None

    if active is not None:
        anomalies.append(
            {
                "kind": "unclosed-block",
                "id": active["id"],
                "line": active["start_line"],
                "start": active["start"],
                "end": active["marker_end"],
            }
        )

    owned = set(owned_ids)
    structural_spans = [(block["start"], block["end"]) for block in blocks]
    owned_spans = [
        (block["start"], block["end"])
        for block in blocks
        if block["id"] in owned and block["ordinal"] == 1
    ]
    interstitial = complement_spans(len(data), structural_spans)
    manual = complement_spans(len(data), owned_spans)
    for span in interstitial:
        span["sha256"] = hashlib.sha256(
            data[span["start"] : span["end"]]
        ).hexdigest()
    for span in manual:
        span["sha256"] = hashlib.sha256(
            data[span["start"] : span["end"]]
        ).hexdigest()
    return {
        "contract": "managed-block-map/v2",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "trustworthy": not anomalies,
        "blocks": blocks,
        "anomalies": anomalies,
        "interstitial_spans": interstitial,
        "manual_spans": manual,
        "owned_ids": sorted(owned),
    }


def inspect_claude_only(data: bytes) -> dict[str, Any]:
    """Find subtractable Claude-only pairs with marker/fence semantics."""

    records = byte_records(data)
    spans: list[dict[str, int]] = []
    anomalies: list[dict[str, Any]] = []
    active: Optional[dict[str, int]] = None
    fence_open = False
    for record in records:
        content = record["content"]
        if fence_line(content):
            fence_open = not fence_open
            continue
        if fence_open:
            continue
        if content == CLAUDE_ONLY_START:
            if active is not None:
                anomalies.append(
                    {
                        "kind": "nested-claude-only-start",
                        "line": record["line"],
                        "start": record["start"],
                        "end": record["end"],
                    }
                )
                continue
            active = {
                "line": record["line"],
                "start": record["start"],
            }
            continue
        if content != CLAUDE_ONLY_END:
            continue
        if active is None:
            anomalies.append(
                {
                    "kind": "orphan-claude-only-end",
                    "line": record["line"],
                    "start": record["start"],
                    "end": record["end"],
                }
            )
            continue
        spans.append(
            {
                "start": active["start"],
                "end": record["end"],
                "start_line": active["line"],
                "end_line": record["line"],
            }
        )
        active = None
    if active is not None:
        anomalies.append(
            {
                "kind": "unclosed-claude-only",
                "line": active["line"],
                "start": active["start"],
                "end": len(data),
            }
        )
    return {
        "spans": spans,
        "anomalies": anomalies,
    }


def parse_intent_line(
    content: bytes,
) -> Optional[tuple[datetime.date, str]]:
    match = INTENT_PATTERN.fullmatch(content)
    if match is None:
        return None
    try:
        intent_date = datetime.date.fromisoformat(
            match.group(1).decode("ascii")
        )
        note = match.group(2).decode("utf-8")
    except (UnicodeError, ValueError):
        return None
    if not (1 <= len(note) <= 120):
        return None
    if (
        note != note.strip(" \t\n\r\v\f")
        or "--" in note
        or "\x00" in note
    ):
        return None
    return intent_date, note


def valid_intent_line(content: bytes) -> bool:
    return parse_intent_line(content) is not None


def recognized_frontmatter_span(
    records: list[dict[str, Any]], *, kind: str
) -> Optional[tuple[int, int, int]]:
    if kind != "rule" or not records or records[0]["content"] != b"---":
        return None
    for index, record in enumerate(records[1:], start=1):
        if record["content"] == b"---":
            return 0, record["end"], index + 1
    return None


def control_header(
    records: list[dict[str, Any]],
    *,
    start_index: int,
    kind: str,
) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
    protected: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    index = start_index
    previous_intent_date: Optional[datetime.date] = None
    if kind == "covenant":
        if index >= len(records) or records[index]["content"] != COVENANT_CONTROL:
            errors.append({"kind": "invalid-covenant-control"})
            return protected, index, errors
        record = records[index]
        protected.append(
            {
                "kind": "covenant-control",
                "start": record["start"],
                "end": record["end"],
            }
        )
        index += 1
    while index < len(records):
        parsed_intent = parse_intent_line(records[index]["content"])
        if parsed_intent is None:
            break
        record = records[index]
        intent_date, _ = parsed_intent
        protected.append(
            {
                "kind": "intent",
                "start": record["start"],
                "end": record["end"],
            }
        )
        if (
            previous_intent_date is not None
            and intent_date < previous_intent_date
        ):
            errors.append(
                {
                    "kind": "intent-not-oldest-first",
                    "line": record["line"],
                    "date": intent_date.isoformat(),
                    "previous_date": previous_intent_date.isoformat(),
                }
            )
        previous_intent_date = intent_date
        index += 1
    if kind == "covenant" and not any(
        span["kind"] == "intent" for span in protected
    ):
        errors.append({"kind": "missing-covenant-intent"})
    return protected, index, errors


def control_comment_anomalies(
    data: bytes, protected: Iterable[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    recognized = {
        (int(span["start"]), int(span["end"]))
        for span in protected
        if span["kind"] in {"covenant-control", "intent", "claude-only"}
    }
    anomalies: list[dict[str, Any]] = []
    fence_open = False
    for record in byte_records(data):
        content = record["content"]
        if fence_line(content):
            fence_open = not fence_open
            continue
        if fence_open or not content.startswith(b"<!-- bridge:"):
            continue
        if any(
            record["start"] >= start and record["end"] <= end
            for start, end in recognized
        ):
            continue
        kind = (
            "misplaced-intent"
            if INTENT_PATTERN.fullmatch(content)
            else "unknown-control-comment"
        )
        anomalies.append(
            {
                "kind": kind,
                "line": record["line"],
                "start": record["start"],
                "end": record["end"],
            }
        )
    return anomalies


def inline_code_spans(
    content: bytes,
    *,
    excluded_spans: Iterable[tuple[int, int]] = (),
) -> list[tuple[int, int]]:
    """Return matched backtick spans without crossing excluded fenced spans."""

    spans: list[tuple[int, int]] = []
    excluded = sorted(excluded_spans)

    def containing(position: int) -> Optional[tuple[int, int]]:
        for start, end in excluded:
            if start <= position < end:
                return start, end
            if start > position:
                break
        return None

    index = 0
    while index < len(content):
        unavailable = containing(index)
        if unavailable is not None:
            index = unavailable[1]
            continue
        if content[index] != 0x60:
            index += 1
            continue
        run_start = index
        while index < len(content) and content[index] == 0x60:
            index += 1
        run_length = index - run_start
        search = index
        closing: Optional[tuple[int, int]] = None
        while search < len(content):
            unavailable = containing(search)
            if unavailable is not None:
                search = unavailable[1]
                continue
            if content[search] != 0x60:
                search += 1
                continue
            close_start = search
            while search < len(content) and content[search] == 0x60:
                search += 1
            if search - close_start == run_length:
                closing = (close_start, search)
                break
        if closing is None:
            index = run_start + run_length
            continue
        spans.append((run_start, closing[1]))
        index = closing[1]
    return spans


def fenced_code_spans(data: bytes) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    opened: Optional[int] = None
    for record in byte_records(data):
        if not fence_line(record["content"]):
            continue
        if opened is None:
            opened = record["start"]
        else:
            spans.append((opened, record["end"]))
            opened = None
    if opened is not None:
        spans.append((opened, len(data)))
    return spans


def active_imports(
    data: bytes,
    *,
    included_spans: Optional[Iterable[tuple[int, int]]] = None,
) -> list[dict[str, Any]]:
    """Locate active Claude imports outside inline and fenced code."""

    requested = (
        [(0, len(data))]
        if included_spans is None
        else sorted(included_spans)
    )
    allowed: list[tuple[int, int]] = []
    for start, end in requested:
        if not (0 <= start <= end <= len(data)):
            raise ValueError("active-import included span is out of range")
        if start == end:
            continue
        if allowed and start < allowed[-1][1]:
            raise ValueError("active-import included spans overlap")
        if allowed and start == allowed[-1][1]:
            allowed[-1] = (allowed[-1][0], end)
        else:
            allowed.append((start, end))

    projected = bytearray()
    projection_map: list[dict[str, int]] = []
    for source_start, source_end in allowed:
        projected_start = len(projected)
        projected.extend(data[source_start:source_end])
        projection_map.append(
            {
                "projected_start": projected_start,
                "projected_end": len(projected),
                "source_start": source_start,
                "source_end": source_end,
            }
        )
    projected_bytes = bytes(projected)
    fenced = fenced_code_spans(projected_bytes)
    code_spans = inline_code_spans(
        projected_bytes, excluded_spans=fenced
    )
    unavailable = fenced + code_spans
    records = byte_records(data)

    def source_span(start: int, end: int) -> Optional[tuple[int, int]]:
        for span in projection_map:
            if (
                start >= span["projected_start"]
                and end <= span["projected_end"]
            ):
                offset = start - span["projected_start"]
                return (
                    span["source_start"] + offset,
                    span["source_start"] + offset + (end - start),
                )
        return None

    def line_for(offset: int) -> int:
        for record in records:
            if record["start"] <= offset < record["end"]:
                return int(record["line"])
        return len(records) if records else 1

    results: list[dict[str, Any]] = []
    for match in ACTIVE_IMPORT_PATTERN.finditer(projected_bytes):
        projected_start = match.start()
        projected_end = match.end()
        mapped = source_span(projected_start, projected_end)
        if mapped is None:
            continue
        if any(
            projected_start >= start and projected_end <= end
            for start, end in unavailable
        ):
            continue
        absolute_start, absolute_end = mapped
        results.append(
            {
                "token": match.group(0).decode("ascii"),
                "line": line_for(absolute_start),
                "start": absolute_start,
                "end": absolute_end,
            }
        )
    return results


def validate_render_paths(paths: Any) -> list[str]:
    """Apply v4 checks that do not require general YAML or brace expansion."""

    errors: list[str] = []
    if paths is None:
        return errors
    if not isinstance(paths, list) or not paths:
        return ["paths-not-nonempty-list"]
    seen: set[str] = set()
    for index, pattern in enumerate(paths):
        prefix = f"paths[{index}]"
        if not isinstance(pattern, str):
            errors.append(f"{prefix}:not-string")
            continue
        try:
            pattern.encode("utf-8")
        except UnicodeEncodeError:
            errors.append(f"{prefix}:invalid-unicode-scalar")
        if not pattern.strip(" \t"):
            errors.append(f"{prefix}:ascii-whitespace-only")
        if pattern in seen:
            errors.append(f"{prefix}:duplicate")
        seen.add(pattern)
        if pattern in UNIVERSAL_PATH_PATTERNS:
            errors.append(f"{prefix}:universal-no-op")
        if pattern.startswith("/"):
            errors.append(f"{prefix}:leading-slash")
        if any(value in pattern for value in ("\x00", "\r", "\n", "`", "\\")):
            errors.append(f"{prefix}:forbidden-character")
        segments = pattern.split("/")
        if any(segment in {"", ".", ".."} for segment in segments):
            errors.append(f"{prefix}:invalid-segment")
        position = 0
        while True:
            opening = pattern.find("[", position)
            if opening < 0:
                break
            closing = pattern.find("]", opening + 1)
            if closing < 0:
                errors.append(f"{prefix}:unclosed-bracket")
                break
            position = closing + 1
    return errors


def render_preamble(paths: list[str]) -> bytes:
    errors = validate_render_paths(paths)
    if errors:
        raise ValueError("invalid v4 render paths: " + ", ".join(errors))
    rendered = ", ".join(f"`{pattern}`" for pattern in paths)
    return (PV2_PREFIX + rendered + PV2_SUFFIX + "\n\n").encode("utf-8")


def parse_preamble(data: bytes) -> dict[str, Any]:
    records = byte_records(data)
    if not records:
        return {"present": False, "valid": True, "paths": [], "end": 0}
    try:
        line = records[0]["content"].decode("utf-8")
    except UnicodeError:
        return {"present": False, "valid": False, "paths": [], "end": 0}
    if not line.startswith(PV2_PREFIX):
        return {"present": False, "valid": True, "paths": [], "end": 0}
    if not line.endswith(PV2_SUFFIX):
        return {"present": True, "valid": False, "paths": [], "end": 0}
    encoded = line[len(PV2_PREFIX) : -len(PV2_SUFFIX)]
    paths: list[str] = []
    index = 0
    while index < len(encoded):
        if encoded[index] != "`":
            return {"present": True, "valid": False, "paths": [], "end": 0}
        closing = encoded.find("`", index + 1)
        if closing < 0:
            return {"present": True, "valid": False, "paths": [], "end": 0}
        paths.append(encoded[index + 1 : closing])
        index = closing + 1
        if index == len(encoded):
            break
        if not encoded.startswith(", ", index):
            return {"present": True, "valid": False, "paths": [], "end": 0}
        index += 2
    if validate_render_paths(paths):
        return {"present": True, "valid": False, "paths": paths, "end": 0}
    if len(records) < 2 or records[1]["content"] != b"":
        return {"present": True, "valid": False, "paths": paths, "end": 0}
    return {
        "present": True,
        "valid": True,
        "paths": paths,
        "end": records[1]["end"],
    }


def render_agents_unit(
    data: bytes,
    *,
    kind: str,
    paths: Optional[list[str]],
) -> dict[str, Any]:
    """Render one v4 entry/rule/covenant unit plus a line origin map."""

    if kind not in {"entry", "rule", "covenant"}:
        raise ValueError(f"invalid agents unit kind: {kind}")
    if kind != "rule" and paths is not None:
        raise ValueError("only rule units accept paths")
    path_errors = validate_render_paths(paths)
    if path_errors:
        raise ValueError("invalid v4 render paths: " + ", ".join(path_errors))

    records = byte_records(data)
    protected: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if kind in {"entry", "rule"} and data.startswith(b"\xef\xbb\xbf"):
        errors.append(
            {
                "kind": "leading-utf8-bom",
                "line": 1,
                "start": 0,
                "end": 3,
            }
        )
    first_content_index = 0
    frontmatter = recognized_frontmatter_span(records, kind=kind)
    if frontmatter is not None:
        start, end, first_content_index = frontmatter
        protected.append(
            {"kind": "frontmatter", "start": start, "end": end}
        )
        if paths is None:
            errors.append({"kind": "frontmatter-without-validated-paths"})
    elif kind == "rule" and paths is not None:
        errors.append({"kind": "scoped-paths-without-frontmatter"})

    controls, first_content_index, control_errors = control_header(
        records, start_index=first_content_index, kind=kind
    )
    protected.extend(controls)
    errors.extend(control_errors)

    body_start = (
        records[first_content_index]["start"]
        if first_content_index < len(records)
        else len(data)
    )
    claude = inspect_claude_only(data[body_start:])
    for span in claude["spans"]:
        span["start"] += body_start
        span["end"] += body_start
        span["start_line"] += first_content_index
        span["end_line"] += first_content_index
    for anomaly in claude["anomalies"]:
        anomaly["start"] += body_start
        anomaly["end"] += body_start
        anomaly["line"] += first_content_index
    protected.extend(
        {
            "kind": "claude-only",
            "start": span["start"],
            "end": span["end"],
        }
        for span in claude["spans"]
    )
    errors.extend(claude["anomalies"])
    protected.sort(key=lambda span: (span["start"], span["end"]))
    errors.extend(control_comment_anomalies(data, protected))

    def overlaps_protected(record: Mapping[str, Any]) -> bool:
        return any(
            record["start"] < span["end"] and record["end"] > span["start"]
            for span in protected
        )

    shared_records = [
        record
        for record in records[first_content_index:]
        if not overlaps_protected(record)
    ]
    while shared_records and not shared_records[0]["content"].rstrip(b" \t"):
        record = shared_records.pop(0)
        protected.append(
            {
                "kind": "leading-blank",
                "start": record["start"],
                "end": record["end"],
            }
        )
    included = [(record["start"], record["end"]) for record in shared_records]
    imports = active_imports(data, included_spans=included)
    errors.extend(
        {
            "kind": "active-import",
            "token": item["token"],
            "line": item["line"],
            "start": item["start"],
            "end": item["end"],
        }
        for item in imports
    )

    output = bytearray()
    origin: list[dict[str, Any]] = []
    if paths:
        preamble = render_preamble(paths)
        output.extend(preamble)
        origin.append(
            {
                "kind": "generated-preamble",
                "render_start": 0,
                "render_end": len(preamble),
                "source_start": None,
                "source_end": None,
            }
        )
    for record in shared_records:
        rendered_line = record["content"].rstrip(b" \t") + b"\n"
        render_start = len(output)
        output.extend(rendered_line)
        origin.append(
            {
                "kind": "shared-line",
                "render_start": render_start,
                "render_end": len(output),
                "source_start": record["start"],
                "source_end": record["end"],
            }
        )
    rendered = normalize_n(bytes(output))
    if len(rendered) != len(output):
        while origin and origin[-1]["render_start"] >= len(rendered):
            origin.pop()
        if origin:
            origin[-1]["render_end"] = min(
                origin[-1]["render_end"], len(rendered)
            )
    protected.sort(key=lambda span: (span["start"], span["end"]))
    return {
        "contract": "agents-unit-render/v4",
        "kind": kind,
        "valid": not errors,
        "errors": errors,
        "paths": [] if paths is None else paths,
        "rendered": {
            "bytes": len(rendered),
            "sha256": hashlib.sha256(rendered).hexdigest(),
            "base64": base64.b64encode(rendered).decode("ascii"),
        },
        "origin_map": origin,
        "protected_spans": protected,
        "active_imports": imports,
    }


def check_agents_budget(data: bytes, budget: int) -> dict[str, Any]:
    if budget < 0:
        raise ValueError("budget must be a non-negative integer")
    size = len(data)
    return {
        "contract": "agents-budget/v1",
        "bytes": size,
        "budget": budget,
        "fits": budget > 0 and size <= budget,
        "disabled": budget == 0,
        "warning_threshold": (
            False if budget == 0 else size >= (7 * budget) // 8
        ),
        "remaining": budget - size,
    }


def is_subsequence(left: list[bytes], right: list[bytes]) -> bool:
    iterator = iter(right)
    return all(any(candidate == item for candidate in iterator) for item in left)


def byte_lines(data: bytes) -> list[bytes]:
    """Split only at LF and retain line endings for raw-byte honesty."""
    lines: list[bytes] = []
    start = 0
    for index, value in enumerate(data):
        if value == 0x0A:
            lines.append(data[start : index + 1])
            start = index + 1
    if start < len(data):
        lines.append(data[start:])
    return lines


def diff_shape(source: bytes, projection: bytes) -> str:
    """Classify a changed byte pair by the report specification."""
    if source == projection:
        return "equal"
    source_lines = byte_lines(source)
    projection_lines = byte_lines(projection)
    if is_subsequence(source_lines, projection_lines):
        return "additions-only"
    if is_subsequence(projection_lines, source_lines):
        return "deletions-only"
    return "both"


def read_bytes(path: Path, normalized: bool) -> bytes:
    data = path.read_bytes()
    return normalize_n(data) if normalized else data


def compare_files(left: Path, right: Path, normalized: bool) -> dict[str, Any]:
    source = read_bytes(left, normalized)
    projection = read_bytes(right, normalized)
    shape = diff_shape(source, projection)
    return {
        "equal": shape == "equal",
        "shape": shape,
        "normalization": "N" if normalized else "none",
        "source": str(left),
        "projection": str(right),
    }


def inspect_tree(root: Path) -> dict[str, Any]:
    """Enumerate a tree without following links or reparse points."""
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    root_stat = root.lstat()
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if root.is_symlink() or (
        reparse_flag
        and getattr(root_stat, "st_file_attributes", 0) & reparse_flag
    ):
        return {
            "safe": False,
            "root": str(root),
            "files": [],
            "special": [{"path": ".", "kind": "linked-root"}],
        }
    files: dict[str, Path] = {}
    special: list[dict[str, str]] = []
    folded: dict[str, str] = {}
    stack: list[tuple[Path, str]] = [(root, "")]

    while stack:
        directory, prefix = stack.pop()
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda item: os.fsencode(item.name))
        for entry in entries:
            relative = f"{prefix}/{entry.name}" if prefix else entry.name
            relative = relative.replace("\\", "/")
            folded_name = relative.casefold()
            prior = folded.get(folded_name)
            if prior is not None and prior != relative:
                special.append(
                    {
                        "path": relative,
                        "kind": "case-fold-collision",
                        "detail": prior,
                    }
                )
                continue
            folded[folded_name] = relative

            entry_stat = entry.stat(follow_symlinks=False)
            is_reparse = bool(
                reparse_flag
                and getattr(entry_stat, "st_file_attributes", 0) & reparse_flag
            )
            if entry.is_symlink():
                special.append({"path": relative, "kind": "symlink"})
            elif is_reparse:
                special.append({"path": relative, "kind": "reparse-point"})
            elif entry.is_dir(follow_symlinks=False):
                stack.append((Path(entry.path), relative))
            elif entry.is_file(follow_symlinks=False) and stat.S_ISREG(
                entry_stat.st_mode
            ):
                files[relative] = Path(entry.path)
            else:
                special.append({"path": relative, "kind": "special-file"})

    return {
        "safe": not special,
        "root": str(root),
        "files": sorted(files),
        "special": sorted(
            special,
            key=lambda item: (
                os.fsencode(item["path"]),
                os.fsencode(item["kind"]),
            ),
        ),
    }


def relative_files(root: Path) -> dict[str, Path]:
    inspection = inspect_tree(root)
    if not inspection["safe"]:
        raise ValueError(
            "unsafe tree entries: "
            + json.dumps(inspection["special"], ensure_ascii=False)
        )
    return {
        name: root.joinpath(*name.split("/"))
        for name in inspection["files"]
    }


def aggregate_shapes(shapes: Iterable[str]) -> str:
    changed = [shape for shape in shapes if shape != "equal"]
    if not changed:
        return "equal"
    if all(shape == "additions-only" for shape in changed):
        return "additions-only"
    if all(shape == "deletions-only" for shape in changed):
        return "deletions-only"
    return "both"


def compare_trees(master: Path, copy: Path) -> dict[str, Any]:
    """Compare only filesystem paths and bytes; Git modes are out of scope."""
    master_files = relative_files(master)
    copy_files = relative_files(copy)
    master_names = set(master_files)
    copy_names = set(copy_files)
    source_only = sorted(master_names - copy_names)
    projection_only = sorted(copy_names - master_names)
    changed: list[dict[str, str]] = []
    shapes: list[str] = []

    shapes.extend("deletions-only" for _ in source_only)
    shapes.extend("additions-only" for _ in projection_only)

    for name in sorted(master_names & copy_names):
        source = master_files[name].read_bytes()
        projection = copy_files[name].read_bytes()
        shape = diff_shape(source, projection)
        if shape != "equal":
            changed.append({"path": name, "shape": shape})
            shapes.append(shape)

    shape = aggregate_shapes(shapes)
    return {
        "comparison": "filesystem-paths-and-bytes/v1",
        "mode_checked": False,
        "equal": shape == "equal",
        "shape": shape,
        "source_only": source_only,
        "projection_only": projection_only,
        "changed": changed,
        "master": str(master),
        "copy": str(copy),
    }


def git_run(
    repo: Path,
    arguments: list[str],
    *,
    allow_failure: bool = False,
    input_data: Optional[bytes] = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run a read-only Git command and retain byte-exact stdout."""
    process = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        input=input_data,
        check=False,
    )
    if process.returncode and not allow_failure:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            f"git {' '.join(arguments)} failed"
            + (f": {detail}" if detail else "")
        )
    return process


def resolve_git_root(repo: Path) -> Path:
    invoked = repo.resolve()
    result = git_run(invoked, ["rev-parse", "--show-toplevel"])
    discovered = Path(
        result.stdout.decode("utf-8", errors="strict").strip()
    ).resolve()
    if os.path.normcase(str(invoked)) != os.path.normcase(str(discovered)):
        raise ValueError(
            f"repository argument is not the worktree root: {repo}"
        )
    return discovered


def resolve_commit_revision(repo: Path, revision: str) -> str:
    """Resolve one revision to a commit and reject tree/blob selectors."""

    result = git_run(
        repo,
        [
            "rev-parse",
            "--verify",
            "--end-of-options",
            f"{revision}^{{commit}}",
        ],
        allow_failure=True,
    )
    if result.returncode:
        raise ValueError(f"revision must resolve to a commit: {revision}")
    resolved = result.stdout.decode("ascii", errors="strict").strip()
    if re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", resolved) is None:
        raise ValueError(
            f"revision resolved to an invalid commit object id: {revision}"
        )
    return resolved


def normalize_unit_root(value: str) -> str:
    """Validate a repository-relative POSIX unit root."""
    if not value or "\\" in value or value.startswith("./"):
        raise ValueError(
            "unit root must be a non-empty canonical repo-relative POSIX path"
        )
    path = PurePosixPath(value)
    if path.is_absolute() or value == "." or any(
        part in {"", ".", ".."} for part in path.parts
    ) or path.as_posix() != value:
        raise ValueError(
            "unit root must be a non-empty canonical repo-relative POSIX path"
        )
    return path.as_posix()


def normalize_entry_path(value: str) -> str:
    """Validate a canonical POSIX path relative to one unit root."""
    if not value or "\\" in value or value.startswith("./"):
        raise ValueError(
            "entry path must be a non-empty canonical unit-relative POSIX path"
        )
    path = PurePosixPath(value)
    if path.is_absolute() or value == "." or any(
        part in {"", ".", ".."} for part in path.parts
    ) or path.as_posix() != value:
        raise ValueError(
            "entry path must be a non-empty canonical unit-relative POSIX path"
        )
    return path.as_posix()


def git_pathspec(unit_root: str) -> str:
    return f":(literal){unit_root}"


def decode_git_path(value: bytes) -> str:
    try:
        path = value.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Git path is not valid UTF-8 and cannot enter the v1 manifest"
        ) from error
    if "\x00" in path:
        raise ValueError("Git path contains NUL")
    return path


def relative_unit_path(repo_path: str, unit_root: str) -> str:
    if repo_path == unit_root:
        return "."
    prefix = unit_root + "/"
    if not repo_path.startswith(prefix):
        raise ValueError(
            f"Git returned a path outside unit {unit_root}: {repo_path}"
        )
    relative = repo_path[len(prefix) :]
    if not relative:
        raise ValueError(f"empty relative path below unit {unit_root}")
    return relative


def parse_index_entries(repo: Path, unit_root: str) -> list[dict[str, str]]:
    result = git_run(
        repo,
        ["ls-files", "--stage", "-z", "--", git_pathspec(unit_root)],
    )
    entries: list[dict[str, str]] = []
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, oid, stage = metadata.decode("ascii").split(" ")
        except (ValueError, UnicodeDecodeError) as error:
            raise ValueError("malformed git ls-files --stage record") from error
        repo_path = decode_git_path(raw_path)
        relative_unit_path(repo_path, unit_root)
        entries.append(
            {
                "repo_path": repo_path,
                "mode": mode,
                "oid": oid,
                "stage": stage,
            }
        )
    return entries


def parse_tree_entries(
    repo: Path, unit_root: str, revision: str
) -> list[dict[str, str]]:
    result = git_run(
        repo,
        [
            "ls-tree",
            "-r",
            "-z",
            "--full-tree",
            revision,
            "--",
            git_pathspec(unit_root),
        ],
    )
    entries: list[dict[str, str]] = []
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, oid = metadata.decode("ascii").split(" ")
        except (ValueError, UnicodeDecodeError) as error:
            raise ValueError("malformed git ls-tree record") from error
        repo_path = decode_git_path(raw_path)
        relative_unit_path(repo_path, unit_root)
        entries.append(
            {
                "repo_path": repo_path,
                "mode": mode,
                "oid": oid,
                "object_type": object_type,
            }
        )
    return entries


def untracked_paths(repo: Path, unit_root: str) -> list[str]:
    result = git_run(
        repo,
        [
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            git_pathspec(unit_root),
        ],
    )
    paths = [
        decode_git_path(record)
        for record in result.stdout.split(b"\0")
        if record
    ]
    for path in paths:
        relative_unit_path(path, unit_root)
    return paths


def core_filemode(repo: Path) -> bool:
    result = git_run(
        repo, ["config", "--bool", "--get", "core.filemode"], allow_failure=True
    )
    if result.returncode == 1:
        return os.name != "nt"
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            "cannot read core.filemode" + (f": {detail}" if detail else "")
        )
    value = result.stdout.decode("ascii", errors="strict").strip()
    if value not in {"true", "false"}:
        raise ValueError(f"unexpected core.filemode value: {value}")
    return value == "true"


def is_reparse(path_stat: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(
        reparse_flag
        and getattr(path_stat, "st_file_attributes", 0) & reparse_flag
    )


def classify_path(repo: Path, repo_path: str) -> tuple[str, Optional[os.stat_result]]:
    """Classify a worktree path while rejecting linked parent traversal."""
    candidate = repo
    parts = PurePosixPath(repo_path).parts
    if os.name == "nt" and any("\\" in part for part in parts):
        return "unrepresentable-git-path", None
    for index, part in enumerate(parts):
        candidate = candidate / part
        try:
            candidate_stat = candidate.lstat()
        except FileNotFoundError:
            return "missing", None
        if candidate.is_symlink():
            return (
                "symlink" if index == len(parts) - 1 else "linked-parent",
                candidate_stat,
            )
        if is_reparse(candidate_stat):
            return (
                "reparse-point"
                if index == len(parts) - 1
                else "linked-parent",
                candidate_stat,
            )
        if index < len(parts) - 1 and not stat.S_ISDIR(candidate_stat.st_mode):
            return "non-directory-parent", candidate_stat

    resolved = candidate.resolve()
    try:
        common = os.path.commonpath([str(repo), str(resolved)])
    except ValueError:
        return "path-escape", candidate_stat
    if os.path.normcase(common) != os.path.normcase(str(repo)):
        return "path-escape", candidate_stat
    if stat.S_ISREG(candidate_stat.st_mode):
        return "regular", candidate_stat
    if stat.S_ISDIR(candidate_stat.st_mode):
        return "directory", candidate_stat
    return "special-file", candidate_stat


def sha256_evidence(data: bytes, source: str, **extra: Any) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "source": source,
    }
    evidence.update(extra)
    return evidence


def filesystem_git_mode(path_stat: os.stat_result) -> str:
    return "100755" if path_stat.st_mode & 0o111 else "100644"


def append_blocker(
    blockers: list[dict[str, str]], token: str, path: str, detail: str
) -> None:
    blocker = {"token": token, "path": path, "detail": detail}
    if blocker not in blockers:
        blockers.append(blocker)


def mode_for_current_file(
    *,
    path_stat: os.stat_result,
    tracked: bool,
    index_mode: Optional[str],
    head_mode: Optional[str],
    probe_reliable: bool,
    blockers: list[dict[str, str]],
    relative: str,
    require_executable: bool,
) -> tuple[str, dict[str, Any]]:
    """Resolve effective Git mode and expose each evidence layer."""
    filesystem_mode = (
        filesystem_git_mode(path_stat) if probe_reliable else None
    )
    if tracked:
        if index_mode not in REGULAR_GIT_MODES:
            raise ValueError(f"unsupported regular index mode: {index_mode}")
        effective = filesystem_mode if filesystem_mode is not None else index_mode
        if (
            require_executable
            and effective != "100755"
            and not probe_reliable
        ):
            append_blocker(
                blockers,
                "mode-limited",
                relative,
                "explicit executable intent cannot be realized because "
                "worktree mode changes are unavailable",
            )
        return effective, {
            "head": head_mode or "absent",
            "index": index_mode,
            "worktree": filesystem_mode or "unavailable",
            "effective_source": (
                "posix-filesystem-exec"
                if filesystem_mode is not None
                else "git-index"
            ),
            "staged_change": head_mode is not None and head_mode != index_mode,
            "unstaged_change": (
                filesystem_mode != index_mode
                if filesystem_mode is not None
                else "unobservable"
            ),
            "prospective": False,
            "explicit_executable_required": require_executable,
        }

    if filesystem_mode is None:
        if require_executable:
            append_blocker(
                blockers,
                "mode-limited",
                relative,
                "explicit executable intent requires 100755, but this host "
                "can establish only the prospective untracked default 100644",
            )
        return "100644", {
            "head": "absent",
            "index": "absent",
            "worktree": "unavailable",
            "effective_source": "platform-untracked-default",
            "staged_change": False,
            "unstaged_change": "unobservable",
            "prospective": True,
            "explicit_executable_required": require_executable,
        }
    return filesystem_mode, {
        "head": "absent",
        "index": "absent",
        "worktree": filesystem_mode,
        "effective_source": "posix-filesystem-exec",
        "staged_change": False,
        "unstaged_change": False,
        "prospective": True,
        "explicit_executable_required": require_executable,
    }


def detect_casefold_collisions(
    paths: Iterable[str], blockers: list[dict[str, str]]
) -> None:
    folded: dict[str, str] = {}
    for path in sorted(paths, key=lambda item: item.encode("utf-8")):
        prior = folded.get(path.casefold())
        if prior is not None and prior != path:
            append_blocker(
                blockers,
                "unsafe-tree-entry",
                path,
                f"case-fold-collision with {prior}",
            )
        else:
            folded[path.casefold()] = path


def detect_unit_casefold_collisions(
    current_paths: Iterable[str],
    tracked_deletions: Iterable[str],
    blockers: list[dict[str, str]],
) -> None:
    """Apply the unit-wide gate to current and deleted tracked path names."""
    domain = set(current_paths)
    domain.update(tracked_deletions)
    detect_casefold_collisions(domain, blockers)


def manifest_from_revision(
    repo: Path,
    unit_root: str,
    revision_input: str,
    resolved_commit: str,
) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    entries: list[dict[str, Any]] = []
    tree_entries = parse_tree_entries(repo, unit_root, resolved_commit)

    for item in tree_entries:
        relative = relative_unit_path(item["repo_path"], unit_root)
        mode = item["mode"]
        object_type = item["object_type"]
        if mode not in REGULAR_GIT_MODES or object_type != "blob":
            kind = (
                "git-symlink"
                if mode == "120000"
                else "gitlink"
                if mode == "160000"
                else f"git-{object_type}-{mode}"
            )
            append_blocker(
                blockers, "unsafe-tree-entry", relative, kind
            )
            entries.append(
                {
                    "path": relative,
                    "repo_path": item["repo_path"],
                    "type": kind,
                    "bytes": None,
                    "mode": mode,
                    "mode_evidence": {
                        "tree": resolved_commit,
                        "tree_mode": mode,
                        "effective_source": "git-tree",
                    },
                    "tracked": True,
                }
            )
            continue

        blob = git_run(repo, ["cat-file", "blob", item["oid"]]).stdout
        entries.append(
            {
                "path": relative,
                "repo_path": item["repo_path"],
                "type": "regular",
                "bytes": sha256_evidence(
                    blob,
                    "git-blob",
                    blob_oid=item["oid"],
                    revision=resolved_commit,
                ),
                "mode": mode,
                "mode_evidence": {
                    "tree": resolved_commit,
                    "tree_mode": mode,
                    "effective_source": "git-tree",
                },
                "tracked": True,
            }
        )

    detect_unit_casefold_collisions(
        (entry["path"] for entry in entries), (), blockers
    )
    entries.sort(key=lambda item: item["path"].encode("utf-8"))
    blockers.sort(
        key=lambda item: (
            item["path"].encode("utf-8"),
            item["token"].encode("utf-8"),
            item["detail"].encode("utf-8"),
        )
    )
    return {
        "contract": "git-tree-manifest/v1",
        "repository": str(repo),
        "unit": unit_root,
        "snapshot": "revision",
        "revision": revision_input,
        "resolved_commit": resolved_commit,
        "include_untracked": False,
        "core_filemode": None,
        "worktree_mode_probe": "not-applicable",
        "worktree_mode_write": "not-applicable",
        "required_executable": [],
        "safe": not blockers,
        "mode_limited": any(
            blocker["token"] == "mode-limited" for blocker in blockers
        ),
        "entries": entries,
        "tracked_deletions": [],
        "blockers": blockers,
    }


def manifest_from_worktree(
    repo: Path,
    unit_root: str,
    include_untracked: bool,
    required_executable: set[str],
) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    entries: list[dict[str, Any]] = []
    tracked_deletions: list[str] = []
    filemode = core_filemode(repo)
    probe_reliable = os.name != "nt" and filemode

    root_kind, _ = classify_path(repo, unit_root)
    if root_kind not in {"missing", "directory"}:
        append_blocker(
            blockers, "unsafe-tree-entry", ".", f"unit-root-{root_kind}"
        )

    index_entries = parse_index_entries(repo, unit_root)
    head_result = git_run(
        repo, ["rev-parse", "--verify", "HEAD^{tree}"], allow_failure=True
    )
    head_entries = (
        parse_tree_entries(repo, unit_root, "HEAD")
        if head_result.returncode == 0
        else []
    )
    head_modes = {
        item["repo_path"]: item["mode"] for item in head_entries
    }

    seen_index: set[str] = set()
    for item in index_entries:
        relative = relative_unit_path(item["repo_path"], unit_root)
        if item["stage"] != "0":
            append_blocker(
                blockers,
                "unsafe-tree-entry",
                relative,
                f"unmerged-index-stage-{item['stage']}",
            )
            continue
        if item["repo_path"] in seen_index:
            append_blocker(
                blockers,
                "unsafe-tree-entry",
                relative,
                "duplicate-index-entry",
            )
            continue
        seen_index.add(item["repo_path"])

        if item["mode"] not in REGULAR_GIT_MODES:
            kind = (
                "git-symlink"
                if item["mode"] == "120000"
                else "gitlink"
                if item["mode"] == "160000"
                else f"git-mode-{item['mode']}"
            )
            append_blocker(
                blockers, "unsafe-tree-entry", relative, kind
            )
            entries.append(
                {
                    "path": relative,
                    "repo_path": item["repo_path"],
                    "type": kind,
                    "bytes": None,
                    "mode": item["mode"],
                    "mode_evidence": {
                        "head": head_modes.get(item["repo_path"], "absent"),
                        "index": item["mode"],
                        "worktree": "not-read",
                        "effective_source": "git-index",
                    },
                    "tracked": True,
                }
            )
            continue

        path_kind, path_stat = classify_path(repo, item["repo_path"])
        if path_kind == "missing":
            tracked_deletions.append(relative)
            continue
        if path_kind != "regular" or path_stat is None:
            append_blocker(
                blockers,
                "unsafe-tree-entry",
                relative,
                f"worktree-{path_kind}",
            )
            continue

        worktree_path = repo.joinpath(*PurePosixPath(item["repo_path"]).parts)
        data = worktree_path.read_bytes()
        mode, mode_evidence = mode_for_current_file(
            path_stat=path_stat,
            tracked=True,
            index_mode=item["mode"],
            head_mode=head_modes.get(item["repo_path"]),
            probe_reliable=probe_reliable,
            blockers=blockers,
            relative=relative,
            require_executable=relative in required_executable,
        )
        entries.append(
            {
                "path": relative,
                "repo_path": item["repo_path"],
                "type": "regular",
                "bytes": sha256_evidence(
                    data,
                    "worktree",
                    index_oid=item["oid"],
                ),
                "mode": mode,
                "mode_evidence": mode_evidence,
                "tracked": True,
            }
        )

    for repo_path in head_modes:
        if repo_path not in seen_index:
            tracked_deletions.append(relative_unit_path(repo_path, unit_root))

    if include_untracked:
        for repo_path in untracked_paths(repo, unit_root):
            relative = relative_unit_path(repo_path, unit_root)
            path_kind, path_stat = classify_path(repo, repo_path)
            if path_kind != "regular" or path_stat is None:
                append_blocker(
                    blockers,
                    "unsafe-tree-entry",
                    relative,
                    f"untracked-{path_kind}",
                )
                continue
            worktree_path = repo.joinpath(*PurePosixPath(repo_path).parts)
            data = worktree_path.read_bytes()
            mode, mode_evidence = mode_for_current_file(
                path_stat=path_stat,
                tracked=False,
                index_mode=None,
                head_mode=None,
                probe_reliable=probe_reliable,
                blockers=blockers,
                relative=relative,
                require_executable=relative in required_executable,
            )
            entries.append(
                {
                    "path": relative,
                    "repo_path": repo_path,
                    "type": "regular",
                    "bytes": sha256_evidence(data, "untracked-worktree"),
                    "mode": mode,
                    "mode_evidence": mode_evidence,
                    "tracked": False,
                }
            )

    present_paths = {entry["path"] for entry in entries}
    if not probe_reliable:
        for relative in required_executable - present_paths:
            append_blocker(
                blockers,
                "mode-limited",
                relative,
                "explicit executable intent requires creating 100755, but "
                "this host can establish only the prospective default 100644",
            )

    detect_unit_casefold_collisions(
        (entry["path"] for entry in entries), tracked_deletions, blockers
    )
    entries.sort(key=lambda item: item["path"].encode("utf-8"))
    tracked_deletions.sort(key=lambda item: item.encode("utf-8"))
    blockers.sort(
        key=lambda item: (
            item["path"].encode("utf-8"),
            item["token"].encode("utf-8"),
            item["detail"].encode("utf-8"),
        )
    )
    return {
        "contract": "git-tree-manifest/v1",
        "repository": str(repo),
        "unit": unit_root,
        "snapshot": "worktree",
        "revision": None,
        "include_untracked": include_untracked,
        "core_filemode": filemode,
        "worktree_mode_probe": (
            "posix-executable-bits"
            if probe_reliable
            else "index-for-tracked; prospective-100644-for-untracked"
        ),
        "worktree_mode_write": (
            "posix-executable-bits" if probe_reliable else "unavailable"
        ),
        "required_executable": sorted(
            required_executable, key=lambda item: item.encode("utf-8")
        ),
        "safe": not blockers,
        "mode_limited": any(
            blocker["token"] == "mode-limited" for blocker in blockers
        ),
        "entries": entries,
        "tracked_deletions": tracked_deletions,
        "blockers": blockers,
    }


def git_manifest(
    repo: Path,
    unit_root_value: str,
    *,
    revision: Optional[str],
    include_untracked: bool,
    required_executable: Iterable[str] = (),
) -> dict[str, Any]:
    root = resolve_git_root(repo)
    unit_root = normalize_unit_root(unit_root_value)
    executable_paths = {
        normalize_entry_path(path) for path in required_executable
    }
    if revision is not None and include_untracked:
        raise ValueError("--include-untracked is valid only for a worktree manifest")
    if revision is not None and executable_paths:
        raise ValueError(
            "--require-executable is valid only for a worktree manifest"
        )
    if revision is not None and (
        revision.startswith("-") or "\x00" in revision
    ):
        raise ValueError("revision must not begin with '-' or contain NUL")
    if revision is not None:
        resolved_commit = resolve_commit_revision(root, revision)
        return manifest_from_revision(
            root,
            unit_root,
            revision,
            resolved_commit,
        )
    return manifest_from_worktree(
        root, unit_root, include_untracked, executable_paths
    )


def target_can_realize_mode(
    target_manifest: dict[str, Any],
    target_entry: Optional[dict[str, Any]],
    required_mode: str,
) -> bool:
    if target_entry is not None and target_entry.get("mode") == required_mode:
        return True
    if target_manifest.get("worktree_mode_write") == "posix-executable-bits":
        return True
    if target_entry is None:
        return required_mode == "100644"
    if (
        not target_entry.get("tracked", True)
        and target_entry.get("mode_evidence", {}).get("effective_source")
        == "platform-untracked-default"
    ):
        return required_mode == "100644"
    return False


def compare_git_manifests(
    source: dict[str, Any],
    projection: dict[str, Any],
    *,
    direction: str = "observe",
) -> dict[str, Any]:
    if direction not in GIT_TREE_DIRECTIONS:
        raise ValueError(f"unsupported Git-tree comparison direction: {direction}")
    if direction != "observe" and (
        source["snapshot"] != "worktree"
        or projection["snapshot"] != "worktree"
    ):
        raise ValueError(
            "a write direction is valid only between worktree manifests"
        )
    source_entries = {entry["path"]: entry for entry in source["entries"]}
    projection_entries = {
        entry["path"]: entry for entry in projection["entries"]
    }
    source_names = set(source_entries)
    projection_names = set(projection_entries)
    source_only = sorted(
        source_names - projection_names, key=lambda item: item.encode("utf-8")
    )
    projection_only = sorted(
        projection_names - source_names,
        key=lambda item: item.encode("utf-8"),
    )
    changed: list[dict[str, Any]] = []

    for path in sorted(
        source_names & projection_names, key=lambda item: item.encode("utf-8")
    ):
        left = source_entries[path]
        right = projection_entries[path]
        type_changed = left["type"] != right["type"]
        left_bytes = (
            left["bytes"]["sha256"] if left["bytes"] is not None else None
        )
        right_bytes = (
            right["bytes"]["sha256"] if right["bytes"] is not None else None
        )
        bytes_changed = left_bytes != right_bytes
        mode_changed = left["mode"] != right["mode"]
        if not (type_changed or bytes_changed or mode_changed):
            continue
        if type_changed:
            kind = "type"
        elif bytes_changed and mode_changed:
            kind = "bytes-and-mode"
        elif bytes_changed:
            kind = "bytes-only"
        else:
            kind = "mode-only"
        changed.append(
            {
                "path": path,
                "kind": kind,
                "source": {
                    "type": left["type"],
                    "bytes_sha256": left_bytes,
                    "mode": left["mode"],
                },
                "projection": {
                    "type": right["type"],
                    "bytes_sha256": right_bytes,
                    "mode": right["mode"],
                },
            }
        )

    blockers = [
        {"side": "source", **item} for item in source["blockers"]
    ] + [
        {"side": "projection", **item}
        for item in projection["blockers"]
    ]
    if direction != "observe":
        if direction == "source-to-projection":
            authority_entries = source_entries
            authority_manifest = source
            target_entries = projection_entries
            target_manifest = projection
            target_side = "projection"
        else:
            authority_entries = projection_entries
            authority_manifest = projection
            target_entries = source_entries
            target_manifest = source
            target_side = "source"

        executable_requirements = set(
            authority_manifest.get("required_executable", [])
        )
        for path in sorted(
            authority_entries, key=lambda item: item.encode("utf-8")
        ):
            authority_entry = authority_entries[path]
            required_mode = (
                "100755"
                if path in executable_requirements
                else authority_entry.get("mode")
            )
            if (
                authority_entry.get("type") != "regular"
                or required_mode not in REGULAR_GIT_MODES
            ):
                continue
            target_entry = target_entries.get(path)
            if target_entry is not None and target_entry.get("type") != "regular":
                continue
            if target_can_realize_mode(
                target_manifest, target_entry, required_mode
            ):
                continue
            blocker = {
                "side": target_side,
                "token": "mode-limited",
                "path": path,
                "detail": (
                    f"{direction} requires target mode {required_mode}, but "
                    "this host cannot realize that mode without changing "
                    "the Git index"
                ),
            }
            if blocker not in blockers:
                blockers.append(blocker)
    blockers.sort(
        key=lambda item: (
            item["side"].encode("utf-8"),
            item["path"].encode("utf-8"),
            item["token"].encode("utf-8"),
            item["detail"].encode("utf-8"),
        )
    )
    comparable = source["safe"] and projection["safe"] and not blockers
    equal = (
        comparable
        and not source_only
        and not projection_only
        and not changed
    )
    return {
        "contract": "git-tree-comparison/v1",
        "direction": direction,
        "identity_fields": ["path", "type", "bytes.sha256", "mode"],
        "comparable": comparable,
        "mode_limited": any(
            blocker["token"] == "mode-limited" for blocker in blockers
        ),
        "equal": equal,
        "source_only": source_only,
        "projection_only": projection_only,
        "changed": changed,
        "blockers": blockers,
        "source_manifest": source,
        "projection_manifest": projection,
    }


def compare_git_trees(
    repo: Path,
    source_unit: str,
    projection_unit: str,
    *,
    revision: Optional[str],
    include_untracked: bool,
    direction: str = "observe",
    required_executable: Iterable[str] = (),
) -> dict[str, Any]:
    source = git_manifest(
        repo,
        source_unit,
        revision=revision,
        include_untracked=include_untracked,
        required_executable=required_executable,
    )
    projection = git_manifest(
        repo,
        projection_unit,
        revision=revision,
        include_untracked=include_untracked,
        required_executable=required_executable,
    )
    return compare_git_manifests(
        source, projection, direction=direction
    )


def normalized_text(path: Path) -> list[str]:
    return normalize_n(path.read_bytes()).decode("utf-8").splitlines()


def header_value(lines: list[str], key: str) -> Optional[str]:
    prefix = f"- {key}:"
    headings = [
        index for index, line in enumerate(lines) if line.startswith("## ")
    ]
    limit = headings[0] if headings else len(lines)
    matches = [
        line[len(prefix) :].strip()
        for line in lines[:limit]
        if line.startswith(prefix)
    ]
    if len(matches) > 1:
        raise ValueError(f"duplicate header: - {key}:")
    return matches[0] if matches else None


def validate_report_document(
    lines: list[str], *, expectation: bool
) -> dict[str, str]:
    """Validate the closed report/v5 or expectation document skeleton."""

    heading_indexes = [
        index for index, line in enumerate(lines) if line.startswith("## ")
    ]
    if not heading_indexes:
        raise ValueError("report document has no level-two sections")
    header_lines = [
        line for line in lines[: heading_indexes[0]] if line != ""
    ]
    keys = (
        (
            "expectation",
            "scan root",
            "scope excludes",
            "activation profile",
            "onboarding",
        )
        if expectation
        else (
            "project",
            "scan root",
            "scope excludes",
            "date",
            "spec",
            "scan surfaces",
            "onboarding",
        )
    )
    if expectation:
        metadata = header_lines
    else:
        if not header_lines or header_lines[0] != "# Bridge Sentinel Report":
            raise ValueError(
                "produced report must start with '# Bridge Sentinel Report'"
            )
        metadata = header_lines[1:]
    if len(metadata) != len(keys):
        raise ValueError("report header has missing or unexpected fields")
    fields: dict[str, str] = {}
    for line, key in zip(metadata, keys):
        prefix = f"- {key}: "
        if not line.startswith(prefix):
            raise ValueError(
                f"report header expected '- {key}: <value>'"
            )
        value = line[len(prefix) :]
        if not value or value != value.strip(" \t"):
            raise ValueError(f"report header {key} has an invalid value")
        fields[key] = value

    headings = [lines[index][3:] for index in heading_indexes]
    required_headings = (
        ["Findings", "Observations"]
        if expectation
        else [
            "Findings",
            "Observations",
            "Evidence and notes",
            "Local environment notes",
        ]
    )
    if headings != required_headings:
        raise ValueError(
            "report sections must be exactly: "
            + ", ".join(required_headings)
        )

    version_key = "expectation" if expectation else "spec"
    if fields[version_key] != REPORT_SPEC:
        raise ValueError(
            f"report document expected {version_key}: {REPORT_SPEC}"
        )
    if fields["onboarding"] not in {
        "onboarded",
        "not-onboarded",
        "blocked",
    }:
        raise ValueError("report onboarding value is invalid")
    if not expectation:
        if fields["scan surfaces"] != "agents-md, hooks, skills":
            raise ValueError("produced report scan surfaces are invalid")
        try:
            parsed_date = datetime.date.fromisoformat(fields["date"])
        except ValueError as error:
            raise ValueError("produced report date is invalid") from error
        if parsed_date.isoformat() != fields["date"]:
            raise ValueError("produced report date is not canonical")
    return fields


def section_lines(lines: list[str], heading: str) -> list[str]:
    marker = f"## {heading}"
    try:
        start = lines.index(marker) + 1
    except ValueError as error:
        raise ValueError(f"missing section: {marker}") from error
    result: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        result.append(line)
    return result


def parse_findings(lines: list[str]) -> tuple[str, list[tuple[str, ...]]]:
    content = [line for line in section_lines(lines, "Findings") if line]
    if len(content) < 2:
        raise ValueError("Findings must contain a header and separator")
    header = content[0]
    if header != FINDINGS_HEADER:
        raise ValueError("Findings header is malformed")
    if content[1] != FINDINGS_SEPARATOR:
        raise ValueError("Findings separator is malformed")

    rows: list[tuple[str, ...]] = []
    for line in content[2:]:
        if not line.startswith("|") or not line.endswith("|"):
            raise ValueError(f"malformed Findings row: {line}")
        raw_cells = line.split("|")[1:-1]
        if len(raw_cells) != 7:
            raise ValueError(f"wrong Findings cell count: {line}")
        parsed: list[str] = []
        for raw_cell in raw_cells:
            if not raw_cell.startswith(" ") or not raw_cell.endswith(" "):
                raise ValueError(
                    f"Findings row lacks exact cell padding: {line}"
                )
            cell = raw_cell[1:-1]
            if (
                not cell
                or cell != cell.strip(" \t")
                or "\t" in cell
            ):
                raise ValueError(
                    f"Findings row has an invalid cell: {line}"
                )
            parsed.append(cell)
        rows.append(tuple(parsed))
    return header, sorted(rows)


def parse_observations(lines: list[str]) -> list[str]:
    section = section_lines(lines, "Observations")
    content = [line for line in section if line]
    if not content:
        raise ValueError("Observations must contain at least '- (none)'")
    if any(not line.startswith("- ") for line in content):
        raise ValueError(
            "Observations may contain only observation list items"
        )
    if content == ["- (none)"]:
        return []
    if "- (none)" in content:
        raise ValueError("Observations cannot mix '- (none)' with tokens")
    for line in content:
        match = re.fullmatch(
            r"- ([a-z0-9][a-z0-9-]*): (\S(?:.*\S)?)",
            line,
        )
        if match is None:
            raise ValueError(f"malformed observation line: {line}")
    return sorted(content)


def validate_activation_profile(path: Path) -> dict[str, Any]:
    """Validate the closed report/v5 fixture activation profile."""

    try:
        path_stat = path.lstat()
    except OSError as error:
        raise ValueError(
            f"cannot inspect activation profile {path}: {error}"
        ) from error
    if (
        not stat.S_ISREG(path_stat.st_mode)
        or path.is_symlink()
        or is_reparse(path_stat)
    ):
        raise ValueError(
            f"activation profile must be a safe regular file: {path}"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(
            f"cannot read activation profile {path}: {error}"
        ) from error
    required = {
        "version",
        "root_markers",
        "fallback_filenames",
        "project_doc_max_bytes",
        "budget_source",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(
            "activation profile must contain exactly version, root_markers, "
            "fallback_filenames, project_doc_max_bytes, and budget_source"
        )
    if value["version"] != ACTIVATION_PROFILE_SPEC:
        raise ValueError(
            f"activation profile expected version {ACTIVATION_PROFILE_SPEC}"
        )
    for field in ("root_markers", "fallback_filenames"):
        items = value[field]
        if items is None:
            continue
        if not isinstance(items, list) or not all(
            isinstance(item, str) for item in items
        ):
            raise ValueError(
                f"activation profile {field} must be a string array or null"
            )
    budget = value["project_doc_max_bytes"]
    if budget is not None and (
        isinstance(budget, bool)
        or not isinstance(budget, int)
        or budget < 0
    ):
        raise ValueError(
            "activation profile project_doc_max_bytes must be a "
            "non-negative integer or null"
        )
    if value["budget_source"] not in {
        "resolved",
        "documented-default",
    }:
        raise ValueError(
            "activation profile budget_source must be resolved or "
            "documented-default"
        )
    return {
        "contract": ACTIVATION_PROFILE_SPEC,
        "path": str(path),
        "profile": value,
    }


def expectation_activation_profile(
    expected_path: Path, expected_lines: list[str]
) -> dict[str, Any]:
    raw = header_value(expected_lines, "activation profile")
    if raw is None:
        raise ValueError("expectation is missing - activation profile:")
    if raw == "environment-dependent":
        return {
            "mode": "environment-dependent",
            "filtered_observations": sorted(
                LIVE_ACTIVATION_OBSERVATIONS | CAPABILITY_OBSERVATIONS
            ),
        }
    if not raw or raw == "." or "\\" in raw:
        raise ValueError(
            "activation profile path must be non-empty and use '/' separators"
        )
    relative = PurePosixPath(raw)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise ValueError(
            "activation profile must be a contained relative path"
        )
    base = expected_path.parent.resolve()
    profile_path = base.joinpath(*relative.parts)
    profile_kind, _ = classify_path(base, raw)
    if profile_kind != "regular":
        raise ValueError(
            "activation profile must be a contained safe regular file "
            f"without linked parents: {raw} ({profile_kind})"
        )
    try:
        resolved = profile_path.resolve(strict=True)
        resolved.relative_to(base)
    except (OSError, ValueError) as error:
        raise ValueError(
            f"activation profile escapes expectation directory: {raw}"
        ) from error
    validated = validate_activation_profile(profile_path)
    return {
        "mode": "pinned",
        "profile": validated["profile"],
        "path": str(resolved),
        "filtered_observations": sorted(CAPABILITY_OBSERVATIONS),
    }


def observation_token(line: str) -> Optional[str]:
    if not line.startswith("- ") or ": " not in line:
        return None
    return line[2:].split(": ", 1)[0]


def compare_expectations(produced: Path, expected: Path) -> dict[str, Any]:
    actual_lines = normalized_text(produced)
    expected_lines = normalized_text(expected)
    actual_fields = validate_report_document(
        actual_lines, expectation=False
    )
    expected_fields = validate_report_document(
        expected_lines, expectation=True
    )
    activation = expectation_activation_profile(expected, expected_lines)
    differences: list[dict[str, Any]] = []

    scalar_pairs = (
        (
            "version",
            actual_fields["spec"],
            expected_fields["expectation"],
        ),
        (
            "scope excludes",
            actual_fields["scope excludes"],
            expected_fields["scope excludes"],
        ),
        (
            "onboarding",
            actual_fields["onboarding"],
            expected_fields["onboarding"],
        ),
    )
    for field, actual, wanted in scalar_pairs:
        if actual != wanted:
            differences.append({"field": field, "actual": actual, "expected": wanted})

    actual_header, actual_rows = parse_findings(actual_lines)
    expected_header, expected_rows = parse_findings(expected_lines)
    if actual_header != expected_header:
        differences.append(
            {
                "field": "findings header",
                "actual": actual_header,
                "expected": expected_header,
            }
        )
    if actual_rows != expected_rows:
        differences.append(
            {
                "field": "findings rows",
                "actual": actual_rows,
                "expected": expected_rows,
            }
        )

    actual_observations = parse_observations(actual_lines)
    expected_observations = parse_observations(expected_lines)
    filtered = set(activation["filtered_observations"])
    actual_observations = [
        line
        for line in actual_observations
        if observation_token(line) not in filtered
    ]
    expected_observations = [
        line
        for line in expected_observations
        if observation_token(line) not in filtered
    ]
    if actual_observations != expected_observations:
        differences.append(
            {
                "field": "observations",
                "actual": actual_observations,
                "expected": expected_observations,
            }
        )

    return {
        "pass": not differences,
        "produced": str(produced),
        "expected": str(expected),
        "activation_profile": activation,
        "differences": differences,
    }


def self_test_require(condition: Any, detail: str) -> None:
    if not condition:
        raise ValueError(f"self-test failed: {detail}")


def self_test_expect_value_error(operation: Any, detail: str) -> None:
    try:
        operation()
    except ValueError:
        return
    raise ValueError(f"self-test failed: {detail} was accepted")


@contextmanager
def isolated_self_test_git_environment(
    root: Path,
) -> Iterable[dict[str, Path]]:
    """Run self-test Git commands without ambient config or hooks."""

    isolation_root = root / "git-process-isolation"
    isolation_root.mkdir()
    empty_global = isolation_root / "global.gitconfig"
    empty_global.write_bytes(b"")
    hooks = isolation_root / "hooks"
    template = isolation_root / "template"
    hooks.mkdir()
    template.mkdir()

    poison_hooks = isolation_root / "poison-hooks"
    poison_hooks.mkdir()
    poison_hook = poison_hooks / "pre-commit"
    poison_hook.write_bytes(b"#!/bin/sh\nexit 97\n")
    try:
        poison_hook.chmod(0o755)
    except OSError:
        pass
    system_config = isolation_root / "system.gitconfig"
    system_config.write_text(
        "[user]\n"
        "\tname = Ambient Poison\n"
        "[commit]\n"
        "\tgpgsign = true\n"
        "[core]\n"
        f"\thooksPath = {poison_hooks.as_posix()}\n",
        encoding="utf-8",
    )

    exact_keys = {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_AUTHOR_EMAIL",
        "GIT_AUTHOR_NAME",
        "GIT_CEILING_DIRECTORIES",
        "GIT_COMMITTER_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMON_DIR",
        "GIT_CONFIG",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_SYSTEM",
        "GIT_DIR",
        "GIT_DISCOVERY_ACROSS_FILESYSTEM",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_TEMPLATE_DIR",
        "GIT_TERMINAL_PROMPT",
        "GIT_WORK_TREE",
    }
    inherited_keys = {
        key
        for key in os.environ
        if (
            key in exact_keys
            or key.startswith("GIT_CONFIG_KEY_")
            or key.startswith("GIT_CONFIG_VALUE_")
        )
    }
    inherited = {key: os.environ[key] for key in inherited_keys}
    try:
        for key in inherited_keys:
            os.environ.pop(key, None)
        os.environ.update(
            {
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_SYSTEM": str(system_config),
                "GIT_CONFIG_GLOBAL": str(empty_global),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.hooksPath",
                "GIT_CONFIG_VALUE_0": str(hooks),
                "GIT_TEMPLATE_DIR": str(template),
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_AUTHOR_NAME": "Bridge Self Test",
                "GIT_AUTHOR_EMAIL": "bridge-self-test@example.invalid",
                "GIT_COMMITTER_NAME": "Bridge Self Test",
                "GIT_COMMITTER_EMAIL": "bridge-self-test@example.invalid",
            }
        )
        yield {
            "global": empty_global,
            "system": system_config,
            "hooks": hooks,
            "template": template,
        }
    finally:
        for key in list(os.environ):
            if (
                key in exact_keys
                or key.startswith("GIT_CONFIG_KEY_")
                or key.startswith("GIT_CONFIG_VALUE_")
            ):
                os.environ.pop(key, None)
        os.environ.update(inherited)


def run_self_test() -> dict[str, Any]:
    checks: list[str] = []
    control_hints = get_type_hints(control_comment_anomalies)
    self_test_require(
        "protected" in control_hints,
        "runtime resolution of Mapping annotations",
    )
    checks.append("runtime-type-annotations")
    source_syntax = ast.parse(
        Path(__file__).read_text(encoding="utf-8")
    )
    self_test_require(
        not any(
            isinstance(node, ast.Assert)
            for node in ast.walk(source_syntax)
        ),
        "assert-free self-test implementation",
    )
    checks.append("assert-independent-self-test")
    self_test_require(
        normalize_n(b"a  \r\nb\t\r\n\r\n") == b"a\nb\n",
        "normalization N",
    )
    checks.append("normalize-n")
    records = byte_records(b"a\r\nb\rc\nlast")
    self_test_require(
        [record["content"] for record in records]
        == [b"a", b"b", b"c", b"last"],
        "byte record contents",
    )
    self_test_require(
        [(record["start"], record["end"]) for record in records]
        == [(0, 3), (3, 5), (5, 7), (7, 11)],
        "byte record offsets",
    )
    checks.append("byte-offset-lines")

    agents_bytes = (
        b"manual-before\r\n"
        b"<!-- bridge:managed:start id=entry source=CLAUDE.md -->\r\n"
        b"# Shared  \r\n"
        b"<!-- bridge:managed:end -->\r\n"
        b"manual-after\r\n"
    )
    block_map = inspect_managed_blocks(
        agents_bytes,
        entry_source="CLAUDE.md",
        owned_ids=["entry"],
    )
    self_test_require(block_map["trustworthy"], "managed block map")
    self_test_require(
        len(block_map["blocks"]) == 1,
        "managed block count",
    )
    self_test_require(
        block_map["blocks"][0]["body_start"]
        == len(
            b"manual-before\r\n"
            b"<!-- bridge:managed:start id=entry source=CLAUDE.md -->\r\n"
        ),
        "managed block body offset",
    )
    self_test_require(
        b"".join(
            agents_bytes[span["start"] : span["end"]]
            for span in block_map["manual_spans"]
        )
        == b"manual-before\r\nmanual-after\r\n",
        "manual span preservation",
    )
    checks.append("managed-block-byte-map")

    anomalous_agents = (
        b"<!-- bridge:managed:start id=entry source=CLAUDE.md mode=semantic -->\n"
        b"<!-- bridge:managed:end -->\n"
        b"<!-- bridge:managed:start id=entry source=wrong.md -->\n"
        b"x\n"
        b"<!-- bridge:managed:end -->\n"
        b"<!-- bridge:managed:start id=entry source=CLAUDE.md -->\n"
        b"y\n"
        b"<!-- bridge:managed:end -->\n"
    )
    anomaly_map = inspect_managed_blocks(
        anomalous_agents, entry_source="CLAUDE.md"
    )
    anomaly_kinds = {
        item["kind"] for item in anomaly_map["anomalies"]
    }
    self_test_require(
        {
            "legacy-managed-mode",
            "orphan-end",
            "source-mismatch",
            "duplicate-id",
        }
        <= anomaly_kinds,
        "managed block anomaly registry",
    )
    self_test_require(
        not anomaly_map["trustworthy"],
        "anomalous managed block trust",
    )
    checks.append("managed-block-anomalies")

    claude_regions = (
        b"before\n"
        b"<!-- bridge:claude-only:start -->\n"
        b"hidden\n"
        b"<!-- bridge:claude-only:end -->\n"
        b"between\n"
        b"<!-- bridge:claude-only:start -->\n"
        b"unclosed\n"
    )
    claude_map = inspect_claude_only(claude_regions)
    self_test_require(
        len(claude_map["spans"]) == 1,
        "Claude-only closed span count",
    )
    self_test_require(
        claude_map["anomalies"][0]["kind"] == "unclosed-claude-only",
        "Claude-only unclosed anomaly",
    )
    checks.append("claude-only-spans")

    active_source = (
        b"`@inline/one`\n"
        b"``multi\n @inline/two``\n"
        b"```\n@fenced/one\n```\n"
        b"Shared(@not-active/no-leading-space)\n"
        b" @active/rules.md\n"
    )
    imports = active_imports(active_source)
    self_test_require(
        [item["token"] for item in imports] == ["@active/rules.md"],
        "active import code-boundary filtering",
    )
    self_test_require(
        active_source[imports[0]["start"] : imports[0]["end"]]
        == b"@active/rules.md",
        "active import source offsets",
    )
    checks.append("active-import-spans")

    protected_import_source = (
        b"<!-- bridge:intent 2026-07-23 Initial shared intent -->\n"
        b"<!-- bridge:intent 2026-07-24 Shared entry -->\n"
        b"<!-- bridge:claude-only:start -->\n"
        b"`excluded opener\n"
        b"<!-- bridge:claude-only:end -->\n"
        b" @active/protected-boundary.md\n"
        b"`unmatched shared delimiter\n"
    )
    protected_import_render = render_agents_unit(
        protected_import_source,
        kind="entry",
        paths=None,
    )
    self_test_require(
        [
            item["token"]
            for item in protected_import_render["active_imports"]
        ]
        == ["@active/protected-boundary.md"],
        "active imports after protected-span projection",
    )
    protected_fence_rule = (
        b"---\n"
        b"paths:\n"
        b"  - \"docs/**/*\"\n"
        b"```\n"
        b"---\n"
        b"<!-- bridge:intent 2026-07-24 Shared docs -->\n"
        b" @active/frontmatter-boundary.md\n"
    )
    protected_fence_render = render_agents_unit(
        protected_fence_rule,
        kind="rule",
        paths=["docs/**/*"],
    )
    self_test_require(
        [
            item["token"]
            for item in protected_fence_render["active_imports"]
        ]
        == ["@active/frontmatter-boundary.md"],
        "active imports after protected frontmatter projection",
    )
    checks.append("active-import-protected-projection")

    rule_source = (
        b"---\r\n"
        b"paths:\r\n"
        b"  - \"docs/**/*\"\r\n"
        b"---\r\n"
        b"<!-- bridge:intent 2026-07-24 Keep docs guidance shared -->\r\n"
        b"\r\n"
        b"# Docs  \r\n"
        b"\r\n"
        b"<!-- bridge:claude-only:start -->\r\n"
        b"Claude-only detail.\r\n"
        b"<!-- bridge:claude-only:end -->\r\n"
        b"Use `@literal/example` in examples.\r\n"
    )
    rendered_rule = render_agents_unit(
        rule_source, kind="rule", paths=["docs/**/*"]
    )
    expected_render = (
        b"Applies only while reading or editing files that match at least "
        b"one of these source globs: `docs/**/*`. (bridge:pv2)\n\n"
        b"# Docs\n\n"
        b"Use `@literal/example` in examples.\n"
    )
    self_test_require(
        rendered_rule["valid"],
        f"valid v4 rule render: {rendered_rule['errors']}",
    )
    self_test_require(
        base64.b64decode(rendered_rule["rendered"]["base64"])
        == expected_render,
        "v4 rendered bytes",
    )
    self_test_require(
        {
            span["kind"] for span in rendered_rule["protected_spans"]
        }
        >= {"frontmatter", "intent", "claude-only", "leading-blank"},
        "v4 protected span kinds",
    )
    self_test_require(
        any(
            item["kind"] == "generated-preamble"
            for item in rendered_rule["origin_map"]
        ),
        "v4 generated preamble origin",
    )
    parsed_preamble = parse_preamble(expected_render)
    self_test_require(
        parsed_preamble
        == {
            "present": True,
            "valid": True,
            "paths": ["docs/**/*"],
            "end": len(expected_render.split(b"# Docs", 1)[0]),
        },
        "pv2 preamble round trip",
    )
    checks.append("render-v4-origin-map")
    checks.append("preamble-pv2-roundtrip")

    blocked_render = render_agents_unit(
        b"<!-- bridge:intent 2026-07-24 Shared entry -->\n"
        b"# Entry\n\n"
        b" @shared/import.md\n",
        kind="entry",
        paths=None,
    )
    self_test_require(
        not blocked_render["valid"],
        "active import blocks v4 render",
    )
    self_test_require(
        blocked_render["active_imports"][0]["token"]
        == "@shared/import.md",
        "active import blocker token",
    )
    unknown_control = render_agents_unit(
        b"<!-- bridge:unknown value -->\n# Entry\n",
        kind="entry",
        paths=None,
    )
    self_test_require(
        not unknown_control["valid"],
        "unknown control comment blocks render",
    )
    self_test_require(
        unknown_control["errors"][0]["kind"]
        == "unknown-control-comment",
        "unknown control comment blocker",
    )
    checks.append("render-v4-blockers")

    for unit_kind in ("entry", "rule"):
        bom_render = render_agents_unit(
            b"\xef\xbb\xbf"
            b"<!-- bridge:intent 2026-07-24 Shared guidance -->\n"
            b"# Shared\n",
            kind=unit_kind,
            paths=None,
        )
        self_test_require(
            not bom_render["valid"]
            and any(
                error["kind"] == "leading-utf8-bom"
                for error in bom_render["errors"]
            ),
            f"leading UTF-8 BOM blocks {unit_kind}",
        )
    checks.append("entry-rule-leading-bom")

    self_test_require(
        not valid_intent_line(
            b"<!-- bridge:intent 2026-07-24 \vleading -->"
        ),
        "leading ASCII whitespace in intent",
    )
    self_test_require(
        not valid_intent_line(
            b"<!-- bridge:intent 2026-07-24 trailing\f -->"
        ),
        "trailing ASCII whitespace in intent",
    )
    self_test_require(
        valid_intent_line(
            "<!-- bridge:intent 2026-07-24 \u00a0Unicode space -->".encode(
                "utf-8"
            )
        ),
        "non-ASCII intent boundary whitespace",
    )
    reverse_intents = render_agents_unit(
        b"<!-- bridge:intent 2026-07-24 Newer -->\n"
        b"<!-- bridge:intent 2026-07-23 Older -->\n"
        b"# Shared\n",
        kind="entry",
        paths=None,
    )
    self_test_require(
        not reverse_intents["valid"]
        and any(
            error["kind"] == "intent-not-oldest-first"
            for error in reverse_intents["errors"]
        ),
        "intent records oldest-first ordering",
    )
    checks.append("intent-order-ascii-whitespace")

    self_test_require(
        "paths[0]:universal-no-op" in validate_render_paths(["**/*"]),
        "universal render path guard",
    )
    self_test_require(
        "paths[1]:duplicate"
        in validate_render_paths(["docs/**/*", "docs/**/*"]),
        "duplicate render path guard",
    )
    self_test_require(
        "paths[0]:unclosed-bracket"
        in validate_render_paths(["src/[a"]),
        "unclosed bracket render path guard",
    )
    checks.append("paths-closed-guards")

    budget = check_agents_budget(b"x" * 28, 32)
    self_test_require(
        budget["fits"] and budget["warning_threshold"],
        "budget warning threshold",
    )
    self_test_require(
        not check_agents_budget(b"x", 0)["fits"],
        "zero budget",
    )
    self_test_require(
        not check_agents_budget(b"x" * 33, 32)["fits"],
        "exceeded budget",
    )
    checks.append("agents-budget")

    self_test_require(
        diff_shape(b"a\n", b"a\nb\n") == "additions-only",
        "additions-only diff shape",
    )
    self_test_require(
        diff_shape(b"a\nb\n", b"a\n") == "deletions-only",
        "deletions-only diff shape",
    )
    self_test_require(
        diff_shape(b"a\n", b"b\n") == "both",
        "bidirectional diff shape",
    )
    checks.append("diff-shape")

    with ExitStack() as stack:
        temp = stack.enter_context(
            tempfile.TemporaryDirectory(prefix="bridge-sentinel-")
        )
        root = Path(temp)
        git_isolation = stack.enter_context(
            isolated_self_test_git_environment(root)
        )
        master = root / "master"
        copy = root / "copy"
        master.mkdir()
        copy.mkdir()
        (master / "same").write_bytes(b"same\n")
        (copy / "same").write_bytes(b"same\n")
        byte_comparison = compare_trees(master, copy)
        self_test_require(
            byte_comparison["equal"],
            "equal filesystem tree comparison",
        )
        self_test_require(
            byte_comparison["mode_checked"] is False,
            "filesystem comparison mode boundary",
        )
        (copy / "extra").write_bytes(b"extra\n")
        self_test_require(
            compare_trees(master, copy)["shape"] == "additions-only",
            "filesystem addition shape",
        )
        produced = root / "produced.md"
        expected = root / "expected.md"
        findings = (
            "## Findings\n\n"
            + FINDINGS_HEADER
            + "\n"
            + FINDINGS_SEPARATOR
            + "\n"
            "| skills | demo | codex | in-sync | - | native | - |\n\n"
        )

        def produced_report(observations: str) -> str:
            return (
                "# Bridge Sentinel Report\n\n"
                "- project: demo\n"
                "- scan root: .\n"
                "- scope excludes: (none)\n"
                "- date: 2026-07-24\n"
                "- spec: report/v5\n"
                "- scan surfaces: agents-md, hooks, skills\n"
                "- onboarding: onboarded\n\n"
                + findings
                + "## Observations\n\n"
                + observations
                + "\n\n## Evidence and notes\n\nSelf-test evidence.\n\n"
                "## Local environment notes\n\nSelf-test environment.\n"
            )

        def expected_report(
            observations: str, activation_header: str
        ) -> str:
            return (
                "- expectation: report/v5\n"
                "- scan root: .\n"
                "- scope excludes: (none)\n"
                f"- activation profile: {activation_header}\n"
                "- onboarding: onboarded\n\n"
                + findings
                + "## Observations\n\n"
                + observations
                + "\n"
            )

        produced.write_text(
            produced_report(
                "- mode-limited: .claude/skills/demo/tool "
                "(worktree-mode-unobservable)\n"
                "- codex-root-unresolved: . (effective-root-unknown)"
            ),
            encoding="utf-8",
        )
        expected.write_text(
            expected_report("- (none)", "environment-dependent"),
            encoding="utf-8",
        )
        self_test_require(
            compare_expectations(produced, expected)["pass"],
            "environment-dependent expectation comparison",
        )

        invalid_version = root / "invalid-version.md"
        invalid_version.write_text(
            produced.read_text(encoding="utf-8").replace(
                "- spec: report/v5",
                "- spec: report/v4",
            ),
            encoding="utf-8",
        )
        self_test_expect_value_error(
            lambda: compare_expectations(invalid_version, expected),
            "non-v5 produced report",
        )
        missing_section = root / "missing-section.md"
        missing_section.write_text(
            produced.read_text(encoding="utf-8").replace(
                "\n## Local environment notes\n\nSelf-test environment.\n",
                "\n",
            ),
            encoding="utf-8",
        )
        self_test_expect_value_error(
            lambda: compare_expectations(missing_section, expected),
            "produced report missing a required section",
        )
        malformed_row = root / "malformed-row.md"
        malformed_row.write_text(
            produced.read_text(encoding="utf-8").replace(
                "| skills | demo | codex | in-sync | - | native | - |",
                "|skills| demo | codex | in-sync | - | native | - |",
            ),
            encoding="utf-8",
        )
        self_test_expect_value_error(
            lambda: compare_expectations(malformed_row, expected),
            "Findings row without exact padding",
        )
        prose_observation = root / "prose-observation.md"
        prose_observation.write_text(
            produced_report("observation prose is not a list item"),
            encoding="utf-8",
        )
        self_test_expect_value_error(
            lambda: compare_expectations(prose_observation, expected),
            "non-observation prose in Observations",
        )
        checks.append("report-v5-strict-grammar")

        activation_profile = root / "activation-profile.json"
        activation_profile.write_text(
            json.dumps(
                {
                    "version": "activation-fixture/v1",
                    "root_markers": [".git"],
                    "fallback_filenames": ["AGENTS.fallback.md"],
                    "project_doc_max_bytes": 32768,
                    "budget_source": "resolved",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        pinned_produced = root / "pinned-produced.md"
        pinned_expected = root / "pinned-expected.md"
        pinned_produced.write_text(
            produced_report(
                "- codex-effective-budget: AGENTS.md "
                "(project_doc_max_bytes=32768; source=resolved)\n"
                "- mode-limited: .claude/skills/demo/tool "
                "(worktree-mode-unobservable)"
            ),
            encoding="utf-8",
        )
        pinned_expected.write_text(
            expected_report(
                "- codex-effective-budget: AGENTS.md "
                "(project_doc_max_bytes=32768; source=resolved)",
                "activation-profile.json",
            ),
            encoding="utf-8",
        )
        pinned_result = compare_expectations(
            pinned_produced, pinned_expected
        )
        self_test_require(
            pinned_result["pass"],
            f"pinned expectation comparison: {pinned_result}",
        )
        self_test_require(
            pinned_result["activation_profile"]["mode"] == "pinned",
            "pinned activation profile provenance",
        )
        checks.append("activation-profile-provenance")

        dot_expected = root / "dot-activation-expected.md"
        dot_expected.write_text(
            expected_report("- (none)", "."),
            encoding="utf-8",
        )
        self_test_expect_value_error(
            lambda: compare_expectations(produced, dot_expected),
            "dot activation-profile header",
        )
        dot_process = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "compare-expectation",
                str(produced),
                str(dot_expected),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self_test_require(
            dot_process.returncode == 2,
            "dot activation-profile CLI exit code",
        )
        try:
            dot_error = json.loads(dot_process.stdout.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "self-test failed: dot activation-profile error is not JSON"
            ) from error
        self_test_require(
            isinstance(dot_error, dict)
            and isinstance(dot_error.get("error"), str),
            "dot activation-profile JSON error",
        )
        checks.append("activation-dot-json-error")
        activation_target = root / "activation-target"
        activation_target.mkdir()
        linked_profile = activation_target / "profile.json"
        linked_profile.write_bytes(activation_profile.read_bytes())
        activation_link = root / "activation-link"
        try:
            os.symlink(
                activation_target,
                activation_link,
                target_is_directory=True,
            )
        except (NotImplementedError, OSError):
            checks.append("activation-profile-no-follow-skipped")
        else:
            linked_expected = root / "linked-expected.md"
            linked_expected.write_text(
                "- activation profile: activation-link/profile.json\n",
                encoding="utf-8",
            )
            self_test_expect_value_error(
                lambda: expectation_activation_profile(
                    linked_expected,
                    normalized_text(linked_expected),
                ),
                "linked activation-profile parent",
            )
            checks.append("activation-profile-no-follow")
        self_test_require(inspect_tree(master)["safe"], "safe tree inspection")

        repository = root / "git-tree"
        repository.mkdir()
        self_test_require(
            Path(os.environ["GIT_CONFIG_GLOBAL"])
            == git_isolation["global"]
            and Path(os.environ["GIT_CONFIG_SYSTEM"])
            == git_isolation["system"]
            and os.environ["GIT_CONFIG_NOSYSTEM"] == "1"
            and os.environ["GIT_CONFIG_COUNT"] == "1"
            and os.environ["GIT_CONFIG_KEY_0"] == "core.hooksPath"
            and Path(os.environ["GIT_CONFIG_VALUE_0"])
            == git_isolation["hooks"],
            "self-test Git environment controls",
        )
        git_run(
            repository,
            [
                "init",
                "--quiet",
                f"--template={git_isolation['template']}",
            ],
        )
        git_run(repository, ["config", "core.filemode", "false"])
        ambient_user = git_run(
            repository,
            ["config", "--get", "user.name"],
            allow_failure=True,
        )
        self_test_require(
            ambient_user.returncode == 1,
            "ambient Git user config isolation",
        )
        local_injection = git_run(
            repository,
            [
                "config",
                "--local",
                "--get-regexp",
                r"^(include|core\.hooksPath)",
            ],
            allow_failure=True,
        )
        self_test_require(
            local_injection.returncode == 1,
            "self-test local Git config isolation",
        )
        self_test_require(
            not (repository / ".git" / "hooks" / "pre-commit").exists(),
            "self-test Git template hook isolation",
        )
        source_unit = repository / "source"
        projection_unit = repository / "projection"
        deletion_unit = repository / "normal-deletion"
        source_unit.mkdir()
        projection_unit.mkdir()
        deletion_unit.mkdir()
        (source_unit / "tool").write_bytes(b"same\n")
        (projection_unit / "tool").write_bytes(b"same\n")
        (deletion_unit / "file").write_bytes(b"tracked\n")
        git_run(
            repository,
            [
                "add",
                "--",
                "source/tool",
                "projection/tool",
                "normal-deletion/file",
            ],
        )
        git_run(
            repository, ["update-index", "--chmod=+x", "--", "source/tool"]
        )
        git_run(
            repository,
            ["update-index", "--chmod=-x", "--", "projection/tool"],
        )
        mode_comparison = compare_git_trees(
            repository,
            "source",
            "projection",
            revision=None,
            include_untracked=False,
        )
        self_test_require(
            not mode_comparison["equal"],
            "Git mode-only inequality",
        )
        self_test_require(
            mode_comparison["comparable"],
            "Git mode-only comparability",
        )
        self_test_require(
            not mode_comparison["blockers"],
            "Git mode-only blocker absence",
        )
        self_test_require(
            mode_comparison["changed"][0]["kind"] == "mode-only",
            "Git mode-only classification",
        )

        untracked_unit = repository / "untracked"
        untracked_unit.mkdir()
        (untracked_unit / "tool").write_bytes(b"untracked\n")
        ordinary_manifest = git_manifest(
            repository,
            "untracked",
            revision=None,
            include_untracked=True,
        )
        self_test_require(
            ordinary_manifest["safe"],
            "ordinary untracked manifest safety",
        )
        self_test_require(
            not ordinary_manifest["mode_limited"],
            "ordinary untracked mode availability",
        )
        self_test_require(
            ordinary_manifest["entries"][0]["mode"] == "100644",
            "ordinary untracked default mode",
        )
        self_test_require(
            ordinary_manifest["entries"][0]["mode_evidence"][
                "effective_source"
            ]
            == "platform-untracked-default",
            "ordinary untracked mode evidence",
        )

        explicit_manifest = git_manifest(
            repository,
            "untracked",
            revision=None,
            include_untracked=True,
            required_executable=["tool"],
        )
        self_test_require(
            explicit_manifest["mode_limited"],
            "explicit executable mode limitation",
        )
        self_test_require(
            any(
                blocker["token"] == "mode-limited"
                for blocker in explicit_manifest["blockers"]
            ),
            "explicit executable mode blocker",
        )

        prospective_unit = repository / "prospective"
        prospective_unit.mkdir()
        (prospective_unit / "tool").write_bytes(b"same\n")
        observe_comparison = compare_git_trees(
            repository,
            "source",
            "prospective",
            revision=None,
            include_untracked=True,
        )
        self_test_require(
            observe_comparison["comparable"],
            "observe comparison comparability",
        )
        self_test_require(
            not observe_comparison["blockers"],
            "observe comparison blocker absence",
        )
        directed_comparison = compare_git_trees(
            repository,
            "source",
            "prospective",
            revision=None,
            include_untracked=True,
            direction="source-to-projection",
        )
        self_test_require(
            not directed_comparison["comparable"],
            "directed comparison mode-limited comparability",
        )
        self_test_require(
            directed_comparison["mode_limited"],
            "directed comparison mode limitation",
        )
        self_test_require(
            any(
                blocker["token"] == "mode-limited"
                and blocker["side"] == "projection"
                for blocker in directed_comparison["blockers"]
            ),
            "directed comparison target mode blocker",
        )

        git_run(
            repository,
            [
                "commit",
                "--quiet",
                "--no-gpg-sign",
                "--no-verify",
                "-m",
                "baseline",
            ],
        )
        checks.append("git-self-test-process-isolation")

        head_tree_oid = (
            git_run(repository, ["rev-parse", "HEAD^{tree}"])
            .stdout.decode("ascii")
            .strip()
        )
        for non_commit_revision in (
            "HEAD^{tree}",
            "HEAD:projection",
            "HEAD:",
            head_tree_oid,
        ):
            self_test_expect_value_error(
                lambda value=non_commit_revision: git_manifest(
                    repository,
                    "projection",
                    revision=value,
                    include_untracked=False,
                ),
                f"non-commit revision {non_commit_revision}",
            )
        self_test_expect_value_error(
            lambda: compare_git_trees(
                repository,
                "source",
                "projection",
                revision="HEAD:projection",
                include_untracked=False,
            ),
            "subtree revision comparison",
        )
        checks.append("revision-commit-only")

        revision_manifest = git_manifest(
            repository,
            "projection",
            revision="HEAD",
            include_untracked=False,
        )
        (projection_unit / "tool").write_bytes(b"worktree\n")
        worktree_manifest = git_manifest(
            repository,
            "projection",
            revision=None,
            include_untracked=False,
        )
        snapshot_comparison = compare_git_manifests(
            revision_manifest, worktree_manifest
        )
        self_test_require(
            re.fullmatch(
                r"(?:[0-9a-f]{40}|[0-9a-f]{64})",
                revision_manifest["resolved_commit"],
            )
            is not None,
            "resolved revision commit object id",
        )
        self_test_require(
            not snapshot_comparison["equal"],
            "revision versus worktree inequality",
        )
        self_test_require(
            snapshot_comparison["changed"][0]["kind"] == "bytes-only",
            "revision versus worktree byte classification",
        )

        blob_oid = git_run(
            repository,
            ["hash-object", "-w", "--stdin"],
            input_data=b"literal path identity\n",
        ).stdout.decode("ascii").strip()
        literal_unit_tree = git_run(
            repository,
            ["mktree", "-z"],
            input_data=(
                f"100644 blob {blob_oid}\t".encode("ascii")
                + b"literal\\name\0"
            ),
        ).stdout.decode("ascii").strip()
        nested_leaf_tree = git_run(
            repository,
            ["mktree", "-z"],
            input_data=(
                f"100644 blob {blob_oid}\tname\0".encode("ascii")
            ),
        ).stdout.decode("ascii").strip()
        nested_unit_tree = git_run(
            repository,
            ["mktree", "-z"],
            input_data=(
                f"040000 tree {nested_leaf_tree}\tliteral\0".encode(
                    "ascii"
                )
            ),
        ).stdout.decode("ascii").strip()

        def root_tree(unit_tree: str) -> str:
            return (
                git_run(
                    repository,
                    ["mktree", "-z"],
                    input_data=(
                        f"040000 tree {unit_tree}\tliteral-unit\0".encode(
                            "ascii"
                        )
                    ),
                )
                .stdout.decode("ascii")
                .strip()
            )

        literal_commit = (
            git_run(
                repository,
                ["commit-tree", root_tree(literal_unit_tree)],
                input_data=b"literal backslash path\n",
            )
            .stdout.decode("ascii")
            .strip()
        )
        nested_commit = (
            git_run(
                repository,
                ["commit-tree", root_tree(nested_unit_tree)],
                input_data=b"nested slash path\n",
            )
            .stdout.decode("ascii")
            .strip()
        )
        literal_manifest = git_manifest(
            repository,
            "literal-unit",
            revision=literal_commit,
            include_untracked=False,
        )
        nested_manifest = git_manifest(
            repository,
            "literal-unit",
            revision=nested_commit,
            include_untracked=False,
        )
        self_test_require(
            literal_manifest["entries"][0]["path"]
            == "literal\\name",
            "literal Git backslash path preservation",
        )
        literal_comparison = compare_git_manifests(
            literal_manifest,
            nested_manifest,
        )
        self_test_require(
            not literal_comparison["equal"]
            and literal_comparison["source_only"] == ["literal\\name"]
            and literal_comparison["projection_only"] == ["literal/name"],
            "literal backslash and slash path identity separation",
        )
        checks.append("git-literal-backslash-identity")

        (deletion_unit / "file").unlink()
        deletion_manifest = git_manifest(
            repository,
            "normal-deletion",
            revision=None,
            include_untracked=True,
        )
        self_test_require(
            deletion_manifest["safe"],
            "tracked deletion manifest safety",
        )
        self_test_require(
            deletion_manifest["tracked_deletions"] == ["file"],
            "tracked deletion preservation",
        )

        collision_blockers: list[dict[str, str]] = []
        detect_unit_casefold_collisions(
            ["foo", "foo"], ["Foo", "Foo"], collision_blockers
        )
        collision_safe = not collision_blockers
        self_test_require(
            not collision_safe,
            "deleted/current case-fold collision safety",
        )
        self_test_require(
            len(collision_blockers) == 1,
            "deleted/current collision blocker count",
        )
        self_test_require(
            collision_blockers[0]["token"] == "unsafe-tree-entry",
            "deleted/current collision blocker token",
        )
        self_test_require(
            collision_blockers[0]["detail"].startswith(
                "case-fold-collision"
            ),
            "deleted/current collision blocker detail",
        )
        no_false_positive: list[dict[str, str]] = []
        detect_unit_casefold_collisions(
            ["same"], ["same"], no_false_positive
        )
        self_test_require(
            not no_false_positive,
            "identical deleted/current path collision false positive",
        )

        if os.name != "nt":
            git_run(repository, ["config", "core.filemode", "true"])
            posix_unit = repository / "posix-untracked"
            posix_unit.mkdir()
            (posix_unit / "tool").write_bytes(b"executable\n")
            os.chmod(posix_unit / "tool", 0o755)
            posix_manifest = git_manifest(
                repository,
                "posix-untracked",
                revision=None,
                include_untracked=True,
            )
            self_test_require(
                posix_manifest["safe"],
                "POSIX untracked executable manifest safety",
            )
            self_test_require(
                posix_manifest["entries"][0]["mode"] == "100755",
                "POSIX untracked executable mode",
            )
            self_test_require(
                posix_manifest["entries"][0]["mode_evidence"][
                    "effective_source"
                ]
                == "posix-filesystem-exec",
                "POSIX untracked executable evidence",
            )
            checks.append("posix-untracked-exec")
        else:
            checks.append("posix-untracked-exec-skipped")
    checks.append("compare-trees")
    checks.append("inspect-tree")
    checks.append("git-tree-mode-only")
    checks.append("ordinary-untracked-100644")
    checks.append("explicit-exec-mode-limited")
    checks.append("directional-mode-limited")
    checks.append("observe-mode-nonblocking")
    checks.append("revision-vs-worktree")
    checks.append("tracked-deletion-preserved")
    checks.append("deleted-current-casefold-collision")
    checks.append("compare-expectation")
    return {"pass": True, "checks": checks}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only byte and Git-tree mechanics for Bridge skills."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    files = subparsers.add_parser("compare-files")
    files.add_argument("source", type=Path)
    files.add_argument("projection", type=Path)
    files.add_argument("--normalize-n", action="store_true")

    agents = subparsers.add_parser("inspect-agents-md")
    agents.add_argument("path", type=Path)
    agents.add_argument("--entry-source")
    agents.add_argument("--owned-id", action="append", default=[])

    render = subparsers.add_parser("render-agents-unit")
    render.add_argument("source", type=Path)
    render.add_argument(
        "--kind", choices=("entry", "rule", "covenant"), required=True
    )
    render.add_argument(
        "--paths-json",
        help=(
            "ordered JSON string list already validated against v4 paths "
            "and brace-expansion limits"
        ),
    )

    imports = subparsers.add_parser("inspect-active-imports")
    imports.add_argument("source", type=Path)

    preamble = subparsers.add_parser("parse-preamble")
    preamble.add_argument("path", type=Path)

    paths = subparsers.add_parser("validate-render-paths")
    paths.add_argument("paths_json")

    budget = subparsers.add_parser("check-agents-budget")
    budget.add_argument("path", type=Path)
    budget.add_argument("--budget", type=int, required=True)

    trees = subparsers.add_parser("compare-trees")
    trees.add_argument("master", type=Path)
    trees.add_argument("copy", type=Path)

    manifest = subparsers.add_parser("git-manifest")
    manifest.add_argument("repository", type=Path)
    manifest.add_argument("unit")
    manifest.add_argument("--revision")
    manifest.add_argument("--include-untracked", action="store_true")
    manifest.add_argument("--require-executable", action="append", default=[])

    git_trees = subparsers.add_parser("compare-git-trees")
    git_trees.add_argument("repository", type=Path)
    git_trees.add_argument("source_unit")
    git_trees.add_argument("projection_unit")
    git_trees.add_argument("--revision")
    git_trees.add_argument("--include-untracked", action="store_true")
    git_trees.add_argument(
        "--direction",
        choices=sorted(GIT_TREE_DIRECTIONS),
        default="observe",
    )
    git_trees.add_argument(
        "--require-executable", action="append", default=[]
    )

    expectation = subparsers.add_parser("compare-expectation")
    expectation.add_argument("produced", type=Path)
    expectation.add_argument("expected", type=Path)

    activation = subparsers.add_parser("validate-activation-profile")
    activation.add_argument("path", type=Path)

    inspect = subparsers.add_parser("inspect-tree")
    inspect.add_argument("root", type=Path)

    subparsers.add_parser("self-test")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "compare-files":
            result = compare_files(args.source, args.projection, args.normalize_n)
            success = result["equal"]
        elif args.command == "inspect-agents-md":
            result = inspect_managed_blocks(
                args.path.read_bytes(),
                entry_source=args.entry_source,
                owned_ids=args.owned_id,
            )
            result["path"] = str(args.path)
            success = result["trustworthy"]
        elif args.command == "render-agents-unit":
            paths_value: Optional[list[str]] = None
            if args.paths_json is not None:
                parsed_paths = json.loads(args.paths_json)
                if not isinstance(parsed_paths, list):
                    raise ValueError("--paths-json must decode to a list")
                paths_value = parsed_paths
            result = render_agents_unit(
                args.source.read_bytes(),
                kind=args.kind,
                paths=paths_value,
            )
            result["source"] = str(args.source)
            success = result["valid"]
        elif args.command == "inspect-active-imports":
            found = active_imports(args.source.read_bytes())
            result = {
                "contract": "active-import-scan/v1",
                "source": str(args.source),
                "blocked": bool(found),
                "imports": found,
            }
            success = not found
        elif args.command == "parse-preamble":
            result = parse_preamble(args.path.read_bytes())
            result["path"] = str(args.path)
            success = result["valid"]
        elif args.command == "validate-render-paths":
            parsed_paths = json.loads(args.paths_json)
            errors = validate_render_paths(parsed_paths)
            result = {
                "contract": "render-paths-check/v1",
                "valid": not errors,
                "errors": errors,
            }
            success = not errors
        elif args.command == "check-agents-budget":
            result = check_agents_budget(
                args.path.read_bytes(), args.budget
            )
            result["path"] = str(args.path)
            success = result["fits"]
        elif args.command == "compare-trees":
            result = compare_trees(args.master, args.copy)
            success = result["equal"]
        elif args.command == "git-manifest":
            result = git_manifest(
                args.repository,
                args.unit,
                revision=args.revision,
                include_untracked=args.include_untracked,
                required_executable=args.require_executable,
            )
            success = result["safe"]
        elif args.command == "compare-git-trees":
            result = compare_git_trees(
                args.repository,
                args.source_unit,
                args.projection_unit,
                revision=args.revision,
                include_untracked=args.include_untracked,
                direction=args.direction,
                required_executable=args.require_executable,
            )
            success = result["equal"]
        elif args.command == "compare-expectation":
            result = compare_expectations(args.produced, args.expected)
            success = result["pass"]
        elif args.command == "validate-activation-profile":
            result = validate_activation_profile(args.path)
            success = True
        elif args.command == "inspect-tree":
            result = inspect_tree(args.root)
            success = result["safe"]
        else:
            result = run_self_test()
            success = result["pass"]
    except (OSError, UnicodeError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
