#!/usr/bin/env python3
"""Read-only byte mechanics for the bridge-sentinel skill."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile

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

from pathlib import Path
from typing import Any, Iterable, Optional


def normalize_n(data: bytes) -> bytes:
    """Apply the specification's closed normalization set N."""
    normalized = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    lines = [line.rstrip(b" \t") for line in normalized.split(b"\n")]
    while lines and lines[-1] == b"":
        lines.pop()
    if not lines:
        return b""
    return b"\n".join(lines) + b"\n"


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


def relative_files(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file()
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
        "equal": shape == "equal",
        "shape": shape,
        "source_only": source_only,
        "projection_only": projection_only,
        "changed": changed,
        "master": str(master),
        "copy": str(copy),
    }


def normalized_text(path: Path) -> list[str]:
    return normalize_n(path.read_bytes()).decode("utf-8").splitlines()


def header_value(lines: list[str], key: str) -> Optional[str]:
    prefix = f"- {key}:"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


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
    expected_separator = "|---|---|---|---|---|---|---|"
    if content[1] != expected_separator:
        raise ValueError("Findings separator is malformed")
    header_width = len(header.split("|")[1:-1])

    rows: list[tuple[str, ...]] = []
    for line in content[2:]:
        if not line.startswith("|") or not line.endswith("|"):
            raise ValueError(f"malformed Findings row: {line}")
        cells = line.split("|")[1:-1]
        if len(cells) != header_width:
            raise ValueError(f"wrong Findings cell count: {line}")
        parsed: list[str] = []
        for cell in cells:
            if cell.startswith(" "):
                cell = cell[1:]
            if cell.endswith(" "):
                cell = cell[:-1]
            parsed.append(cell)
        rows.append(tuple(parsed))
    return header, sorted(rows)


def parse_observations(lines: list[str]) -> list[str]:
    content = [
        line
        for line in section_lines(lines, "Observations")
        if line.startswith("- ")
    ]
    if not content:
        raise ValueError("Observations must contain at least '- (none)'")
    return sorted(content)


def compare_expectations(produced: Path, expected: Path) -> dict[str, Any]:
    actual_lines = normalized_text(produced)
    expected_lines = normalized_text(expected)
    differences: list[dict[str, Any]] = []

    scalar_pairs = (
        ("version", header_value(actual_lines, "spec"), header_value(expected_lines, "expectation")),
        (
            "scope excludes",
            header_value(actual_lines, "scope excludes"),
            header_value(expected_lines, "scope excludes"),
        ),
        (
            "onboarding",
            header_value(actual_lines, "onboarding"),
            header_value(expected_lines, "onboarding"),
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
        "differences": differences,
    }


def run_self_test() -> dict[str, Any]:
    checks: list[str] = []
    assert normalize_n(b"a  \r\nb\t\r\n\r\n") == b"a\nb\n"
    checks.append("normalize-n")
    assert diff_shape(b"a\n", b"a\nb\n") == "additions-only"
    assert diff_shape(b"a\nb\n", b"a\n") == "deletions-only"
    assert diff_shape(b"a\n", b"b\n") == "both"
    checks.append("diff-shape")

    with tempfile.TemporaryDirectory(prefix="bridge-sentinel-") as temp:
        root = Path(temp)
        master = root / "master"
        copy = root / "copy"
        master.mkdir()
        copy.mkdir()
        (master / "same").write_bytes(b"same\n")
        (copy / "same").write_bytes(b"same\n")
        assert compare_trees(master, copy)["equal"]
        (copy / "extra").write_bytes(b"extra\n")
        assert compare_trees(master, copy)["shape"] == "additions-only"
        produced = root / "produced.md"
        expected = root / "expected.md"
        table = (
            "## Findings\n\n"
            "| surface | unit | host | state | suggested action | tier | annotations |\n"
            "|---|---|---|---|---|---|---|\n"
            "| skills | demo | codex | in-sync | - | native | - |\n\n"
            "## Observations\n\n- (none)\n"
        )
        produced.write_text(
            "- spec: report/v2\n"
            "- scope excludes: (none)\n"
            "- onboarding: onboarded\n\n"
            + table,
            encoding="utf-8",
        )
        expected.write_text(
            "- expectation: report/v2\n"
            "- scope excludes: (none)\n"
            "- onboarding: onboarded\n\n"
            + table,
            encoding="utf-8",
        )
        assert compare_expectations(produced, expected)["pass"]
    checks.append("compare-trees")
    checks.append("compare-expectation")
    return {"pass": True, "checks": checks}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only byte mechanics for bridge-sentinel."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    files = subparsers.add_parser("compare-files")
    files.add_argument("source", type=Path)
    files.add_argument("projection", type=Path)
    files.add_argument("--normalize-n", action="store_true")

    trees = subparsers.add_parser("compare-trees")
    trees.add_argument("master", type=Path)
    trees.add_argument("copy", type=Path)

    expectation = subparsers.add_parser("compare-expectation")
    expectation.add_argument("produced", type=Path)
    expectation.add_argument("expected", type=Path)

    subparsers.add_parser("self-test")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "compare-files":
            result = compare_files(args.source, args.projection, args.normalize_n)
            success = result["equal"]
        elif args.command == "compare-trees":
            result = compare_trees(args.master, args.copy)
            success = result["equal"]
        elif args.command == "compare-expectation":
            result = compare_expectations(args.produced, args.expected)
            success = result["pass"]
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
