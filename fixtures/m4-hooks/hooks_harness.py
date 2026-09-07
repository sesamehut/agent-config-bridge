#!/usr/bin/env python3
"""Validate and safely replay the M4 hook projection fixtures.

The harness validates fixture declarations and observed artifacts. It never
selects a Bridge direction, supplies a user decision, executes bridge-sync, or
starts a host. It owns no plan grammar of its own: the sync-plan/v3 document
parser, validator, comparison, materialization, replay-input and cleanup
machinery all live in `fixtures/m3-rules/fixture_harness.py` and are called
here with M4 parameters.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


HERE = Path(__file__).resolve().parent
FIXTURES_ROOT = HERE.parent
REPO_ROOT = FIXTURES_ROOT.parent
sys.path.insert(0, str(FIXTURES_ROOT / "m3-rules"))
sys.path.insert(
    0,
    str(REPO_ROOT / "skills/bridge-sentinel/scripts"),
)

import fixture_harness as m3  # noqa: E402
from sentinel_mechanics import (  # noqa: E402
    HOOK_FENCE_COMMAND_PATTERN,
    HOOK_FENCE_SCAN_SPEC,
    HOOK_INTENT_DOCUMENT,
    inspect_hook_intents,
    scan_hook_fence,
)

FixtureError = m3.FixtureError


SUITE = "m4-hooks"
MATRIX_SPEC = "bridge-m4-hooks-matrix/v1"
SCENARIO_SPEC = "bridge-m4-hooks-scenario/v1"
PLAN_SPEC = "sync-plan/v3"
PLAN_CONTRACTS = "covenant/v3, source-tree/v5, report/v5, reconciliation/v3"
JOURNAL_SPEC = "bridge-live-operation-journal/v2"
JOURNAL_BINDING = "by-reference"
REPLAY_INPUT_SPEC = "bridge-m4-replay-input/v1"
REPLAY_ENVELOPE_SPEC = "bridge-m4-replay-envelope/v1"

MATRIX_PATH = HERE / "scenario-matrix.json"
TREE_MANIFEST = HERE / "tree-manifest.json"
SHARED_DIR = REPO_ROOT
EXPECTATIONS_DIR = HERE / "expectations"
DECISIONS_DIR = HERE / "decisions"
ACTIVATION_PROFILES_DIR = HERE / "profiles"
WRITE_CAPABILITIES_DIR = HERE / "capabilities"
FAULT_SCHEDULES_DIR = HERE / "fault-schedules"

# The record's section 7 table order. `scenario-matrix.json` keeps that order
# instead of the byte-wise order the M3 matrix uses, so the file reads as the
# design record does; ids stay unique and every other ordering rule is
# unchanged. Scenarios added after the record was written are appended in
# `ADDED_SCENARIO_ORDER` rather than interleaved, so the first block keeps
# reading exactly as the record's table does.
RECORD_SCENARIO_ORDER = (
    "native-both-applied",
    "idempotent-rerun",
    "format-preserved-unchanged",
    "codex-create-blocked",
    "gate-all-or-nothing",
    "opt-in-pending",
    "opt-in-confirmed",
    "acknowledgement-missing-blocked",
    "degrade-codex-agents-md",
    "intent-doc-claude",
    "declared-unsynced-gate",
    "passthrough-preserved",
    "semantics-divergent-annex",
    "foreign-handler-keep",
    "guarded-region-nonunique-blocked",
    "carrier-unusable-blocked",
    "inline-hooks-conflict-blocked",
    "reverse-adopt-command",
    "reverse-adopt-override",
    "both-carriers-conflict",
    "delete-group-reindex",
    "retrust-required",
    "migration-v2-v3",
    "partial-two-carrier",
)
# `codex-blind-change` pins the informational warning the record's table
# never assigned to a scenario, and `delete-event-emptied` pins the Codex
# half of the deletion rule that empties an event member.
ADDED_SCENARIO_ORDER = (
    "codex-blind-change",
    "delete-event-emptied",
)
SCENARIO_ORDER = RECORD_SCENARIO_ORDER + ADDED_SCENARIO_ORDER

SCENARIO_FIELDS = {
    "activation_profile",
    "baseline",
    "coverage",
    "decision_fixture",
    "expectations",
    "fault",
    "fault_schedule_fixture",
    "history",
    "id",
    "input",
    "rendered_state",
    "replay",
    "replay_inputs",
    "replay_reason",
    "safeguards",
    "spec",
    "summary",
    "workflow",
    "write_capability_fixture",
}
REPLAY_INPUT_FIELDS = {
    "decision_fixture",
    "fault_schedule_fixture",
    "id",
    "rendered_state",
}

# Extension to fence carrier name for the mirrored `shared/` scan. The public
# `scan_hook_fence` selects its reader from the repository-relative path
# suffix, and a shared tree file is stored under an authoring name, so the
# mirror gives every shared file the carrier name its bytes stand for.
FENCE_MIRROR_NAMES = {
    ".json": ".claude/settings.json",
    ".md": ".claude/rules/hooks.md",
    ".toml": ".codex/config.toml",
}
FENCE_SHARED_TREES = (
    "m3-rules/shared",
    "m4-hooks/shared",
)
# A shared tree file whose suffix is neither mirrored nor listed here is a
# fence hole, so the mirror refuses it instead of skipping it. Neither host
# reads a hook command from these two suffixes: `.yaml` is skill
# frontmatter and `.txt` is inert project payload.
FENCE_IGNORED_SUFFIXES = {".txt", ".yaml"}
# A carrier that fails to parse yields no command value at all, so an armed
# command inside one would never reach the grammar. Exactly one fixture is
# deliberately unparseable; anything else is a fence hole and the allowlist
# keeps adding one an explicit edit.
FENCE_UNREADABLE_ALLOWLIST = ["fixtures/hooks-broken-json/.codex/hooks.json"]
# Floors under the whole-tree scan. The fence is only worth its exit code
# while it still reaches every carrier, and a renamed directory, a new
# suffix or a typo silently shrinks the scan, so `self-test` refuses a run
# that covers materially less than the tree it was written against.
FENCE_MIN_CARRIERS = 165
FENCE_MIN_VALUES = 121

_M4_BINDINGS: Dict[str, Any] = {
    "ACTIVATION_PROFILES_DIR": ACTIVATION_PROFILES_DIR,
    "DECISIONS_DIR": DECISIONS_DIR,
    "EXPECTATIONS_DIR": EXPECTATIONS_DIR,
    "FAULT_SCHEDULES_DIR": FAULT_SCHEDULES_DIR,
    "HERE": HERE,
    "MATRIX_PATH": MATRIX_PATH,
    "MATRIX_SPEC": MATRIX_SPEC,
    "REPLAY_ENVELOPE_SPEC": REPLAY_ENVELOPE_SPEC,
    "REPLAY_INPUT_SPEC": REPLAY_INPUT_SPEC,
    "SCENARIO_SPEC": SCENARIO_SPEC,
    "SUITE": SUITE,
    "TREE_MANIFEST": TREE_MANIFEST,
    "WRITE_CAPABILITIES_DIR": WRITE_CAPABILITIES_DIR,
}


def _json_output(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


@contextlib.contextmanager
def m4_parameters() -> Iterable[None]:
    """Rebind the shared M3 machinery to this suite's paths and tokens."""

    previous = {name: getattr(m3, name) for name in _M4_BINDINGS}
    for name, value in _M4_BINDINGS.items():
        setattr(m3, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(m3, name, value)


def assert_bound_contracts() -> int:
    """Assert every contract token this suite binds by reference."""

    bindings = (
        ("PLAN_SPEC", m3.PLAN_SPEC, PLAN_SPEC),
        ("PLAN_CONTRACTS", m3.PLAN_CONTRACTS, PLAN_CONTRACTS),
        ("JOURNAL_SPEC", m3.JOURNAL_SPEC, JOURNAL_SPEC),
        ("SHARED_DIR", m3.SHARED_DIR, SHARED_DIR),
    )
    for name, actual, expected in bindings:
        if actual != expected:
            raise FixtureError(
                f"M3 harness {name} is {actual!r}, expected {expected!r}"
            )
    if m3.ACTIVATION_PROFILE_SPEC != "activation-fixture/v2":
        raise FixtureError("activation profile contract drifted")
    if m3.WRITE_CAPABILITY_SPEC != "write-capability-fixture/v1":
        raise FixtureError("write capability contract drifted")
    if m3.DECISION_SPEC != "replay-decision-fixture/v1":
        raise FixtureError("replay decision contract drifted")
    if m3.PLAN_VALIDATOR_SPEC != "sync-plan-validator/v1":
        raise FixtureError("plan validator contract drifted")
    if m3.PLAN_DIAGNOSTIC_SPEC != "sync-plan-diagnostic/v1":
        raise FixtureError("plan diagnostic contract drifted")
    if "hooks-carrier-composition" not in m3.PLAN_VALIDATOR_FAILURES:
        raise FixtureError("hooks-carrier-composition failure id is absent")
    if m3.HOOK_ROW_TIERS != {"native", "semantic", "declared-unsynced"}:
        raise FixtureError("hook row tier registry drifted")
    if HOOK_FENCE_SCAN_SPEC != "hook-fence-scan/v1":
        raise FixtureError("hook fence scan contract drifted")
    if (
        HOOK_FENCE_COMMAND_PATTERN.pattern
        != r"^bridge-fixture-noop( [a-z0-9-]+)?$"
    ):
        raise FixtureError("hook fence command grammar drifted")
    return len(bindings) + 9


def _m3_closed_field_sets() -> Tuple[
    Optional[frozenset], Optional[frozenset]
]:
    """Recover the shared validator's two closed field sets when visible.

    Both sets are constant displays inside `m3._validate_scenario`, which
    CPython folds into frozenset constants. They are matched by anchor
    members rather than by position, and an interpreter that does not fold
    them yields `None`, which leaves the behavioural probe below as the
    only guarantee.
    """

    candidates = [
        value
        for value in m3._validate_scenario.__code__.co_consts
        if isinstance(value, frozenset)
        and all(isinstance(item, str) for item in value)
    ]
    scenarios = [
        value
        for value in candidates
        if {"baseline", "expectations", "id", "input", "spec"} <= value
    ]
    replays = [
        value
        for value in candidates
        if {"decision_fixture", "id", "rendered_state"} <= value
        and "spec" not in value
    ]
    return (
        scenarios[0] if len(scenarios) == 1 else None,
        replays[0] if len(replays) == 1 else None,
    )


def assert_scenario_field_closure() -> int:
    """Assert the trees-only field closure stays inside the shared one.

    `validate_matrix` reads a scenario with the shared validator when the
    scenario is selected and with `_validate_scenario_trees` when it is
    not, so the two closed field sets must not drift apart. The shared set
    is a local inside `m3._validate_scenario`, so it is probed twice: a
    scenario document carrying one field and nothing else fails on the spec
    header, never on the closure, exactly when the shared validator admits
    that field, and where the interpreter exposes the folded constants the
    two closures are compared for exact equality in both directions.
    """

    def admitted(field: str) -> bool:
        try:
            m3._validate_scenario(
                {field: None},
                default_activation_profile="",
                default_write_capability_fixture="",
            )
        except FixtureError as error:
            return "scenario contains unknown fields" not in str(error)
        return True

    unknown = sorted(
        field for field in SCENARIO_FIELDS if not admitted(field)
    )
    if unknown:
        raise FixtureError(
            f"trees-only scenario fields left the shared closure: {unknown}"
        )
    if admitted("not-a-scenario-field"):
        raise FixtureError("the shared scenario field set is not closed")
    scenario_fields, replay_fields = _m3_closed_field_sets()
    if scenario_fields is None or replay_fields is None:
        return 2
    if set(scenario_fields) != SCENARIO_FIELDS:
        raise FixtureError(
            "trees-only scenario fields differ from the shared closure: "
            f"{sorted(set(scenario_fields) ^ SCENARIO_FIELDS)}"
        )
    if set(replay_fields) != REPLAY_INPUT_FIELDS:
        raise FixtureError(
            "trees-only replay input fields differ from the shared "
            "closure: "
            f"{sorted(set(replay_fields) ^ REPLAY_INPUT_FIELDS)}"
        )
    return 4


# ---------------------------------------------------------------------------
# Hook rules the shared M3 machinery does not carry
# ---------------------------------------------------------------------------
#
# `fixtures/m3-rules/fixture_harness.py` owns the sync-plan/v3 document
# grammar, and this suite never forks it. Four of its checks reject a hook
# shape M4 introduces: the public tier authentication, the mutating-action
# authorization rule, the post-write carrier-touch predicate, and the
# warning detail grammar. The rules below widen exactly those four and
# nothing else. They are rebound onto the shared module for the duration of
# a call, every non-hook row still reaches the shared function untouched,
# and a sibling rule the shared function already carries, such as the
# `awaiting-host-trust` predicate for a `hooks/<entry-id>/codex` row, is
# delegated rather than restated.

_M3_VALIDATE_PUBLIC_UNIT_TIERS = m3._validate_public_unit_tiers
_M3_VALIDATE_ROW_SEMANTICS = m3._validate_row_semantics
_M3_VALIDATE_CARRIER_ANNOTATION_TIMING = m3._validate_carrier_annotation_timing

# sync-plan-spec.md closes `behavior-degraded` on a hook row: attach it to
# every row whose declared tier is `semantic` and to every row whose owned
# handler carries a host passthrough or unknown Codex key. It therefore
# accompanies a pinned decision or conflict annotation set exactly as
# `awaiting-host-trust` and `event-unverified` do.
HOOK_NEUTRAL_ANNOTATIONS = m3.HOOK_NEUTRAL_ANNOTATIONS | {"behavior-degraded"}
HOOK_CONFLICT_EXTRA_ANNOTATIONS = HOOK_NEUTRAL_ANNOTATIONS | {
    "opt-in-required",
}

# sync-plan-spec.md pins the `undeclared-hooks-key` detail to the exact
# declared matcher string, and a declared matcher is a regular expression such
# as `^(Edit)$`, so a warning detail carries parentheses. The warning path
# itself stays free of spaces and parentheses.
WARNING_LINE_PATTERN = re.compile(
    r"^- ([a-z][a-z0-9-]*): (\.|[^ ()]+)(?: (\(.+\)))?$"
)
HOOK_UNDECLARED_KEY_DETAIL_PATTERN = re.compile(
    rf"{m3.HOOK_EVENT} matcher=[^\r\n]+"
)


# Returned when no reachable intent document declares the entry at all, which
# is the shape of a proven managed deletion rather than a tier mismatch.
HOOK_ENTRY_ABSENT = "hook-entry-absent"
# The intent document reachable at the marker's baseline commit, published
# for the duration of one plan validation. A managed deletion removes the
# entry from the working tree, so the declaration that authenticates its
# tier survives only in reachable Git; reading it there keeps the oracle
# independent of the document being validated.
_BASELINE_HOOK_TREE: Dict[str, Any] = {}
# The row cells that prove a managed hook projection deletion: the source
# document no longer declares the entry, and the plan removes the projection
# in the source-to-projection direction.
HOOK_DELETION_ROW = ("source-only", "delete", "source-to-projection")


def _authenticated_hook_tier(
    unit: str,
    *,
    input_tree: Mapping[str, Any],
    rendered_tree: Mapping[str, Any],
) -> Optional[str]:
    """Read a hook row's public tier from the authenticated intent document.

    sync-plan-spec.md forbids deriving a hook tier from a host capability
    table: it is `targets.<host>.tier` in the same `.claude/rules/hooks.md`
    entry, and `-` for the source row. The rendered state answers first so a
    rewritten entry authenticates against the bytes the operation leaves
    behind, then the input bytes, then the intent document reachable at the
    baseline commit, which is the only surviving declaration of a managed
    deletion. The result is `HOOK_ENTRY_ABSENT` when no reachable document
    declares the entry.
    """

    host = m3._hook_unit_host(unit)
    if host == "source":
        return "-"
    entry_id = unit.split("/")[1]
    for tree in (rendered_tree, input_tree, _BASELINE_HOOK_TREE):
        document = tree.get(HOOK_INTENT_DOCUMENT)
        if (
            not isinstance(document, dict)
            or document.get("type") != "file"
            or not isinstance(document.get("bytes"), bytes)
        ):
            continue
        for entry in inspect_hook_intents(document["bytes"])["entries"]:
            if entry["id"] != entry_id:
                continue
            for target in entry["authenticated"]:
                if target["host"] == host:
                    return target["tier"]
            return None
    return HOOK_ENTRY_ABSENT


def _deleted_hook_tier(
    plan: Mapping[str, Any],
    row: Sequence[str],
) -> Optional[str]:
    """Authenticate a deleted hook row against its `## Hook tiers` row.

    This is the last resort, not the rule. `_authenticated_hook_tier` reads
    the intent document reachable at the baseline commit first, so a managed
    deletion normally authenticates against a declaration the plan cannot
    influence. Only when the baseline commit itself never declared the entry
    is there nothing left but the plan's own `## Hook tiers` row, which
    still states the class, surface, tier and reason the removed projection
    had. That reading is circular, so it is refused unless the row
    serializes the closed deletion shape.
    """

    if (row[4], row[5], row[6]) != HOOK_DELETION_ROW:
        return None
    for tier_row in plan.get("hook_tiers", ()):
        if tier_row[0] == row[0]:
            return tier_row[3]
    return None


def _git_blob_bytes(
    root: Path, commit: str, relative: str
) -> Optional[bytes]:
    """Read one path's exact bytes at a commit, or None when it is absent."""

    process = subprocess.run(
        ["git", "-C", str(root), "cat-file", "blob", f"{commit}:{relative}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        return None
    return process.stdout


@contextlib.contextmanager
def _published_baseline(document: Optional[bytes]) -> Iterable[None]:
    """Publish one intent document as the baseline oracle."""

    global _BASELINE_HOOK_TREE
    previous = _BASELINE_HOOK_TREE
    _BASELINE_HOOK_TREE = (
        {}
        if document is None
        else {HOOK_INTENT_DOCUMENT: {"type": "file", "bytes": document}}
    )
    try:
        yield
    finally:
        _BASELINE_HOOK_TREE = previous


@contextlib.contextmanager
def baseline_hook_declarations(
    root: Path, baseline_commit: Optional[str]
) -> Iterable[None]:
    """Publish the intent document reachable at the baseline commit.

    The bytes come from reachable Git, never from the plan under
    validation and never from the working tree, so a deleted hook row is
    authenticated against the declaration the deletion removed. When the
    marker or the commit cannot be resolved nothing is published and
    `_deleted_hook_tier` keeps its documented last resort.
    """

    document = (
        None
        if baseline_commit is None
        else _git_blob_bytes(root, baseline_commit, HOOK_INTENT_DOCUMENT)
    )
    with _published_baseline(document):
        yield


# The shared plan validator reaches these three rules through the module
# globals `m4_parameters` rebinds. Nothing in the shared module promises to
# keep doing that, so each override counts its own calls and `self-test`
# refuses a run in which one of them never fired.
_ROUTING_COUNTS: Dict[str, int] = {
    "carrier_annotation_timing": 0,
    "public_unit_tiers": 0,
    "row_semantics": 0,
}


def _validate_public_unit_tiers(
    plan: Mapping[str, Any],
    *,
    input_tree: Mapping[str, Any],
    rendered_tree: Mapping[str, Any],
) -> None:
    """Authenticate every unit tier, hook rows included."""

    _ROUTING_COUNTS["public_unit_tiers"] += 1
    hook_rows = [
        row for row in plan["rows"] if m3._hook_unit_host(row[0]) is not None
    ]
    _M3_VALIDATE_PUBLIC_UNIT_TIERS(
        dict(
            plan,
            rows=[
                row
                for row in plan["rows"]
                if m3._hook_unit_host(row[0]) is None
            ],
        ),
        input_tree=input_tree,
        rendered_tree=rendered_tree,
    )
    for row in hook_rows:
        unit = row[0]
        expected = _authenticated_hook_tier(
            unit,
            input_tree=input_tree,
            rendered_tree=rendered_tree,
        )
        if expected == HOOK_ENTRY_ABSENT:
            expected = _deleted_hook_tier(plan, row)
        if expected is None:
            raise FixtureError(
                f"unit {unit!r} has no authenticated public tier mapping"
            )
        if row[9] != expected:
            raise FixtureError(
                f"unit {unit!r} tier {row[9]!r} differs from authenticated "
                f"public tier {expected!r}"
            )


def _validate_row_semantics(
    path: Path,
    *,
    unit: str,
    phase: str,
    selection: str,
    state: str,
    action: str,
    direction: str,
    authorization: str,
    outcome: str,
    annotations: Sequence[str],
) -> None:
    """Admit the narrowed blocker scope on a hook carrier row."""

    _ROUTING_COUNTS["row_semantics"] += 1
    scoped_blocked = (
        m3._hook_unit_host(unit) is not None
        and selection == "selected"
        and action in m3.MUTATING_ACTIONS
        and authorization == "not-applicable"
        and outcome == "blocked"
    )
    _M3_VALIDATE_ROW_SEMANTICS(
        path,
        unit=unit,
        phase=phase,
        selection=selection,
        state=state,
        action=action,
        direction=direction,
        # sync-plan-spec.md `Narrowed blocker scope (closed exception)`: a
        # scoped-blocked closure keeps `selected`, authorization
        # `not-applicable` and outcome `blocked`, and each of its unit rows
        # repeats that shape; canonical-plan-cases.md serializes it on a
        # `create` row. The shared rule predates the exception and accepts
        # only `required`/`planned` or `confirmed` for a mutating action, so
        # the delegated call is told the row is authorized while the exact
        # exception shape stays closed here.
        authorization="confirmed" if scoped_blocked else authorization,
        outcome=outcome,
        annotations=annotations,
    )


def _validate_carrier_annotation_timing(
    path: Path,
    *,
    unit: str,
    closure: str,
    outcome: str,
    phase: str,
    annotations: set[str],
    write_capabilities: Sequence[Tuple[str, ...]],
) -> None:
    """Follow the two degradation annotations to the root `AGENTS.md` write.

    sync-plan-spec.md attaches `live-activation-unknown` and
    `restart-may-be-required` to a `hooks/<entry-id>/codex` row on the
    `agents-md` surface whose degradation block was written into root
    `AGENTS.md`. That is the whole hook branch. `awaiting-host-trust` on a
    `hooks/<entry-id>/codex` row whose `.codex/hooks.json` carrier was
    written is a rule the shared function already carries, so it is
    delegated: the two degradation annotations are withheld from the
    delegated call, which then answers for every other annotation exactly
    as it does for a non-hook row, and only the withheld pair is decided
    here.
    """

    _ROUTING_COUNTS["carrier_annotation_timing"] += 1
    degraded_annotations = {
        "live-activation-unknown",
        "restart-may-be-required",
    }
    hook_row = m3._hook_unit_host(unit) is not None
    _M3_VALIDATE_CARRIER_ANNOTATION_TIMING(
        path,
        unit=unit,
        closure=closure,
        outcome=outcome,
        phase=phase,
        annotations=(
            annotations - degraded_annotations if hook_row else annotations
        ),
        write_capabilities=write_capabilities,
    )
    if not hook_row:
        return
    degraded_carrier_written = (
        phase == "post-write"
        and outcome in {"applied", "partial"}
        and m3._hook_unit_host(unit) == "codex"
        and any(
            operation[1] == closure and operation[2] == "AGENTS.md"
            for operation in write_capabilities
        )
    )
    for annotation in sorted(degraded_annotations):
        if (annotation in annotations) != degraded_carrier_written:
            raise FixtureError(
                f"{path}: {annotation} does not match post-write "
                f"carrier-touch timing for {unit}"
            )


_M4_BINDINGS.update(
    {
        "HOOK_CONFLICT_EXTRA_ANNOTATIONS": HOOK_CONFLICT_EXTRA_ANNOTATIONS,
        "HOOK_NEUTRAL_ANNOTATIONS": HOOK_NEUTRAL_ANNOTATIONS,
        "HOOK_UNDECLARED_KEY_DETAIL_PATTERN": (
            HOOK_UNDECLARED_KEY_DETAIL_PATTERN
        ),
        "WARNING_LINE_PATTERN": WARNING_LINE_PATTERN,
        "_validate_carrier_annotation_timing": (
            _validate_carrier_annotation_timing
        ),
        "_validate_public_unit_tiers": _validate_public_unit_tiers,
        "_validate_row_semantics": _validate_row_semantics,
    }
)


def assert_hook_rule_overrides() -> int:
    """Assert the hook branches this suite adds to the shared machinery."""

    if not m3.HOOK_NEUTRAL_ANNOTATIONS <= HOOK_NEUTRAL_ANNOTATIONS:
        raise FixtureError("neutral hook annotation override lost a token")
    if "behavior-degraded" not in HOOK_NEUTRAL_ANNOTATIONS:
        raise FixtureError(
            "behavior-degraded is not a neutral hook annotation"
        )
    detail = "PostToolUse matcher=^(Edit)$"
    line = f"- undeclared-hooks-key: .claude/settings.json ({detail})"
    match = WARNING_LINE_PATTERN.fullmatch(line)
    if match is None or match.group(3) != f"({detail})":
        raise FixtureError("warning grammar rejects a regular matcher detail")
    if HOOK_UNDECLARED_KEY_DETAIL_PATTERN.fullmatch(detail) is None:
        raise FixtureError("undeclared key detail rejects a regular matcher")
    plain = "- active-shared-import: . (@shared)"
    spaced = "- local-hooks-present: a b"
    if (
        WARNING_LINE_PATTERN.fullmatch(plain) is None
        or WARNING_LINE_PATTERN.fullmatch(spaced) is not None
    ):
        raise FixtureError("warning grammar no longer closes the path field")
    if (
        _authenticated_hook_tier(
            "hooks/fence/source", input_tree={}, rendered_tree={}
        )
        != "-"
    ):
        raise FixtureError("a hook source row must authenticate tier '-'")
    deleted = "hooks/stale-check/codex"
    if (
        _authenticated_hook_tier(
            deleted, input_tree={}, rendered_tree={}
        )
        != HOOK_ENTRY_ABSENT
    ):
        raise FixtureError(
            "a removed entry must read as absent without a baseline"
        )
    declaration = (HERE / "shared" / "hooks-stale-check.md").read_bytes()
    with _published_baseline(declaration):
        if (
            _authenticated_hook_tier(
                deleted, input_tree={}, rendered_tree={}
            )
            != "native"
        ):
            raise FixtureError(
                "a deleted hook row must authenticate against the "
                "declaration reachable at its baseline commit"
            )
    return 8


def assert_hook_rule_routing(before: Mapping[str, int]) -> int:
    """Prove the shared machinery still routed through every override."""

    for name, count in sorted(_ROUTING_COUNTS.items()):
        if count <= before[name]:
            raise FixtureError(
                "the shared plan validator never routed through the M4 "
                f"{name} rule"
            )
    return len(_ROUTING_COUNTS)


# ---------------------------------------------------------------------------
# Fixture hook fence
# ---------------------------------------------------------------------------


def _mirror_shared_trees(mirror: Path) -> Dict[str, str]:
    """Copy every shared tree file under the carrier name its bytes stand for."""

    mapping: Dict[str, str] = {}
    index = 0
    for relative_tree in FENCE_SHARED_TREES:
        root = FIXTURES_ROOT / relative_tree
        if not root.is_dir():
            raise FixtureError(
                f"fence shared tree is missing: {relative_tree}"
            )
        for path in sorted(root.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            carrier = FENCE_MIRROR_NAMES.get(path.suffix)
            if carrier is None:
                if path.suffix in FENCE_IGNORED_SUFFIXES:
                    continue
                raise FixtureError(
                    "fence mirror has no carrier name for "
                    f"{path.relative_to(REPO_ROOT).as_posix()}"
                )
            index += 1
            target = mirror / f"shared-{index:04d}" / carrier
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            mapping[
                target.relative_to(mirror).as_posix()
            ] = path.relative_to(REPO_ROOT).as_posix()
    return mapping


def check_hook_fence() -> Dict[str, Any]:
    """Assert the closed no-op grammar over the complete fixture tree."""

    tree = scan_hook_fence(FIXTURES_ROOT)
    contract = tree["contract"]
    violations = [
        dict(item, path=f"fixtures/{item['path']}")
        for item in tree["violations"]
    ]
    unreadable = [f"fixtures/{item}" for item in tree["unreadable"]]
    checked = [f"fixtures/{item}" for item in tree["checked"]]
    values = tree["values"]
    with tempfile.TemporaryDirectory(prefix="bridge-m4-fence-") as raw:
        mirror = Path(raw)
        mapping = _mirror_shared_trees(mirror)
        shared = scan_hook_fence(mirror)
        if shared["contract"] != contract:
            raise FixtureError("hook fence scans disagree on the contract")
        values += shared["values"]
        for item in shared["violations"]:
            violations.append(dict(item, path=mapping[item["path"]]))
        for item in shared["unreadable"]:
            unreadable.append(mapping[item])
        for item in shared["checked"]:
            checked.append(mapping[item])
    return {
        "contract": contract,
        "root": "fixtures",
        "ok": not violations,
        "checked": sorted(checked),
        "unreadable": sorted(unreadable),
        "values": values,
        "violations": sorted(
            violations, key=lambda item: (item["path"], item["location"])
        ),
    }


# ---------------------------------------------------------------------------
# Matrix validation
# ---------------------------------------------------------------------------


def _named_tree(name: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(name, str) or not name:
        raise FixtureError(f"{label}: tree name must be a non-empty string")
    return m3.resolve_named_tree(
        HERE,
        TREE_MANIFEST,
        name,
        shared_dir=SHARED_DIR,
    )


def _token_list(value: Any, *, label: str) -> List[str]:
    if (
        not isinstance(value, list)
        or not value
        or value != sorted(set(value))
        or not all(
            isinstance(item, str) and m3.TOKEN_PATTERN.fullmatch(item)
            for item in value
        )
    ):
        raise FixtureError(f"{label} must be sorted unique tokens")
    return list(value)


def _validate_scenario_trees(
    scenario: Mapping[str, Any],
    *,
    default_activation_profile: str,
    default_write_capability_fixture: str,
) -> Dict[str, Any]:
    """Validate everything that does not read an expectation, decision or plan."""

    if not isinstance(scenario, dict) or set(scenario) - SCENARIO_FIELDS:
        raise FixtureError("scenario contains unknown fields")
    if scenario.get("spec") != SCENARIO_SPEC:
        raise FixtureError(f"scenario expected spec {SCENARIO_SPEC}")
    scenario_id = scenario.get("id")
    if (
        not isinstance(scenario_id, str)
        or m3.TOKEN_PATTERN.fullmatch(scenario_id) is None
    ):
        raise FixtureError("scenario id must be a lowercase token")
    if not isinstance(scenario.get("summary"), str) or not scenario["summary"]:
        raise FixtureError(f"{scenario_id}: summary must be non-empty")
    replay = scenario.get("replay")
    if replay not in m3.REPLAY_MODES:
        raise FixtureError(f"{scenario_id}: invalid replay mode")
    workflow = scenario.get("workflow")
    if (
        not isinstance(workflow, list)
        or not workflow
        or not all(isinstance(step, str) and step for step in workflow)
    ):
        raise FixtureError(f"{scenario_id}: workflow must document replay steps")
    reason = scenario.get("replay_reason")
    fault = scenario.get("fault")
    if replay == "declarative-only":
        if not isinstance(reason, str) or not reason:
            raise FixtureError(
                f"{scenario_id}: declarative-only needs replay_reason"
            )
        if fault is None:
            raise FixtureError(
                f"{scenario_id}: declarative-only needs an explicit fault"
            )
        m3._validate_fault(scenario_id, fault)
    elif reason is not None or fault is not None:
        raise FixtureError(
            f"{scenario_id}: agent replay may not declare a synthetic boundary"
        )
    _token_list(scenario.get("coverage"), label=f"{scenario_id}: coverage")
    _token_list(scenario.get("safeguards"), label=f"{scenario_id}: safeguards")
    baseline = _named_tree(
        scenario.get("baseline"), label=f"{scenario_id}: baseline"
    )
    input_tree = _named_tree(scenario.get("input"), label=f"{scenario_id}: input")
    history = m3._validate_history(scenario_id, scenario.get("history"))
    activation_profile = m3._load_activation_profile(
        scenario.get("activation_profile", default_activation_profile)
    )
    write_capability = m3._load_write_capability_fixture(
        scenario.get(
            "write_capability_fixture", default_write_capability_fixture
        )
    )
    declarations = scenario.get("replay_inputs")
    if declarations is None:
        declarations = [
            {
                key: value
                for key, value in {
                    "id": scenario_id,
                    "decision_fixture": scenario.get("decision_fixture"),
                    "fault_schedule_fixture": scenario.get(
                        "fault_schedule_fixture"
                    ),
                    "rendered_state": scenario.get("rendered_state"),
                }.items()
                if value is not None
            }
        ]
    elif any(
        field in scenario
        for field in (
            "decision_fixture",
            "fault_schedule_fixture",
            "rendered_state",
        )
    ):
        raise FixtureError(
            f"{scenario_id}: scenario-level replay facts conflict with "
            "replay_inputs"
        )
    if not isinstance(declarations, list) or not declarations:
        raise FixtureError(f"{scenario_id}: replay_inputs must be non-empty")
    replay_inputs: Dict[str, Dict[str, Any]] = {}
    replay_ids: List[str] = []
    for declaration in declarations:
        if (
            not isinstance(declaration, dict)
            or set(declaration) - REPLAY_INPUT_FIELDS
        ):
            raise FixtureError(
                f"{scenario_id}: replay input fields are not closed"
            )
        replay_id = declaration.get("id")
        if (
            not isinstance(replay_id, str)
            or m3.TOKEN_PATTERN.fullmatch(replay_id) is None
        ):
            raise FixtureError(f"{scenario_id}: invalid replay input id")
        rendered_name = declaration.get("rendered_state")
        rendered_tree = (
            None
            if rendered_name is None
            else _named_tree(
                rendered_name, label=f"{scenario_id}/{replay_id}: rendered_state"
            )
        )
        schedule_name = declaration.get("fault_schedule_fixture")
        fault_schedule = (
            None
            if schedule_name is None
            else m3._load_fault_schedule_fixture(
                schedule_name, input_tree=input_tree
            )
        )
        replay_ids.append(replay_id)
        replay_inputs[replay_id] = {
            "id": replay_id,
            "decision": None,
            "rendered_tree": rendered_tree,
            "fault_schedule": fault_schedule,
        }
    if replay_ids != sorted(set(replay_ids)):
        raise FixtureError(
            f"{scenario_id}: replay input ids must be sorted and unique"
        )
    expectations = scenario.get("expectations")
    if not isinstance(expectations, list) or not expectations:
        raise FixtureError(f"{scenario_id}: expectations must be non-empty")
    ids: List[str] = []
    assigned: set[str] = set()
    for expectation in expectations:
        if not isinstance(expectation, dict):
            raise FixtureError(f"{scenario_id}: expectation must be an object")
        expectation_id = expectation.get("id")
        if (
            not isinstance(expectation_id, str)
            or m3.TOKEN_PATTERN.fullmatch(expectation_id) is None
        ):
            raise FixtureError(f"{scenario_id}: invalid expectation id")
        ids.append(expectation_id)
        assigned.update(
            _token_list(
                expectation.get("covers"),
                label=f"{scenario_id}/{expectation_id}: covers",
            )
        )
        plan = expectation.get("plan")
        if (
            not isinstance(plan, str)
            or not plan.startswith("expectations/")
            or not plan.endswith(".md")
        ):
            raise FixtureError(
                f"{scenario_id}/{expectation_id}: plan must name an "
                "expectations/*.md document"
            )
        m3.safe_relative(
            plan, field=f"{scenario_id}/{expectation_id} expectation plan"
        )
        _named_tree(
            expectation.get("post_state"),
            label=f"{scenario_id}/{expectation_id}: post_state",
        )
        replay_id = expectation.get("replay_input", scenario_id)
        if replay_id not in replay_inputs:
            raise FixtureError(
                f"{scenario_id}/{expectation_id}: unknown replay_input "
                f"{replay_id!r}"
            )
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise FixtureError(
            f"{scenario_id}: expectation ids must be sorted and unique"
        )
    if assigned != set(scenario["coverage"]):
        raise FixtureError(
            f"{scenario_id}: expectation coverage union differs from scenario"
        )
    return {
        "definition": scenario,
        "baseline": baseline,
        "input": input_tree,
        "activation_profile": activation_profile,
        "write_capability": write_capability,
        "replay_inputs": replay_inputs,
        "history": history,
        "expectations": [],
        "expectations_validated": False,
    }


def validate_matrix(
    *,
    scenarios: Optional[Sequence[str]] = None,
    trees_only: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Validate the matrix, its trees, and the selected scenarios in full.

    Trees, activation profiles, write capabilities and fault declarations are
    always validated. Expectation documents, decision fixtures and plan bytes
    are validated only for the selected scenarios, and never under
    `trees_only`.
    """

    selected: Optional[set[str]] = None
    if scenarios is not None:
        selected = set(scenarios)
    with m4_parameters():
        matrix = m3._load_matrix()
        parsed: Dict[str, Dict[str, Any]] = {}
        ids: List[str] = []
        replay_ids: List[str] = []
        coverage: set[str] = set()
        safeguards: set[str] = set()
        for scenario in matrix["scenarios"]:
            scenario_id = (
                scenario.get("id") if isinstance(scenario, dict) else None
            )
            full = (
                not trees_only
                and (selected is None or scenario_id in selected)
            )
            if full:
                result = m3._validate_scenario(
                    scenario,
                    default_activation_profile=matrix[
                        "default_activation_profile"
                    ],
                    default_write_capability_fixture=matrix[
                        "default_write_capability_fixture"
                    ],
                )
                result["expectations_validated"] = True
            else:
                result = _validate_scenario_trees(
                    scenario,
                    default_activation_profile=matrix[
                        "default_activation_profile"
                    ],
                    default_write_capability_fixture=matrix[
                        "default_write_capability_fixture"
                    ],
                )
            scenario_id = result["definition"]["id"]
            ids.append(scenario_id)
            replay_ids.extend(result["replay_inputs"])
            coverage.update(result["definition"]["coverage"])
            safeguards.update(result["definition"]["safeguards"])
            parsed[scenario_id] = result
    if len(ids) != len(set(ids)):
        raise FixtureError("scenario ids must be unique")
    if tuple(ids) != SCENARIO_ORDER:
        raise FixtureError(
            "scenario order must equal the design record's table order "
            "followed by the appended scenarios"
        )
    if len(replay_ids) != len(set(replay_ids)):
        raise FixtureError("replay input ids must be globally unique")
    if coverage != set(matrix["required_coverage"]):
        raise FixtureError(
            "matrix coverage union differs from required_coverage"
        )
    if safeguards != set(matrix["required_safeguards"]):
        raise FixtureError(
            "matrix safeguard union differs from required_safeguards"
        )
    modes = {item["definition"]["replay"] for item in parsed.values()}
    if modes != m3.REPLAY_MODES:
        raise FixtureError("matrix must exercise both replay modes")
    if selected is not None:
        unknown = sorted(selected - set(parsed))
        if unknown:
            raise FixtureError(f"unknown scenario filter {unknown!r}")
    return matrix, parsed


def _scenario_filter(values: Optional[Sequence[str]]) -> Optional[List[str]]:
    if not values:
        return None
    ordered = sorted(set(values))
    return ordered


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def _scenario(scenario_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    _, parsed = validate_matrix(scenarios=[scenario_id])
    try:
        result = parsed[scenario_id]
    except KeyError as error:
        raise FixtureError(f"unknown scenario {scenario_id!r}") from error
    return result["definition"], result


def _owning_scenario(replay_id: str) -> str:
    document = m3.read_json(MATRIX_PATH)
    matches: List[str] = []
    for scenario in document.get("scenarios", []):
        if not isinstance(scenario, dict):
            continue
        scenario_id = scenario.get("id")
        declarations = scenario.get("replay_inputs")
        if declarations is None:
            candidates = [scenario_id]
        elif isinstance(declarations, list):
            candidates = [
                item.get("id")
                for item in declarations
                if isinstance(item, dict)
            ]
        else:
            candidates = []
        if replay_id in candidates:
            matches.append(scenario_id)
    if len(matches) != 1:
        raise FixtureError(
            f"expected one replay input {replay_id!r}, found {len(matches)}"
        )
    return matches[0]


def _replay_input_by_id(
    replay_id: str,
) -> Tuple[str, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    scenario_id = _owning_scenario(replay_id)
    definition, parsed = _scenario(scenario_id)
    replay_input = parsed["replay_inputs"].get(replay_id)
    if replay_input is None:
        raise FixtureError(f"unknown replay input {replay_id!r}")
    return scenario_id, definition, parsed, replay_input


def _expectation(
    parsed: Mapping[str, Any], expectation_id: str
) -> Mapping[str, Any]:
    matches = [
        item
        for item in parsed["expectations"]
        if item["definition"]["id"] == expectation_id
    ]
    if len(matches) != 1:
        raise FixtureError(f"expected one expectation {expectation_id!r}")
    return matches[0]


def _lifecycle(plan: Mapping[str, Any], definition: Mapping[str, Any]) -> str:
    if plan["headers"]["phase"] != "post-write":
        return "prepared"
    if definition.get("fault") is not None:
        return "partial"
    return "verified"


# ---------------------------------------------------------------------------
# Self test
# ---------------------------------------------------------------------------


def run_self_test(
    *, scenarios: Optional[Sequence[str]] = None
) -> Dict[str, Any]:
    """Validate declarations, leased materialization, trees and plan shape."""

    with m4_parameters():
        m3._validate_covenant_assets()
    contract_checks = (
        assert_bound_contracts()
        + assert_hook_rule_overrides()
        + assert_scenario_field_closure()
        + 1
    )
    fence = check_hook_fence()
    if not fence["ok"]:
        raise FixtureError(
            "fixture hook fence rejected "
            f"{len(fence['violations'])} command values: "
            + "; ".join(
                f"{item['path']} {item['location']} {item['key']}"
                for item in fence["violations"][:5]
            )
        )
    if fence["unreadable"] != FENCE_UNREADABLE_ALLOWLIST:
        raise FixtureError(
            f"unexpected unreadable hook carriers: {fence['unreadable']}"
        )
    if (
        len(fence["checked"]) < FENCE_MIN_CARRIERS
        or fence["values"] < FENCE_MIN_VALUES
    ):
        raise FixtureError(
            "the hook fence lost coverage: "
            f"{len(fence['checked'])} carriers and {fence['values']} "
            f"values, floors {FENCE_MIN_CARRIERS} and {FENCE_MIN_VALUES}"
        )
    fence_checks = 3
    selected = _scenario_filter(scenarios)
    matrix, parsed = validate_matrix(scenarios=selected)
    matrix_checks = 1
    replay_counts = {
        mode: sum(
            item["definition"]["replay"] == mode for item in parsed.values()
        )
        for mode in sorted(m3.REPLAY_MODES)
    }
    replay_input_counts = {
        mode: sum(
            len(item["replay_inputs"])
            for item in parsed.values()
            if item["definition"]["replay"] == mode
        )
        for mode in sorted(m3.REPLAY_MODES)
    }
    driven = [
        item for item in parsed.values() if item["expectations_validated"]
    ]
    scenario_count = len(driven)
    expectation_count = sum(
        len(item["definition"]["expectations"]) for item in driven
    )
    matrix_scenario_count = len(parsed)
    matrix_expectation_count = sum(
        len(item["definition"]["expectations"]) for item in parsed.values()
    )
    replay_checks = 0
    plan_checks = 0
    cleanup_checks = 0
    routing_before = dict(_ROUTING_COUNTS)
    with m4_parameters():
        for scenario_id, item in parsed.items():
            if not item["expectations_validated"]:
                continue
            for replay_input in item["replay_inputs"].values():
                materialized = m3.create_temp_git_project(
                    suite=SUITE,
                    scenario=scenario_id,
                    baseline=item["baseline"],
                    input_tree=item["input"],
                    history=(
                        None
                        if item["history"] is None
                        else item["history"]["commits"]
                    ),
                    history_head=(
                        None
                        if item["history"] is None
                        else item["history"]["head"]
                    ),
                )
                root = Path(materialized["worktree"])
                lease = materialized["lease"]
                published = contextlib.ExitStack()
                try:
                    m3._install_activation_profile(
                        root, item["activation_profile"]
                    )
                    m3._install_replay_input(
                        root,
                        lease=lease,
                        scenario_id=scenario_id,
                        parsed=item,
                        replay_input=replay_input,
                    )
                    input_errors = m3.compare_tree(root, item["input"])
                    if input_errors:
                        raise FixtureError(
                            f"{scenario_id}: input materialization mismatch: "
                            + "; ".join(input_errors)
                        )
                    marker = m3.validate_marker(
                        root,
                        suite=SUITE,
                        scenario=scenario_id,
                        lease=lease,
                    )
                    published.enter_context(
                        baseline_hook_declarations(
                            root, marker["baseline_commit"]
                        )
                    )
                    envelope = m3._validate_installed_replay_input(
                        root,
                        lease=lease,
                        scenario_id=scenario_id,
                        parsed=item,
                        replay_input=replay_input,
                    )
                    blind = m3._validate_blind_installed_replay_input(
                        root,
                        lease=lease,
                        replay_id=replay_input["id"],
                        require_input_tree=True,
                    )
                    if blind != envelope:
                        raise FixtureError(
                            "blind and authoring replay validators disagree"
                        )
                    public = m3._public_replay_dto(envelope)
                    if _contains_expectation_material(public):
                        raise FixtureError(
                            "blind replay input leaked expectation material"
                        )
                    replay_checks += 4
                    matching = [
                        candidate
                        for candidate in item["expectations"]
                        if candidate["replay_input"]["id"]
                        == replay_input["id"]
                    ]
                    if not matching:
                        raise FixtureError(
                            f"{scenario_id}/{replay_input['id']}: replay input "
                            "has no expectation binding"
                        )
                    for candidate in matching:
                        expectation = candidate["definition"]
                        m3.materialize_tree(root, candidate["tree"])
                        tree_errors = m3.compare_tree(root, candidate["tree"])
                        if tree_errors:
                            raise FixtureError(
                                f"{scenario_id}/{expectation['id']}: expected "
                                "tree does not round-trip: "
                                + "; ".join(tree_errors)
                            )
                        actual_path = (
                            root
                            / ".git"
                            / f"bridge-fixture-plan-{expectation['id']}.md"
                        )
                        actual_path.write_bytes(
                            m3._actual_plan_bytes(
                                candidate["plan"],
                                marker["baseline_commit"],
                                commit_refs=m3._resolved_commit_refs(
                                    expectation,
                                    baseline_commit=marker["baseline_commit"],
                                    history_commits=marker.get(
                                        "history_commits"
                                    ),
                                ),
                            )
                        )
                        actual = m3.parse_plan(actual_path, expectation=False)
                        expected = m3.bind_expected_baselines(
                            item["definition"],
                            expectation,
                            candidate["plan"],
                            initial_commit=marker["baseline_commit"],
                            history_commits=marker.get("history_commits"),
                        )
                        differences = m3.compare_plans(expected, actual)
                        if differences:
                            raise FixtureError(
                                f"{scenario_id}/{expectation['id']}: plan "
                                "self-compare failed: "
                                + "; ".join(differences)
                            )
                        lifecycle = _lifecycle(actual, item["definition"])
                        validation = m3._validate_plan_result(
                            replay_input=replay_input["id"],
                            root=root,
                            lease=lease,
                            plan_path=actual_path,
                            lifecycle=lifecycle,
                        )
                        if (
                            validation["contract"] != m3.PLAN_VALIDATOR_SPEC
                            or not validation["pass"]
                            or validation["failures"]
                        ):
                            raise FixtureError(
                                f"{scenario_id}/{expectation['id']}: formal "
                                f"validator rejected the plan: {validation}"
                            )
                        # The formal validator answers pass/fail on the
                        # closed failure ids. The diagnostic companion also
                        # derives the public warning lines the context
                        # requires, so it catches a warning line an
                        # expectation emits or drops without the public
                        # evidence for it.
                        explained = m3._explain_plan_result(
                            replay_input=replay_input["id"],
                            root=root,
                            lease=lease,
                            plan_path=actual_path,
                            lifecycle=lifecycle,
                        )
                        if (
                            explained["contract"] != m3.PLAN_DIAGNOSTIC_SPEC
                            or explained["failures"]
                            or explained["diagnostics"]
                        ):
                            raise FixtureError(
                                f"{scenario_id}/{expectation['id']}: plan "
                                f"diagnostics are not empty: {explained}"
                            )
                        plan_checks += 4
                finally:
                    published.close()
                    if root.exists():
                        m3.cleanup_leased_project(
                            root,
                            suite=SUITE,
                            scenario=scenario_id,
                            lease=lease,
                        )
                        cleanup_checks += 1
    routing_checks = (
        assert_hook_rule_routing(routing_before) if plan_checks else 0
    )
    check_accounting = {
        "cleanup": cleanup_checks,
        "contracts": contract_checks,
        "fence": fence_checks,
        "matrix": matrix_checks,
        "plan": plan_checks,
        "replay": replay_checks,
        "routing": routing_checks,
    }
    checks = sum(check_accounting.values())
    return {
        "pass": True,
        "spec": MATRIX_SPEC,
        "suite": SUITE,
        "checks": checks,
        "check_accounting": check_accounting,
        "scenarios": scenario_count,
        "scenario_filter": selected,
        "matrix_scenarios": matrix_scenario_count,
        "matrix_expectations": matrix_expectation_count,
        "expectations": expectation_count,
        "replay": replay_counts,
        "replay_inputs": {
            "agent": replay_input_counts["agent"],
            "declarative-only": replay_input_counts["declarative-only"],
            "total": sum(replay_input_counts.values()),
        },
        "coverage_tokens": len(matrix["required_coverage"]),
        "safeguards": len(matrix["required_safeguards"]),
        "fence": {
            "contract": fence["contract"],
            "ok": fence["ok"],
            "carriers": len(fence["checked"]),
            "values": fence["values"],
            "unreadable": fence["unreadable"],
        },
        "plan_spec": PLAN_SPEC,
        "plan_contracts": PLAN_CONTRACTS,
        "validator_spec": m3.PLAN_VALIDATOR_SPEC,
        "diagnostic_spec": m3.PLAN_DIAGNOSTIC_SPEC,
        "journal_spec": JOURNAL_SPEC,
        "journal_binding": JOURNAL_BINDING,
        "workflow_executed": False,
        "replay_boundary": (
            "The harness validates declarations, leased materialization, "
            "expected trees, sync-plan/v3 shape, and the fixture hook fence. "
            "It never runs bridge-sync and never starts a host; an agent must "
            "run $bridge-sync for agent scenarios. The live journal contract "
            "bridge-live-operation-journal/v2 is bound by reference and its "
            "suite is not re-run here."
        ),
    }


FORBIDDEN_PUBLIC_KEYS = {
    "expectation",
    "expectations",
    "expected_plan_path",
    "golden",
    "oracle",
    "plan",
    "planned_state",
    "post_state",
    "result_state",
}


def _contains_expectation_material(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(FORBIDDEN_PUBLIC_KEYS & set(value)) or any(
            _contains_expectation_material(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_expectation_material(item) for item in value)
    return False


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def command_validate_matrix(arguments: argparse.Namespace) -> int:
    if arguments.trees_only and arguments.scenario:
        raise FixtureError("--trees-only takes no --scenario filter")
    selected = _scenario_filter(arguments.scenario)
    matrix, parsed = validate_matrix(
        scenarios=selected, trees_only=arguments.trees_only
    )
    _json_output(
        {
            "pass": True,
            "spec": MATRIX_SPEC,
            "suite": SUITE,
            "trees_only": bool(arguments.trees_only),
            "scenario_filter": selected,
            "scenarios": [
                {
                    "id": scenario_id,
                    "summary": item["definition"]["summary"],
                    "replay": item["definition"]["replay"],
                    "baseline": item["definition"]["baseline"],
                    "input": item["definition"]["input"],
                    "replay_inputs": sorted(item["replay_inputs"]),
                    "expectations": [
                        expectation["id"]
                        for expectation in item["definition"]["expectations"]
                    ],
                    "expectations_validated": item["expectations_validated"],
                    "safeguards": item["definition"]["safeguards"],
                }
                for scenario_id, item in parsed.items()
            ],
            "coverage_tokens": len(matrix["required_coverage"]),
            "safeguards": len(matrix["required_safeguards"]),
            "journal_spec": JOURNAL_SPEC,
            "journal_binding": JOURNAL_BINDING,
        }
    )
    return 0


def command_check_hook_fence(_: argparse.Namespace) -> int:
    result = check_hook_fence()
    _json_output(result)
    return 0 if result["ok"] else 1


def command_self_test(arguments: argparse.Namespace) -> int:
    _json_output(run_self_test(scenarios=arguments.scenario))
    return 0


def command_materialize(arguments: argparse.Namespace) -> int:
    scenario_id, definition, parsed, replay_input = _replay_input_by_id(
        arguments.replay_input
    )
    if definition["replay"] != "agent":
        raise FixtureError(
            f"{arguments.replay_input} is declarative-only: "
            f"{definition['replay_reason']}"
        )
    with m4_parameters():
        result = m3.create_temp_git_project(
            suite=SUITE,
            scenario=scenario_id,
            baseline=parsed["baseline"],
            input_tree=parsed["input"],
            history=(
                None
                if parsed["history"] is None
                else parsed["history"]["commits"]
            ),
            history_head=(
                None if parsed["history"] is None else parsed["history"]["head"]
            ),
        )
        root = Path(result["worktree"])
        try:
            profile_path = m3._install_activation_profile(
                root, parsed["activation_profile"]
            )
            (
                capability_path,
                replay_path,
                _fault_schedule_path,
                commitment_path,
            ) = m3._install_replay_input(
                root,
                lease=result["lease"],
                scenario_id=scenario_id,
                parsed=parsed,
                replay_input=replay_input,
            )
        except Exception:
            m3.cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=result["lease"],
            )
            raise
        result.update(
            {
                "activation_profile": {
                    "path": str(profile_path),
                    "sha256": parsed["activation_profile"]["sha256"],
                    "spec": m3.ACTIVATION_PROFILE_SPEC,
                },
                "write_capability": {
                    "path": str(capability_path),
                    "sha256": m3._sha256(capability_path.read_bytes()),
                    "spec": m3.WRITE_CAPABILITY_SPEC,
                },
                "replay_commitment": {
                    "path": str(commitment_path),
                    "sha256": m3._sha256(commitment_path.read_bytes()),
                    "spec": m3.REPLAY_COMMITMENT_SPEC,
                },
                "replay_input": arguments.replay_input,
                "replay_input_path": str(replay_path),
                "replay_input_sha256": m3._sha256(replay_path.read_bytes()),
                "scenario": scenario_id,
                "suite": SUITE,
                "workflow_executed": False,
            }
        )
    _json_output(result)
    return 0


def command_replay_input(arguments: argparse.Namespace) -> int:
    with m4_parameters():
        envelope = m3._validate_blind_installed_replay_input(
            Path(arguments.worktree),
            lease=arguments.lease,
            replay_id=arguments.replay_input,
            require_input_tree=True,
        )
        payload = m3._public_replay_dto(envelope)
    _json_output(payload)
    return 0


def command_validate_plan(arguments: argparse.Namespace) -> int:
    scenario_id, _definition, _parsed, _replay = _replay_input_by_id(
        arguments.replay_input
    )
    root = Path(arguments.worktree)
    with m4_parameters():
        # A hook deletion authenticates its tier against the declaration
        # reachable at the baseline commit. The marker is read here only to
        # resolve that commit; when it cannot be read the admission contract
        # still answers on its own closed failure ids rather than raising.
        try:
            baseline_commit = m3.validate_marker(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=arguments.lease,
            )["baseline_commit"]
        except (FixtureError, OSError, UnicodeError, ValueError):
            baseline_commit = None
        with baseline_hook_declarations(root, baseline_commit):
            result = m3._validate_plan_result(
                replay_input=arguments.replay_input,
                root=root,
                lease=arguments.lease,
                plan_path=Path(arguments.plan),
                lifecycle=arguments.operation_lifecycle,
            )
    _json_output(result)
    return 0 if result["pass"] else 1


def command_compare(arguments: argparse.Namespace) -> int:
    definition, parsed = _scenario(arguments.scenario)
    item = _expectation(parsed, arguments.expectation)
    with m4_parameters():
        marker = m3.validate_marker(
            Path(arguments.worktree),
            suite=SUITE,
            scenario=arguments.scenario,
            lease=arguments.lease,
        )
        m3._validate_installed_activation_profile(
            Path(arguments.worktree), parsed["activation_profile"]
        )
        m3._validate_installed_replay_input(
            Path(arguments.worktree),
            lease=arguments.lease,
            scenario_id=arguments.scenario,
            parsed=parsed,
            replay_input=item["replay_input"],
        )
        actual = m3.parse_plan(Path(arguments.actual_plan), expectation=False)
        expected = m3.bind_expected_baselines(
            definition,
            item["definition"],
            item["plan"],
            initial_commit=marker["baseline_commit"],
            history_commits=marker.get("history_commits"),
        )
        plan_errors = m3.compare_plans(expected, actual)
        tree_errors = m3.compare_tree(Path(arguments.worktree), item["tree"])
    passed = not plan_errors and not tree_errors
    _json_output(
        {
            "pass": passed,
            "suite": SUITE,
            "scenario": arguments.scenario,
            "expectation": arguments.expectation,
            "plan_differences": plan_errors,
            "tree_differences": tree_errors,
            "coverage": item["definition"]["covers"],
        }
    )
    return 0 if passed else 1


def command_cleanup(arguments: argparse.Namespace) -> int:
    _scenario(arguments.scenario)
    with m4_parameters():
        m3.cleanup_leased_project(
            Path(arguments.worktree),
            suite=SUITE,
            scenario=arguments.scenario,
            lease=arguments.lease,
        )
    _json_output(
        {
            "removed": str(Path(arguments.worktree).resolve()),
            "recoverable": False,
            "suite": SUITE,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and replay M4 hook projection fixtures safely."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    matrix_parser = subparsers.add_parser("validate-matrix")
    matrix_parser.add_argument("--scenario", action="append", default=[])
    matrix_parser.add_argument("--trees-only", action="store_true")
    matrix_parser.set_defaults(handler=command_validate_matrix)

    materialize_parser = subparsers.add_parser("materialize")
    materialize_parser.add_argument("replay_input")
    materialize_parser.set_defaults(handler=command_materialize)

    replay_input_parser = subparsers.add_parser("replay-input")
    replay_input_parser.add_argument("replay_input")
    replay_input_parser.add_argument("worktree")
    replay_input_parser.add_argument("--lease", required=True)
    replay_input_parser.set_defaults(handler=command_replay_input)

    validate_plan_parser = subparsers.add_parser("validate-plan")
    validate_plan_parser.add_argument("replay_input")
    validate_plan_parser.add_argument("worktree")
    validate_plan_parser.add_argument("--lease", required=True)
    validate_plan_parser.add_argument("--plan", required=True)
    validate_plan_parser.add_argument(
        "--operation-lifecycle",
        required=True,
        choices=[
            "prepared",
            "executing",
            "compensating",
            "verified",
            "failed",
            "partial",
            "closed",
        ],
    )
    validate_plan_parser.set_defaults(handler=command_validate_plan)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("scenario")
    compare_parser.add_argument("worktree")
    compare_parser.add_argument("--lease", required=True)
    compare_parser.add_argument("--expectation", required=True)
    compare_parser.add_argument("--actual-plan", required=True)
    compare_parser.set_defaults(handler=command_compare)

    fence_parser = subparsers.add_parser("check-hook-fence")
    fence_parser.set_defaults(handler=command_check_hook_fence)

    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("scenario")
    cleanup_parser.add_argument("worktree")
    cleanup_parser.add_argument("--lease", required=True)
    cleanup_parser.set_defaults(handler=command_cleanup)

    self_test_parser = subparsers.add_parser("self-test")
    self_test_parser.add_argument("--scenario", action="append", default=[])
    self_test_parser.set_defaults(handler=command_self_test)

    return parser


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()
    try:
        return int(arguments.handler(arguments))
    except (FixtureError, OSError, UnicodeError, ValueError) as error:
        _json_output({"pass": False, "error": str(error)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
