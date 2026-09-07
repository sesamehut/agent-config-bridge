#!/usr/bin/env python3
"""Validate and safely replay the M3 entry/rule reconciliation fixtures.

The harness validates fixture declarations and observed artifacts. It never
selects a Bridge direction, supplies a user decision, or executes bridge-sync.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


HERE = Path(__file__).resolve().parent
FIXTURES_ROOT = HERE.parent
REPO_ROOT = FIXTURES_ROOT.parent
sys.path.insert(0, str(FIXTURES_ROOT))
sys.path.insert(
    0,
    str(REPO_ROOT / "skills/bridge-sentinel/scripts"),
)

from _support.fixture_support import (  # noqa: E402
    FixtureError,
    HASH_PATTERN,
    MARKER_NAME,
    MARKER_SPEC,
    NONCE_PATTERN,
    TOKEN_PATTERN,
    cleanup_leased_project,
    compare_tree,
    create_temp_git_project,
    git_run,
    is_reparse,
    materialize_tree,
    markdown_header,
    markdown_section,
    normalize_n,
    normalized_markdown_lines,
    operation_bytes,
    os_temp_root,
    parse_list_section,
    parse_table,
    read_json,
    resolve_named_tree,
    safe_regular_file,
    safe_relative,
    strict_remove_tree,
    validate_marker,
    validate_temp_root,
    write_json,
)
from _support.safe_root_child import (  # noqa: E402
    RetainedRootDirectory,
    WindowsPinnedTreePartialError,
    WindowsRootQuarantinedError,
    inspect_root_child,
    pin_quarantined_tree_windows,
    quarantine_root_child_windows,
    replace_root_child,
    root_child_capability,
    windows_root_quarantine_capability,
)
from sentinel_mechanics import (  # noqa: E402
    byte_records as source_byte_records,
    inspect_managed_blocks,
    parse_preamble,
    recognized_frontmatter_span,
)


SUITE = "m3-rules"
MATRIX_SPEC = "bridge-m3-rules-matrix/v2"
SCENARIO_SPEC = "bridge-m3-rules-scenario/v2"
PLAN_SPEC = "sync-plan/v3"
PLAN_CONTRACTS = "covenant/v3, source-tree/v5, report/v5, reconciliation/v3"
TREE_MANIFEST = HERE / "tree-manifest.json"
MATRIX_PATH = HERE / "scenario-matrix.json"
JOURNAL_VALIDATOR_TESTS_PATH = HERE / "journal_validator_tests.py"
SHARED_DIR = REPO_ROOT
EXPECTATIONS_DIR = HERE / "expectations"
ACTIVATION_PROFILES_DIR = HERE / "profiles"
ACTIVATION_PROFILE_SPEC = "activation-fixture/v2"
CODEX_PROJECT_TRUST_VALUES = {"trusted", "untrusted", "unknown"}
CODEX_HOOKS_FEATURE_VALUES = {"enabled", "disabled", "unknown"}
ACTIVATION_PROFILE_TARGET = "bridge-fixture-activation.json"
WRITE_CAPABILITIES_DIR = HERE / "capabilities"
WRITE_CAPABILITY_SPEC = "write-capability-fixture/v1"
WRITE_CAPABILITY_TARGET = "bridge-fixture-write-capability.json"
FAULT_SCHEDULES_DIR = HERE / "fault-schedules"
FAULT_SCHEDULE_SPEC = "fault-schedule-fixture/v1"
FAULT_SCHEDULE_TARGET = "bridge-fixture-fault-schedule.json"
DECISIONS_DIR = HERE / "decisions"
DECISION_SPEC = "replay-decision-fixture/v1"
REPLAY_INPUT_SPEC = "bridge-m3-replay-input/v2"
REPLAY_ENVELOPE_SPEC = "bridge-m3-replay-envelope/v2"
REPLAY_INPUT_TARGET = "bridge-fixture-replay-input.json"
REPLAY_COMMITMENT_SPEC = "replay-bundle-commitment/v1"
REPLAY_COMMITMENT_TARGET = "bridge-fixture-replay-commitment.json"
FAULT_PHASE_EVIDENCE_SPEC = "fault-phase-evidence/v1"
FAULT_PHASE_ARMED_TARGET = "bridge-fixture-fault-armed.json"
FAULT_PHASE_CLAIM_TARGET = "bridge-fixture-fault-claim.json"
FAULT_PHASE_INJECTED_TARGET = "bridge-fixture-fault-injected.json"
RECOVERY_CLAIM_SPEC = "bridge-m3-stale-recovery-claim/v1"
RECOVERY_CLAIM_TARGET = "bridge-fixture-stale-recovery-claim.json"
STALE_RECOVERY_SPEC = "bridge-m3-stale-recovery/v1"
CANONICAL_JSON_SPEC = "canonical-json/v1"
PLAN_VALIDATOR_SPEC = "sync-plan-validator/v1"
PLAN_DIAGNOSTIC_SPEC = "sync-plan-diagnostic/v1"
JOURNAL_SPEC = "bridge-live-operation-journal/v2"
JOURNAL_VALIDATOR_SPEC = "bridge-live-operation-journal-validator/v2"
JOURNAL_CASE_COUNT = 66
ZERO_BASELINE = "0" * 40
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
COVENANT_CARRIERS = (
    ".claude/rules/bridge-covenant.md",
    "AGENTS.md",
)
COVENANT_TEMPLATES = {
    ".claude/rules/bridge-covenant.md": (
        REPO_ROOT / "templates/covenant/claude-rules-bridge.md"
    ),
    "AGENTS.md": REPO_ROOT / "templates/covenant/agents-md-covenant-block.md",
}
GENERAL_PLAN_CONTEXT = "general"
EMPTY_BOOTSTRAP_POST_CONTEXT = "operation-scoped-empty-bootstrap-post"
EMPTY_UNTRACKED_SCAN_CONTEXT = "independent-empty-untracked-scan"

UNIT_HEADER = (
    "| unit | closure | selection | baseline | state | action | direction | "
    "authorization | outcome | tier | annotations |"
)
UNIT_SEPARATOR = "|---|---|---|---|---|---|---|---|---|---|---|"
CLOSURE_HEADER = (
    "| closure | members | depends on | selection | authorization | outcome |"
)
CLOSURE_SEPARATOR = "|---|---|---|---|---|---|"
CAPABILITY_PROFILE_HEADER = (
    "| binding | profile | host | host version | tool surface | platform | "
    "filesystem assumptions |"
)
CAPABILITY_PROFILE_SEPARATOR = "|---|---|---|---|---|---|---|"
WRITE_CAPABILITY_HEADER = (
    "| step | closure | path | operation | protocol | binding | "
    "inverse protocol | inverse binding |"
)
WRITE_CAPABILITY_SEPARATOR = "|---|---|---|---|---|---|---|---|"
MIGRATION_HEADER = (
    "| unit | legacy baseline | current relation | disposition | decision |"
)
MIGRATION_SEPARATOR = "|---|---|---|---|---|"
MIGRATION_CANDIDATE_HEADER = "| unit | legacy candidate |"
MIGRATION_CANDIDATE_SEPARATOR = "|---|---|"
ADOPTION_HEADER = (
    "| segment | lines | disposition | destination | decision |"
)
ADOPTION_SEPARATOR = "|---|---|---|---|---|"
HOOK_TIER_HEADER = "| unit | class | surface | tier | reason |"
HOOK_TIER_SEPARATOR = "|---|---|---|---|---|"
HOOK_ADOPTION_HEADER = (
    "| handler | location | disposition | destination | decision |"
)
HOOK_ADOPTION_SEPARATOR = "|---|---|---|---|---|"

PLAN_STATES = {
    "unchanged",
    "source-only",
    "projection-only",
    "both-changed",
    "no-baseline",
    "intent-missing",
    "contract-migration",
    "declared-unsynced",
    "offboarding",
    "blocked",
}
PLAN_ACTIONS = {
    "create",
    "repair",
    "restore",
    "update",
    "reproject",
    "adopt",
    "conflict",
    "delete",
    "rename",
    "annex-or-keep",
    "annex",
    "keep",
    "migrate",
    "offboard",
    "opt-in-or-skip",
    "resolve-blocker",
    "unchanged",
}
PLAN_DIRECTIONS = {
    "-",
    "source-to-projection",
    "projection-to-source",
    "user-decision",
}
PLAN_OUTCOMES = {
    "planned",
    "applied",
    "unchanged",
    "not-selected",
    "deferred",
    "blocked",
    "failed",
    "compensated",
    "partial",
    "not-attempted",
    "rolled-back",
}
PLAN_TIERS = {
    "native",
    "structural",
    "semantic",
    "declared-unsynced",
    "-",
}
HOOK_ROW_TIERS = {"native", "semantic", "declared-unsynced"}
PLAN_ANNOTATIONS = {
    "awaiting-host-trust",
    "behavior-degraded",
    "decision-required",
    "event-unverified",
    "intent-required",
    "live-activation-unknown",
    "migration-transition-required",
    "opt-in-required",
    "restart-may-be-required",
    "semantic-review-required",
}
# Neutral hook annotations that attach to every affected hook row and so may
# accompany the pinned annotation set of a hook conflict or hook decision row.
HOOK_NEUTRAL_ANNOTATIONS = {
    "awaiting-host-trust",
    "event-unverified",
}
HOOK_CONFLICT_EXTRA_ANNOTATIONS = HOOK_NEUTRAL_ANNOTATIONS | {
    "opt-in-required",
}
PLAN_WARNINGS = {
    "active-shared-import",
    "agents-md-budget-disabled",
    "agents-md-budget-exceeded",
    "agents-md-near-budget",
    "ambiguous-baseline",
    "authorization-incomplete",
    "closure-dependency-unsatisfied",
    "codex-activation-unresolved",
    "codex-root-unresolved",
    "conditional-write-unavailable",
    "covenant-anchor-anomaly",
    "dual-project-entry",
    "entry-rule-source-anomaly",
    "fallback-shadow",
    "guarded-patch-non-cas",
    "guarded-patch-unavailable",
    "ignored-files-excluded",
    "ignored-required-input",
    "invalid-rule-paths",
    "legacy-managed-mode",
    "manual-zone-guarded",
    "manual-zone-preserved",
    "marker-anomaly",
    "migration-closure-incomplete",
    "migration-transition-uncommitted",
    "mode-limited",
    "sensitive-or-generated-blocked",
    "skill-loadability-blocked",
    "surface-shadowed",
    "strict-compensation-unavailable",
    "unrelated-dirty-preserved",
    "unsafe-tree-entry",
    "untracked-files-included",
    "validator-profile-mismatch",
}
BLOCKING_WARNINGS = {
    "active-shared-import",
    "agents-md-budget-disabled",
    "agents-md-budget-exceeded",
    "ambiguous-baseline",
    "authorization-incomplete",
    "closure-dependency-unsatisfied",
    "codex-activation-unresolved",
    "codex-root-unresolved",
    "conditional-write-unavailable",
    "covenant-anchor-anomaly",
    "dual-project-entry",
    "entry-rule-source-anomaly",
    "fallback-shadow",
    "guarded-patch-unavailable",
    "ignored-required-input",
    "invalid-rule-paths",
    "legacy-managed-mode",
    "marker-anomaly",
    "migration-closure-incomplete",
    "migration-transition-uncommitted",
    "mode-limited",
    "sensitive-or-generated-blocked",
    "skill-loadability-blocked",
    "surface-shadowed",
    "unsafe-tree-entry",
}
HOOK_WARNING_CLASSES = {
    "claude-hooks-shared-execution": "acknowledged",
    "codex-handler-unknown-key": "informational",
    "codex-hook-retrust-required": "acknowledged",
    "codex-inline-hooks-conflict": "blocker",
    "codex-project-untrusted": "informational",
    "codex-trust-blind-change": "informational",
    "codex-trust-reindex": "acknowledged",
    "hook-acknowledgement-missing": "blocker",
    "hook-carrier-absent": "informational",
    "hook-format-preserved": "informational",
    "hook-opt-in-required": "blocker",
    "hook-output-not-delivered": "informational",
    "hook-projection-asymmetric": "acknowledged",
    "hooks-carrier-unusable": "blocker",
    "hooks-globally-disabled": "informational",
    "intent-doc-anomaly": "blocker",
    "local-hooks-present": "informational",
    "matcher-grammar-divergent": "acknowledged",
    "platform-branch-divergence": "acknowledged",
    "undeclared-hooks-key": "informational",
}
PLAN_WARNINGS.update(HOOK_WARNING_CLASSES)
BLOCKING_WARNINGS.update(
    token
    for token, warning_class in HOOK_WARNING_CLASSES.items()
    if warning_class == "blocker"
)
APPLY_BLOCKER_GATES = {
    "hook carrier": frozenset(
        {"codex-inline-hooks-conflict", "hooks-carrier-unusable"}
    ),
    "hook opt-in": frozenset(
        {"hook-acknowledgement-missing", "hook-opt-in-required"}
    ),
    "hook source": frozenset({"intent-doc-anomaly"}),
    "write capability": frozenset(
        {"conditional-write-unavailable", "guarded-patch-unavailable"}
    ),
}
CLOSURE_SCOPED_APPLY_BLOCKER_GATES = frozenset(
    {"hook carrier", "hook opt-in", "write capability"}
)
CLOSURE_SCOPED_BLOCKING_WARNINGS = frozenset(
    token
    for gate in CLOSURE_SCOPED_APPLY_BLOCKER_GATES
    for token in APPLY_BLOCKER_GATES[gate]
)
PROJECT_WIDE_BLOCKING_WARNINGS = (
    BLOCKING_WARNINGS - CLOSURE_SCOPED_BLOCKING_WARNINGS
)
HOOK_CARRIER_CLOSURES = {
    ".claude/rules/hooks.md": "closure/hooks/source",
    ".claude/settings.json": "closure/hooks/claude",
    ".codex/config.toml": "closure/hooks/codex",
    ".codex/hooks.json": "closure/hooks/codex",
}
HOOK_BLOCKER_SCOPE_CLOSURES = {
    "codex-inline-hooks-conflict": ("closure/hooks/codex",),
    "hook-acknowledgement-missing": ("closure/hooks/claude",),
}
PLAN_VALIDATOR_FAILURES = {
    "adoption-consistency",
    "decision-transition",
    "document-grammar",
    "fixture-attestation",
    "hooks-carrier-composition",
    "migration-candidates",
    "phase-lifecycle",
    "unit-closure",
    "warning-grammar",
    "write-capability",
}
PLAN_SELECTIONS = {"selected", "not-selected"}
PLAN_AUTHORIZATIONS = {"required", "confirmed", "not-applicable"}
WRITE_PROTOCOLS = {
    "strict-replace/v1",
    "strict-create/v1",
    "strict-delete/v1",
    "guarded-patch/v1",
    "unavailable",
}
MUTATING_ACTIONS = {
    "create",
    "repair",
    "restore",
    "update",
    "reproject",
    "adopt",
    "delete",
    "rename",
    "annex",
    "migrate",
    "offboard",
}
REPLAY_MODES = {"agent", "declarative-only"}
SEGMENT_PATTERN = re.compile(r"segment/([1-9][0-9]*)")
LINES_PATTERN = re.compile(r"([1-9][0-9]*)-([1-9][0-9]*)")
BUDGET_WARNING_PATTERN = re.compile(
    r"^- (agents-md-near-budget|agents-md-budget-exceeded): "
    r"AGENTS\.md \(([0-9]+) bytes of ([0-9]+)\)$"
)
WARNING_LINE_PATTERN = re.compile(
    r"^- ([a-z][a-z0-9-]*): (\.|[^ ()]+)(?: (\([^()\r\n]+\)))?$"
)
WARNING_DIAGNOSTIC_PATTERN = re.compile(
    r"^- ([a-z][a-z0-9-]*): (.*)$"
)
PLAN_DIAGNOSTIC_KINDS = {
    "cardinality",
    "extra",
    "generic",
    "invalid-order",
    "missing",
    "path",
    "token",
}
PLAN_DIAGNOSTIC_FIELDS = {
    "actual_count",
    "actual_line",
    "detail",
    "kind",
    "path",
    "required_count",
    "required_line",
    "section",
    "token",
}
PUBLIC_DERIVED_WARNING_TOKENS = {
    "authorization-incomplete",
    "conditional-write-unavailable",
    "covenant-anchor-anomaly",
    "guarded-patch-non-cas",
    "guarded-patch-unavailable",
    "legacy-managed-mode",
    "manual-zone-guarded",
    "manual-zone-preserved",
    "marker-anomaly",
    "migration-transition-uncommitted",
    "strict-compensation-unavailable",
    "untracked-files-included",
}
GRAPH_WARNING_TOKENS = {
    "ambiguous-baseline",
    "authorization-incomplete",
    "closure-dependency-unsatisfied",
    "codex-activation-unresolved",
    "codex-root-unresolved",
    "dual-project-entry",
    "migration-closure-incomplete",
    "migration-transition-uncommitted",
}
HOOK_CLASSES = {"reminder", "observation", "gate", "side-effect"}
HOOK_SURFACES = {
    "claude": {"settings-json", "intent-doc", "none"},
    "codex": {"codex-hooks-json", "agents-md", "none"},
}
HOOK_SURFACE_TIERS = {
    ("claude", "settings-json"): "native",
    ("claude", "intent-doc"): "semantic",
    ("claude", "none"): "declared-unsynced",
    ("codex", "codex-hooks-json"): "native",
    ("codex", "agents-md"): "semantic",
    ("codex", "none"): "declared-unsynced",
}
HOOK_TIER_REASONS = {
    "shared-event-command",
    "claude-only-event",
    "codex-only-event",
    "degraded-standing-instruction",
    "intent-doc-standing-instruction",
    "declared-none",
    "decision-not-portable",
    "handler-type-not-portable",
    "async-not-portable",
    "matcher-domain",
    "codex-matcher-ignored",
    "platform-command-branch",
    "timeout-cap-differs",
    "output-not-delivered",
    "opt-in-pending",
}
HOOK_ADOPTION_DISPOSITIONS = {"adopt", "keep", "discard"}
HOOK_ADOPTION_DECISIONS = {"pending", "confirmed"}
# The five closed hook decision shapes of sync-plan/v3, in first-match order.
# Each entry is (name, (selection, authorization, outcome), required
# annotations). A matching row may add only neutral hook annotations.
HOOK_DECISION_SHAPES = (
    (
        "opt-in-pending",
        ("selected", "required", "deferred"),
        frozenset({"decision-required", "opt-in-required"}),
    ),
    (
        "two-sided-conflict",
        ("selected", "required", "deferred"),
        frozenset({"decision-required"}),
    ),
    (
        "pending-occupancy",
        ("not-selected", "not-applicable", "not-selected"),
        frozenset({"decision-required"}),
    ),
    (
        "confirmed-keep",
        ("selected", "not-applicable", "deferred"),
        frozenset(),
    ),
    (
        "surface-none",
        ("selected", "not-applicable", "unchanged"),
        frozenset(),
    ),
)
# Outcomes under which a selected row still writes nothing. A `class: gate`
# entry projects both host carriers or neither, so a blocked or unavailable
# carrier forces its sibling to a zero-write row.
HOOK_ZERO_WRITE_OUTCOMES = {
    "blocked",
    "deferred",
    "not-attempted",
    "not-selected",
    "unchanged",
}
HOOK_ENTRY_ID = r"[a-z0-9][a-z0-9-]*"
HOOK_EVENT = r"[A-Z][A-Za-z0-9]*"
HOOK_INDEX = r"(?:0|[1-9][0-9]*)"
HOOK_UNIT_PATTERN = re.compile(
    rf"hooks/{HOOK_ENTRY_ID}/(?:source|claude|codex)"
)
HOOK_DESTINATION_PATTERN = re.compile(rf"hooks/{HOOK_ENTRY_ID}")
HOOK_DECISION_CLOSURE_PATTERN = re.compile(
    rf"closure/decision/hooks/{HOOK_ENTRY_ID}"
)
HOOK_HANDLER_PATTERN = re.compile(r"handler/([1-9][0-9]*)")
HOOK_LOCATION_PATTERN = re.compile(
    rf"([^ #\[\]]+)#({HOOK_EVENT})\[({HOOK_INDEX})\]\[({HOOK_INDEX})\]"
)
HOOK_ENTRY_DETAIL_PATTERN = re.compile(rf"entry {HOOK_ENTRY_ID}")
HOOK_HANDLER_DETAIL_PATTERN = re.compile(
    rf"{HOOK_EVENT} group={HOOK_INDEX} handler={HOOK_INDEX}"
)
HOOK_UNKNOWN_KEY_DETAIL_PATTERN = re.compile(
    rf"{HOOK_EVENT} group={HOOK_INDEX} handler={HOOK_INDEX} "
    r"key=[A-Za-z_][A-Za-z0-9_-]*"
)
HOOK_REINDEX_DETAIL_PATTERN = re.compile(
    rf"{HOOK_EVENT} from={HOOK_INDEX}"
)
HOOK_UNDECLARED_KEY_DETAIL_PATTERN = re.compile(
    rf"{HOOK_EVENT} matcher=[^()\r\n]+"
)
HOOK_WARNING_PATHS = {
    "claude-hooks-shared-execution": ".claude/settings.json",
    "codex-handler-unknown-key": ".codex/hooks.json",
    "codex-hook-retrust-required": ".codex/hooks.json",
    "codex-inline-hooks-conflict": ".codex/config.toml",
    "codex-trust-blind-change": ".codex/hooks.json",
    "codex-trust-reindex": ".codex/hooks.json",
    "hook-acknowledgement-missing": ".claude/rules/hooks.md",
    "hook-opt-in-required": ".claude/rules/hooks.md",
    "hook-output-not-delivered": ".claude/rules/hooks.md",
    "intent-doc-anomaly": ".claude/rules/hooks.md",
    "local-hooks-present": ".claude/settings.local.json",
    "matcher-grammar-divergent": ".claude/rules/hooks.md",
    "platform-branch-divergence": ".claude/rules/hooks.md",
}
HOOK_ANY_CARRIER_PATHS = {
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".codex/hooks.json",
    "AGENTS.md",
}
HOOK_JSON_CARRIER_PATHS = {
    ".claude/settings.json",
    ".codex/hooks.json",
}
HOOK_SETTINGS_CARRIER_PATHS = {
    ".claude/settings.json",
    ".claude/settings.local.json",
}
HOOK_CARRIER_WARNING_PATHS = {
    "hook-carrier-absent": HOOK_ANY_CARRIER_PATHS,
    "hook-format-preserved": HOOK_JSON_CARRIER_PATHS,
    "hook-projection-asymmetric": HOOK_ANY_CARRIER_PATHS,
    "hooks-carrier-unusable": HOOK_JSON_CARRIER_PATHS,
    "hooks-globally-disabled": HOOK_SETTINGS_CARRIER_PATHS,
    "undeclared-hooks-key": HOOK_JSON_CARRIER_PATHS,
}
HOOK_CARRIER_WARNING_TOKENS = set(HOOK_CARRIER_WARNING_PATHS)
WARNING_REASON_SETS = {
    "codex-activation-unresolved": {
        "config-unresolved",
        "override-carrier-unsafe",
        "agents-carrier-unsafe",
        "fallback-carrier-unsafe",
        "fallback-selection-unknown",
        "budget-unknown",
    },
    "codex-root-unresolved": {
        "effective-root-unknown",
        "empty-markers",
        "root-marker-excluded",
    },
    "covenant-anchor-anomaly": {
        "partial",
        "untracked",
        "malformed",
        "modified",
        "version-mismatch",
    },
    "invalid-rule-paths": {
        "schema",
        "empty",
        "unsafe",
        "invalid-bracket",
        "no-op-universal",
        "duplicate",
        "expansion-count",
        "expansion-bytes",
        "expansion-unproved",
    },
    "mode-limited": {
        "explicit-executable-unrealizable",
        "worktree-mode-unobservable",
        "target-mode-unpreservable",
    },
    "hooks-carrier-unusable": {
        "parse-error",
        "duplicate-key",
        "unmodelled-shape",
    },
}
WARNING_DETAIL_TOKENS = {
    "active-shared-import",
    "agents-md-budget-exceeded",
    "agents-md-near-budget",
    "codex-activation-unresolved",
    "codex-handler-unknown-key",
    "codex-hook-retrust-required",
    "codex-inline-hooks-conflict",
    "codex-root-unresolved",
    "codex-trust-blind-change",
    "codex-trust-reindex",
    "covenant-anchor-anomaly",
    "hook-opt-in-required",
    "hook-output-not-delivered",
    "hook-projection-asymmetric",
    "hooks-carrier-unusable",
    "intent-doc-anomaly",
    "invalid-rule-paths",
    "legacy-managed-mode",
    "marker-anomaly",
    "matcher-grammar-divergent",
    "mode-limited",
    "platform-branch-divergence",
    "undeclared-hooks-key",
}
ROOT_PATH_WARNING_TOKENS = GRAPH_WARNING_TOKENS | {"codex-project-untrusted"}
RULE_UNIT_PATTERN = re.compile(
    r"rules/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*"
)
SKILL_UNIT_PATTERN = re.compile(r"skills/[a-z0-9]+(?:-[a-z0-9]+)*")


Plan = Dict[str, Any]


def _json_output(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _safe_expectation_path(value: Any) -> Path:
    relative = safe_relative(value, field="expectation plan")
    path = (HERE / relative).resolve()
    try:
        path.relative_to(EXPECTATIONS_DIR.resolve())
    except ValueError as error:
        raise FixtureError(
            f"expectation plan must stay under {EXPECTATIONS_DIR}"
        ) from error
    if not path.is_file():
        raise FixtureError(f"expectation plan is not a file: {path}")
    return path


def _load_activation_profile(value: Any) -> Dict[str, Any]:
    path = safe_regular_file(
        HERE,
        value,
        field="activation profile",
    )
    try:
        path.relative_to(ACTIVATION_PROFILES_DIR.resolve())
    except ValueError as error:
        raise FixtureError(
            f"activation profile must stay under {ACTIVATION_PROFILES_DIR}"
        ) from error
    profile = read_json(path)
    required = {
        "version",
        "root_markers",
        "fallback_filenames",
        "project_doc_max_bytes",
        "budget_source",
        "codex_project_trust",
        "codex_hooks_feature",
    }
    if set(profile) != required:
        raise FixtureError(f"{path}: activation profile fields are not closed")
    if profile["version"] != ACTIVATION_PROFILE_SPEC:
        raise FixtureError(
            f"{path}: expected activation profile {ACTIVATION_PROFILE_SPEC}"
        )
    for field in ("root_markers", "fallback_filenames"):
        items = profile[field]
        if items is not None and (
            not isinstance(items, list)
            or not all(isinstance(item, str) for item in items)
        ):
            raise FixtureError(f"{path}: {field} must be string array or null")
    budget = profile["project_doc_max_bytes"]
    if budget is not None and (
        isinstance(budget, bool)
        or not isinstance(budget, int)
        or budget < 0
    ):
        raise FixtureError(
            f"{path}: project_doc_max_bytes must be non-negative integer or null"
        )
    if profile["budget_source"] not in {
        "resolved",
        "documented-default",
    }:
        raise FixtureError(f"{path}: invalid budget_source")
    if profile["codex_project_trust"] not in CODEX_PROJECT_TRUST_VALUES:
        raise FixtureError(f"{path}: invalid codex_project_trust")
    if profile["codex_hooks_feature"] not in CODEX_HOOKS_FEATURE_VALUES:
        raise FixtureError(f"{path}: invalid codex_hooks_feature")
    installed_profile = {
        "version": profile["version"],
        "root_markers": copy.deepcopy(profile["root_markers"]),
        "fallback_filenames": copy.deepcopy(
            profile["fallback_filenames"]
        ),
        "project_doc_max_bytes": (
            None
            if profile["project_doc_max_bytes"] is None
            else str(profile["project_doc_max_bytes"])
        ),
        "budget_source": profile["budget_source"],
        "codex_project_trust": profile["codex_project_trust"],
        "codex_hooks_feature": profile["codex_hooks_feature"],
    }
    installed_bytes = _canonical_json_bytes(installed_profile)
    return {
        "path": path,
        "relative": path.relative_to(HERE).as_posix(),
        "profile": profile,
        "installed_profile": installed_profile,
        "bytes": installed_bytes,
        "sha256": hashlib.sha256(installed_bytes).hexdigest(),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _install_activation_profile(
    root: Path, profile: Mapping[str, Any]
) -> Path:
    target = root / ".git" / ACTIVATION_PROFILE_TARGET
    try:
        with target.open("xb") as stream:
            stream.write(profile["bytes"])
    except OSError as error:
        raise FixtureError(
            f"cannot create exact activation profile {target}: {error}"
        ) from error
    _validate_installed_activation_profile(root, profile)
    return target


def _validate_installed_activation_profile(
    root: Path, profile: Mapping[str, Any]
) -> Path:
    target = root / ".git" / ACTIVATION_PROFILE_TARGET
    try:
        status = os.lstat(target)
    except OSError as error:
        raise FixtureError(
            f"cannot inspect installed activation profile: {error}"
        ) from error
    if (
        not stat.S_ISREG(status.st_mode)
        or stat.S_ISLNK(status.st_mode)
        or target.read_bytes() != profile["bytes"]
        or _read_canonical_json(
            target, label="activation profile"
        )
        != profile["installed_profile"]
    ):
        raise FixtureError("installed activation profile is not exact")
    return target


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_canonical_json_value(value: Any, *, path: str = "$") -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise FixtureError(
                f"{path}: canonical JSON string contains a lone surrogate"
            ) from error
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_canonical_json_value(
                item, path=f"{path}[{index}]"
            )
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise FixtureError(
                    f"{path}: canonical JSON object key is not a string"
                )
            _validate_canonical_json_value(
                key, path=f"{path}.<key>"
            )
            _validate_canonical_json_value(
                item, path=f"{path}.{key}"
            )
        return
    raise FixtureError(
        f"{path}: restricted canonical JSON forbids numeric/unknown values"
    )


def _canonical_json_bytes(value: Any) -> bytes:
    _validate_canonical_json_value(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _parse_canonical_json_bytes(
    raw: bytes, *, label: str
) -> Dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise FixtureError(
            f"cannot read canonical {label}: {error}"
        ) from error
    if not isinstance(value, dict) or _canonical_json_bytes(value) != raw:
        raise FixtureError(
            f"installed {label} is not exact {CANONICAL_JSON_SPEC}"
        )
    return value


def _read_canonical_json(path: Path, *, label: str) -> Dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise FixtureError(
            f"cannot read canonical {label}: {error}"
        ) from error
    return _parse_canonical_json_bytes(raw, label=label)


def _load_write_capability_fixture(value: Any) -> Dict[str, Any]:
    path = safe_regular_file(
        HERE,
        value,
        field="write capability fixture",
    )
    try:
        path.relative_to(WRITE_CAPABILITIES_DIR.resolve())
    except ValueError as error:
        raise FixtureError(
            f"write capability fixture must stay under {WRITE_CAPABILITIES_DIR}"
        ) from error
    fixture = read_json(path)
    if set(fixture) != {"version", "profiles", "operations"}:
        raise FixtureError(
            f"{path}: write capability fixture fields are not closed"
        )
    if fixture["version"] != WRITE_CAPABILITY_SPEC:
        raise FixtureError(
            f"{path}: expected write capability fixture {WRITE_CAPABILITY_SPEC}"
        )
    profiles = fixture["profiles"]
    operations = fixture["operations"]
    if not isinstance(profiles, list) or not isinstance(operations, list):
        raise FixtureError(f"{path}: profiles/operations must be arrays")
    identifier = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:+/-]*")
    assumption = re.compile(r"[a-z0-9][a-z0-9._-]*/v[1-9][0-9]*")
    parsed_profiles: List[Tuple[str, ...]] = []
    profile_by_binding: Dict[str, Mapping[str, Any]] = {}
    for index, profile in enumerate(profiles, start=1):
        required = {
            "binding",
            "profile",
            "host",
            "host_version",
            "tool_surface",
            "platform",
            "filesystem_assumptions",
            "attestations",
        }
        if not isinstance(profile, dict) or set(profile) != required:
            raise FixtureError(
                f"{path}: capability profile {index} fields are not closed"
            )
        binding = profile["binding"]
        if binding != f"capability/{index}":
            raise FixtureError(
                f"{path}: capability bindings must be capability/1..N"
            )
        if profile["profile"] != "capability-profile/v1":
            raise FixtureError(f"{path}: invalid capability profile")
        if profile["host"] != "other" or profile["platform"] != "other":
            raise FixtureError(
                f"{path}: fixture capability may not attest a real host/platform"
            )
        version = profile["host_version"]
        tool = profile["tool_surface"]
        if (
            not isinstance(version, str)
            or not version.startswith("fixture-")
            or identifier.fullmatch(version) is None
            or not isinstance(tool, str)
            or identifier.fullmatch(tool) is None
        ):
            raise FixtureError(
                f"{path}: capability host/tool must be fixture-scoped identifiers"
            )
        assumptions = profile["filesystem_assumptions"]
        if (
            not isinstance(assumptions, list)
            or not assumptions
            or assumptions != sorted(set(assumptions))
            or any(
                not isinstance(item, str)
                or assumption.fullmatch(item) is None
                for item in assumptions
            )
        ):
            raise FixtureError(
                f"{path}: invalid filesystem assumption declarations"
            )
        attestations = profile["attestations"]
        if not isinstance(attestations, list) or not attestations:
            raise FixtureError(f"{path}: positive profile needs attestations")
        seen_attestations: List[Tuple[str, str, Tuple[str, ...], Tuple[str, ...]]] = []
        for attestation in attestations:
            if not isinstance(attestation, dict) or set(attestation) != {
                "protocol",
                "proof",
                "operations",
                "paths",
            }:
                raise FixtureError(
                    f"{path}: capability attestation fields are not closed"
                )
            protocol = attestation["protocol"]
            proof = attestation["proof"]
            attested_operations = attestation["operations"]
            paths = attestation["paths"]
            if protocol not in WRITE_PROTOCOLS - {"unavailable"}:
                raise FixtureError(f"{path}: invalid attested protocol")
            if (
                not isinstance(proof, str)
                or not proof.startswith("fixture-")
                or assumption.fullmatch(proof) is None
            ):
                raise FixtureError(
                    f"{path}: capability proof must be fixture-scoped and versioned"
                )
            if (
                not isinstance(attested_operations, list)
                or not attested_operations
                or attested_operations != sorted(set(attested_operations))
                or any(
                    operation not in {"create", "delete", "replace"}
                    for operation in attested_operations
                )
            ):
                raise FixtureError(f"{path}: invalid attested operations")
            if (
                not isinstance(paths, list)
                or not paths
                or paths != sorted(set(paths))
            ):
                raise FixtureError(f"{path}: invalid attested paths")
            for relative in paths:
                safe_relative(
                    relative,
                    field=f"{path} capability attestation path",
                )
            seen_attestations.append(
                (
                    protocol,
                    proof,
                    tuple(attested_operations),
                    tuple(paths),
                )
            )
        if seen_attestations != sorted(set(seen_attestations)):
            raise FixtureError(
                f"{path}: attestations must be sorted and unique"
            )
        profile_by_binding[binding] = profile
        parsed_profiles.append(
            (
                binding,
                profile["profile"],
                profile["host"],
                version,
                tool,
                profile["platform"],
                "; ".join(assumptions),
            )
        )
    parsed_operations: List[Tuple[str, ...]] = []
    for index, operation in enumerate(operations, start=1):
        required = {
            "closure",
            "path",
            "operation",
            "protocol",
            "binding",
            "inverse_protocol",
            "inverse_binding",
        }
        if not isinstance(operation, dict) or set(operation) != required:
            raise FixtureError(
                f"{path}: write operation {index} fields are not closed"
            )
        closure = operation["closure"]
        relative = safe_relative(
            operation["path"],
            field=f"{path} write operation {index} path",
        )
        operation_name = operation["operation"]
        protocol = operation["protocol"]
        binding = operation["binding"]
        inverse = operation["inverse_protocol"]
        inverse_binding = operation["inverse_binding"]
        if not _closure_id_valid(closure):
            raise FixtureError(f"{path}: invalid write closure {closure!r}")
        if operation_name not in {"create", "delete", "replace"}:
            raise FixtureError(f"{path}: invalid write operation")
        for label, candidate_protocol, candidate_binding in (
            ("forward", protocol, binding),
            ("inverse", inverse, inverse_binding),
        ):
            if candidate_protocol not in WRITE_PROTOCOLS:
                raise FixtureError(
                    f"{path}: invalid {label} write protocol"
                )
            if candidate_protocol == "unavailable":
                if candidate_binding is not None:
                    raise FixtureError(
                        f"{path}: unavailable {label} protocol has a binding"
                    )
                continue
            if candidate_binding not in profile_by_binding:
                raise FixtureError(
                    f"{path}: {label} protocol has no declared profile"
                )
            attested = any(
                item["protocol"] == candidate_protocol
                and operation_name in item["operations"]
                and relative in item["paths"]
                for item in profile_by_binding[candidate_binding][
                    "attestations"
                ]
            )
            if not attested:
                raise FixtureError(
                    f"{path}: {label} protocol lacks path/operation proof"
                )
        parsed_operations.append(
            (
                str(index),
                closure,
                relative,
                operation_name,
                protocol,
                "-" if binding is None else binding,
                inverse,
                "-" if inverse_binding is None else inverse_binding,
            )
        )
    raw = path.read_bytes()
    return {
        "path": path,
        "relative": path.relative_to(HERE).as_posix(),
        "fixture": fixture,
        "bytes": raw,
        "sha256": _sha256(raw),
        "profile_rows": parsed_profiles,
        "operation_rows": parsed_operations,
    }


def _load_fault_schedule_fixture(
    value: Any,
    *,
    input_tree: Mapping[str, Any],
) -> Dict[str, Any]:
    path = safe_regular_file(
        HERE,
        value,
        field="fault schedule fixture",
    )
    try:
        path.relative_to(FAULT_SCHEDULES_DIR.resolve())
    except ValueError as error:
        raise FixtureError(
            f"fault schedule fixture must stay under {FAULT_SCHEDULES_DIR}"
        ) from error
    fixture = read_json(path)
    required = {
        "version",
        "phase",
        "target",
        "expected_preimage_sha256",
        "injected_state",
        "injected_sha256",
        "persistence",
        "zero_bridge_write",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise FixtureError(
            f"{path}: fault schedule fixture fields are not closed"
        )
    if fixture["version"] != FAULT_SCHEDULE_SPEC:
        raise FixtureError(
            f"{path}: expected fault schedule {FAULT_SCHEDULE_SPEC}"
        )
    if (
        fixture["phase"]
        != "after-confirmation-before-final-preflight"
        or fixture["persistence"] != "persistent"
        or fixture["zero_bridge_write"] is not True
    ):
        raise FixtureError(f"{path}: invalid fault timing/persistence contract")
    target = safe_relative(
        fixture["target"], field=f"{path} fault target"
    )
    expected = input_tree.get(target)
    if (
        not isinstance(expected, dict)
        or expected.get("type") != "file"
        or expected.get("mode") not in {"100644", "100755"}
        or not isinstance(expected.get("bytes"), bytes)
        or fixture["expected_preimage_sha256"]
        != _sha256(expected["bytes"])
    ):
        raise FixtureError(
            f"{path}: fault expected preimage does not bind input bytes"
        )
    injected_state = fixture["injected_state"]
    if not isinstance(injected_state, str) or not injected_state:
        raise FixtureError(f"{path}: injected_state must name a tree")
    injected_tree = resolve_named_tree(
        HERE,
        TREE_MANIFEST,
        injected_state,
        shared_dir=SHARED_DIR,
    )
    injected = injected_tree.get(target)
    if (
        not isinstance(injected, dict)
        or injected.get("type") != "file"
        or injected.get("mode") not in {"100644", "100755"}
        or not isinstance(injected.get("bytes"), bytes)
        or fixture["injected_sha256"] != _sha256(injected["bytes"])
        or injected == expected
    ):
        raise FixtureError(
            f"{path}: injected state does not bind distinct exact file bytes"
        )
    raw = path.read_bytes()
    return {
        "path": path,
        "relative": path.relative_to(HERE).as_posix(),
        "fixture": fixture,
        "bytes": raw,
        "sha256": _sha256(raw),
        "target": target,
        "expected": copy.deepcopy(expected),
        "injected": copy.deepcopy(injected),
    }


def _load_decision_fixture(
    value: Any,
    *,
    input_tree: Mapping[str, Any],
) -> Dict[str, Any]:
    path = safe_regular_file(HERE, value, field="replay decision fixture")
    try:
        path.relative_to(DECISIONS_DIR.resolve())
    except ValueError as error:
        raise FixtureError(
            f"replay decision fixture must stay under {DECISIONS_DIR}"
        ) from error
    decision = read_json(path)
    required = {
        "version",
        "status",
        "motivation",
        "intent",
        "authorized_closures",
        "source_bindings",
        "segments",
    }
    if set(decision) != required:
        raise FixtureError(f"{path}: decision fixture fields are not closed")
    if decision["version"] != DECISION_SPEC:
        raise FixtureError(f"{path}: expected decision fixture {DECISION_SPEC}")
    status = decision["status"]
    if status not in {"confirmed", "pending"}:
        raise FixtureError(f"{path}: invalid decision status")
    motivation = decision["motivation"]
    intent = decision["intent"]
    if status == "confirmed":
        if (
            not isinstance(motivation, str)
            or not motivation
            or (
                intent is not None
                and (not isinstance(intent, str) or not intent)
            )
        ):
            raise FixtureError(
                f"{path}: confirmed decision needs motivation and valid intent"
            )
    elif motivation is not None or intent is not None:
        raise FixtureError(
            f"{path}: pending decision may not invent motivation or intent"
        )
    authorized_closures = decision["authorized_closures"]
    if (
        not isinstance(authorized_closures, list)
        or authorized_closures != sorted(set(authorized_closures))
        or any(
            not isinstance(closure, str) or not _closure_id_valid(closure)
            for closure in authorized_closures
        )
    ):
        raise FixtureError(f"{path}: invalid authorized_closures")
    if status == "confirmed" and not authorized_closures:
        raise FixtureError(
            f"{path}: confirmed decision needs an authorized closure"
        )
    if status == "pending" and authorized_closures:
        raise FixtureError(
            f"{path}: pending decision cannot authorize a closure"
        )
    bindings = decision["source_bindings"]
    if not isinstance(bindings, list):
        raise FixtureError(f"{path}: source_bindings must be an array")
    seen_paths: List[str] = []
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != {
            "path",
            "sha256",
        }:
            raise FixtureError(
                f"{path}: source binding fields are not closed"
            )
        relative = safe_relative(
            binding["path"], field=f"{path} decision source path"
        )
        entry = input_tree.get(relative)
        if (
            not isinstance(entry, dict)
            or entry.get("type") != "file"
            or not isinstance(entry.get("bytes"), bytes)
        ):
            raise FixtureError(
                f"{path}: decision source must bind an input regular file"
            )
        digest = binding["sha256"]
        if (
            not isinstance(digest, str)
            or SHA256_PATTERN.fullmatch(digest) is None
            or _sha256(entry["bytes"]) != digest
        ):
            raise FixtureError(
                f"{path}: decision source hash does not bind exact input bytes"
            )
        seen_paths.append(relative)
    if seen_paths != sorted(set(seen_paths)):
        raise FixtureError(
            f"{path}: decision source bindings must be sorted and unique"
        )
    segments = decision["segments"]
    if not isinstance(segments, list):
        raise FixtureError(f"{path}: segments must be an array")
    previous_end = 0
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict) or set(segment) != {
            "id",
            "lines",
            "disposition",
            "destination",
            "decision",
        }:
            raise FixtureError(f"{path}: segment fields are not closed")
        if segment["id"] != f"segment/{index}":
            raise FixtureError(f"{path}: segments must be segment/1..N")
        match = LINES_PATTERN.fullmatch(segment["lines"])
        if match is None:
            raise FixtureError(f"{path}: invalid segment line span")
        start, end = map(int, match.groups())
        if start > end or start <= previous_end:
            raise FixtureError(f"{path}: segment spans overlap")
        previous_end = end
        if segment["disposition"] not in {
            "shared-entry",
            "shared-rule",
            "manual",
            "discard",
        }:
            raise FixtureError(f"{path}: invalid segment disposition")
        if segment["decision"] != status:
            raise FixtureError(
                f"{path}: segment decision must equal fixture status"
            )
        destination = segment["destination"]
        disposition = segment["disposition"]
        if disposition == "shared-entry" and destination != "entry":
            raise FixtureError(
                f"{path}: shared-entry segment must target entry"
            )
        if disposition == "shared-rule":
            if RULE_UNIT_PATTERN.fullmatch(destination) is None:
                raise FixtureError(
                    f"{path}: shared-rule segment must target a rule"
                )
        elif disposition in {"manual", "discard"} and destination != "-":
            raise FixtureError(
                f"{path}: manual/discard segment destination must be '-'"
            )
    raw = path.read_bytes()
    return {
        "path": path,
        "relative": path.relative_to(HERE).as_posix(),
        "decision": decision,
        "bytes": raw,
        "sha256": _sha256(raw),
    }


def _entry_fact(relative: str, entry: Mapping[str, Any]) -> Dict[str, Any]:
    fact: Dict[str, Any] = {"path": relative, "type": entry.get("type")}
    if entry.get("type") == "file":
        data = entry.get("bytes")
        if not isinstance(data, bytes):
            raise FixtureError(f"{relative}: file entry has invalid bytes")
        fact.update(
            {
                "mode": entry.get("mode"),
                "sha256": _sha256(data),
                "bytes_base64": base64.b64encode(data).decode("ascii"),
            }
        )
    elif entry.get("type") == "symlink":
        fact["target"] = entry.get("target")
    else:
        fact.update(
            {
                key: value
                for key, value in entry.items()
                if key != "type" and isinstance(value, (str, int, bool))
            }
        )
    return fact


def _tree_facts(tree: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [_entry_fact(path, tree[path]) for path in sorted(tree)]


def _tree_digest(tree: Mapping[str, Any]) -> str:
    return _sha256(_canonical_json_bytes(_tree_facts(tree)))


def _render_operations(
    input_tree: Mapping[str, Any],
    rendered_tree: Optional[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    if rendered_tree is None:
        return []
    operations: List[Dict[str, Any]] = []
    for relative in sorted(set(input_tree) | set(rendered_tree)):
        before = input_tree.get(relative)
        after = rendered_tree.get(relative)
        if before == after:
            continue
        if after is None:
            operations.append({"operation": "delete", "path": relative})
            continue
        fact = _entry_fact(relative, after)
        fact["operation"] = "create" if before is None else "replace"
        operations.append(fact)
    return operations


def _decision_facts(
    decision: Optional[Mapping[str, Any]],
    input_tree: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    if decision is None:
        return None
    payload = copy.deepcopy(decision["decision"])
    for binding in payload["source_bindings"]:
        entry = input_tree[binding["path"]]
        binding["bytes_base64"] = base64.b64encode(entry["bytes"]).decode(
            "ascii"
        )
    payload["sha256"] = decision["sha256"]
    return payload


def _capability_document(
    root: Path,
    *,
    lease: str,
    scenario_id: str,
    replay_input: Mapping[str, Any],
    parsed: Mapping[str, Any],
    marker: Mapping[str, Any],
) -> Dict[str, Any]:
    source = parsed["write_capability"]
    return {
        "version": WRITE_CAPABILITY_SPEC,
        "binding": {
            "marker_spec": marker["spec"],
            "suite": SUITE,
            "scenario": scenario_id,
            "replay_input": replay_input["id"],
            "resolved_root": str(root.resolve()),
            "baseline_commit": marker["baseline_commit"],
            "lease_sha256": _sha256(lease.encode("ascii")),
            "source_sha256": source["sha256"],
        },
        "profiles": copy.deepcopy(source["fixture"]["profiles"]),
        "operations": copy.deepcopy(source["fixture"]["operations"]),
    }


def _fault_schedule_document(
    root: Path,
    *,
    lease: str,
    scenario_id: str,
    replay_input: Mapping[str, Any],
    marker: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    source = replay_input["fault_schedule"]
    if source is None:
        return None
    injected = source["injected"]
    return {
        "version": FAULT_SCHEDULE_SPEC,
        "binding": {
            "marker_spec": marker["spec"],
            "suite": SUITE,
            "scenario": scenario_id,
            "replay_input": replay_input["id"],
            "resolved_root": str(root.resolve()),
            "baseline_commit": marker["baseline_commit"],
            "lease_sha256": _sha256(lease.encode("ascii")),
            "source_sha256": source["sha256"],
        },
        "phase": source["fixture"]["phase"],
        "target": source["target"],
        "expected_preimage_sha256": source["fixture"][
            "expected_preimage_sha256"
        ],
        "injected": {
            "type": "file",
            "mode": injected["mode"],
            "sha256": _sha256(injected["bytes"]),
            "bytes_base64": base64.b64encode(injected["bytes"]).decode(
                "ascii"
            ),
        },
        "persistence": source["fixture"]["persistence"],
        "zero_bridge_write": source["fixture"]["zero_bridge_write"],
    }


def _marker_identity(marker: Mapping[str, Any]) -> Dict[str, Any]:
    required = {
        "spec",
        "suite",
        "scenario",
        "nonce",
        "resolved_root",
        "lease_sha256",
        "baseline_commit",
        "replay_input",
        "write_capability_sha256",
    }
    optional = {
        "history_commits",
        "fault_schedule_sha256",
        "commitment_sha256",
    }
    if (
        not isinstance(marker, dict)
        or not required.issubset(marker)
        or set(marker) - required - optional
    ):
        raise FixtureError("fixture marker identity fields are not closed")
    identity = {
        "spec": marker["spec"],
        "suite": marker["suite"],
        "scenario": marker["scenario"],
        "nonce": marker["nonce"],
        "resolved_root": marker["resolved_root"],
        "lease_sha256": marker["lease_sha256"],
        "baseline_commit": marker["baseline_commit"],
        "history_commits": copy.deepcopy(
            marker.get("history_commits")
        ),
        "replay_input": marker["replay_input"],
        "write_capability_sha256": marker[
            "write_capability_sha256"
        ],
        "fault_schedule_sha256": marker.get(
            "fault_schedule_sha256"
        ),
    }
    _canonical_json_bytes(identity)
    return identity


def _replay_payload(
    root: Path,
    *,
    lease: str,
    scenario_id: str,
    parsed: Mapping[str, Any],
    replay_input: Mapping[str, Any],
    marker: Mapping[str, Any],
) -> Dict[str, Any]:
    capability_document = _capability_document(
        root,
        lease=lease,
        scenario_id=scenario_id,
        replay_input=replay_input,
        parsed=parsed,
        marker=marker,
    )
    capability_bytes = _canonical_json_bytes(capability_document)
    fault_schedule_document = _fault_schedule_document(
        root,
        lease=lease,
        scenario_id=scenario_id,
        replay_input=replay_input,
        marker=marker,
    )
    marker_identity = _marker_identity(marker)
    return {
        "canonicalization": CANONICAL_JSON_SPEC,
        "binding": {
            "suite": SUITE,
            "scenario": scenario_id,
            "replay_input": replay_input["id"],
            "resolved_root": str(root.resolve()),
            "nonce": marker["nonce"],
            "lease_sha256": _sha256(lease.encode("ascii")),
            "baseline_commit": marker["baseline_commit"],
            "head": marker["baseline_commit"],
            "marker_identity_sha256": _sha256(
                _canonical_json_bytes(marker_identity)
            ),
            "input_tree_sha256": _tree_digest(parsed["input"]),
        },
        "profile": {
            "version": ACTIVATION_PROFILE_SPEC,
            "sha256": parsed["activation_profile"]["sha256"],
            "facts": copy.deepcopy(
                parsed["activation_profile"]["installed_profile"]
            ),
        },
        "capability": {
            "version": WRITE_CAPABILITY_SPEC,
            "sha256": _sha256(capability_bytes),
            "facts": capability_document,
        },
        "fault_schedule": (
            None
            if fault_schedule_document is None
            else {
                "version": FAULT_SCHEDULE_SPEC,
                "sha256": _sha256(
                    _canonical_json_bytes(fault_schedule_document)
                ),
                "facts": fault_schedule_document,
            }
        ),
        "decision": _decision_facts(
            replay_input["decision"], parsed["input"]
        ),
        "input": {
            "files": _tree_facts(parsed["input"]),
            "sha256": _tree_digest(parsed["input"]),
        },
        "render": {
            "operations": _render_operations(
                parsed["input"], replay_input["rendered_tree"]
            )
        },
    }


def _bundle_commitment(
    *,
    lease: str,
    marker: Mapping[str, Any],
    payload: Mapping[str, Any],
    profile_sha256: str,
    capability_sha256: str,
    fault_schedule_sha256: Optional[str],
) -> Dict[str, Any]:
    marker_identity = _marker_identity(marker)
    unsigned = {
        "version": REPLAY_COMMITMENT_SPEC,
        "canonicalization": CANONICAL_JSON_SPEC,
        "binding": {
            "suite": marker["suite"],
            "scenario": marker["scenario"],
            "replay_input": marker["replay_input"],
            "resolved_root": marker["resolved_root"],
            "nonce": marker["nonce"],
            "lease_sha256": marker["lease_sha256"],
            "baseline_commit": marker["baseline_commit"],
            "head": marker["baseline_commit"],
        },
        "components": {
            "marker_identity": marker_identity,
            "marker_identity_sha256": _sha256(
                _canonical_json_bytes(marker_identity)
            ),
            "activation_profile_sha256": profile_sha256,
            "write_capability_sha256": capability_sha256,
            "fault_schedule_sha256": fault_schedule_sha256,
            "fault_phase_evidence_spec": (
                None
                if fault_schedule_sha256 is None
                else FAULT_PHASE_EVIDENCE_SPEC
            ),
            "replay_payload_sha256": _sha256(
                _canonical_json_bytes(payload)
            ),
        },
    }
    authentication = hmac.new(
        lease.encode("ascii"),
        _canonical_json_bytes(unsigned),
        hashlib.sha256,
    ).hexdigest()
    return {
        **unsigned,
        "authentication": {
            "algorithm": "hmac-sha256/v1",
            "sha256": authentication,
        },
    }


def _replay_envelope(
    *,
    payload: Mapping[str, Any],
    commitment_sha256: str,
) -> Dict[str, Any]:
    return {
        "version": REPLAY_ENVELOPE_SPEC,
        "commitment_sha256": commitment_sha256,
        "payload": copy.deepcopy(payload),
    }


def _install_replay_input(
    root: Path,
    *,
    lease: str,
    scenario_id: str,
    parsed: Mapping[str, Any],
    replay_input: Mapping[str, Any],
) -> Tuple[Path, Path, Optional[Path], Path]:
    marker = validate_marker(
        root,
        suite=SUITE,
        scenario=scenario_id,
        lease=lease,
    )
    capability_path = root / ".git" / WRITE_CAPABILITY_TARGET
    fault_schedule_path = root / ".git" / FAULT_SCHEDULE_TARGET
    commitment_path = root / ".git" / REPLAY_COMMITMENT_TARGET
    replay_path = root / ".git" / REPLAY_INPUT_TARGET
    try:
        capability_document = _capability_document(
            root,
            lease=lease,
            scenario_id=scenario_id,
            replay_input=replay_input,
            parsed=parsed,
            marker=marker,
        )
        capability_bytes = _canonical_json_bytes(capability_document)
        with capability_path.open("xb") as stream:
            stream.write(capability_bytes)
        marker["write_capability_sha256"] = _sha256(capability_bytes)
        fault_schedule_document = _fault_schedule_document(
            root,
            lease=lease,
            scenario_id=scenario_id,
            replay_input=replay_input,
            marker=marker,
        )
        if fault_schedule_document is not None:
            fault_schedule_bytes = _canonical_json_bytes(
                fault_schedule_document
            )
            with fault_schedule_path.open("xb") as stream:
                stream.write(fault_schedule_bytes)
            marker["fault_schedule_sha256"] = _sha256(
                fault_schedule_bytes
            )
        marker["replay_input"] = replay_input["id"]
        payload = _replay_payload(
            root,
            lease=lease,
            scenario_id=scenario_id,
            parsed=parsed,
            replay_input=replay_input,
            marker=marker,
        )
        commitment = _bundle_commitment(
            lease=lease,
            marker=marker,
            payload=payload,
            profile_sha256=parsed["activation_profile"]["sha256"],
            capability_sha256=_sha256(capability_bytes),
            fault_schedule_sha256=marker.get(
                "fault_schedule_sha256"
            ),
        )
        commitment_bytes = _canonical_json_bytes(commitment)
        with commitment_path.open("xb") as stream:
            stream.write(commitment_bytes)
        commitment_sha256 = _sha256(commitment_bytes)
        marker["commitment_sha256"] = commitment_sha256
        marker_path = root / ".git" / "bridge-fixture.json"
        marker_path.write_bytes(_canonical_json_bytes(marker))
        envelope = _replay_envelope(
            payload=payload,
            commitment_sha256=commitment_sha256,
        )
        with replay_path.open("xb") as stream:
            stream.write(_canonical_json_bytes(envelope))
    except OSError as error:
        raise FixtureError(
            f"cannot install bound replay input: {error}"
        ) from error
    _validate_installed_replay_input(
        root,
        lease=lease,
        scenario_id=scenario_id,
        parsed=parsed,
        replay_input=replay_input,
    )
    return (
        capability_path,
        replay_path,
        (
            fault_schedule_path
            if replay_input["fault_schedule"] is not None
            else None
        ),
        commitment_path,
    )


def _validate_installed_replay_input(
    root: Path,
    *,
    lease: str,
    scenario_id: str,
    parsed: Mapping[str, Any],
    replay_input: Mapping[str, Any],
) -> Dict[str, Any]:
    marker = validate_marker(
        root,
        suite=SUITE,
        scenario=scenario_id,
        lease=lease,
    )
    capability_path = root / ".git" / WRITE_CAPABILITY_TARGET
    fault_schedule_path = root / ".git" / FAULT_SCHEDULE_TARGET
    commitment_path = root / ".git" / REPLAY_COMMITMENT_TARGET
    replay_path = root / ".git" / REPLAY_INPUT_TARGET
    for label, candidate in (
        ("write capability", capability_path),
        ("replay commitment", commitment_path),
        ("replay input", replay_path),
    ):
        try:
            status = os.lstat(candidate)
        except OSError as error:
            raise FixtureError(
                f"cannot inspect installed {label}: {error}"
            ) from error
        if (
            not stat.S_ISREG(status.st_mode)
            or stat.S_ISLNK(status.st_mode)
            or is_reparse(candidate)
        ):
            raise FixtureError(f"installed {label} must be a plain file")
    capability_document = _capability_document(
        root,
        lease=lease,
        scenario_id=scenario_id,
        replay_input=replay_input,
        parsed=parsed,
        marker=marker,
    )
    if capability_path.read_bytes() != _canonical_json_bytes(
        capability_document
    ):
        raise FixtureError(
            "installed write capability fixture is not exact"
        )
    capability_digest = _sha256(capability_path.read_bytes())
    if (
        marker.get("write_capability_sha256") != capability_digest
        or marker.get("replay_input") != replay_input["id"]
    ):
        raise FixtureError(
            "fixture marker does not bind capability document and replay input"
        )
    expected_fault_schedule = _fault_schedule_document(
        root,
        lease=lease,
        scenario_id=scenario_id,
        replay_input=replay_input,
        marker=marker,
    )
    if expected_fault_schedule is None:
        if (
            "fault_schedule_sha256" in marker
            or os.path.lexists(fault_schedule_path)
        ):
            raise FixtureError(
                "fixture unexpectedly exposes a fault schedule"
            )
    else:
        installed_fault_schedule = _plain_installed_file(
            root,
            FAULT_SCHEDULE_TARGET,
            label="fault schedule",
        )
        expected_fault_bytes = _canonical_json_bytes(
            expected_fault_schedule
        )
        if installed_fault_schedule.read_bytes() != expected_fault_bytes:
            raise FixtureError(
                "installed fault schedule fixture is not exact"
            )
        if marker.get("fault_schedule_sha256") != _sha256(
            expected_fault_bytes
        ):
            raise FixtureError(
                "fixture marker does not bind fault schedule document"
            )
    payload = _replay_payload(
        root,
        lease=lease,
        scenario_id=scenario_id,
        parsed=parsed,
        replay_input=replay_input,
        marker=marker,
    )
    expected_commitment = _bundle_commitment(
        lease=lease,
        marker=marker,
        payload=payload,
        profile_sha256=parsed["activation_profile"]["sha256"],
        capability_sha256=capability_digest,
        fault_schedule_sha256=marker.get("fault_schedule_sha256"),
    )
    commitment_bytes = _canonical_json_bytes(expected_commitment)
    if commitment_path.read_bytes() != commitment_bytes:
        raise FixtureError("installed replay commitment is not exact")
    commitment_sha256 = _sha256(commitment_bytes)
    if marker.get("commitment_sha256") != commitment_sha256:
        raise FixtureError("fixture marker commitment binding mismatch")
    expected = _replay_envelope(
        payload=payload,
        commitment_sha256=commitment_sha256,
    )
    actual = _read_canonical_json(replay_path, label="replay input")
    if actual != expected:
        raise FixtureError("installed replay input binding is not exact")
    return actual


def _plain_installed_file(root: Path, name: str, *, label: str) -> Path:
    path = root / ".git" / name
    try:
        status = os.lstat(path)
    except OSError as error:
        raise FixtureError(f"cannot inspect installed {label}: {error}") from error
    if (
        not stat.S_ISREG(status.st_mode)
        or stat.S_ISLNK(status.st_mode)
        or is_reparse(path)
        or status.st_nlink != 1
    ):
        raise FixtureError(
            f"installed {label} must be a single-link plain file"
        )
    return path


def _installed_canonical_snapshot(
    root: Path, name: str, *, label: str
) -> Tuple[bytes, Dict[str, Any]]:
    snapshot = inspect_root_child(root / ".git", name)
    document = _parse_canonical_json_bytes(
        snapshot["bytes"], label=label
    )
    return snapshot["bytes"], document


def _facts_tree(files: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(files, list):
        raise FixtureError("blind replay input files must be an array")
    tree: Dict[str, Dict[str, Any]] = {}
    paths: List[str] = []
    for fact in files:
        if not isinstance(fact, dict):
            raise FixtureError("blind replay input file fact must be an object")
        relative = safe_relative(
            fact.get("path"), field="blind replay input file path"
        )
        entry_type = fact.get("type")
        if entry_type == "file":
            if set(fact) != {
                "path",
                "type",
                "mode",
                "sha256",
                "bytes_base64",
            }:
                raise FixtureError(
                    "blind replay regular-file fields are not closed"
                )
            try:
                data = base64.b64decode(
                    fact["bytes_base64"], validate=True
                )
            except (TypeError, ValueError, binascii.Error) as error:
                raise FixtureError(
                    "blind replay regular-file bytes are invalid"
                ) from error
            if (
                fact["mode"] not in {"100644", "100755"}
                or fact["sha256"] != _sha256(data)
                or base64.b64encode(data).decode("ascii")
                != fact["bytes_base64"]
            ):
                raise FixtureError(
                    "blind replay regular-file mode/hash mismatch"
                )
            tree[relative] = {
                "type": "file",
                "mode": fact["mode"],
                "bytes": data,
            }
        elif entry_type == "symlink":
            if set(fact) != {"path", "type", "target"} or not isinstance(
                fact["target"], str
            ):
                raise FixtureError(
                    "blind replay symlink fields are not closed"
                )
            tree[relative] = {"type": "symlink", "target": fact["target"]}
        else:
            raise FixtureError(
                "blind replay input exposes an unsupported entry type"
            )
        paths.append(relative)
    if paths != sorted(set(paths)):
        raise FixtureError(
            "blind replay input file facts must be sorted and unique"
        )
    return tree


def _validate_blind_fault_schedule(
    root: Path,
    *,
    lease: str,
    replay_id: str,
    scenario_id: str,
    marker: Mapping[str, Any],
    envelope: Mapping[str, Any],
    input_tree: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    wrapper = envelope["fault_schedule"]
    schedule_path = root / ".git" / FAULT_SCHEDULE_TARGET
    if wrapper is None:
        if (
            "fault_schedule_sha256" in marker
            or os.path.lexists(schedule_path)
        ):
            raise FixtureError(
                "blind replay has an unbound fault schedule"
            )
        return None
    if not isinstance(wrapper, dict) or set(wrapper) != {
        "version",
        "sha256",
        "facts",
    }:
        raise FixtureError(
            "blind replay fault schedule fields are not closed"
        )
    installed_bytes, document = _installed_canonical_snapshot(
        root,
        FAULT_SCHEDULE_TARGET,
        label="fault schedule",
    )
    if (
        wrapper["version"] != FAULT_SCHEDULE_SPEC
        or wrapper["sha256"] != _sha256(installed_bytes)
        or marker.get("fault_schedule_sha256") != wrapper["sha256"]
        or wrapper["facts"] != document
    ):
        raise FixtureError(
            "blind replay fault schedule hash chain mismatch"
        )
    required = {
        "version",
        "binding",
        "phase",
        "target",
        "expected_preimage_sha256",
        "injected",
        "persistence",
        "zero_bridge_write",
    }
    if not isinstance(document, dict) or set(document) != required:
        raise FixtureError(
            "blind replay fault schedule document fields are not closed"
        )
    binding = document["binding"]
    if not isinstance(binding, dict) or set(binding) != {
        "marker_spec",
        "suite",
        "scenario",
        "replay_input",
        "resolved_root",
        "baseline_commit",
        "lease_sha256",
        "source_sha256",
    }:
        raise FixtureError(
            "blind replay fault schedule binding fields are not closed"
        )
    if (
        document["version"] != FAULT_SCHEDULE_SPEC
        or binding["marker_spec"] != marker["spec"]
        or binding["suite"] != SUITE
        or binding["scenario"] != scenario_id
        or binding["replay_input"] != replay_id
        or binding["resolved_root"] != str(root.resolve())
        or binding["baseline_commit"] != marker["baseline_commit"]
        or binding["lease_sha256"] != _sha256(lease.encode("ascii"))
        or SHA256_PATTERN.fullmatch(str(binding["source_sha256"])) is None
    ):
        raise FixtureError(
            "blind replay fault schedule document binding mismatch"
        )
    if (
        document["phase"]
        != "after-confirmation-before-final-preflight"
        or document["persistence"] != "persistent"
        or document["zero_bridge_write"] is not True
    ):
        raise FixtureError(
            "blind replay fault schedule timing/persistence mismatch"
        )
    target = safe_relative(
        document["target"], field="blind replay fault target"
    )
    preimage = input_tree.get(target)
    if (
        not isinstance(preimage, dict)
        or preimage.get("type") != "file"
        or not isinstance(preimage.get("bytes"), bytes)
        or document["expected_preimage_sha256"]
        != _sha256(preimage["bytes"])
    ):
        raise FixtureError(
            "blind replay fault expected preimage hash mismatch"
        )
    injected = document["injected"]
    if not isinstance(injected, dict) or set(injected) != {
        "type",
        "mode",
        "sha256",
        "bytes_base64",
    }:
        raise FixtureError(
            "blind replay injected file fields are not closed"
        )
    try:
        injected_bytes = base64.b64decode(
            injected["bytes_base64"], validate=True
        )
    except (TypeError, ValueError, binascii.Error) as error:
        raise FixtureError(
            "blind replay injected file bytes are invalid"
        ) from error
    if (
        injected["type"] != "file"
        or injected["mode"] not in {"100644", "100755"}
        or injected["sha256"] != _sha256(injected_bytes)
        or base64.b64encode(injected_bytes).decode("ascii")
        != injected["bytes_base64"]
        or injected_bytes == preimage["bytes"]
    ):
        raise FixtureError(
            "blind replay injected file mode/hash mismatch"
        )
    guarded_targets = [
        operation.get("path")
        for operation in envelope["capability"]["facts"].get(
            "operations", []
        )
        if operation.get("protocol") == "guarded-patch/v1"
    ]
    if guarded_targets != [target]:
        raise FixtureError(
            "blind replay fault target is not the exact guarded host call"
        )
    return document


def _rendered_tree_from_envelope(
    input_tree: Mapping[str, Any],
    operations: Any,
) -> Dict[str, Dict[str, Any]]:
    if not isinstance(operations, list):
        raise FixtureError("blind replay render operations must be an array")
    rendered = copy.deepcopy(input_tree)
    paths: List[str] = []
    for operation in operations:
        if not isinstance(operation, dict):
            raise FixtureError("blind replay render operation must be an object")
        relative = safe_relative(
            operation.get("path"), field="blind replay render path"
        )
        operation_name = operation.get("operation")
        before = input_tree.get(relative)
        if operation_name == "delete":
            if set(operation) != {"operation", "path"} or before is None:
                raise FixtureError(
                    "blind replay delete operation is not exact"
                )
            rendered.pop(relative, None)
        elif operation_name in {"create", "replace"}:
            if (operation_name == "create") != (before is None):
                raise FixtureError(
                    "blind replay create/replace preimage relation mismatch"
                )
            fact = {
                key: value
                for key, value in operation.items()
                if key != "operation"
            }
            entry = _facts_tree([fact])[relative]
            if before == entry:
                raise FixtureError(
                    "blind replay render operation is byte-neutral"
                )
            rendered[relative] = entry
        else:
            raise FixtureError("blind replay render operation kind is invalid")
        paths.append(relative)
    if paths != sorted(set(paths)):
        raise FixtureError(
            "blind replay render operations must be sorted and path-unique"
        )
    return rendered


def _validate_replay_bundle(
    root: Path,
    *,
    lease: str,
    replay_id: str,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    _, envelope = _installed_canonical_snapshot(
        root, REPLAY_INPUT_TARGET, label="replay input"
    )
    if (
        set(envelope)
        != {"version", "commitment_sha256", "payload"}
        or envelope["version"] != REPLAY_ENVELOPE_SPEC
    ):
        raise FixtureError(
            "blind replay outer envelope fields/spec are not closed"
        )
    payload = envelope["payload"]
    if not isinstance(payload, dict) or set(payload) != {
        "canonicalization",
        "binding",
        "profile",
        "capability",
        "fault_schedule",
        "decision",
        "input",
        "render",
    }:
        raise FixtureError("blind replay payload fields are not closed")
    if payload["canonicalization"] != CANONICAL_JSON_SPEC:
        raise FixtureError("blind replay canonicalization spec mismatch")
    binding = payload["binding"]
    if not isinstance(binding, dict) or set(binding) != {
        "suite",
        "scenario",
        "replay_input",
        "resolved_root",
        "nonce",
        "lease_sha256",
        "baseline_commit",
        "head",
        "marker_identity_sha256",
        "input_tree_sha256",
    }:
        raise FixtureError("blind replay binding fields are not closed")
    scenario_id = binding["scenario"]
    if (
        binding["suite"] != SUITE
        or binding["replay_input"] != replay_id
        or binding["resolved_root"] != str(root.resolve())
        or binding["lease_sha256"] != _sha256(lease.encode("ascii"))
        or not isinstance(scenario_id, str)
        or TOKEN_PATTERN.fullmatch(scenario_id) is None
    ):
        raise FixtureError("blind replay root/lease/id binding mismatch")
    marker = validate_marker(
        root,
        suite=SUITE,
        scenario=scenario_id,
        lease=lease,
    )
    _, retained_marker = _installed_canonical_snapshot(
        root, "bridge-fixture.json", label="fixture marker"
    )
    if retained_marker != marker:
        raise FixtureError("fixture marker canonical read mismatch")
    marker_identity = _marker_identity(marker)
    marker_identity_sha256 = _sha256(
        _canonical_json_bytes(marker_identity)
    )
    if (
        binding["nonce"] != marker["nonce"]
        or binding["baseline_commit"] != marker["baseline_commit"]
        or binding["head"] != marker["baseline_commit"]
        or binding["marker_identity_sha256"]
        != marker_identity_sha256
        or marker.get("replay_input") != replay_id
    ):
        raise FixtureError("blind replay marker identity mismatch")
    commitment_bytes, commitment = _installed_canonical_snapshot(
        root, REPLAY_COMMITMENT_TARGET, label="replay commitment"
    )
    commitment_sha256 = _sha256(commitment_bytes)
    if (
        envelope["commitment_sha256"] != commitment_sha256
        or marker.get("commitment_sha256") != commitment_sha256
    ):
        raise FixtureError(
            "marker/envelope commitment references do not match"
        )
    if not isinstance(commitment, dict) or set(commitment) != {
        "version",
        "canonicalization",
        "binding",
        "components",
        "authentication",
    }:
        raise FixtureError("replay commitment fields are not closed")
    if (
        commitment["version"] != REPLAY_COMMITMENT_SPEC
        or commitment["canonicalization"] != CANONICAL_JSON_SPEC
    ):
        raise FixtureError("replay commitment spec mismatch")
    commitment_binding = commitment["binding"]
    if not isinstance(commitment_binding, dict) or set(
        commitment_binding
    ) != {
        "suite",
        "scenario",
        "replay_input",
        "resolved_root",
        "nonce",
        "lease_sha256",
        "baseline_commit",
        "head",
    }:
        raise FixtureError("replay commitment binding fields are not closed")
    expected_binding = {
        "suite": SUITE,
        "scenario": scenario_id,
        "replay_input": replay_id,
        "resolved_root": str(root.resolve()),
        "nonce": marker["nonce"],
        "lease_sha256": _sha256(lease.encode("ascii")),
        "baseline_commit": marker["baseline_commit"],
        "head": marker["baseline_commit"],
    }
    if commitment_binding != expected_binding:
        raise FixtureError("replay commitment root/lease/HEAD mismatch")
    components = commitment["components"]
    if not isinstance(components, dict) or set(components) != {
        "marker_identity",
        "marker_identity_sha256",
        "activation_profile_sha256",
        "write_capability_sha256",
        "fault_schedule_sha256",
        "fault_phase_evidence_spec",
        "replay_payload_sha256",
    }:
        raise FixtureError("replay commitment component fields are not closed")
    profile_bytes, _ = _installed_canonical_snapshot(
        root, ACTIVATION_PROFILE_TARGET, label="activation profile"
    )
    capability_bytes, _ = _installed_canonical_snapshot(
        root, WRITE_CAPABILITY_TARGET, label="write capability"
    )
    fault_digest = components["fault_schedule_sha256"]
    if fault_digest is None:
        if (
            os.path.lexists(root / ".git" / FAULT_SCHEDULE_TARGET)
            or marker.get("fault_schedule_sha256") is not None
            or components["fault_phase_evidence_spec"] is not None
        ):
            raise FixtureError("replay commitment has a stray fault component")
    else:
        fault_bytes, _ = _installed_canonical_snapshot(
            root, FAULT_SCHEDULE_TARGET, label="fault schedule"
        )
        if (
            fault_digest != _sha256(fault_bytes)
            or marker.get("fault_schedule_sha256") != fault_digest
            or components["fault_phase_evidence_spec"]
            != FAULT_PHASE_EVIDENCE_SPEC
        ):
            raise FixtureError("fault schedule commitment mismatch")
    if (
        components["marker_identity"] != marker_identity
        or components["marker_identity_sha256"]
        != marker_identity_sha256
        or components["activation_profile_sha256"]
        != _sha256(profile_bytes)
        or components["write_capability_sha256"]
        != _sha256(capability_bytes)
        or components["write_capability_sha256"]
        != marker.get("write_capability_sha256")
        or components["replay_payload_sha256"]
        != _sha256(_canonical_json_bytes(payload))
    ):
        raise FixtureError("replay commitment component digest mismatch")
    authentication = commitment["authentication"]
    if not isinstance(authentication, dict) or set(authentication) != {
        "algorithm",
        "sha256",
    }:
        raise FixtureError(
            "replay commitment authentication fields are not closed"
        )
    unsigned = {
        key: value
        for key, value in commitment.items()
        if key != "authentication"
    }
    wanted_mac = hmac.new(
        lease.encode("ascii"),
        _canonical_json_bytes(unsigned),
        hashlib.sha256,
    ).hexdigest()
    if (
        authentication["algorithm"] != "hmac-sha256/v1"
        or not hmac.compare_digest(
            str(authentication["sha256"]), wanted_mac
        )
    ):
        raise FixtureError("replay commitment authentication mismatch")
    return envelope, payload, marker, commitment


def _validate_blind_installed_replay_input(
    root: Path,
    *,
    lease: str,
    replay_id: str,
    require_input_tree: bool,
) -> Dict[str, Any]:
    _reject_recovery_claim(root)
    envelope, payload, marker, _ = _validate_replay_bundle(
        root,
        lease=lease,
        replay_id=replay_id,
    )
    binding = payload["binding"]
    scenario_id = binding["scenario"]
    capability_bytes, capability_facts = _installed_canonical_snapshot(
        root,
        WRITE_CAPABILITY_TARGET,
        label="write capability",
    )
    capability = payload["capability"]
    if not isinstance(capability, dict) or set(capability) != {
        "version",
        "sha256",
        "facts",
    }:
        raise FixtureError("blind replay capability fields are not closed")
    if (
        capability["version"] != WRITE_CAPABILITY_SPEC
        or capability["sha256"] != _sha256(capability_bytes)
        or capability["facts"] != capability_facts
        or marker.get("write_capability_sha256")
        != capability["sha256"]
    ):
        raise FixtureError("blind replay capability hash chain mismatch")
    capability_binding = capability_facts.get("binding")
    if (
        not isinstance(capability_facts, dict)
        or set(capability_facts)
        != {"version", "binding", "profiles", "operations"}
        or capability_facts.get("version") != WRITE_CAPABILITY_SPEC
        or not isinstance(capability_binding, dict)
        or set(capability_binding)
        != {
            "marker_spec",
            "suite",
            "scenario",
            "replay_input",
            "resolved_root",
            "baseline_commit",
            "lease_sha256",
            "source_sha256",
        }
        or capability_binding.get("marker_spec") != marker["spec"]
        or capability_binding.get("suite") != SUITE
        or capability_binding.get("scenario") != scenario_id
        or capability_binding.get("replay_input") != replay_id
        or capability_binding.get("resolved_root") != str(root.resolve())
        or capability_binding.get("baseline_commit")
        != marker["baseline_commit"]
        or capability_binding.get("lease_sha256")
        != _sha256(lease.encode("ascii"))
        or SHA256_PATTERN.fullmatch(
            str(capability_binding.get("source_sha256"))
        )
        is None
    ):
        raise FixtureError("blind replay capability document binding mismatch")
    profile_bytes, installed_profile = _installed_canonical_snapshot(
        root, ACTIVATION_PROFILE_TARGET, label="activation profile"
    )
    profile = payload["profile"]
    profile_facts = profile.get("facts") if isinstance(profile, dict) else None
    if (
        not isinstance(profile, dict)
        or set(profile) != {"version", "sha256", "facts"}
        or profile["version"] != ACTIVATION_PROFILE_SPEC
        or profile["sha256"] != _sha256(profile_bytes)
        or profile["facts"] != installed_profile
        or not isinstance(profile_facts, dict)
        or set(profile_facts)
        != {
            "version",
            "root_markers",
            "fallback_filenames",
            "project_doc_max_bytes",
            "budget_source",
            "codex_project_trust",
            "codex_hooks_feature",
        }
        or profile_facts["version"] != ACTIVATION_PROFILE_SPEC
        or profile_facts["codex_project_trust"]
        not in CODEX_PROJECT_TRUST_VALUES
        or profile_facts["codex_hooks_feature"]
        not in CODEX_HOOKS_FEATURE_VALUES
        or any(
            value is not None
            and (
                not isinstance(value, list)
                or not all(isinstance(item, str) for item in value)
            )
            for value in (
                profile_facts["root_markers"],
                profile_facts["fallback_filenames"],
            )
        )
        or (
            profile_facts["project_doc_max_bytes"] is not None
            and (
                not isinstance(
                    profile_facts["project_doc_max_bytes"], str
                )
                or re.fullmatch(
                    r"(?:0|[1-9][0-9]*)",
                    profile_facts["project_doc_max_bytes"],
                )
                is None
            )
        )
        or profile_facts["budget_source"]
        not in {"resolved", "documented-default"}
    ):
        raise FixtureError("blind replay activation profile mismatch")
    input_facts = payload["input"]
    if not isinstance(input_facts, dict) or set(input_facts) != {
        "files",
        "sha256",
    }:
        raise FixtureError("blind replay input facts are not closed")
    input_tree = _facts_tree(input_facts["files"])
    input_digest = _tree_digest(input_tree)
    if (
        input_facts["sha256"] != input_digest
        or binding["input_tree_sha256"] != input_digest
    ):
        raise FixtureError("blind replay input-tree hash mismatch")
    if require_input_tree:
        differences = compare_tree(root, input_tree)
        if differences:
            raise FixtureError(
                "blind replay worktree no longer equals bound input: "
                + "; ".join(differences)
            )
    _validate_blind_fault_schedule(
        root,
        lease=lease,
        replay_id=replay_id,
        scenario_id=scenario_id,
        marker=marker,
        envelope=payload,
        input_tree=input_tree,
    )
    render = payload["render"]
    if not isinstance(render, dict) or set(render) != {"operations"}:
        raise FixtureError("blind replay render fields are not closed")
    _rendered_tree_from_envelope(input_tree, render["operations"])
    _capability_rows_from_envelope(envelope)
    decision = payload["decision"]
    if decision is not None:
        if not isinstance(decision, dict) or set(decision) != {
            "version",
            "status",
            "motivation",
            "intent",
            "authorized_closures",
            "source_bindings",
            "segments",
            "sha256",
        }:
            raise FixtureError(
                "blind replay decision fields are not closed"
            )
        if (
            decision["version"] != DECISION_SPEC
            or decision["status"] not in {"confirmed", "pending"}
            or SHA256_PATTERN.fullmatch(str(decision["sha256"])) is None
            or decision["motivation"] is not None
            and (
                not isinstance(decision["motivation"], str)
                or not decision["motivation"]
            )
            or decision["intent"] is not None
            and (
                not isinstance(decision["intent"], str)
                or not decision["intent"]
            )
            or not isinstance(decision["authorized_closures"], list)
            or decision["authorized_closures"]
            != sorted(set(decision["authorized_closures"]))
            or any(
                not isinstance(item, str)
                or not item.startswith("closure/")
                for item in decision["authorized_closures"]
            )
            or not isinstance(decision["source_bindings"], list)
            or not isinstance(decision["segments"], list)
        ):
            raise FixtureError("blind replay decision facts are invalid")
        for source in decision["source_bindings"]:
            if not isinstance(source, dict) or set(source) != {
                "path",
                "sha256",
                "bytes_base64",
            }:
                raise FixtureError(
                    "blind replay decision source fields are not closed"
                )
            try:
                data = base64.b64decode(
                    source["bytes_base64"], validate=True
                )
            except (KeyError, TypeError, ValueError, binascii.Error) as error:
                raise FixtureError(
                    "blind replay decision source bytes are invalid"
                ) from error
            if (
                _sha256(data) != source.get("sha256")
                or base64.b64encode(data).decode("ascii")
                != source["bytes_base64"]
            ):
                raise FixtureError(
                    "blind replay decision source hash mismatch"
                )
            safe_relative(
                source["path"], field="blind replay decision source path"
            )
        for segment in decision["segments"]:
            if not isinstance(segment, dict) or set(segment) != {
                "id",
                "lines",
                "disposition",
                "destination",
                "decision",
            }:
                raise FixtureError(
                    "blind replay decision segment fields are not closed"
                )
            if (
                not all(
                    isinstance(segment[field], str)
                    for field in (
                        "id",
                        "lines",
                        "disposition",
                        "destination",
                        "decision",
                    )
                )
                or not segment["id"].startswith("segment/")
                or re.fullmatch(r"[1-9][0-9]*-[1-9][0-9]*", segment["lines"])
                is None
                or segment["decision"] != decision["status"]
            ):
                raise FixtureError(
                    "blind replay decision segment values are invalid"
                )
    return envelope


def _journal_value(tree: Mapping[str, Any], path: str) -> Dict[str, Any]:
    entry = tree.get(path)
    if entry is None:
        return {"kind": "missing"}
    if not isinstance(entry, dict) or entry.get("type") != "file":
        raise FixtureError(
            f"journal path {path!r} must resolve to a regular file or missing"
        )
    data = entry.get("bytes")
    mode = entry.get("mode")
    if not isinstance(data, bytes) or mode not in {"100644", "100755"}:
        raise FixtureError(f"journal path {path!r} has invalid file evidence")
    return {
        "base64": base64.b64encode(data).decode("ascii"),
        "kind": "file",
        "mode": mode,
    }




def _validate_confirmed_prewrite_plan(plan: Plan) -> None:
    headers = plan.get("headers")
    rows = plan.get("rows")
    closures = plan.get("closures")
    write_capabilities = plan.get("write_capabilities")
    if (
        not isinstance(headers, dict)
        or not isinstance(rows, list)
        or not isinstance(closures, list)
        or not isinstance(write_capabilities, list)
    ):
        raise FixtureError("journal plan structure is invalid")
    if headers.get("phase") != "pre-write":
        raise FixtureError("journal requires an exact pre-write plan")
    if headers.get("authorization") != "confirmed":
        raise FixtureError("journal requires confirmed header authorization")
    scoped_blocked = {
        row[1]
        for row in rows
        if row[2] == "selected"
        and row[5] in MUTATING_ACTIONS
        and row[7] == "not-applicable"
        and row[8] == "blocked"
    }
    mutating_rows = [
        row
        for row in rows
        if row[2] == "selected"
        and row[5] in MUTATING_ACTIONS
        and row[1] not in scoped_blocked
    ]
    if not mutating_rows or not write_capabilities:
        raise FixtureError("journal plan has no selected physical mutation")
    if any(
        row[7] != "confirmed" or row[8] != "planned"
        for row in mutating_rows
    ):
        raise FixtureError(
            "journal plan mutations must be confirmed and planned"
        )
    mutating_closures = {row[1] for row in mutating_rows}
    closure_rows = {
        row[0]: row
        for row in closures
        if row[3] == "selected" and row[0] in mutating_closures
    }
    if set(closure_rows) != mutating_closures or any(
        row[4] != "confirmed" or row[5] != "planned"
        for row in closure_rows.values()
    ):
        raise FixtureError(
            "journal plan closure authorization/outcome is not executable"
        )
    if any(
        row[1] not in mutating_closures or row[4] == "unavailable"
        for row in write_capabilities
        if row[1] not in scoped_blocked
    ):
        raise FixtureError(
            "journal plan contains an unavailable or unrelated forward step"
        )




def _strict_utf8(value: bytes, *, field: str) -> str:
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FixtureError(f"{field} must be strict UTF-8") from error


def _utf8_boundaries(value: str) -> set[int]:
    boundaries = {0}
    offset = 0
    for character in value:
        offset += len(character.encode("utf-8"))
        boundaries.add(offset)
    return boundaries


def _guarded_region(preimage: bytes, postimage: bytes) -> Dict[str, Any]:
    if not preimage or preimage == postimage:
        raise FixtureError(
            "guarded region requires a changed non-empty preimage"
        )
    pre_text = _strict_utf8(preimage, field="guarded preimage")
    post_text = _strict_utf8(postimage, field="guarded postimage")
    start = 0
    limit = min(len(pre_text), len(post_text))
    while start < limit and pre_text[start] == post_text[start]:
        start += 1
    suffix = 0
    remaining_pre = len(pre_text) - start
    remaining_post = len(post_text) - start
    while (
        suffix < remaining_pre
        and suffix < remaining_post
        and pre_text[len(pre_text) - suffix - 1]
        == post_text[len(post_text) - suffix - 1]
    ):
        suffix += 1
    old_end = len(pre_text) - suffix
    new_end = len(post_text) - suffix
    while True:
        old_text = pre_text[start:old_end]
        first = pre_text.find(old_text) if old_text else -1
        second = (
            pre_text.find(old_text, first + 1)
            if first >= 0
            else -1
        )
        if old_text and first == start and second == -1:
            break
        if start > 0:
            start -= 1
            continue
        if old_end < len(pre_text) and new_end < len(post_text):
            old_end += 1
            new_end += 1
            continue
        raise FixtureError("cannot derive a unique guarded old region")
    new_text = post_text[start:new_end]
    if pre_text[:start] + new_text + pre_text[old_end:] != post_text:
        raise FixtureError("guarded region does not reconstruct postimage")
    byte_offset = len(pre_text[:start].encode("utf-8"))
    old_region = old_text.encode("utf-8")
    new_region = new_text.encode("utf-8")
    return {
        "byte-offset": byte_offset,
        "new-base64": base64.b64encode(new_region).decode("ascii"),
        "old-base64": base64.b64encode(old_region).decode("ascii"),
    }


def _validate_guarded_region(
    region: Mapping[str, Any],
    *,
    preimage: bytes,
    postimage: bytes,
) -> None:
    if not isinstance(region, dict) or set(region) != {
        "byte-offset",
        "new-base64",
        "old-base64",
    }:
        raise FixtureError("guarded journal region fields are invalid")
    offset = region["byte-offset"]
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise FixtureError("guarded journal offset is invalid")
    try:
        old_region = base64.b64decode(
            region["old-base64"], validate=True
        )
        new_region = base64.b64decode(
            region["new-base64"], validate=True
        )
    except (TypeError, ValueError, binascii.Error) as error:
        raise FixtureError("guarded journal region is not exact base64") from error
    pre_text = _strict_utf8(preimage, field="guarded journal preimage")
    _strict_utf8(postimage, field="guarded journal postimage")
    _strict_utf8(old_region, field="guarded journal old region")
    _strict_utf8(new_region, field="guarded journal new region")
    boundaries = _utf8_boundaries(pre_text)
    old_end = offset + len(old_region)
    if offset not in boundaries or old_end not in boundaries:
        raise FixtureError(
            "guarded journal region cuts a UTF-8 code-point boundary"
        )
    if (
        not old_region
        or preimage.find(old_region) != offset
        or preimage.find(old_region, offset + 1) != -1
        or preimage[:offset] + new_region + preimage[old_end:] != postimage
    ):
        raise FixtureError(
            "guarded journal region does not prove exact replacement"
        )




def _operation_id_valid(operation_id: Any) -> bool:
    return (
        isinstance(operation_id, str)
        and 16 <= len(operation_id) <= 128
        and not any(value in operation_id for value in ("/", "\\", "\x00"))
    )


def _journal_lease_prefix(operation_id: str) -> str:
    if not _operation_id_valid(operation_id):
        raise FixtureError("live journal operation-id is invalid")
    digest = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()[:24]
    return f"bridge-live-operation-{digest}-"


def _is_within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_journal_lease_path(
    path: Path,
    *,
    root: Path,
    operation_id: str,
) -> Path:
    prefix = _journal_lease_prefix(operation_id)
    absolute = Path(os.path.abspath(path))
    if absolute.name != "journal.json":
        raise FixtureError("live journal path must name the retained journal")
    temp_root = os_temp_root().resolve()
    parent = absolute.parent
    if parent.parent != temp_root or not parent.name.startswith(prefix):
        raise FixtureError(
            "live journal lease must be a direct OS-temporary child bound "
            "to the operation-id"
        )
    nonce = parent.name[len(prefix) :]
    if not nonce or re.fullmatch(r"[A-Za-z0-9_-]+", nonce) is None:
        raise FixtureError("live journal lease nonce is invalid")
    try:
        parent_status = os.lstat(parent)
    except OSError as error:
        raise FixtureError(f"cannot inspect live journal lease: {error}") from error
    if (
        not stat.S_ISDIR(parent_status.st_mode)
        or stat.S_ISLNK(parent_status.st_mode)
        or is_reparse(parent)
    ):
        raise FixtureError(
            "live journal lease may not be a link or reparse point"
        )
    resolved_parent = parent.resolve()
    if resolved_parent.parent != temp_root:
        raise FixtureError("resolved live journal lease escaped OS temporary")
    resolved_repo = root.resolve()
    if _is_within(resolved_parent, resolved_repo):
        raise FixtureError("live journal lease must remain outside repository")
    if os.name != "nt" and parent_status.st_mode & 0o077:
        raise FixtureError("live journal lease is not access-safe")
    return absolute


def _allocate_journal_path(root: Path, operation_id: str) -> Path:
    _reject_recovery_claim(root)
    prefix = _journal_lease_prefix(operation_id)
    temp_root = os_temp_root()
    directory = Path(
        tempfile.mkdtemp(prefix=prefix, dir=str(temp_root))
    )
    try:
        os.chmod(directory, 0o700)
        path = directory / "journal.json"
        _validate_journal_lease_path(
            path,
            root=root,
            operation_id=operation_id,
        )
        return path
    except Exception:
        strict_remove_tree(directory)
        raise
















def _unit_valid(unit: str) -> bool:
    return (
        unit in {"onboarding/covenant", "onboarding/agents-md", "entry"}
        or RULE_UNIT_PATTERN.fullmatch(unit) is not None
        or SKILL_UNIT_PATTERN.fullmatch(unit) is not None
        or HOOK_UNIT_PATTERN.fullmatch(unit) is not None
    )


def _hook_unit_host(unit: str) -> Optional[str]:
    if HOOK_UNIT_PATTERN.fullmatch(unit) is None:
        return None
    return unit.rsplit("/", 1)[1]


def _validate_unit_tier(path: Path, unit: str, tier: str) -> None:
    host = _hook_unit_host(unit)
    if unit.startswith("onboarding/"):
        allowed = {"-"}
    elif unit == "entry":
        allowed = {"structural"}
    elif unit.startswith("rules/"):
        allowed = {"structural", "semantic"}
    elif host is not None:
        allowed = {"-"} if host == "source" else set(HOOK_ROW_TIERS)
    else:
        allowed = {"native", "-"}
    if tier not in allowed:
        raise FixtureError(
            f"{path}: tier {tier!r} is invalid for unit {unit!r}"
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
    annotation_set = set(annotations)
    if state == "both-changed":
        if _hook_unit_host(unit) is None:
            annotations_valid = annotation_set == {"decision-required"}
        else:
            annotations_valid = (
                "decision-required" in annotation_set
                and annotation_set - {"decision-required"}
                <= HOOK_CONFLICT_EXTRA_ANNOTATIONS
            )
        if (
            selection != "selected"
            or action != "conflict"
            or direction != "user-decision"
            or authorization != "required"
            or outcome != "deferred"
            or not annotations_valid
        ):
            raise FixtureError(
                f"{path}: both-changed requires selected/required/deferred "
                "conflict with decision-required"
            )
    if (
        state == "projection-only"
        and action == "adopt"
        and "semantic-review-required" in annotation_set
        and (
            selection != "selected"
            or direction != "projection-to-source"
            or authorization != "required"
            or outcome != "planned"
            or "intent-required" not in annotation_set
        )
    ):
        raise FixtureError(
            f"{path}: semantic projection adoption requires a selected, "
            "required, planned source candidate with intent-required"
        )
    if selection == "not-selected":
        if outcome != "not-selected" or authorization != "not-applicable":
            raise FixtureError(
                f"{path}: not-selected row requires not-selected outcome and "
                "not-applicable authorization"
            )
        return
    if outcome == "not-selected":
        raise FixtureError(f"{path}: selected row cannot use not-selected outcome")
    fixed_outcomes = {
        "unchanged": "unchanged",
        "conflict": "deferred",
        "annex-or-keep": "deferred",
        "keep": "deferred",
        "opt-in-or-skip": "deferred",
        "resolve-blocker": "blocked",
    }
    required = fixed_outcomes.get(action)
    if required is not None and outcome != required:
        raise FixtureError(
            f"{path}: action {action} requires outcome {required}, got {outcome}"
        )
    if state == "intent-missing":
        if action != "update":
            raise FixtureError(
                f"{path}: intent-missing requires update"
            )
        if phase == "pre-write" and "intent-required" not in annotations:
            raise FixtureError(
                f"{path}: unresolved intent-missing row needs intent-required"
            )
        if phase == "post-write" and "intent-required" in annotations:
            raise FixtureError(
                f"{path}: completed intent update retains intent-required"
            )
    if phase == "pre-write" and outcome in {
        "applied",
        "failed",
        "compensated",
        "partial",
        "not-attempted",
        "rolled-back",
    }:
        raise FixtureError(
            f"{path}: pre-write plan has post-write outcome {outcome}"
        )
    if phase == "post-write" and outcome == "planned":
        raise FixtureError(f"{path}: post-write plan retains planned outcome")
    if action in MUTATING_ACTIONS:
        if phase == "pre-write" and authorization == "required":
            if outcome != "planned":
                raise FixtureError(
                    f"{path}: required selected mutation must be planned"
                )
        elif authorization != "confirmed":
            raise FixtureError(
                f"{path}: selected mutation must be required or confirmed"
            )
    elif authorization == "confirmed":
        raise FixtureError(
            f"{path}: non-mutating decision row may not be confirmed"
        )
    if action == "unchanged" and direction != "-":
        raise FixtureError(f"{path}: unchanged action requires '-' direction")
    if action in {
        "conflict",
        "annex-or-keep",
        "opt-in-or-skip",
        "repair",
        "restore",
        "migrate",
        "offboard",
        "resolve-blocker",
    } and direction != "user-decision":
        raise FixtureError(
            f"{path}: {action} requires user-decision direction"
        )
    if action == "opt-in-or-skip" and "opt-in-required" not in annotation_set:
        raise FixtureError(
            f"{path}: opt-in-or-skip requires the opt-in-required annotation"
        )
    if state == "declared-unsynced" and action != "unchanged":
        raise FixtureError(
            f"{path}: declared-unsynced requires the unchanged action"
        )


def _parse_headers(
    path: Path, lines: Sequence[str], *, expectation: bool
) -> Dict[str, str]:
    if not lines or lines[0] != "# Bridge Sync Plan":
        raise FixtureError(f"{path}: invalid plan title")
    version_key = "expectation" if expectation else "spec"
    forbidden = "spec" if expectation else "expectation"
    ordered_keys = [
        "project",
        "scan root",
        "date",
        version_key,
        "contracts",
        "phase",
        "onboarding",
        "authorization",
    ]
    try:
        units_index = list(lines).index("## Units")
    except ValueError as error:
        raise FixtureError(f"{path}: missing Units section") from error
    header_lines = [line for line in lines[1:units_index] if line]
    if len(header_lines) != len(ordered_keys):
        raise FixtureError(f"{path}: plan header has missing or extra lines")
    headers: Dict[str, str] = {}
    for line, wanted_key in zip(header_lines, ordered_keys):
        prefix = f"- {wanted_key}: "
        if not line.startswith(prefix):
            raise FixtureError(
                f"{path}: expected header {wanted_key!r} in normative order"
            )
        value = line[len(prefix) :]
        if not value:
            raise FixtureError(f"{path}: empty header {wanted_key}")
        headers[wanted_key] = value
    if markdown_header(lines, forbidden) is not None:
        raise FixtureError(f"{path}: unexpected header {forbidden}")
    if headers[version_key] != PLAN_SPEC:
        raise FixtureError(f"{path}: expected {version_key} {PLAN_SPEC}")
    if headers["contracts"] != PLAN_CONTRACTS:
        raise FixtureError(f"{path}: contract tuple drift")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", headers["date"]) is None:
        raise FixtureError(f"{path}: date must use YYYY-MM-DD")
    if headers["phase"] not in {"pre-write", "post-write"}:
        raise FixtureError(f"{path}: invalid phase")
    if headers["onboarding"] not in {
        "onboarded",
        "bootstrap-required",
        "blocked",
    }:
        raise FixtureError(f"{path}: invalid onboarding")
    if headers["authorization"] not in {
        "required",
        "confirmed",
        "not-applicable",
    }:
        raise FixtureError(f"{path}: invalid authorization")
    return headers


def _parse_adoption(path: Path, lines: Sequence[str]) -> List[Tuple[str, ...]]:
    content = [
        line
        for line in markdown_section(lines, "Adoption decisions")
        if line
    ]
    if content == ["- (none)"]:
        return []
    rows = parse_table(
        lines,
        heading="Adoption decisions",
        expected_header=ADOPTION_HEADER,
        expected_separator=ADOPTION_SEPARATOR,
    )
    if not rows:
        raise FixtureError(f"{path}: Adoption decisions table has no rows")
    previous_end = 0
    for index, row in enumerate(rows, start=1):
        segment, source_lines, disposition, destination, decision = row
        match = SEGMENT_PATTERN.fullmatch(segment)
        if match is None or int(match.group(1)) != index:
            raise FixtureError(
                f"{path}: adoption segments must be segment/1..N in file order"
            )
        line_match = LINES_PATTERN.fullmatch(source_lines)
        if line_match is None:
            raise FixtureError(f"{path}: invalid segment lines {source_lines}")
        start, end = map(int, line_match.groups())
        if start > end or start <= previous_end:
            raise FixtureError(
                f"{path}: adoption line spans overlap or are out of order"
            )
        previous_end = end
        if disposition not in {
            "shared-entry",
            "shared-rule",
            "manual",
            "discard",
        }:
            raise FixtureError(f"{path}: invalid adoption disposition")
        if decision not in {"pending", "confirmed"}:
            raise FixtureError(f"{path}: invalid adoption decision")
        if disposition == "shared-entry" and destination != "entry":
            raise FixtureError(
                f"{path}: shared-entry destination must be entry"
            )
        if disposition == "shared-rule":
            if RULE_UNIT_PATTERN.fullmatch(destination) is None:
                raise FixtureError(
                    f"{path}: shared-rule destination must be rules/<id>"
                )
        elif disposition in {"manual", "discard"} and destination != "-":
            raise FixtureError(
                f"{path}: {disposition} destination must be '-'"
            )
    return rows


def _parse_hook_tiers(
    path: Path, lines: Sequence[str]
) -> List[Tuple[str, ...]]:
    content = [
        line for line in markdown_section(lines, "Hook tiers") if line
    ]
    if content == ["- (none)"]:
        return []
    rows = parse_table(
        lines,
        heading="Hook tiers",
        expected_header=HOOK_TIER_HEADER,
        expected_separator=HOOK_TIER_SEPARATOR,
    )
    if not rows:
        raise FixtureError(f"{path}: Hook tiers table has no rows")
    units: List[str] = []
    for row in rows:
        unit, hook_class, surface, tier, reason = row
        host = _hook_unit_host(unit)
        if host is None:
            raise FixtureError(
                f"{path}: Hook tiers row must name a hook unit, got {unit!r}"
            )
        if hook_class not in HOOK_CLASSES:
            raise FixtureError(f"{path}: invalid hook class {hook_class!r}")
        if host == "source":
            if (surface, tier, reason) != ("-", "-", "-"):
                raise FixtureError(
                    f"{path}: hook source row uses '-' for surface, tier "
                    "and reason"
                )
        else:
            if surface not in HOOK_SURFACES[host]:
                raise FixtureError(
                    f"{path}: surface {surface!r} is invalid for host {host}"
                )
            if tier not in HOOK_ROW_TIERS:
                raise FixtureError(f"{path}: invalid hook tier {tier!r}")
            if HOOK_SURFACE_TIERS[(host, surface)] != tier:
                raise FixtureError(
                    f"{path}: surface {surface!r} requires tier "
                    f"{HOOK_SURFACE_TIERS[(host, surface)]!r}"
                )
            if reason not in HOOK_TIER_REASONS:
                raise FixtureError(
                    f"{path}: invalid hook tier reason {reason!r}"
                )
        units.append(unit)
    if units != sorted(units) or len(units) != len(set(units)):
        raise FixtureError(
            f"{path}: Hook tiers rows must be byte-wise sorted and unique"
        )
    return rows


def _parse_hook_adoption(
    path: Path, lines: Sequence[str]
) -> List[Tuple[str, ...]]:
    content = [
        line
        for line in markdown_section(lines, "Hook adoption decisions")
        if line
    ]
    if content == ["- (none)"]:
        return []
    rows = parse_table(
        lines,
        heading="Hook adoption decisions",
        expected_header=HOOK_ADOPTION_HEADER,
        expected_separator=HOOK_ADOPTION_SEPARATOR,
    )
    if not rows:
        raise FixtureError(
            f"{path}: Hook adoption decisions table has no rows"
        )
    locations: List[str] = []
    carriers: List[str] = []
    for index, row in enumerate(rows, start=1):
        handler, location, disposition, destination, decision = row
        match = HOOK_HANDLER_PATTERN.fullmatch(handler)
        if match is None or int(match.group(1)) != index:
            raise FixtureError(
                f"{path}: hook handlers must be handler/1..N in file order"
            )
        location_match = HOOK_LOCATION_PATTERN.fullmatch(location)
        if location_match is None:
            raise FixtureError(
                f"{path}: invalid hook handler location {location!r}"
            )
        carrier = location_match.group(1)
        safe_relative(carrier, field=f"{path} hook handler carrier")
        if carriers and carrier != carriers[-1]:
            if carrier < carriers[-1] or carrier in set(carriers):
                raise FixtureError(
                    f"{path}: hook handler rows must be grouped by carrier "
                    "in byte-wise carrier path order"
                )
        carriers.append(carrier)
        if disposition not in HOOK_ADOPTION_DISPOSITIONS:
            raise FixtureError(
                f"{path}: invalid hook adoption disposition {disposition!r}"
            )
        if decision not in HOOK_ADOPTION_DECISIONS:
            raise FixtureError(
                f"{path}: invalid hook adoption decision {decision!r}"
            )
        if disposition == "adopt":
            if HOOK_DESTINATION_PATTERN.fullmatch(destination) is None:
                raise FixtureError(
                    f"{path}: adopt destination must be hooks/<id>"
                )
        elif destination != "-":
            raise FixtureError(
                f"{path}: {disposition} destination must be '-'"
            )
        locations.append(location)
    if len(locations) != len(set(locations)):
        raise FixtureError(
            f"{path}: hook handler locations must be unique"
        )
    return rows


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
    """Bind post-write-only annotations to a carrier this row may have written.

    `live-activation-unknown` and `restart-may-be-required` follow the
    entry/rule/skill carrier. `awaiting-host-trust` follows the Codex hooks
    carrier only, so a Claude or source hook row and every pre-write plan
    never carry it.
    """

    carrier_written = False
    hook_carrier_written = False
    if phase == "post-write" and outcome in {"applied", "partial"}:
        if unit.startswith("skills/"):
            name = unit[len("skills/") :]
            prefix = f".agents/skills/{name}/"
            carrier_written = any(
                operation[1] == closure
                and operation[2].startswith(prefix)
                for operation in write_capabilities
            )
        elif unit in {
            "entry",
            "onboarding/agents-md",
            "onboarding/covenant",
        } or unit.startswith("rules/"):
            carrier_written = any(
                operation[1] == closure and operation[2] == "AGENTS.md"
                for operation in write_capabilities
            )
        elif _hook_unit_host(unit) == "codex":
            hook_carrier_written = any(
                operation[1] == closure
                and operation[2] == ".codex/hooks.json"
                for operation in write_capabilities
            )
    for annotation, expected in (
        ("live-activation-unknown", carrier_written),
        ("restart-may-be-required", carrier_written),
        ("awaiting-host-trust", hook_carrier_written),
    ):
        if (annotation in annotations) != expected:
            raise FixtureError(
                f"{path}: {annotation} does not match post-write "
                f"carrier-touch timing for {unit}"
            )


def _hook_decision_shape(
    selection: str,
    authorization: str,
    outcome: str,
    annotations: set[str],
) -> Optional[str]:
    """Name the closed hook decision shape a row serializes, or None."""

    triple = (selection, authorization, outcome)
    for name, shape_triple, required in HOOK_DECISION_SHAPES:
        if shape_triple != triple or not required <= annotations:
            continue
        if annotations - required <= HOOK_NEUTRAL_ANNOTATIONS:
            return name
    return None


def _validate_hook_decisions(
    path: Path,
    parsed_rows: Sequence[Tuple[str, ...]],
    hook_tiers: Sequence[Tuple[str, ...]],
) -> None:
    """Enforce hook decision shapes and the gate all-or-nothing rule."""

    hook_classes = {row[0]: row[1] for row in hook_tiers}
    gate_projection: Dict[str, Dict[str, bool]] = {}
    for row in parsed_rows:
        unit = row[0]
        host = _hook_unit_host(unit)
        if host is None:
            continue
        entry_id = unit.split("/")[1]
        closure = row[1]
        annotations = set() if row[10] == "-" else set(row[10].split("; "))
        if HOOK_DECISION_CLOSURE_PATTERN.fullmatch(closure) is not None:
            if closure != f"closure/decision/hooks/{entry_id}":
                raise FixtureError(
                    f"{path}: {unit} must use its own hook decision closure"
                )
            shape = _hook_decision_shape(row[2], row[7], row[8], annotations)
            if shape is None:
                raise FixtureError(
                    f"{path}: {unit} is not one of the closed hook decision "
                    "shapes"
                )
        if host != "source" and hook_classes.get(unit) == "gate":
            gate_projection.setdefault(entry_id, {})[host] = (
                row[2] == "selected"
                and row[8] not in HOOK_ZERO_WRITE_OUTCOMES
            )
    for entry_id in sorted(gate_projection):
        projection = gate_projection[entry_id]
        if len(projection) == 2 and len(set(projection.values())) != 1:
            raise FixtureError(
                f"{path}: class gate entry {entry_id} must project both "
                "host carriers together or neither"
            )


def _parse_capability_profiles(
    path: Path, lines: Sequence[str]
) -> List[Tuple[str, ...]]:
    content = [
        line
        for line in markdown_section(lines, "Capability profiles")
        if line
    ]
    if content == ["- (none)"]:
        return []
    rows = parse_table(
        lines,
        heading="Capability profiles",
        expected_header=CAPABILITY_PROFILE_HEADER,
        expected_separator=CAPABILITY_PROFILE_SEPARATOR,
    )
    if not rows:
        raise FixtureError(f"{path}: Capability profiles table has no rows")
    identifier = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:+/-]*")
    assumption = re.compile(r"[a-z0-9][a-z0-9._-]*/v[1-9][0-9]*")
    for index, row in enumerate(rows, start=1):
        binding, profile, host, version, tool, platform, assumptions = row
        if binding != f"capability/{index}":
            raise FixtureError(
                f"{path}: capability bindings must be capability/1..N"
            )
        if profile != "capability-profile/v1":
            raise FixtureError(f"{path}: invalid capability profile token")
        if host not in {"claude-code", "codex", "other", "unresolved"}:
            raise FixtureError(f"{path}: invalid capability host")
        if platform not in {
            "linux",
            "macos",
            "windows",
            "other",
            "unresolved",
        }:
            raise FixtureError(f"{path}: invalid capability platform")
        if version != "unresolved" and identifier.fullmatch(version) is None:
            raise FixtureError(f"{path}: invalid capability host version")
        if tool != "unresolved" and identifier.fullmatch(tool) is None:
            raise FixtureError(f"{path}: invalid capability tool surface")
        if assumptions != "unresolved":
            tokens = assumptions.split("; ")
            if tokens != sorted(set(tokens)) or any(
                assumption.fullmatch(token) is None for token in tokens
            ):
                raise FixtureError(
                    f"{path}: invalid filesystem assumption tokens"
                )
    return rows


def _parse_write_capabilities(
    path: Path, lines: Sequence[str]
) -> List[Tuple[str, ...]]:
    content = [
        line
        for line in markdown_section(lines, "Write capabilities")
        if line
    ]
    if content == ["- (none)"]:
        return []
    rows = parse_table(
        lines,
        heading="Write capabilities",
        expected_header=WRITE_CAPABILITY_HEADER,
        expected_separator=WRITE_CAPABILITY_SEPARATOR,
    )
    if not rows:
        raise FixtureError(f"{path}: Write capabilities table has no rows")
    for index, row in enumerate(rows, start=1):
        (
            step,
            closure,
            relative,
            operation,
            protocol,
            binding,
            inverse,
            inverse_binding,
        ) = row
        if step != str(index):
            raise FixtureError(
                f"{path}: write capability steps must be 1..N in row order"
            )
        if not _closure_id_valid(closure):
            raise FixtureError(
                f"{path}: invalid write capability closure {closure!r}"
            )
        safe_relative(
            relative,
            field=f"{path} write capability step {step} path",
        )
        if operation not in {"replace", "create", "delete"}:
            raise FixtureError(
                f"{path}: invalid write capability operation {operation!r}"
            )
        if protocol not in WRITE_PROTOCOLS or inverse not in WRITE_PROTOCOLS:
            raise FixtureError(f"{path}: invalid write protocol token")
        if (protocol == "unavailable") != (binding == "-"):
            raise FixtureError(
                f"{path}: forward binding does not match protocol"
            )
        if (inverse == "unavailable") != (inverse_binding == "-"):
            raise FixtureError(
                f"{path}: inverse binding does not match protocol"
            )
        allowed_forward = {
            "replace": {
                "strict-replace/v1",
                "guarded-patch/v1",
                "unavailable",
            },
            "create": {"strict-create/v1", "unavailable"},
            "delete": {"strict-delete/v1", "unavailable"},
        }[operation]
        allowed_inverse = {
            "replace": {"strict-replace/v1", "unavailable"},
            "create": {"strict-delete/v1", "unavailable"},
            "delete": {"strict-create/v1", "unavailable"},
        }[operation]
        if protocol not in allowed_forward or inverse not in allowed_inverse:
            raise FixtureError(
                f"{path}: protocol does not match {operation} at step {step}"
            )
    return rows


def _validate_capability_binding_order(
    path: Path,
    capability_profiles: Sequence[Tuple[str, ...]],
    write_capabilities: Sequence[Tuple[str, ...]],
) -> None:
    first_use: List[str] = []
    seen: set[str] = set()
    for row in write_capabilities:
        for binding in (row[5], row[7]):
            if binding != "-" and binding not in seen:
                seen.add(binding)
                first_use.append(binding)
    declared = [row[0] for row in capability_profiles]
    if first_use != declared:
        raise FixtureError(
            f"{path}: capability bindings must be allocated contiguously "
            "by numeric suffix in forward-then-inverse first-use order"
        )


def _expect_fixture_error(callback: Any, *, label: str) -> None:
    try:
        callback()
    except FixtureError:
        return
    raise FixtureError(f"adversarial fixture was unexpectedly accepted: {label}")


def _exercise_contract_adversarials() -> int:
    path = Path("<m3-contract-adversarial>")
    profile_rows = [
        (
            f"capability/{index}",
            "capability-profile/v1",
            "other",
            f"fixture-{index}",
            f"tool-{index}",
            "other",
            "existing-regular-utf8/v1",
        )
        for index in range(1, 11)
    ]
    write_rows = [
        (
            str(index),
            "closure/agents-md",
            f"fixture-{index}.txt",
            "replace",
            "strict-replace/v1",
            f"capability/{index}",
            "unavailable",
            "-",
        )
        for index in range(1, 11)
    ]

    def section_lines(
        heading: str,
        header: str,
        separator: str,
        rows: Sequence[Tuple[str, ...]],
    ) -> List[str]:
        return [
            f"## {heading}",
            "",
            header,
            separator,
            *["| " + " | ".join(row) + " |" for row in rows],
        ]

    profiles = _parse_capability_profiles(
        path,
        section_lines(
            "Capability profiles",
            CAPABILITY_PROFILE_HEADER,
            CAPABILITY_PROFILE_SEPARATOR,
            profile_rows,
        ),
    )
    writes = _parse_write_capabilities(
        path,
        section_lines(
            "Write capabilities",
            WRITE_CAPABILITY_HEADER,
            WRITE_CAPABILITY_SEPARATOR,
            write_rows,
        ),
    )
    _validate_capability_binding_order(path, profiles, writes)
    checks = 1

    bytewise_rows = [
        profile_rows[0],
        profile_rows[9],
        *profile_rows[1:9],
    ]
    _expect_fixture_error(
        lambda: _parse_capability_profiles(
            path,
            section_lines(
                "Capability profiles",
                CAPABILITY_PROFILE_HEADER,
                CAPABILITY_PROFILE_SEPARATOR,
                bytewise_rows,
            ),
        ),
        label="capability/1, capability/10, capability/2 order",
    )
    checks += 1
    _expect_fixture_error(
        lambda: _parse_capability_profiles(
            path,
            section_lines(
                "Capability profiles",
                CAPABILITY_PROFILE_HEADER,
                CAPABILITY_PROFILE_SEPARATOR,
                [profile_rows[0], *profile_rows[2:]],
            ),
        ),
        label="missing capability numeric suffix",
    )
    checks += 1
    _expect_fixture_error(
        lambda: _validate_capability_binding_order(
            path,
            profiles,
            writes[:-1],
        ),
        label="unreferenced capability profile",
    )
    checks += 1
    first_use_out_of_order = list(writes)
    first = list(first_use_out_of_order[0])
    second = list(first_use_out_of_order[1])
    first[5], second[5] = second[5], first[5]
    first_use_out_of_order[0] = tuple(first)
    first_use_out_of_order[1] = tuple(second)
    _expect_fixture_error(
        lambda: _validate_capability_binding_order(
            path,
            profiles,
            first_use_out_of_order,
        ),
        label="capability binding not allocated by first use",
    )
    checks += 1
    _expect_fixture_error(
        lambda: _validate_row_semantics(
            path,
            unit="entry",
            phase="pre-write",
            selection="selected",
            state="blocked",
            action="resolve-blocker",
            direction="-",
            authorization="not-applicable",
            outcome="blocked",
            annotations=[],
        ),
        label="resolve-blocker without user-decision direction",
    )
    checks += 1

    unicode_cases = (
        ("café".encode("utf-8"), "cafê".encode("utf-8")),
        ("alpha beta".encode("utf-8"), "alpha 你好 beta".encode("utf-8")),
        ("alpha café beta".encode("utf-8"), "alpha caf beta".encode("utf-8")),
    )
    for preimage, postimage in unicode_cases:
        region = _guarded_region(preimage, postimage)
        _validate_guarded_region(
            region,
            preimage=preimage,
            postimage=postimage,
        )
        checks += 1
    mid_codepoint = {
        "byte-offset": 1,
        "old-base64": base64.b64encode(b"x").decode("ascii"),
        "new-base64": base64.b64encode(b"y").decode("ascii"),
    }
    _expect_fixture_error(
        lambda: _validate_guarded_region(
            mid_codepoint,
            preimage="éx".encode("utf-8"),
            postimage="éy".encode("utf-8"),
        ),
        label="guarded region starts inside a UTF-8 code point",
    )
    checks += 1
    return checks


def _hook_section_lines(
    heading: str,
    header: str,
    separator: str,
    rows: Sequence[Tuple[str, ...]],
) -> List[str]:
    return [
        f"## {heading}",
        "",
        header,
        separator,
        *["| " + " | ".join(row) + " |" for row in rows],
    ]


def _exercise_hook_section_contract() -> int:
    """Named checks for the two sync-plan/v3 hook sections and registries."""

    path = Path("<m3-hook-section-adversarial>")

    def tiers(rows: Sequence[Tuple[str, ...]]) -> List[Tuple[str, ...]]:
        return _parse_hook_tiers(
            path,
            _hook_section_lines(
                "Hook tiers",
                HOOK_TIER_HEADER,
                HOOK_TIER_SEPARATOR,
                rows,
            ),
        )

    def hook_adoption(
        rows: Sequence[Tuple[str, ...]]
    ) -> List[Tuple[str, ...]]:
        return _parse_hook_adoption(
            path,
            _hook_section_lines(
                "Hook adoption decisions",
                HOOK_ADOPTION_HEADER,
                HOOK_ADOPTION_SEPARATOR,
                rows,
            ),
        )

    checks = 0
    tier_rows = [
        (
            "hooks/repo-guard/claude",
            "gate",
            "settings-json",
            "native",
            "shared-event-command",
        ),
        (
            "hooks/repo-guard/codex",
            "gate",
            "none",
            "declared-unsynced",
            "decision-not-portable",
        ),
        ("hooks/repo-guard/source", "gate", "-", "-", "-"),
    ]
    if tiers(tier_rows) != [tuple(row) for row in tier_rows]:
        raise FixtureError("hook tier rows did not round-trip")
    checks += 1
    if _parse_hook_tiers(path, ["## Hook tiers", "", "- (none)"]) != []:
        raise FixtureError("empty Hook tiers section did not parse as none")
    checks += 1
    adoption_rows = [
        (
            "handler/1",
            ".claude/settings.json#PreToolUse[0][1]",
            "adopt",
            "hooks/repo-guard",
            "confirmed",
        ),
        (
            "handler/2",
            ".codex/hooks.json#SessionStart[2][0]",
            "keep",
            "-",
            "pending",
        ),
    ]
    if hook_adoption(adoption_rows) != [tuple(row) for row in adoption_rows]:
        raise FixtureError("hook adoption rows did not round-trip")
    checks += 1
    if (
        _parse_hook_adoption(
            path, ["## Hook adoption decisions", "", "- (none)"]
        )
        != []
    ):
        raise FixtureError(
            "empty Hook adoption decisions section did not parse as none"
        )
    checks += 1
    for label, rows in (
        (
            "hook tier reason outside the closed registry",
            [
                (
                    "hooks/repo-guard/claude",
                    "gate",
                    "settings-json",
                    "native",
                    "structural-projection",
                )
            ],
        ),
        (
            "hook tier disagreeing with its surface",
            [
                (
                    "hooks/repo-guard/claude",
                    "gate",
                    "settings-json",
                    "semantic",
                    "shared-event-command",
                )
            ],
        ),
        (
            "hook source row claiming a projected surface",
            [
                (
                    "hooks/repo-guard/source",
                    "gate",
                    "settings-json",
                    "native",
                    "shared-event-command",
                )
            ],
        ),
        (
            "hook tier row naming a report-shaped unit id",
            [("hooks/repo-guard", "gate", "-", "-", "-")],
        ),
        (
            "hook tier surface invalid for the host",
            [
                (
                    "hooks/repo-guard/claude",
                    "reminder",
                    "agents-md",
                    "semantic",
                    "degraded-standing-instruction",
                )
            ],
        ),
        (
            "hook tier rows out of byte-wise order",
            [tier_rows[1], tier_rows[0]],
        ),
        (
            "hook tier class outside the closed registry",
            [
                (
                    "hooks/repo-guard/claude",
                    "advisory",
                    "settings-json",
                    "native",
                    "shared-event-command",
                )
            ],
        ),
    ):
        _expect_fixture_error(
            lambda rows=rows: tiers(rows), label=label
        )
        checks += 1
    for label, rows in (
        (
            "hook handler ids out of file order",
            [adoption_rows[1]],
        ),
        (
            "hook handler location outside the closed grammar",
            [
                (
                    "handler/1",
                    ".claude/settings.json#PreToolUse[0]",
                    "keep",
                    "-",
                    "pending",
                )
            ],
        ),
        (
            "hook adoption without a hooks destination",
            [
                (
                    "handler/1",
                    ".claude/settings.json#PreToolUse[0][0]",
                    "adopt",
                    "-",
                    "pending",
                )
            ],
        ),
        (
            "hook keep with an invented destination",
            [
                (
                    "handler/1",
                    ".claude/settings.json#PreToolUse[0][0]",
                    "keep",
                    "hooks/repo-guard",
                    "pending",
                )
            ],
        ),
        (
            "duplicate hook handler location",
            [
                adoption_rows[0],
                ("handler/2",) + tuple(adoption_rows[0][1:]),
            ],
        ),
        (
            "hook handler carriers in inverted carrier-path order",
            [
                ("handler/1",) + tuple(adoption_rows[1][1:]),
                ("handler/2",) + tuple(adoption_rows[0][1:]),
            ],
        ),
        (
            "hook handler carriers interleaved instead of grouped",
            [
                adoption_rows[0],
                adoption_rows[1],
                (
                    "handler/3",
                    ".claude/settings.json#SessionStart[0][0]",
                    "keep",
                    "-",
                    "pending",
                ),
            ],
        ),
    ):
        _expect_fixture_error(
            lambda rows=rows: hook_adoption(rows), label=label
        )
        checks += 1
    accepted_warnings = [
        "- claude-hooks-shared-execution: .claude/settings.json",
        "- codex-handler-unknown-key: .codex/hooks.json "
        "(PostToolUse group=0 handler=1 key=retryLimit)",
        "- codex-hook-retrust-required: .codex/hooks.json "
        "(SessionStart group=1 handler=0)",
        "- codex-inline-hooks-conflict: .codex/config.toml (SessionStart)",
        "- codex-inline-hooks-conflict: .codex/config.toml (pointer-key)",
        "- codex-project-untrusted: .",
        "- codex-trust-blind-change: .codex/hooks.json "
        "(Stop group=0 handler=0)",
        "- codex-trust-reindex: .codex/hooks.json (PreToolUse from=1)",
        "- hook-acknowledgement-missing: .claude/rules/hooks.md",
        "- hook-carrier-absent: .codex/hooks.json",
        "- hook-format-preserved: .claude/settings.json",
        "- hook-opt-in-required: .claude/rules/hooks.md "
        "(entry deploy-on-stop)",
        "- hook-output-not-delivered: .claude/rules/hooks.md "
        "(entry reminder-start)",
        "- hook-projection-asymmetric: .codex/hooks.json "
        "(hooks/reminder-start/codex)",
        "- hooks-carrier-unusable: .codex/hooks.json (duplicate-key)",
        "- hooks-globally-disabled: .claude/settings.json",
        "- intent-doc-anomaly: .claude/rules/hooks.md (entry repo-guard)",
        "- intent-doc-anomaly: .claude/rules/hooks.md (line 42)",
        "- local-hooks-present: .claude/settings.local.json",
        "- matcher-grammar-divergent: .claude/rules/hooks.md "
        "(entry repo-guard)",
        "- platform-branch-divergence: .claude/rules/hooks.md "
        "(entry repo-guard)",
        "- undeclared-hooks-key: .claude/settings.json "
        "(SessionEnd matcher=omitted)",
    ]
    for line in accepted_warnings:
        _validate_warning_line(path, line)
    covered = {line[2:].split(": ", 1)[0] for line in accepted_warnings}
    if covered != set(HOOK_WARNING_CLASSES):
        raise FixtureError(
            "hook warning grammar coverage is incomplete"
        )
    checks += 1
    for line in (
        "- hook-carrier-absent: AGENTS.md",
        "- hook-projection-asymmetric: AGENTS.md "
        "(hooks/reminder-start/codex)",
    ):
        _validate_warning_line(path, line)
    checks += 1
    for label, line in (
        (
            "hook warning naming the wrong carrier",
            "- intent-doc-anomaly: AGENTS.md (entry repo-guard)",
        ),
        (
            "hook warning with a malformed handler position",
            "- codex-hook-retrust-required: .codex/hooks.json "
            "(SessionStart group=one handler=0)",
        ),
        (
            "hook warning detail that is not a unit id",
            "- hook-projection-asymmetric: .codex/hooks.json "
            "(hooks/reminder-start)",
        ),
        (
            "project-scope hook warning with a file path",
            "- codex-project-untrusted: .codex/hooks.json",
        ),
        (
            "hook carrier warning with an unregistered reason",
            "- hooks-carrier-unusable: .codex/hooks.json (encoding-error)",
        ),
        (
            "hook warning with a missing required detail",
            "- hook-opt-in-required: .claude/rules/hooks.md",
        ),
        (
            "hook warning with a forbidden detail",
            "- hook-format-preserved: .claude/settings.json (entry alpha)",
        ),
        (
            "global hooks disablement outside a settings file",
            "- hooks-globally-disabled: .codex/hooks.json",
        ),
        (
            "undeclared hooks key outside a JSON hooks carrier",
            "- undeclared-hooks-key: AGENTS.md (SessionEnd matcher=omitted)",
        ),
        (
            "unusable hooks carrier naming a local settings overlay",
            "- hooks-carrier-unusable: .claude/settings.local.json "
            "(parse-error)",
        ),
    ):
        _expect_fixture_error(
            lambda line=line: _validate_warning_line(path, line),
            label=label,
        )
        checks += 1
    for unit in (
        "hooks/repo-guard/source",
        "hooks/repo-guard/claude",
        "hooks/repo-guard/codex",
    ):
        if not _unit_valid(unit):
            raise FixtureError(f"hook unit id {unit!r} was rejected")
    for closure in (
        "closure/hooks/source",
        "closure/hooks/claude",
        "closure/hooks/codex",
        "closure/decision/hooks/repo-guard",
    ):
        if not _closure_id_valid(closure):
            raise FixtureError(f"hook closure id {closure!r} was rejected")
    if (
        _unit_valid("hooks/repo-guard")
        or _unit_valid("hooks/Repo-Guard/claude")
        or _closure_id_valid("closure/hooks/agents-md")
        or _closure_id_valid("closure/decision/hooks/Repo-Guard")
    ):
        raise FixtureError("hook id grammar accepted an off-grammar value")
    checks += 1
    _validate_unit_tier(path, "hooks/repo-guard/codex", "declared-unsynced")
    _validate_unit_tier(path, "hooks/repo-guard/source", "-")
    for label, unit, tier in (
        (
            "structural tier on a hook row",
            "hooks/repo-guard/claude",
            "structural",
        ),
        (
            "native tier on a hook source row",
            "hooks/repo-guard/source",
            "native",
        ),
    ):
        _expect_fixture_error(
            lambda unit=unit, tier=tier: _validate_unit_tier(
                path, unit, tier
            ),
            label=label,
        )
    checks += 1
    _validate_row_semantics(
        path,
        unit="hooks/repo-guard/claude",
        phase="pre-write",
        selection="selected",
        state="no-baseline",
        action="opt-in-or-skip",
        direction="user-decision",
        authorization="required",
        outcome="deferred",
        annotations=["decision-required", "opt-in-required"],
    )
    _expect_fixture_error(
        lambda: _validate_row_semantics(
            path,
            unit="hooks/repo-guard/claude",
            phase="pre-write",
            selection="selected",
            state="no-baseline",
            action="opt-in-or-skip",
            direction="user-decision",
            authorization="required",
            outcome="deferred",
            annotations=["decision-required"],
        ),
        label="opt-in-or-skip without opt-in-required",
    )
    checks += 1
    _validate_row_semantics(
        path,
        unit="hooks/repo-guard/codex",
        phase="pre-write",
        selection="selected",
        state="declared-unsynced",
        action="unchanged",
        direction="-",
        authorization="not-applicable",
        outcome="unchanged",
        annotations=[],
    )
    _expect_fixture_error(
        lambda: _validate_row_semantics(
            path,
            unit="hooks/repo-guard/codex",
            phase="pre-write",
            selection="selected",
            state="declared-unsynced",
            action="update",
            direction="source-to-projection",
            authorization="confirmed",
            outcome="planned",
            annotations=[],
        ),
        label="declared-unsynced with a mutating action",
    )
    checks += 1
    for conflict_annotations in (
        ["decision-required"],
        ["decision-required", "event-unverified"],
        ["awaiting-host-trust", "decision-required", "opt-in-required"],
    ):
        _validate_row_semantics(
            path,
            unit="hooks/repo-guard/codex",
            phase="pre-write",
            selection="selected",
            state="both-changed",
            action="conflict",
            direction="user-decision",
            authorization="required",
            outcome="deferred",
            annotations=conflict_annotations,
        )
    for label, unit, conflict_annotations in (
        (
            "hook conflict without decision-required",
            "hooks/repo-guard/codex",
            ["event-unverified"],
        ),
        (
            "hook conflict carrying an unrelated annotation",
            "hooks/repo-guard/codex",
            ["decision-required", "intent-required"],
        ),
        (
            "entry conflict carrying a hook annotation",
            "entry",
            ["decision-required", "event-unverified"],
        ),
    ):
        _expect_fixture_error(
            lambda unit=unit, conflict_annotations=conflict_annotations: (
                _validate_row_semantics(
                    path,
                    unit=unit,
                    phase="pre-write",
                    selection="selected",
                    state="both-changed",
                    action="conflict",
                    direction="user-decision",
                    authorization="required",
                    outcome="deferred",
                    annotations=conflict_annotations,
                )
            ),
            label=label,
        )
    checks += 1
    scoped_tokens = {
        token
        for gate in CLOSURE_SCOPED_APPLY_BLOCKER_GATES
        for token in APPLY_BLOCKER_GATES[gate]
    }
    blocker_tokens = {
        token
        for token, warning_class in HOOK_WARNING_CLASSES.items()
        if warning_class == "blocker"
    }
    if (
        scoped_tokens != CLOSURE_SCOPED_BLOCKING_WARNINGS
        or not CLOSURE_SCOPED_APPLY_BLOCKER_GATES.issubset(
            set(APPLY_BLOCKER_GATES)
        )
        or not blocker_tokens.issubset(BLOCKING_WARNINGS)
        or PROJECT_WIDE_BLOCKING_WARNINGS & CLOSURE_SCOPED_BLOCKING_WARNINGS
        or "intent-doc-anomaly" not in PROJECT_WIDE_BLOCKING_WARNINGS
        or not set(HOOK_WARNING_CLASSES).issubset(PLAN_WARNINGS)
        or {
            warning_class for warning_class in HOOK_WARNING_CLASSES.values()
        }
        - {"acknowledged", "informational", "blocker"}
    ):
        raise FixtureError("hook warning class registries are inconsistent")
    checks += 1
    for profile_path in sorted(ACTIVATION_PROFILES_DIR.glob("*.json")):
        profile = read_json(profile_path)
        if (
            profile.get("version") != ACTIVATION_PROFILE_SPEC
            or profile.get("codex_project_trust")
            not in CODEX_PROJECT_TRUST_VALUES
            or profile.get("codex_hooks_feature")
            not in CODEX_HOOKS_FEATURE_VALUES
        ):
            raise FixtureError(
                f"{profile_path}: activation profile is not a valid "
                f"{ACTIVATION_PROFILE_SPEC} document"
            )
    checks += 1
    if (
        "hooks-carrier-composition" not in PLAN_VALIDATOR_FAILURES
        or _validator_failure(
            FixtureError("hooks carrier composition is not byte-exact")
        )
        != "hooks-carrier-composition"
    ):
        raise FixtureError(
            "hooks-carrier-composition is not a registered validator failure"
        )
    checks += 1
    checks += _exercise_hook_decision_shapes(path)
    checks += _exercise_hook_trust_annotation_timing(path)
    return checks


def _exercise_hook_trust_annotation_timing(path: Path) -> int:
    """Named checks for the post-write scope of awaiting-host-trust."""

    codex_write = (
        "1",
        "closure/hooks/codex",
        ".codex/hooks.json",
        "replace",
        "guarded-patch/v1",
        "cap1",
        "replace",
        "cap2",
    )

    def timing(
        unit: str,
        annotations: Sequence[str],
        *,
        phase: str = "post-write",
        closure: str = "closure/hooks/codex",
        outcome: str = "applied",
    ) -> None:
        _validate_carrier_annotation_timing(
            path,
            unit=unit,
            closure=closure,
            outcome=outcome,
            phase=phase,
            annotations=set(annotations),
            write_capabilities=[codex_write],
        )

    checks = 0
    timing("hooks/repo-guard/codex", ["awaiting-host-trust"])
    timing("hooks/repo-guard/claude", [], closure="closure/hooks/claude")
    timing("hooks/repo-guard/source", [], closure="closure/hooks/source")
    timing("hooks/repo-guard/codex", [], phase="pre-write", outcome="planned")
    checks += 1
    for label, unit, annotations, phase, closure, outcome in (
        (
            "written Codex hooks carrier without awaiting-host-trust",
            "hooks/repo-guard/codex",
            [],
            "post-write",
            "closure/hooks/codex",
            "applied",
        ),
        (
            "awaiting-host-trust on a Claude hook row",
            "hooks/repo-guard/claude",
            ["awaiting-host-trust"],
            "post-write",
            "closure/hooks/claude",
            "applied",
        ),
        (
            "awaiting-host-trust on a hook source row",
            "hooks/repo-guard/source",
            ["awaiting-host-trust"],
            "post-write",
            "closure/hooks/source",
            "applied",
        ),
        (
            "awaiting-host-trust in a pre-write plan",
            "hooks/repo-guard/codex",
            ["awaiting-host-trust"],
            "pre-write",
            "closure/hooks/codex",
            "planned",
        ),
        (
            "awaiting-host-trust without a touched Codex hooks carrier",
            "hooks/repo-guard/codex",
            ["awaiting-host-trust"],
            "post-write",
            "closure/decision/hooks/repo-guard",
            "applied",
        ),
    ):
        def attempt(
            unit: str = unit,
            annotations: Sequence[str] = annotations,
            phase: str = phase,
            closure: str = closure,
            outcome: str = outcome,
        ) -> None:
            timing(
                unit,
                annotations,
                phase=phase,
                closure=closure,
                outcome=outcome,
            )

        _expect_fixture_error(attempt, label=label)
        checks += 1
    return checks


def _exercise_hook_decision_shapes(path: Path) -> int:
    """Named checks for the five hook decision shapes and the gate rule."""

    def decision_row(
        unit: str,
        selection: str,
        authorization: str,
        outcome: str,
        annotations: str,
        *,
        closure: Optional[str] = None,
    ) -> Tuple[str, ...]:
        entry_id = unit.split("/")[1]
        return (
            unit,
            closure or f"closure/decision/hooks/{entry_id}",
            selection,
            "-",
            "no-baseline",
            "opt-in-or-skip",
            "user-decision",
            authorization,
            outcome,
            "declared-unsynced",
            annotations,
        )

    gate_tiers = [
        (
            "hooks/repo-guard/claude",
            "gate",
            "settings-json",
            "native",
            "shared-event-command",
        ),
        (
            "hooks/repo-guard/codex",
            "gate",
            "codex-hooks-json",
            "native",
            "shared-event-command",
        ),
    ]
    checks = 0
    accepted_shapes = (
        (
            "opt-in-pending",
            "selected",
            "required",
            "deferred",
            "decision-required; opt-in-required",
        ),
        (
            "two-sided-conflict",
            "selected",
            "required",
            "deferred",
            "decision-required",
        ),
        (
            "pending-occupancy",
            "not-selected",
            "not-applicable",
            "not-selected",
            "decision-required",
        ),
        ("confirmed-keep", "selected", "not-applicable", "deferred", "-"),
        ("surface-none", "selected", "not-applicable", "unchanged", "-"),
    )
    for name, selection, authorization, outcome, annotations in (
        accepted_shapes
    ):
        row = decision_row(
            "hooks/repo-guard/claude",
            selection,
            authorization,
            outcome,
            annotations,
        )
        observed = _hook_decision_shape(
            row[2],
            row[7],
            row[8],
            set() if row[10] == "-" else set(row[10].split("; ")),
        )
        if observed != name:
            raise FixtureError(
                f"hook decision shape {name} resolved as {observed!r}"
            )
        _validate_hook_decisions(path, [row], gate_tiers[:1])
    if len({shape[0] for shape in HOOK_DECISION_SHAPES}) != 5:
        raise FixtureError("the hook decision shape registry is not five")
    checks += 1
    neutral_row = decision_row(
        "hooks/repo-guard/codex",
        "selected",
        "required",
        "deferred",
        "awaiting-host-trust; decision-required; event-unverified",
    )
    _validate_hook_decisions(path, [neutral_row], gate_tiers[1:])
    checks += 1
    for label, row in (
        (
            "confirmed hook keep still carrying decision-required",
            decision_row(
                "hooks/repo-guard/claude",
                "selected",
                "not-applicable",
                "deferred",
                "decision-required",
            ),
        ),
        (
            "hook opt-in pending without decision-required",
            decision_row(
                "hooks/repo-guard/claude",
                "selected",
                "required",
                "deferred",
                "opt-in-required",
            ),
        ),
        (
            "hook decision row carrying an unrelated annotation",
            decision_row(
                "hooks/repo-guard/claude",
                "selected",
                "required",
                "deferred",
                "decision-required; intent-required",
            ),
        ),
        (
            "hook decision triple outside the five closed shapes",
            decision_row(
                "hooks/repo-guard/claude",
                "not-selected",
                "required",
                "deferred",
                "decision-required",
            ),
        ),
        (
            "hook row inside another entry's decision closure",
            decision_row(
                "hooks/repo-guard/claude",
                "selected",
                "required",
                "deferred",
                "decision-required",
                closure="closure/decision/hooks/other-entry",
            ),
        ),
    ):
        _expect_fixture_error(
            lambda row=row: _validate_hook_decisions(
                path, [row], gate_tiers
            ),
            label=label,
        )
        checks += 1
    def carrier_row(
        unit: str,
        selection: str,
        outcome: str,
    ) -> Tuple[str, ...]:
        host = unit.rsplit("/", 1)[1]
        return (
            unit,
            f"closure/hooks/{host}",
            selection,
            "-",
            "no-baseline",
            "create",
            "source-to-projection",
            "confirmed",
            outcome,
            "native",
            "-",
        )

    for claude_pair, codex_pair in (
        (("selected", "planned"), ("selected", "planned")),
        (("not-selected", "not-selected"), ("not-selected", "not-selected")),
        (("selected", "blocked"), ("not-selected", "not-selected")),
        (("selected", "deferred"), ("selected", "unchanged")),
    ):
        _validate_hook_decisions(
            path,
            [
                carrier_row("hooks/repo-guard/claude", *claude_pair),
                carrier_row("hooks/repo-guard/codex", *codex_pair),
            ],
            gate_tiers,
        )
    checks += 1
    for label, claude_pair, codex_pair in (
        (
            "class gate entry projected on one host only",
            ("selected", "applied"),
            ("not-selected", "not-selected"),
        ),
        (
            "class gate entry writing beside a blocked sibling carrier",
            ("selected", "blocked"),
            ("selected", "planned"),
        ),
    ):
        def gate_attempt(
            claude_pair: Tuple[str, str] = claude_pair,
            codex_pair: Tuple[str, str] = codex_pair,
        ) -> None:
            _validate_hook_decisions(
                path,
                [
                    carrier_row("hooks/repo-guard/claude", *claude_pair),
                    carrier_row("hooks/repo-guard/codex", *codex_pair),
                ],
                gate_tiers,
            )

        _expect_fixture_error(gate_attempt, label=label)
        checks += 1
    return checks


def _exercise_public_tier_contract() -> int:
    def entry(data: bytes) -> Dict[str, Any]:
        return {"type": "file", "mode": "100644", "bytes": data}

    def row(
        unit: str,
        tier: str,
        *,
        action: str = "unchanged",
    ) -> Tuple[str, ...]:
        return (
            unit,
            "closure/decision/" + unit,
            "selected",
            "-",
            "unchanged",
            action,
            "-",
            "not-applicable",
            "unchanged",
            tier,
            "-",
        )

    def accepts(
        candidate: Tuple[str, ...],
        *,
        input_tree: Mapping[str, Any],
        rendered_tree: Mapping[str, Any],
    ) -> None:
        _validate_public_unit_tiers(
            {"rows": [candidate]},
            input_tree=input_tree,
            rendered_tree=rendered_tree,
        )

    structural = entry(
        b"<!-- bridge:intent 2026-07-24 Structural fixture -->\n# Rule\n"
    )
    scoped = entry(
        b"---\n'paths':\n  - \"docs/**/*\"\n---\n# Rule\n"
    )
    raw_non_delimiter = entry(
        b"--- \npaths:\n  - \"docs/**/*\"\n---\n# Rule\n"
    )
    rule_path = ".claude/rules/tier-fixture.md"

    accepts(
        row("rules/tier-fixture", "structural"),
        input_tree={rule_path: raw_non_delimiter},
        rendered_tree={rule_path: raw_non_delimiter},
    )
    accepts(
        row("rules/tier-fixture", "semantic"),
        input_tree={rule_path: scoped},
        rendered_tree={rule_path: scoped},
    )
    accepts(
        row("rules/tier-fixture", "semantic"),
        input_tree={rule_path: structural},
        rendered_tree={rule_path: scoped},
    )
    accepts(
        row("rules/tier-fixture", "structural"),
        input_tree={rule_path: scoped},
        rendered_tree={rule_path: structural},
    )
    accepts(
        row("skills/unmanaged-fixture", "-", action="keep"),
        input_tree={},
        rendered_tree={},
    )
    accepts(
        row("skills/managed-fixture", "native"),
        input_tree={},
        rendered_tree={},
    )
    accepts(
        row("rules/tier-fixture", "semantic", action="delete"),
        input_tree={rule_path: scoped},
        rendered_tree={},
    )

    projection = entry(
        b"<!-- bridge:managed:start id=rules/tier-fixture "
        b"source=.claude/rules/tier-fixture.md -->\n"
        b"Applies only while reading or editing files that match at least "
        b"one of these source globs: `docs/**/*`. (bridge:pv2)\n\n"
        b"# Rule\n"
        b"<!-- bridge:managed:end -->\n"
    )
    accepts(
        row("rules/tier-fixture", "semantic", action="delete"),
        input_tree={"AGENTS.md": projection},
        rendered_tree={},
    )

    rejection_cases = [
        (
            row("rules/tier-fixture", "semantic"),
            {rule_path: raw_non_delimiter},
            {rule_path: raw_non_delimiter},
            "raw non-delimiter rule tier",
        ),
        (
            row("rules/tier-fixture", "structural"),
            {rule_path: scoped},
            {rule_path: scoped},
            "quoted paths rule tier",
        ),
        (
            row("rules/tier-fixture", "structural"),
            {rule_path: structural},
            {rule_path: scoped},
            "rendered scoped tier wins",
        ),
        (
            row("rules/tier-fixture", "semantic"),
            {rule_path: scoped},
            {rule_path: structural},
            "rendered unscoped tier wins",
        ),
        (
            row("skills/unmanaged-fixture", "native", action="keep"),
            {},
            {},
            "unresolved skill tier",
        ),
        (
            row("skills/managed-fixture", "-"),
            {},
            {},
            "managed skill tier",
        ),
        (
            row("rules/tier-fixture", "structural", action="delete"),
            {rule_path: scoped},
            {},
            "delete source fallback tier",
        ),
        (
            row("rules/tier-fixture", "structural", action="delete"),
            {"AGENTS.md": projection},
            {},
            "delete projection fallback tier",
        ),
        (
            row("rules/missing", "structural", action="delete"),
            {},
            {},
            "delete tier fallback evidence",
        ),
    ]
    for candidate, input_tree, rendered_tree, label in rejection_cases:
        _expect_fixture_error(
            lambda candidate=candidate,
            input_tree=input_tree,
            rendered_tree=rendered_tree: accepts(
                candidate,
                input_tree=input_tree,
                rendered_tree=rendered_tree,
            ),
            label=label,
        )
    return 17


def _parse_migration(path: Path, lines: Sequence[str]) -> List[Tuple[str, ...]]:
    content = [
        line
        for line in markdown_section(lines, "Migration decisions")
        if line
    ]
    if content == ["- (none)"]:
        return []
    rows = parse_table(
        lines,
        heading="Migration decisions",
        expected_header=MIGRATION_HEADER,
        expected_separator=MIGRATION_SEPARATOR,
    )
    if not rows:
        raise FixtureError(f"{path}: Migration decisions table has no rows")
    units: List[str] = []
    for unit, baseline, relation, disposition, decision in rows:
        if not _unit_valid(unit) or unit == "onboarding/covenant":
            raise FixtureError(f"{path}: invalid migration unit {unit!r}")
        if baseline != "-" and HASH_PATTERN.fullmatch(baseline) is None:
            raise FixtureError(
                f"{path}: invalid migration baseline {baseline!r}"
            )
        if relation not in {
            "converged",
            "repair-required",
            "missing",
            "unsafe",
            "ambiguous",
        }:
            raise FixtureError(f"{path}: invalid migration relation")
        if (relation == "ambiguous") != (baseline == "-"):
            raise FixtureError(
                f"{path}: ambiguous migration relation requires '-' baseline"
            )
        if disposition not in {
            "carry-forward",
            "repair-and-carry",
            "release",
            "block",
        }:
            raise FixtureError(f"{path}: invalid migration disposition")
        if decision not in {"derived", "pending", "confirmed"}:
            raise FixtureError(f"{path}: invalid migration decision")
        if disposition == "carry-forward" and decision != "derived":
            raise FixtureError(
                f"{path}: carry-forward migration decision must be derived"
            )
        if disposition == "block" and decision != "pending":
            raise FixtureError(
                f"{path}: blocked migration decision must be pending"
            )
        units.append(unit)
    if units != sorted(units) or len(units) != len(set(units)):
        raise FixtureError(
            f"{path}: migration rows must be byte-wise sorted and unique"
        )
    return rows


def _parse_migration_candidates(
    path: Path, lines: Sequence[str]
) -> List[Tuple[str, ...]]:
    content = [
        line
        for line in markdown_section(lines, "Migration candidates")
        if line
    ]
    if content == ["- (none)"]:
        return []
    rows = parse_table(
        lines,
        heading="Migration candidates",
        expected_header=MIGRATION_CANDIDATE_HEADER,
        expected_separator=MIGRATION_CANDIDATE_SEPARATOR,
    )
    if not rows:
        raise FixtureError(f"{path}: Migration candidates table has no rows")
    for unit, candidate in rows:
        if (
            not _unit_valid(unit)
            or unit == "onboarding/covenant"
            or HASH_PATTERN.fullmatch(candidate) is None
        ):
            raise FixtureError(f"{path}: invalid migration candidate row")
    if rows != sorted(set(rows)):
        raise FixtureError(
            f"{path}: migration candidates must be sorted and unique"
        )
    return rows


def _closure_id_valid(value: str) -> bool:
    if value in {
        "closure/migration",
        "closure/agents-md",
        "closure/hooks/source",
        "closure/hooks/claude",
        "closure/hooks/codex",
    }:
        return True
    if HOOK_DECISION_CLOSURE_PATTERN.fullmatch(value) is not None:
        return True
    if value.startswith("closure/decision/"):
        return _unit_valid(value[len("closure/decision/") :])
    if value.startswith("closure/skill/"):
        return SKILL_UNIT_PATTERN.fullmatch(
            "skills/" + value[len("closure/skill/") :]
        ) is not None
    return re.fullmatch(
        r"closure/skill-rename/[a-z0-9-]+--to--[a-z0-9-]+",
        value,
    ) is not None


def _validate_warning_line(
    plan_path: Path, line: str
) -> Tuple[str, str, Optional[str]]:
    match = WARNING_LINE_PATTERN.fullmatch(line)
    if match is None:
        raise FixtureError(f"{plan_path}: malformed warning {line!r}")
    token, relative, detail = match.groups()
    if token not in PLAN_WARNINGS:
        raise FixtureError(f"{plan_path}: invalid warning token {token!r}")
    if token in ROOT_PATH_WARNING_TOKENS:
        if relative != ".":
            raise FixtureError(
                f"{plan_path}: graph warning {token} must use path '.'"
            )
    else:
        if relative == ".":
            raise FixtureError(
                f"{plan_path}: file warning {token} cannot use path '.'"
            )
        safe_relative(relative, field=f"{plan_path} warning path")
    pinned = HOOK_WARNING_PATHS.get(token)
    if pinned is not None and relative != pinned:
        raise FixtureError(
            f"{plan_path}: warning {token} must name {pinned}"
        )
    allowed_carriers = HOOK_CARRIER_WARNING_PATHS.get(token)
    if allowed_carriers is not None and relative not in allowed_carriers:
        raise FixtureError(
            f"{plan_path}: warning {token} must name a hooks carrier"
        )
    if token in WARNING_DETAIL_TOKENS:
        if detail is None:
            raise FixtureError(
                f"{plan_path}: warning {token} requires closed detail"
            )
    elif detail is not None:
        raise FixtureError(
            f"{plan_path}: warning {token} forbids detail"
        )
    if detail is None:
        return token, relative, detail
    payload = detail[1:-1]
    if token == "active-shared-import":
        if re.fullmatch(r"@[A-Za-z0-9_./~-]+", payload) is None:
            raise FixtureError(
                f"{plan_path}: invalid active import warning detail"
            )
    elif token in {
        "agents-md-budget-exceeded",
        "agents-md-near-budget",
    }:
        if BUDGET_WARNING_PATTERN.fullmatch(line) is None:
            raise FixtureError(
                f"{plan_path}: invalid byte-budget warning detail"
            )
    elif token in WARNING_REASON_SETS:
        if payload not in WARNING_REASON_SETS[token]:
            raise FixtureError(
                f"{plan_path}: invalid {token} warning reason"
            )
    elif token in {"legacy-managed-mode", "marker-anomaly"}:
        line_match = re.fullmatch(r"line ([1-9][0-9]*)", payload)
        if line_match is None:
            raise FixtureError(
                f"{plan_path}: invalid {token} source line detail"
            )
    elif token in {
        "hook-opt-in-required",
        "hook-output-not-delivered",
        "matcher-grammar-divergent",
        "platform-branch-divergence",
    }:
        if HOOK_ENTRY_DETAIL_PATTERN.fullmatch(payload) is None:
            raise FixtureError(
                f"{plan_path}: invalid {token} hook entry detail"
            )
    elif token == "intent-doc-anomaly":
        if (
            HOOK_ENTRY_DETAIL_PATTERN.fullmatch(payload) is None
            and re.fullmatch(r"line [1-9][0-9]*", payload) is None
        ):
            raise FixtureError(
                f"{plan_path}: invalid intent-doc-anomaly detail"
            )
    elif token in {
        "codex-hook-retrust-required",
        "codex-trust-blind-change",
    }:
        if HOOK_HANDLER_DETAIL_PATTERN.fullmatch(payload) is None:
            raise FixtureError(
                f"{plan_path}: invalid {token} handler position detail"
            )
    elif token == "codex-handler-unknown-key":
        if HOOK_UNKNOWN_KEY_DETAIL_PATTERN.fullmatch(payload) is None:
            raise FixtureError(
                f"{plan_path}: invalid codex-handler-unknown-key detail"
            )
    elif token == "codex-trust-reindex":
        if HOOK_REINDEX_DETAIL_PATTERN.fullmatch(payload) is None:
            raise FixtureError(
                f"{plan_path}: invalid codex-trust-reindex detail"
            )
    elif token == "codex-inline-hooks-conflict":
        if payload != "pointer-key" and (
            re.fullmatch(HOOK_EVENT, payload) is None
        ):
            raise FixtureError(
                f"{plan_path}: invalid codex-inline-hooks-conflict detail"
            )
    elif token == "undeclared-hooks-key":
        if HOOK_UNDECLARED_KEY_DETAIL_PATTERN.fullmatch(payload) is None:
            raise FixtureError(
                f"{plan_path}: invalid undeclared-hooks-key detail"
            )
    elif token == "hook-projection-asymmetric":
        if HOOK_UNIT_PATTERN.fullmatch(payload) is None:
            raise FixtureError(
                f"{plan_path}: invalid hook-projection-asymmetric detail"
            )
    else:
        raise FixtureError(
            f"{plan_path}: missing warning detail validator for {token}"
        )
    return token, relative, detail


def _scoped_blocker_closures(
    token: str,
    relative: str,
    detail: Optional[str],
    *,
    closures: Mapping[str, Tuple[str, ...]],
    write_capabilities: Sequence[Tuple[str, ...]],
) -> set[str]:
    """Closures a closure-scoped apply blocker forbids from applying.

    The global apply prohibition still holds for every other gate; the
    write-capability, hook-carrier and hook-opt-in gates are scoped to the
    closure carrying the matching row and to its dependents.
    """

    scope: set[str] = set()
    scope.update(HOOK_BLOCKER_SCOPE_CLOSURES.get(token, ()))
    carrier_closure = HOOK_CARRIER_CLOSURES.get(relative)
    if carrier_closure is not None and token in {
        "hooks-carrier-unusable",
        "conditional-write-unavailable",
        "guarded-patch-unavailable",
    }:
        scope.add(carrier_closure)
    scope.update(
        operation[1]
        for operation in write_capabilities
        if operation[2] == relative
    )
    if token == "hook-opt-in-required" and detail is not None:
        entry = detail[1:-1][len("entry ") :]
        scope.update(
            {
                f"closure/decision/hooks/{entry}",
                "closure/hooks/claude",
                "closure/hooks/codex",
            }
        )
    scope &= set(closures)
    dependents = set(scope)
    changed = True
    while changed:
        changed = False
        for closure_id, closure in closures.items():
            if closure_id in dependents or closure[2] == "-":
                continue
            if set(closure[2].split("; ")) & dependents:
                dependents.add(closure_id)
                changed = True
    return dependents


def _validate_scoped_apply_blockers(
    path: Path,
    *,
    warnings: Sequence[str],
    rows: Sequence[Tuple[str, ...]],
    closures: Mapping[str, Tuple[str, ...]],
    write_capabilities: Sequence[Tuple[str, ...]],
) -> None:
    for line in warnings:
        if line == "- (none)":
            continue
        token, relative, detail = _validate_warning_line(path, line)
        if token not in CLOSURE_SCOPED_BLOCKING_WARNINGS:
            continue
        blocked = _scoped_blocker_closures(
            token,
            relative,
            detail,
            closures=closures,
            write_capabilities=write_capabilities,
        )
        for row in rows:
            if row[1] in blocked and row[8] == "applied":
                raise FixtureError(
                    f"{path}: scoped blocker {token} cannot accompany "
                    f"applied row {row[0]}"
                )


def parse_plan(path: Path, *, expectation: bool) -> Plan:
    lines = normalized_markdown_lines(path)
    headers = _parse_headers(path, lines, expectation=expectation)
    expected_headings = [
        "## Units",
        "## Closures",
        "## Capability profiles",
        "## Write capabilities",
        "## Warnings",
        "## Hook tiers",
        "## Migration decisions",
        "## Migration candidates",
        "## Adoption decisions",
        "## Hook adoption decisions",
    ]
    if not expectation:
        expected_headings.append("## Evidence and notes")
    positions: List[int] = []
    for heading in expected_headings:
        try:
            positions.append(lines.index(heading))
        except ValueError as error:
            raise FixtureError(f"{path}: missing {heading}") from error
    if positions != sorted(positions):
        raise FixtureError(f"{path}: plan sections are out of order")
    headings = [line for line in lines if line.startswith("## ")]
    known = set(expected_headings)
    if [line for line in headings if line in known] != expected_headings:
        raise FixtureError(
            f"{path}: plan sections are not the exact normative sequence"
        )
    for anchor, follower in (
        ("## Warnings", "## Hook tiers"),
        ("## Adoption decisions", "## Hook adoption decisions"),
    ):
        index = headings.index(anchor)
        if headings[index + 1 : index + 2] != [follower]:
            raise FixtureError(
                f"{path}: {follower} must immediately follow {anchor}"
            )

    rows = parse_table(
        lines,
        heading="Units",
        expected_header=UNIT_HEADER,
        expected_separator=UNIT_SEPARATOR,
    )
    if not rows:
        raise FixtureError(f"{path}: Units table must not be empty")
    units: List[str] = []
    parsed_rows: List[Tuple[str, ...]] = []
    for row in rows:
        (
            unit,
            closure,
            selection,
            baseline,
            state,
            action,
            direction,
            authorization,
            outcome,
            tier,
            annotation_cell,
        ) = row
        if not _unit_valid(unit):
            raise FixtureError(f"{path}: invalid unit {unit!r}")
        if not _closure_id_valid(closure):
            raise FixtureError(f"{path}: invalid closure {closure!r}")
        if baseline != "-" and HASH_PATTERN.fullmatch(baseline) is None:
            raise FixtureError(f"{path}: invalid baseline {baseline!r}")
        registries = (
            (selection, PLAN_SELECTIONS, "selection"),
            (state, PLAN_STATES, "state"),
            (action, PLAN_ACTIONS, "action"),
            (direction, PLAN_DIRECTIONS, "direction"),
            (authorization, PLAN_AUTHORIZATIONS, "authorization"),
            (outcome, PLAN_OUTCOMES, "outcome"),
            (tier, PLAN_TIERS, "tier"),
        )
        for token, registry, label in registries:
            if token not in registry:
                raise FixtureError(f"{path}: invalid {label} {token!r}")
        _validate_unit_tier(path, unit, tier)
        annotations: List[str] = []
        if annotation_cell != "-":
            annotations = annotation_cell.split("; ")
            if annotations != sorted(set(annotations)):
                raise FixtureError(
                    f"{path}: annotations must be sorted and unique"
                )
            unknown = set(annotations) - PLAN_ANNOTATIONS
            if unknown:
                raise FixtureError(
                    f"{path}: invalid annotation {sorted(unknown)[0]!r}"
                )
        _validate_row_semantics(
            path,
            unit=unit,
            phase=headers["phase"],
            selection=selection,
            state=state,
            action=action,
            direction=direction,
            authorization=authorization,
            outcome=outcome,
            annotations=annotations,
        )
        units.append(unit)
        parsed_rows.append(tuple(row))
    if units != sorted(units) or len(units) != len(set(units)):
        raise FixtureError(
            f"{path}: Units rows must be byte-wise sorted and unique"
        )
    executed_outcomes = {
        "applied",
        "failed",
        "compensated",
        "partial",
        "not-attempted",
        "rolled-back",
    }
    if headers["phase"] == "post-write" and not any(
        row[8] in executed_outcomes for row in parsed_rows
    ):
        raise FixtureError(
            f"{path}: post-write requires an operation that entered execution"
        )

    closure_rows = parse_table(
        lines,
        heading="Closures",
        expected_header=CLOSURE_HEADER,
        expected_separator=CLOSURE_SEPARATOR,
    )
    if not closure_rows:
        raise FixtureError(f"{path}: Closures table must not be empty")
    closure_ids: List[str] = []
    closure_map: Dict[str, Tuple[str, ...]] = {}
    for closure_row in closure_rows:
        (
            closure,
            member_cell,
            dependency_cell,
            selection,
            authorization,
            outcome,
        ) = closure_row
        if not _closure_id_valid(closure):
            raise FixtureError(f"{path}: invalid closure id {closure!r}")
        members = member_cell.split("; ")
        if (
            not members
            or members != sorted(set(members))
            or any(not _unit_valid(member) for member in members)
        ):
            raise FixtureError(
                f"{path}: closure members must be sorted unique units"
            )
        dependencies: List[str] = []
        if dependency_cell != "-":
            dependencies = dependency_cell.split("; ")
            if dependencies != sorted(set(dependencies)) or any(
                not _closure_id_valid(dependency)
                for dependency in dependencies
            ):
                raise FixtureError(
                    f"{path}: closure dependencies must be sorted unique ids"
                )
        for token, registry, label in (
            (selection, PLAN_SELECTIONS, "closure selection"),
            (authorization, PLAN_AUTHORIZATIONS, "closure authorization"),
            (outcome, PLAN_OUTCOMES, "closure outcome"),
        ):
            if token not in registry:
                raise FixtureError(f"{path}: invalid {label} {token!r}")
        if selection == "not-selected" and (
            authorization != "not-applicable" or outcome != "not-selected"
        ):
            raise FixtureError(
                f"{path}: not-selected closure has invalid authorization/outcome"
            )
        if selection == "selected" and outcome == "not-selected":
            raise FixtureError(
                f"{path}: selected closure cannot use not-selected outcome"
            )
        closure_ids.append(closure)
        closure_map[closure] = closure_row
    if closure_ids != sorted(closure_ids) or len(closure_ids) != len(
        set(closure_ids)
    ):
        raise FixtureError(
            f"{path}: Closures rows must be byte-wise sorted and unique"
        )
    unit_members: Dict[str, List[str]] = {}
    for row in parsed_rows:
        unit_members.setdefault(row[1], []).append(row[0])
        closure = closure_map.get(row[1])
        if closure is None:
            raise FixtureError(
                f"{path}: unit {row[0]} references missing closure {row[1]}"
            )
        if (row[2], row[7], row[8]) != (
            closure[3],
            closure[4],
            closure[5],
        ):
            raise FixtureError(
                f"{path}: unit {row[0]} disagrees with closure "
                "selection/authorization/outcome"
            )
    dependency_unsatisfied = False
    for closure_id, closure in closure_map.items():
        actual_members = sorted(unit_members.get(closure_id, []))
        declared_members = closure[1].split("; ")
        if actual_members != declared_members:
            raise FixtureError(
                f"{path}: closure {closure_id} members disagree with Units"
            )
        dependencies = [] if closure[2] == "-" else closure[2].split("; ")
        for dependency in dependencies:
            target = closure_map.get(dependency)
            if target is None:
                raise FixtureError(
                    f"{path}: closure {closure_id} depends on missing {dependency}"
                )
            if closure[3] == "selected" and (
                target[3] != "selected" or target[4] != "confirmed"
            ):
                dependency_unsatisfied = True

    capability_profiles = _parse_capability_profiles(path, lines)
    profile_bindings = {row[0] for row in capability_profiles}
    write_capabilities = _parse_write_capabilities(path, lines)
    _validate_capability_binding_order(
        path,
        capability_profiles,
        write_capabilities,
    )
    cited_bindings: set[str] = set()
    for (
        step,
        closure_id,
        _,
        _,
        protocol,
        binding,
        inverse,
        inverse_binding,
    ) in write_capabilities:
        closure = closure_map.get(closure_id)
        if closure is None or closure[3] != "selected":
            raise FixtureError(
                f"{path}: write capability step {step} must name a "
                "selected declared closure"
            )
        if protocol != "unavailable":
            if binding not in profile_bindings:
                raise FixtureError(
                    f"{path}: step {step} has unknown forward binding"
                )
            cited_bindings.add(binding)
        if inverse != "unavailable":
            if inverse_binding not in profile_bindings:
                raise FixtureError(
                    f"{path}: step {step} has unknown inverse binding"
                )
            cited_bindings.add(inverse_binding)
    if cited_bindings != profile_bindings:
        raise FixtureError(
            f"{path}: capability profiles must be cited exactly by operations"
        )
    if bool(capability_profiles) != bool(cited_bindings):
        raise FixtureError(
            f"{path}: Capability profiles presence disagrees with bindings"
        )
    for row in parsed_rows:
        unit = row[0]
        closure = row[1]
        outcome = row[8]
        annotations = (
            set() if row[10] == "-" else set(row[10].split("; "))
        )
        _validate_carrier_annotation_timing(
            path,
            unit=unit,
            closure=closure,
            outcome=outcome,
            phase=headers["phase"],
            annotations=annotations,
            write_capabilities=write_capabilities,
        )

    warnings = parse_list_section(lines, heading="Warnings")
    if warnings != ["- (none)"]:
        if warnings != sorted(set(warnings)):
            raise FixtureError(
                f"{path}: warnings must be sorted and unique complete lines"
            )
        for line in warnings:
            _validate_warning_line(path, line)
    hook_tiers = _parse_hook_tiers(path, lines)
    hook_units = {
        row[0]: row[9]
        for row in parsed_rows
        if _hook_unit_host(row[0]) is not None
    }
    if [row[0] for row in hook_tiers] != sorted(hook_units):
        raise FixtureError(
            f"{path}: Hook tiers rows must equal the plan hook unit set"
        )
    for row in hook_tiers:
        if hook_units[row[0]] != row[3]:
            raise FixtureError(
                f"{path}: Hook tiers tier for {row[0]} disagrees with Units"
            )
    migration = _parse_migration(path, lines)
    migration_candidates = _parse_migration_candidates(path, lines)
    if bool(migration) != bool(migration_candidates):
        raise FixtureError(
            f"{path}: migration decisions and candidates must both be "
            "present or both be none"
        )
    candidates_by_unit: Dict[str, List[str]] = {}
    for unit, candidate in migration_candidates:
        candidates_by_unit.setdefault(unit, []).append(candidate)
    if migration:
        migration_units = [row[0] for row in migration]
        if set(migration_units) != set(candidates_by_unit):
            raise FixtureError(
                f"{path}: migration decision/candidate unit sets differ"
            )
        for unit, baseline, relation, _, _ in migration:
            candidates = candidates_by_unit[unit]
            if relation == "ambiguous":
                if baseline != "-" or len(candidates) < 2:
                    raise FixtureError(
                        f"{path}: ambiguous migration needs 2+ candidates"
                    )
            elif candidates != [baseline]:
                raise FixtureError(
                    f"{path}: unique migration candidate must equal baseline"
                )
    adoption = _parse_adoption(path, lines)
    hook_adoption = _parse_hook_adoption(path, lines)
    pending = any(row[4] == "pending" for row in adoption)
    onboarding_agents_rows = [
        row for row in parsed_rows if row[0] == "onboarding/agents-md"
    ]
    if pending:
        if len(onboarding_agents_rows) != 1:
            raise FixtureError(
                f"{path}: pending adoption needs exactly one "
                "onboarding/agents-md row"
            )
        onboarding_row = onboarding_agents_rows[0]
        if (
            onboarding_row[1]
            != "closure/decision/onboarding/agents-md"
            or onboarding_row[2] != "not-selected"
            or onboarding_row[3] != "-"
            or onboarding_row[4] != "no-baseline"
            or onboarding_row[5] != "annex-or-keep"
            or onboarding_row[6] != "user-decision"
            or onboarding_row[7] != "not-applicable"
            or onboarding_row[8] != "not-selected"
            or onboarding_row[9] != "-"
            or onboarding_row[10] != "decision-required"
        ):
            raise FixtureError(
                f"{path}: pending onboarding/agents-md must be the exact "
                "decision-only shape without intent-required"
            )
    elif onboarding_agents_rows:
        raise FixtureError(
            f"{path}: onboarding/agents-md requires explicit pending "
            "AGENTS.md segmentation decisions"
        )
    _validate_hook_decisions(path, parsed_rows, hook_tiers)

    rename_rows = [row for row in parsed_rows if row[5] == "rename"]
    if rename_rows:
        rename_closures = {row[1] for row in rename_rows}
        if any(
            (
                row[3] == "-"
                and row[4] != "no-baseline"
            )
            or (
                row[3] != "-"
                and row[4] != "source-only"
            )
            for row in rename_rows
        ):
            raise FixtureError(
                f"{path}: rename destination needs '-' / no-baseline and "
                "rename source needs a baseline / source-only"
            )
        for closure_id in rename_closures:
            members = [
                row for row in rename_rows if row[1] == closure_id
            ]
            if (
                not any(row[3] == "-" for row in members)
                or not any(row[3] != "-" for row in members)
            ):
                raise FixtureError(
                    f"{path}: rename closure must contain old and new units"
                )

    warning_tokens = {
        line[2:].split(": ", 1)[0]
        for line in warnings
        if line != "- (none)"
    }
    if dependency_unsatisfied != (
        "closure-dependency-unsatisfied" in warning_tokens
    ):
        raise FixtureError(
            f"{path}: closure-dependency-unsatisfied warning does not "
            "match selected-and-confirmed dependencies"
        )
    selected_mutating: List[Tuple[str, ...]] = [
        row
        for row in parsed_rows
        if row[2] == "selected" and row[5] in MUTATING_ACTIONS
    ]
    mutating_closures = {row[1] for row in selected_mutating}
    capability_closures = {row[1] for row in write_capabilities}
    if bool(mutating_closures) != bool(write_capabilities):
        raise FixtureError(
            f"{path}: selected physical mutation and Write capabilities "
            "presence disagree"
        )
    if not capability_closures.issubset(mutating_closures):
        raise FixtureError(
            f"{path}: Write capabilities name a non-mutating closure"
        )
    if any(row[7] == "required" for row in selected_mutating):
        derived_authorization = "required"
    elif selected_mutating:
        derived_authorization = "confirmed"
    else:
        derived_authorization = "not-applicable"
    if headers["authorization"] != derived_authorization:
        raise FixtureError(
            f"{path}: header authorization {headers['authorization']!r} "
            f"does not equal derived {derived_authorization!r}"
        )
    if (
        any(row[7] == "required" for row in selected_mutating)
        != ("authorization-incomplete" in warning_tokens)
    ):
        raise FixtureError(
            f"{path}: authorization-incomplete warning does not match closures"
        )
    guarded_rows = [
        row for row in write_capabilities if row[4] == "guarded-patch/v1"
    ]
    if bool(guarded_rows) != ("guarded-patch-non-cas" in warning_tokens):
        raise FixtureError(
            f"{path}: guarded-patch-non-cas warning does not match "
            "Write capabilities"
        )
    guarded_agents = any(
        row[2] == "AGENTS.md" and row[4] == "guarded-patch/v1"
        for row in write_capabilities
    )
    if guarded_agents != ("manual-zone-guarded" in warning_tokens):
        raise FixtureError(
            f"{path}: manual-zone-guarded warning does not match guarded "
            "AGENTS.md replacement"
        )
    strict_agents = any(
        row[2] == "AGENTS.md" and row[4] == "strict-replace/v1"
        for row in write_capabilities
    )
    if strict_agents != ("manual-zone-preserved" in warning_tokens):
        raise FixtureError(
            f"{path}: manual-zone-preserved warning does not match strict "
            "AGENTS.md replacement"
        )
    unavailable_inverse = any(
        row[6] == "unavailable" and row[4] != "unavailable"
        for row in write_capabilities
    )
    if unavailable_inverse != (
        "strict-compensation-unavailable" in warning_tokens
    ):
        raise FixtureError(
            f"{path}: strict-compensation-unavailable warning does not "
            "match inverse protocols"
        )
    unavailable_forward = any(
        row[4] == "unavailable" for row in write_capabilities
    )
    unavailable_warning = bool(
        warning_tokens
        & {"conditional-write-unavailable", "guarded-patch-unavailable"}
    )
    if unavailable_forward != unavailable_warning:
        raise FixtureError(
            f"{path}: unavailable write protocol does not match a "
            "capability warning"
        )
    has_migration = any(row[4] == "contract-migration" for row in parsed_rows)
    if has_migration != bool(migration):
        raise FixtureError(
            f"{path}: migration state and Migration decisions table disagree"
        )
    if migration:
        migration_by_unit = {row[0]: row for row in migration}
        unit_by_id = {row[0]: row for row in parsed_rows}
        covenant_row = unit_by_id.get("onboarding/covenant")
        wanted_members = {"onboarding/covenant", *migration_by_unit}
        actual_members = {
            row[0]
            for row in parsed_rows
            if row[1] == "closure/migration"
        }
        if (
            covenant_row is None
            or covenant_row[1] != "closure/migration"
            or actual_members != wanted_members
            or any(
                unit_by_id.get(unit, (None, None))[1]
                != "closure/migration"
                for unit in migration_by_unit
            )
        ):
            raise FixtureError(
                f"{path}: migration decisions require one complete "
                "closure/migration unit set"
            )
        ambiguous = any(
            row[2] == "ambiguous" for row in migration
        )
        if ambiguous:
            if headers["phase"] != "pre-write":
                raise FixtureError(
                    f"{path}: ambiguous migration must remain pre-write"
                )
            for unit in sorted(wanted_members):
                row = unit_by_id[unit]
                annotations = (
                    set()
                    if row[10] == "-"
                    else set(row[10].split("; "))
                )
                expected_annotations = (
                    {"migration-transition-required"}
                    if unit == "onboarding/covenant"
                    or migration_by_unit[unit][3]
                    in {"carry-forward", "repair-and-carry"}
                    else {"decision-required"}
                )
                if (
                    row[2] != "selected"
                    or row[3] != "-"
                    or row[4] != "contract-migration"
                    or row[5] != "resolve-blocker"
                    or row[6] != "user-decision"
                    or row[7] != "not-applicable"
                    or row[8] != "blocked"
                    or annotations != expected_annotations
                ):
                    raise FixtureError(
                        f"{path}: ambiguous migration unit {unit} has a "
                        "non-canonical selection/action/baseline/outcome/"
                        "annotation shape"
                    )
        elif headers["phase"] == "post-write":
            if (
                covenant_row[3] != "-"
                or "migration-transition-required"
                not in covenant_row[10].split("; ")
            ):
                raise FixtureError(
                    f"{path}: post-migration covenant has invalid "
                    "baseline/transition annotation"
                )
            for unit, baseline, _, disposition, _ in migration:
                row = unit_by_id[unit]
                annotations = (
                    set()
                    if row[10] == "-"
                    else set(row[10].split("; "))
                )
                if disposition == "release":
                    if row[3] != "-" or annotations:
                        raise FixtureError(
                            f"{path}: released migration unit must have no "
                            "current baseline or transition annotations"
                        )
                elif (
                    row[3] != baseline
                    or "migration-transition-required" not in annotations
                ):
                    raise FixtureError(
                        f"{path}: carried migration unit must retain the "
                        "legacy baseline and transition annotation"
                    )
    if (
        warning_tokens & PROJECT_WIDE_BLOCKING_WARNINGS
        and headers["phase"] == "post-write"
    ):
        for row in parsed_rows:
            if row[8] == "applied" and row[0] in {
                "entry",
                "onboarding/agents-md",
            } | {unit for unit in units if unit.startswith("rules/")}:
                raise FixtureError(
                    f"{path}: blocking AGENTS warning cannot accompany "
                    f"applied row {row[0]}"
                )
    if headers["phase"] == "post-write":
        _validate_scoped_apply_blockers(
            path,
            warnings=warnings,
            rows=parsed_rows,
            closures=closure_map,
            write_capabilities=write_capabilities,
        )
    return {
        "path": str(path),
        "headers": headers,
        "rows": parsed_rows,
        "closures": closure_rows,
        "capability_profiles": capability_profiles,
        "write_capabilities": write_capabilities,
        "warnings": warnings,
        "hook_tiers": hook_tiers,
        "migration": migration,
        "migration_candidates": migration_candidates,
        "adoption": adoption,
        "hook_adoption": hook_adoption,
    }


def _baseline_ref_for(
    scenario: Mapping[str, Any],
    expectation: Mapping[str, Any],
    unit: str,
) -> str:
    reference = expectation.get("baseline_ref")
    if isinstance(reference, str):
        return reference
    if isinstance(reference, dict):
        value = reference.get(unit)
        if isinstance(value, str):
            return value
    raise FixtureError(
        f"{scenario['id']}/{expectation['id']}: missing baseline_ref for {unit}"
    )


def bind_expected_baselines(
    scenario: Mapping[str, Any],
    expectation: Mapping[str, Any],
    plan: Plan,
    *,
    initial_commit: str,
    history_commits: Optional[Mapping[str, str]] = None,
) -> Plan:
    def resolve_reference(reference: str) -> str:
        if reference == "initial":
            return initial_commit
        if reference.startswith("history:") and history_commits is not None:
            commit = history_commits.get(reference[len("history:") :])
            if isinstance(commit, str):
                return commit
        raise FixtureError(
            f"{scenario['id']}/{expectation['id']}: unsupported commit "
            f"reference {reference!r}"
        )

    commit_refs = expectation.get("commit_refs", {})
    replacements = {
        token: resolve_reference(reference)
        for token, reference in commit_refs.items()
    }
    bound = copy.deepcopy(plan)
    rows: List[Tuple[str, ...]] = []
    for row in bound["rows"]:
        cells = list(row)
        if cells[3] == ZERO_BASELINE:
            reference = _baseline_ref_for(scenario, expectation, cells[0])
            cells[3] = resolve_reference(reference)
        elif cells[3] in replacements:
            cells[3] = replacements[cells[3]]
        rows.append(tuple(cells))
    bound["rows"] = rows
    migration_rows: List[Tuple[str, ...]] = []
    for row in bound["migration"]:
        cells = list(row)
        if cells[1] == ZERO_BASELINE:
            reference = _baseline_ref_for(scenario, expectation, cells[0])
            cells[1] = resolve_reference(reference)
        elif cells[1] in replacements:
            cells[1] = replacements[cells[1]]
        migration_rows.append(tuple(cells))
    bound["migration"] = migration_rows
    candidate_rows: List[Tuple[str, ...]] = []
    for row in bound["migration_candidates"]:
        cells = list(row)
        if cells[1] == ZERO_BASELINE:
            reference = _baseline_ref_for(
                scenario, expectation, cells[0]
            )
            cells[1] = resolve_reference(reference)
        elif cells[1] in replacements:
            cells[1] = replacements[cells[1]]
        candidate_rows.append(tuple(cells))
    bound["migration_candidates"] = sorted(candidate_rows)
    return bound


def compare_plans(expected: Plan, actual: Plan) -> List[str]:
    differences: List[str] = []
    expected_headers = expected["headers"]
    actual_headers = actual["headers"]
    for key in (
        "contracts",
        "phase",
        "onboarding",
        "authorization",
    ):
        if expected_headers[key] != actual_headers[key]:
            differences.append(
                f"header {key}: actual={actual_headers[key]!r}, "
                f"expected={expected_headers[key]!r}"
            )
    if expected["rows"] != actual["rows"]:
        differences.append(
            f"units: actual={actual['rows']!r}, expected={expected['rows']!r}"
        )
    if expected["closures"] != actual["closures"]:
        differences.append(
            "closures: "
            f"actual={actual['closures']!r}, expected={expected['closures']!r}"
        )
    if expected["capability_profiles"] != actual["capability_profiles"]:
        differences.append(
            "capability profiles: "
            f"actual={actual['capability_profiles']!r}, "
            f"expected={expected['capability_profiles']!r}"
        )
    if expected["write_capabilities"] != actual["write_capabilities"]:
        differences.append(
            "write capabilities: "
            f"actual={actual['write_capabilities']!r}, "
            f"expected={expected['write_capabilities']!r}"
        )
    if expected["warnings"] != actual["warnings"]:
        differences.append(
            "warnings: "
            f"actual={actual['warnings']!r}, expected={expected['warnings']!r}"
        )
    if expected["hook_tiers"] != actual["hook_tiers"]:
        differences.append(
            "hook tiers: "
            f"actual={actual['hook_tiers']!r}, "
            f"expected={expected['hook_tiers']!r}"
        )
    if expected["migration"] != actual["migration"]:
        differences.append(
            "migration: "
            f"actual={actual['migration']!r}, "
            f"expected={expected['migration']!r}"
        )
    if expected["migration_candidates"] != actual["migration_candidates"]:
        differences.append(
            "migration candidates: "
            f"actual={actual['migration_candidates']!r}, "
            f"expected={expected['migration_candidates']!r}"
        )
    if expected["adoption"] != actual["adoption"]:
        differences.append(
            "adoption: "
            f"actual={actual['adoption']!r}, expected={expected['adoption']!r}"
        )
    if expected["hook_adoption"] != actual["hook_adoption"]:
        differences.append(
            "hook adoption: "
            f"actual={actual['hook_adoption']!r}, "
            f"expected={expected['hook_adoption']!r}"
        )
    return differences


def _load_matrix() -> Dict[str, Any]:
    matrix = read_json(MATRIX_PATH)
    if matrix.get("spec") != MATRIX_SPEC:
        raise FixtureError(f"{MATRIX_PATH}: expected spec {MATRIX_SPEC}")
    if set(matrix) != {
        "default_activation_profile",
        "default_write_capability_fixture",
        "spec",
        "required_coverage",
        "required_safeguards",
        "scenarios",
    }:
        raise FixtureError(f"{MATRIX_PATH}: matrix fields are not closed")
    coverage = matrix["required_coverage"]
    safeguards = matrix["required_safeguards"]
    scenarios = matrix["scenarios"]
    for field, values in (
        ("required_coverage", coverage),
        ("required_safeguards", safeguards),
    ):
        if (
            not isinstance(values, list)
            or not values
            or values != sorted(set(values))
            or not all(
                isinstance(item, str) and TOKEN_PATTERN.fullmatch(item)
                for item in values
            )
        ):
            raise FixtureError(
                f"{MATRIX_PATH}: {field} must be sorted unique tokens"
            )
    if not isinstance(scenarios, list) or not scenarios:
        raise FixtureError(f"{MATRIX_PATH}: scenarios must be non-empty")
    _load_activation_profile(matrix["default_activation_profile"])
    _load_write_capability_fixture(
        matrix["default_write_capability_fixture"]
    )
    return matrix


def _validate_budget_warnings(
    *,
    scenario_id: str,
    expectation_id: str,
    plan: Plan,
    planned_tree: Optional[Mapping[str, Any]],
) -> None:
    budget_lines = [
        line
        for line in plan["warnings"]
        if line.startswith("- agents-md-near-budget: ")
        or line.startswith("- agents-md-budget-exceeded: ")
    ]
    label = f"{scenario_id}/{expectation_id}"
    if not budget_lines:
        if planned_tree is not None:
            raise FixtureError(
                f"{label}: planned_state is unused without a byte-budget warning"
            )
        return
    if len(budget_lines) != 1:
        raise FixtureError(f"{label}: expected exactly one byte-budget warning")
    if planned_tree is None:
        raise FixtureError(
            f"{label}: byte-budget warning requires planned_state"
        )
    entry = planned_tree.get("AGENTS.md")
    if not isinstance(entry, dict) or entry.get("type") != "file":
        raise FixtureError(
            f"{label}: planned_state must contain regular AGENTS.md bytes"
        )
    planned_bytes = entry.get("bytes")
    if not isinstance(planned_bytes, bytes):
        raise FixtureError(f"{label}: planned AGENTS.md bytes are invalid")
    match = BUDGET_WARNING_PATTERN.fullmatch(budget_lines[0])
    if match is None:
        raise FixtureError(f"{label}: malformed byte-budget warning")
    token, serialized_size, serialized_budget = match.groups()
    size = len(planned_bytes)
    budget = int(serialized_budget)
    if int(serialized_size) != size:
        raise FixtureError(
            f"{label}: budget warning says {serialized_size} planned bytes; "
            f"planned_state has {size}"
        )
    if budget <= 0:
        raise FixtureError(
            f"{label}: near/exceeded warning requires a positive budget"
        )
    if token == "agents-md-near-budget":
        threshold = (7 * budget) // 8
        if not threshold <= size <= budget:
            raise FixtureError(
                f"{label}: near-budget warning does not match "
                f"{size} bytes of {budget}"
            )
    elif size <= budget:
        raise FixtureError(
            f"{label}: budget-exceeded warning does not match "
            f"{size} bytes of {budget}"
        )


def _validate_expectation(
    scenario: Mapping[str, Any],
    expectation: Mapping[str, Any],
) -> Tuple[Plan, Mapping[str, Any], Optional[Mapping[str, Any]]]:
    allowed = {
        "id",
        "covers",
        "plan",
        "planned_state",
        "post_state",
        "baseline_ref",
        "commit_refs",
        "replay_input",
    }
    if not isinstance(expectation, dict) or set(expectation) - allowed:
        raise FixtureError(
            f"{scenario['id']}: expectation has unknown fields"
        )
    expectation_id = expectation.get("id")
    if (
        not isinstance(expectation_id, str)
        or TOKEN_PATTERN.fullmatch(expectation_id) is None
    ):
        raise FixtureError(f"{scenario['id']}: invalid expectation id")
    covers = expectation.get("covers")
    if (
        not isinstance(covers, list)
        or not covers
        or covers != sorted(set(covers))
        or not all(
            isinstance(item, str) and TOKEN_PATTERN.fullmatch(item)
            for item in covers
        )
    ):
        raise FixtureError(
            f"{scenario['id']}/{expectation_id}: covers must be sorted tokens"
        )
    plan = parse_plan(
        _safe_expectation_path(expectation.get("plan")),
        expectation=True,
    )
    post_state = expectation.get("post_state")
    if not isinstance(post_state, str) or not post_state:
        raise FixtureError(
            f"{scenario['id']}/{expectation_id}: invalid post_state"
        )
    tree = resolve_named_tree(
        HERE,
        TREE_MANIFEST,
        post_state,
        shared_dir=SHARED_DIR,
    )
    planned_state = expectation.get("planned_state")
    planned_tree: Optional[Mapping[str, Any]] = None
    if planned_state is not None:
        if not isinstance(planned_state, str) or not planned_state:
            raise FixtureError(
                f"{scenario['id']}/{expectation_id}: invalid planned_state"
            )
        planned_tree = resolve_named_tree(
            HERE,
            TREE_MANIFEST,
            planned_state,
            shared_dir=SHARED_DIR,
        )
    _validate_budget_warnings(
        scenario_id=scenario["id"],
        expectation_id=expectation_id,
        plan=plan,
        planned_tree=planned_tree,
    )
    commit_refs = expectation.get("commit_refs", {})
    if (
        not isinstance(commit_refs, dict)
        or any(
            not isinstance(token, str)
            or HASH_PATTERN.fullmatch(token) is None
            or token == ZERO_BASELINE
            or not isinstance(reference, str)
            or (
                reference != "initial"
                and not reference.startswith("history:")
            )
            for token, reference in commit_refs.items()
        )
    ):
        raise FixtureError(
            f"{scenario['id']}/{expectation_id}: invalid commit_refs"
        )
    serialized_hashes = {
        cell
        for row in (
            list(plan["rows"])
            + list(plan["migration"])
            + list(plan["migration_candidates"])
        )
        for cell in row
        if HASH_PATTERN.fullmatch(cell) is not None
    }
    if set(commit_refs) - serialized_hashes:
        raise FixtureError(
            f"{scenario['id']}/{expectation_id}: unused commit_refs"
        )
    has_placeholder = any(
        row[3] == ZERO_BASELINE for row in plan["rows"]
    ) or any(
        row[1] == ZERO_BASELINE for row in plan["migration"]
    ) or any(
        row[1] == ZERO_BASELINE
        for row in plan["migration_candidates"]
    )
    if has_placeholder and "baseline_ref" not in expectation:
        raise FixtureError(
            f"{scenario['id']}/{expectation_id}: zero baseline needs baseline_ref"
        )
    if not has_placeholder and "baseline_ref" in expectation:
        raise FixtureError(
            f"{scenario['id']}/{expectation_id}: unused baseline_ref"
        )
    return plan, tree, planned_tree


def _validate_scenario(
    scenario: Mapping[str, Any],
    *,
    default_activation_profile: str,
    default_write_capability_fixture: str,
) -> Dict[str, Any]:
    allowed = {
        "activation_profile",
        "write_capability_fixture",
        "decision_fixture",
        "rendered_state",
        "fault_schedule_fixture",
        "replay_inputs",
        "spec",
        "id",
        "summary",
        "replay",
        "replay_reason",
        "safeguards",
        "coverage",
        "baseline",
        "input",
        "expectations",
        "fault",
        "history",
        "workflow",
    }
    if not isinstance(scenario, dict) or set(scenario) - allowed:
        raise FixtureError("scenario contains unknown fields")
    if scenario.get("spec") != SCENARIO_SPEC:
        raise FixtureError(f"scenario expected spec {SCENARIO_SPEC}")
    scenario_id = scenario.get("id")
    if (
        not isinstance(scenario_id, str)
        or TOKEN_PATTERN.fullmatch(scenario_id) is None
    ):
        raise FixtureError("scenario id must be a lowercase token")
    if not isinstance(scenario.get("summary"), str) or not scenario["summary"]:
        raise FixtureError(f"{scenario_id}: summary must be non-empty")
    replay = scenario.get("replay")
    if replay not in REPLAY_MODES:
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
        _validate_fault(scenario_id, fault)
    elif reason is not None or fault is not None:
        raise FixtureError(
            f"{scenario_id}: agent replay may not declare a synthetic boundary"
        )
    for field in ("coverage", "safeguards"):
        values = scenario.get(field)
        if (
            not isinstance(values, list)
            or not values
            or values != sorted(set(values))
            or not all(
                isinstance(item, str) and TOKEN_PATTERN.fullmatch(item)
                for item in values
            )
        ):
            raise FixtureError(
                f"{scenario_id}: {field} must be sorted unique tokens"
            )
    baseline_name = scenario.get("baseline")
    input_name = scenario.get("input")
    if not isinstance(baseline_name, str) or not isinstance(input_name, str):
        raise FixtureError(f"{scenario_id}: baseline/input must name trees")
    baseline = resolve_named_tree(
        HERE,
        TREE_MANIFEST,
        baseline_name,
        shared_dir=SHARED_DIR,
    )
    input_tree = resolve_named_tree(
        HERE,
        TREE_MANIFEST,
        input_name,
        shared_dir=SHARED_DIR,
    )
    history = _validate_history(scenario_id, scenario.get("history"))
    profile_value = scenario.get(
        "activation_profile", default_activation_profile
    )
    activation_profile = _load_activation_profile(profile_value)
    capability_value = scenario.get(
        "write_capability_fixture",
        default_write_capability_fixture,
    )
    write_capability = _load_write_capability_fixture(capability_value)
    replay_declarations = scenario.get("replay_inputs")
    if replay_declarations is None:
        replay_declarations = [
            {
                key: value
                for key, value in {
                    "id": scenario_id,
                    "decision_fixture": scenario.get("decision_fixture"),
                    "rendered_state": scenario.get("rendered_state"),
                    "fault_schedule_fixture": scenario.get(
                        "fault_schedule_fixture"
                    ),
                }.items()
                if value is not None
            }
        ]
    elif any(
        field in scenario
        for field in (
            "decision_fixture",
            "rendered_state",
            "fault_schedule_fixture",
        )
    ):
        raise FixtureError(
            f"{scenario_id}: scenario-level replay facts conflict with replay_inputs"
        )
    if not isinstance(replay_declarations, list) or not replay_declarations:
        raise FixtureError(f"{scenario_id}: replay_inputs must be non-empty")
    replay_inputs: Dict[str, Dict[str, Any]] = {}
    replay_ids: List[str] = []
    for declaration in replay_declarations:
        if (
            not isinstance(declaration, dict)
            or set(declaration)
            - {
                "id",
                "decision_fixture",
                "rendered_state",
                "fault_schedule_fixture",
            }
        ):
            raise FixtureError(
                f"{scenario_id}: replay input fields are not closed"
            )
        replay_id = declaration.get("id")
        if (
            not isinstance(replay_id, str)
            or TOKEN_PATTERN.fullmatch(replay_id) is None
        ):
            raise FixtureError(f"{scenario_id}: invalid replay input id")
        decision_value = declaration.get("decision_fixture")
        decision = (
            None
            if decision_value is None
            else _load_decision_fixture(
                decision_value,
                input_tree=input_tree,
            )
        )
        rendered_name = declaration.get("rendered_state")
        if rendered_name is not None and (
            not isinstance(rendered_name, str) or not rendered_name
        ):
            raise FixtureError(
                f"{scenario_id}/{replay_id}: invalid rendered_state"
            )
        rendered_tree = (
            None
            if rendered_name is None
            else resolve_named_tree(
                HERE,
                TREE_MANIFEST,
                rendered_name,
                shared_dir=SHARED_DIR,
            )
        )
        fault_schedule_value = declaration.get(
            "fault_schedule_fixture"
        )
        fault_schedule = (
            None
            if fault_schedule_value is None
            else _load_fault_schedule_fixture(
                fault_schedule_value,
                input_tree=input_tree,
            )
        )
        if fault_schedule is not None and replay != "agent":
            raise FixtureError(
                f"{scenario_id}/{replay_id}: only agent replay may bind "
                "an executable fault schedule"
            )
        replay_ids.append(replay_id)
        replay_inputs[replay_id] = {
            "id": replay_id,
            "decision": decision,
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
    parsed_expectations: List[Dict[str, Any]] = []
    ids: List[str] = []
    assigned: set[str] = set()
    for expectation in expectations:
        plan, tree, planned_tree = _validate_expectation(
            scenario, expectation
        )
        ids.append(expectation["id"])
        assigned.update(expectation["covers"])
        replay_id = expectation.get("replay_input", scenario_id)
        replay_input = replay_inputs.get(replay_id)
        if replay_input is None:
            raise FixtureError(
                f"{scenario_id}/{expectation['id']}: unknown replay_input "
                f"{replay_id!r}"
            )
        declared_untracked = sorted(
            warning_path
            for warning in plan["warnings"]
            if warning != "- (none)"
            for warning_token, warning_path, _ in [
                _validate_warning_line(Path(plan["path"]), warning)
            ]
            if warning_token == "untracked-files-included"
        )
        relevant_untracked = sorted(set(tree) - set(baseline))
        if declared_untracked != relevant_untracked:
            raise FixtureError(
                f"{scenario_id}/{expectation['id']}: untracked warnings "
                f"{declared_untracked!r} do not equal scan context "
                f"{relevant_untracked!r}"
            )
        capability_rows = plan["write_capabilities"]
        profile_rows = plan["capability_profiles"]
        if capability_rows:
            if capability_rows != write_capability["operation_rows"]:
                raise FixtureError(
                    f"{scenario_id}/{expectation['id']}: expected write "
                    "capabilities are not derived from replay input"
                )
            if profile_rows != write_capability["profile_rows"]:
                raise FixtureError(
                    f"{scenario_id}/{expectation['id']}: expected capability "
                    "profiles are not derived from replay input"
                )
        elif profile_rows:
            raise FixtureError(
                f"{scenario_id}/{expectation['id']}: capability profiles "
                "cannot appear without write rows"
            )
        decision = replay_input["decision"]
        confirmed_closures = {
            row[1]
            for row in plan["rows"]
            if row[2] == "selected"
            and row[5] in MUTATING_ACTIONS
            and row[7] == "confirmed"
        }
        if confirmed_closures:
            if (
                decision is None
                or decision["decision"]["status"] != "confirmed"
                or set(
                    decision["decision"]["authorized_closures"]
                )
                != confirmed_closures
            ):
                raise FixtureError(
                    f"{scenario_id}/{expectation['id']}: confirmed closures "
                    "are not authorized by replay input"
                )
        if decision is not None:
            serialized_segments = [
                (
                    segment["id"],
                    segment["lines"],
                    segment["disposition"],
                    segment["destination"],
                    segment["decision"],
                )
                for segment in decision["decision"]["segments"]
            ]
            if plan["adoption"] != serialized_segments:
                raise FixtureError(
                    f"{scenario_id}/{expectation['id']}: adoption decisions "
                    "are not derived from replay input"
                )
            if decision["decision"]["status"] == "confirmed":
                authorized = set(
                    decision["decision"]["authorized_closures"]
                )
                retained = {
                    token
                    for row in plan["rows"]
                    if row[1] in authorized
                    for token in row[10].split("; ")
                    if token in {"decision-required", "intent-required"}
                }
                if retained:
                    raise FixtureError(
                        f"{scenario_id}/{expectation['id']}: confirmed replay "
                        "input retains satisfied decision/intent annotations"
                    )
        has_applied = any(row[8] == "applied" for row in plan["rows"])
        if has_applied:
            if replay_input["rendered_tree"] is None:
                raise FixtureError(
                    f"{scenario_id}/{expectation['id']}: applied desired "
                    "bytes lack a replay-input render"
                )
            if tree != replay_input["rendered_tree"]:
                raise FixtureError(
                    f"{scenario_id}/{expectation['id']}: applied desired "
                    "bytes differ from replay-input render"
                )
        fault_schedule = replay_input["fault_schedule"]
        if fault_schedule is not None:
            if replay_input["rendered_tree"] is None:
                raise FixtureError(
                    f"{scenario_id}/{expectation['id']}: fault schedule "
                    "needs exact intended render bytes"
                )
            derived_tree = copy.deepcopy(input_tree)
            derived_tree[fault_schedule["target"]] = copy.deepcopy(
                fault_schedule["injected"]
            )
            if tree != derived_tree:
                raise FixtureError(
                    f"{scenario_id}/{expectation['id']}: expected tree "
                    "is not derived from the bound fault injection"
                )
        parsed_expectations.append(
            {
                "definition": expectation,
                "plan": plan,
                "tree": tree,
                "planned_tree": planned_tree,
                "replay_input": replay_input,
            }
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
        "expectations": parsed_expectations,
    }


def _validate_history(
    scenario_id: str, value: Any
) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"commits", "head"}:
        raise FixtureError(f"{scenario_id}: history fields are not closed")
    head = value["head"]
    commits = value["commits"]
    if (
        not isinstance(head, str)
        or TOKEN_PATTERN.fullmatch(head) is None
        or not isinstance(commits, list)
        or not commits
    ):
        raise FixtureError(f"{scenario_id}: invalid history head/commits")
    ids: set[str] = set()
    parsed: List[Dict[str, Any]] = []
    for commit in commits:
        if not isinstance(commit, dict) or set(commit) != {
            "id",
            "message",
            "parents",
            "tree",
        }:
            raise FixtureError(
                f"{scenario_id}: history commit fields are not closed"
            )
        commit_id = commit["id"]
        parents = commit["parents"]
        if (
            not isinstance(commit_id, str)
            or TOKEN_PATTERN.fullmatch(commit_id) is None
            or commit_id in ids
            or not isinstance(parents, list)
            or parents != sorted(set(parents))
            or any(parent not in ids for parent in parents)
            or not isinstance(commit["message"], str)
            or not commit["message"]
            or not isinstance(commit["tree"], str)
            or not commit["tree"]
        ):
            raise FixtureError(
                f"{scenario_id}: invalid/topologically unordered history commit"
            )
        ids.add(commit_id)
        parsed.append(
            {
                "id": commit_id,
                "message": commit["message"],
                "parents": parents,
                "tree": resolve_named_tree(
                    HERE,
                    TREE_MANIFEST,
                    commit["tree"],
                    shared_dir=SHARED_DIR,
                ),
            }
        )
    if head not in ids or parsed[-1]["id"] != head:
        raise FixtureError(
            f"{scenario_id}: history head must be the final commit"
        )
    return {"commits": parsed, "head": head}


def _validate_fault(scenario_id: str, fault: Any) -> None:
    if not isinstance(fault, dict) or set(fault) != {
        "kind",
        "checkpoint",
        "operations",
    }:
        raise FixtureError(f"{scenario_id}: fault fields are not closed")
    if fault["kind"] not in {
        "post-write-verification",
        "compensation",
        "host-environment",
    }:
        raise FixtureError(f"{scenario_id}: invalid fault kind")
    if not isinstance(fault["checkpoint"], str) or not fault["checkpoint"]:
        raise FixtureError(f"{scenario_id}: fault checkpoint is empty")
    operations = fault["operations"]
    if not isinstance(operations, list):
        raise FixtureError(f"{scenario_id}: fault operations must be an array")
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict) or operation.get("op") not in {
            "write",
            "delete",
            "environment",
        }:
            raise FixtureError(
                f"{scenario_id}: invalid fault operation {index}"
            )
        if operation["op"] in {"write", "delete"}:
            safe_relative(
                operation.get("path"),
                field=f"{scenario_id} fault operation {index} path",
            )
        if operation["op"] == "write":
            if operation.get("mode") not in {"100644", "100755"}:
                raise FixtureError(
                    f"{scenario_id}: invalid fault write mode"
                )
            if not isinstance(operation.get("source"), str):
                raise FixtureError(
                    f"{scenario_id}: fault write needs source evidence"
                )
        if operation["op"] == "environment":
            if not isinstance(operation.get("setting"), str) or not isinstance(
                operation.get("value"), (str, int)
            ):
                raise FixtureError(
                    f"{scenario_id}: invalid environment evidence"
                )


def validate_matrix() -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    matrix = _load_matrix()
    parsed: Dict[str, Dict[str, Any]] = {}
    ids: List[str] = []
    replay_ids: List[str] = []
    coverage: set[str] = set()
    safeguards: set[str] = set()
    for scenario in matrix["scenarios"]:
        result = _validate_scenario(
            scenario,
            default_activation_profile=matrix["default_activation_profile"],
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
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise FixtureError("scenario ids must be byte-wise sorted and unique")
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
    replay_modes = {
        item["definition"]["replay"] for item in parsed.values()
    }
    if replay_modes != REPLAY_MODES:
        raise FixtureError("matrix must exercise both replay modes")
    return matrix, parsed


def _validate_covenant_assets() -> None:
    required = (
        REPO_ROOT / "templates/covenant/claude-rules-bridge.md",
        REPO_ROOT / "templates/covenant/agents-md-covenant-block.md",
        REPO_ROOT / "templates/covenant/v1/claude-rules-bridge.md",
        REPO_ROOT / "templates/covenant/v1/agents-md-covenant-block.md",
        REPO_ROOT / "templates/covenant/v2/claude-rules-bridge.md",
        REPO_ROOT / "templates/covenant/v2/agents-md-covenant-block.md",
    )
    for template in required:
        if not template.is_file() or not template.read_bytes():
            raise FixtureError(f"required covenant template is absent: {template}")


def _resolved_commit_refs(
    expectation: Mapping[str, Any],
    *,
    baseline_commit: str,
    history_commits: Optional[Mapping[str, str]],
) -> Dict[str, str]:
    resolved: Dict[str, str] = {}
    for token, reference in expectation.get("commit_refs", {}).items():
        if reference == "initial":
            resolved[token] = baseline_commit
        elif reference.startswith("history:") and history_commits is not None:
            commit = history_commits.get(reference[len("history:") :])
            if not isinstance(commit, str):
                raise FixtureError(
                    f"unknown history commit reference {reference!r}"
                )
            resolved[token] = commit
        else:
            raise FixtureError(
                f"unsupported commit reference {reference!r}"
            )
    return resolved


SYNTHESIZED_EVIDENCE = (
    "\n"
    "## Evidence and notes\n"
    "\n"
    "Synthesized from the bound fixture expectation, which may omit this\n"
    "section; a serialized plan document may not, so the harness restores it\n"
    "before parsing the document as an agent-produced plan.\n"
)


def _actual_plan_bytes(
    expectation: Plan,
    baseline_commit: str,
    *,
    commit_refs: Mapping[str, str],
) -> bytes:
    path = Path(expectation["path"])
    data = path.read_bytes()
    old = f"- expectation: {PLAN_SPEC}".encode("ascii")
    new = f"- spec: {PLAN_SPEC}".encode("ascii")
    if data.count(old) != 1:
        raise FixtureError(f"{path}: expected one expectation header")
    data = data.replace(old, new)
    data = data.replace(
        ZERO_BASELINE.encode("ascii"),
        baseline_commit.encode("ascii"),
    )
    for token, commit in commit_refs.items():
        data = data.replace(
            token.encode("ascii"), commit.encode("ascii")
        )
    text = data.decode("utf-8")
    lines = text.splitlines(keepends=True)
    try:
        heading = next(
            index
            for index, line in enumerate(lines)
            if line.rstrip("\r\n") == "## Migration candidates"
        )
    except StopIteration as error:
        raise FixtureError(
            f"{path}: missing Migration candidates section"
        ) from error
    header_index = heading + 2
    if (
        header_index < len(lines)
        and lines[header_index].rstrip("\r\n")
        == MIGRATION_CANDIDATE_HEADER
    ):
        row_start = header_index + 2
        row_end = row_start
        while row_end < len(lines) and lines[row_end].startswith("| "):
            row_end += 1
        lines[row_start:row_end] = sorted(lines[row_start:row_end])
    rendered = "".join(lines)
    if "\n## Evidence and notes\n" not in rendered:
        rendered = rendered.rstrip("\n") + "\n" + SYNTHESIZED_EVIDENCE
    return rendered.encode("utf-8")


def _confirmed_plan_bytes(plan: Plan, baseline_commit: str) -> bytes:
    path = Path(plan["path"])
    data = path.read_bytes()
    spec_header = f"- spec: {PLAN_SPEC}".encode("ascii")
    expectation_header = f"- expectation: {PLAN_SPEC}".encode("ascii")
    if data.count(spec_header) != 1 or expectation_header in data:
        raise FixtureError(
            f"{path}: confirmed plan must carry one exact spec header"
        )
    if HASH_PATTERN.fullmatch(baseline_commit) is None:
        raise FixtureError("confirmed plan baseline binding is invalid")
    if ZERO_BASELINE.encode("ascii") not in data:
        raise FixtureError(
            f"{path}: confirmed plan has no fixture baseline placeholder"
        )
    return data.replace(
        ZERO_BASELINE.encode("ascii"),
        baseline_commit.encode("ascii"),
    )


def _replace_once(
    data: bytes,
    old: bytes,
    new: bytes,
    *,
    label: str,
) -> bytes:
    if data.count(old) != 1:
        raise FixtureError(
            f"formal adversarial {label} expected one mutation anchor"
        )
    return data.replace(old, new, 1)


def _formal_adversarial_plans(
    scenario_id: str,
    expectation_id: str,
    *,
    plan_bytes: bytes,
    marker: Mapping[str, Any],
) -> List[Tuple[str, bytes]]:
    key = (scenario_id, expectation_id)
    mutations: List[Tuple[str, bytes]] = []
    if key == ("codex-first-mixed", "pending"):
        mutations.append(
            (
                "pending-onboarding-invented-intent",
                _replace_once(
                    plan_bytes,
                    b"| - | decision-required |\n",
                    b"| - | decision-required; intent-required |\n",
                    label="pending onboarding intent",
                ),
            )
        )
    elif key == ("create-unavailable", "blocked"):
        data = _replace_once(
            plan_bytes,
            (
                b"| onboarding/covenant | closure/agents-md | selected | - | "
                b"no-baseline | create | source-to-projection | confirmed | "
                b"blocked | - | - |\n"
            ),
            (
                b"| onboarding/covenant | closure/agents-md | selected | - | "
                b"no-baseline | create | source-to-projection | confirmed | "
                b"blocked | - | - |\n"
                b"| onboarding/agents-md | closure/agents-md | selected | - | "
                b"no-baseline | create | source-to-projection | confirmed | "
                b"blocked | - | - |\n"
            ),
            label="create unavailable unit",
        )
        data = _replace_once(
            data,
            (
                b"| closure/agents-md | onboarding/covenant | - | selected | "
                b"confirmed | blocked |\n"
            ),
            (
                b"| closure/agents-md | onboarding/agents-md; "
                b"onboarding/covenant | - | selected | confirmed | blocked |\n"
            ),
            label="create unavailable closure",
        )
        mutations.append(("empty-create-invented-segmentation", data))
    elif key == ("both-changed-zero-write", "deferred"):
        baseline = marker["baseline_commit"].encode("ascii")
        data = _replace_once(
            plan_bytes,
            (
                b"| entry | closure/decision/entry | selected | "
                + baseline
                + b" | both-changed | conflict | user-decision | required | "
                b"deferred | structural | decision-required |\n"
            ),
            (
                b"| entry | closure/decision/entry | not-selected | "
                + baseline
                + b" | both-changed | conflict | user-decision | "
                b"not-applicable | not-selected | structural | "
                b"decision-required |\n"
            ),
            label="both-changed row",
        )
        data = _replace_once(
            data,
            b"| selected | required | deferred |\n",
            b"| not-selected | not-applicable | not-selected |\n",
            label="both-changed closure",
        )
        mutations.append(("both-changed-not-selected", data))
    elif key == ("multi-unit-partial-selection", "selected"):
        baseline = marker["baseline_commit"].encode("ascii")
        row = (
            b"| rules/beta | closure/decision/rules/beta | selected | "
            + baseline
            + b" | both-changed | conflict | user-decision | required | "
            b"deferred | structural | decision-required |\n"
        )
        mutations.append(
            (
                "multi-unit-rule-tier",
                _replace_once(
                    plan_bytes,
                    b"| deferred | structural | decision-required |\n",
                    b"| deferred | semantic | decision-required |\n",
                    label="multi-unit rule tier",
                ),
            )
        )
        missing = _replace_once(
            plan_bytes,
            b"| rules/beta | closure/decision/rules/beta |",
            b"| rules/gamma | closure/decision/rules/gamma |",
            label="multi-unit missing tier row mapping",
        )
        missing = _replace_once(
            missing,
            b"| closure/decision/rules/beta | rules/beta |",
            b"| closure/decision/rules/gamma | rules/gamma |",
            label="multi-unit missing tier closure mapping",
        )
        mutations.append(("multi-unit-missing-tier-mapping", missing))
        mutations.append(
            (
                "multi-unit-duplicate-tier-mapping",
                _replace_once(
                    plan_bytes,
                    row,
                    row + row,
                    label="multi-unit duplicate tier mapping",
                ),
            )
        )
    elif key == ("scoped-project", "applied"):
        mutations.append(
            (
                "claude-to-codex-scoped-rule-tier",
                _replace_once(
                    plan_bytes,
                    b"| semantic | live-activation-unknown; "
                    b"restart-may-be-required |\n",
                    b"| structural | live-activation-unknown; "
                    b"restart-may-be-required |\n",
                    label="Claude-to-Codex scoped rule tier",
                ),
            )
        )
    elif key == ("scoped-reverse", "applied"):
        mutations.append(
            (
                "codex-to-claude-scoped-rule-tier",
                _replace_once(
                    plan_bytes,
                    b"| applied | semantic | - |\n",
                    b"| applied | structural | - |\n",
                    label="Codex-to-Claude scoped rule tier",
                ),
            )
        )
    elif key == ("closure-dependency-unsatisfied", "blocked"):
        mutations.append(
            (
                "closure-dependency-skill-tier",
                _replace_once(
                    plan_bytes,
                    b"| required | planned | native | - |\n",
                    b"| required | planned | - | - |\n",
                    label="closure dependency skill tier",
                ),
            )
        )
    elif key == ("semantic-neutralization", "deferred"):
        mutations.extend(
            [
                (
                    "semantic-adoption-without-intent",
                    _replace_once(
                        plan_bytes,
                        b"| intent-required; semantic-review-required |\n",
                        b"| semantic-review-required |\n",
                        label="semantic intent",
                    ),
                ),
                (
                    "semantic-neutralization-entry-tier",
                    _replace_once(
                        plan_bytes,
                        b"| planned | structural | intent-required; "
                        b"semantic-review-required |\n",
                        b"| planned | semantic | intent-required; "
                        b"semantic-review-required |\n",
                        label="semantic neutralization entry tier",
                    ),
                ),
            ]
        )
    elif key == ("legacy-mode", "blocked"):
        mutations.append(
            (
                "legacy-incomplete-warning-set",
                _replace_once(
                    plan_bytes,
                    b"- marker-anomaly: AGENTS.md (line 56)\n",
                    b"",
                    label="legacy marker warning",
                ),
            )
        )
    elif key == ("fallback-shadow", "blocked"):
        mutations.append(
            (
                "fallback-wrong-scope-carrier",
                _replace_once(
                    plan_bytes,
                    b"- fallback-shadow: BRIDGE_FALLBACK.md\n",
                    b"- fallback-shadow: CLAUDE.md\n",
                    label="fallback carrier",
                ),
            )
        )
    elif key == ("migration-ambiguous-dag", "blocked"):
        root_commit = marker.get("history_commits", {}).get("root")
        if not isinstance(root_commit, str):
            raise FixtureError("migration adversarial lacks root commit")
        mutations.append(
            (
                "ambiguous-migration-current-baseline",
                _replace_once(
                    plan_bytes,
                    (
                        b"| skills/fixture-legacy-release | closure/migration | "
                        b"selected | - | contract-migration |"
                    ),
                    (
                        b"| skills/fixture-legacy-release | closure/migration | "
                        b"selected | "
                        + root_commit.encode("ascii")
                        + b" | contract-migration |"
                    ),
                    label="ambiguous migration baseline",
                ),
            )
        )
    elif key == ("migration-v1-v3", "applied"):
        baseline = marker["baseline_commit"].encode("ascii")
        mutations.append(
            (
                "released-migration-retained-baseline",
                _replace_once(
                    plan_bytes,
                    (
                        b"| skills/fixture-legacy-release | closure/migration | "
                        b"selected | - | contract-migration | migrate | "
                        b"user-decision | confirmed | applied | native | - |\n"
                    ),
                    (
                        b"| skills/fixture-legacy-release | closure/migration | "
                        b"selected | "
                        + baseline
                        + b" | contract-migration | migrate | user-decision | "
                        b"confirmed | applied | native | "
                        b"migration-transition-required |\n"
                    ),
                    label="released migration state",
                ),
            )
        )
    elif key == ("rename-rule", "blocked"):
        baseline = marker["baseline_commit"].encode("ascii")
        mutations.append(
            (
                "rename-new-unit-has-baseline",
                _replace_once(
                    plan_bytes,
                    (
                        b"| rules/new | closure/agents-md | selected | - | "
                        b"no-baseline | rename |"
                    ),
                    (
                        b"| rules/new | closure/agents-md | selected | "
                        + baseline
                        + b" | source-only | rename |"
                    ),
                    label="rename destination baseline",
                ),
            )
        )
    elif key == ("empty-create", "applied"):
        mutations.extend(
            [
                (
                    "post-write-missing-untracked-warning",
                    _replace_once(
                        plan_bytes,
                        b"- untracked-files-included: AGENTS.md\n",
                        b"",
                        label="post-write untracked warning",
                    ),
                ),
                (
                    "post-write-false-onboarded-header",
                    _replace_once(
                        plan_bytes,
                        b"- onboarding: bootstrap-required\n",
                        b"- onboarding: onboarded\n",
                        label="post-write onboarding header",
                    ),
                ),
                (
                    "post-write-reclassified-covenant-state",
                    _replace_once(
                        plan_bytes,
                        (
                            b"| no-baseline | create | "
                            b"source-to-projection |"
                        ),
                        (
                            b"| blocked | repair | "
                            b"user-decision |"
                        ),
                        label="post-write covenant state/action",
                    ),
                ),
                (
                    "post-write-invented-covenant-anomaly",
                    _replace_once(
                        plan_bytes,
                        b"## Warnings\n\n",
                        (
                            b"## Warnings\n\n"
                            b"- covenant-anchor-anomaly: AGENTS.md "
                            b"(untracked)\n"
                        ),
                        label="post-write covenant anomaly",
                    ),
                ),
                (
                    "hook-tiers-section-missing",
                    _replace_once(
                        plan_bytes,
                        b"## Hook tiers\n\n- (none)\n\n",
                        b"",
                        label="hook tiers section",
                    ),
                ),
                (
                    "hook-tiers-section-misplaced",
                    _replace_once(
                        plan_bytes,
                        (
                            b"## Hook tiers\n\n- (none)\n\n"
                            b"## Migration decisions\n\n- (none)\n\n"
                        ),
                        (
                            b"## Migration decisions\n\n- (none)\n\n"
                            b"## Hook tiers\n\n- (none)\n\n"
                        ),
                        label="hook tiers section position",
                    ),
                ),
                (
                    "hook-tiers-invented-row",
                    _replace_once(
                        plan_bytes,
                        b"## Hook tiers\n\n- (none)\n",
                        (
                            b"## Hook tiers\n\n"
                            b"| unit | class | surface | tier | reason |\n"
                            b"|---|---|---|---|---|\n"
                            b"| hooks/repo-guard/claude | gate | "
                            b"settings-json | native | shared-event-command "
                            b"|\n"
                        ),
                        label="hook tiers row",
                    ),
                ),
                (
                    "hook-adoption-out-of-file-order",
                    _replace_once(
                        plan_bytes,
                        b"## Hook adoption decisions\n\n- (none)\n",
                        (
                            b"## Hook adoption decisions\n\n"
                            b"| handler | location | disposition | "
                            b"destination | decision |\n"
                            b"|---|---|---|---|---|\n"
                            b"| handler/2 | "
                            b".claude/settings.json#PreToolUse[0][0] | keep "
                            b"| - | pending |\n"
                        ),
                        label="hook adoption row",
                    ),
                ),
                (
                    "hook-adoption-out-of-carrier-order",
                    _replace_once(
                        plan_bytes,
                        b"## Hook adoption decisions\n\n- (none)\n",
                        (
                            b"## Hook adoption decisions\n\n"
                            b"| handler | location | disposition | "
                            b"destination | decision |\n"
                            b"|---|---|---|---|---|\n"
                            b"| handler/1 | "
                            b".codex/hooks.json#PreToolUse[0][0] | keep "
                            b"| - | pending |\n"
                            b"| handler/2 | "
                            b".claude/settings.json#PreToolUse[0][0] | keep "
                            b"| - | pending |\n"
                        ),
                        label="hook adoption carrier order",
                    ),
                ),
            ]
        )
    elif key == ("empty-untracked-rescan", "blocked"):
        baseline = marker["baseline_commit"].encode("ascii")
        mutations.extend(
            [
                (
                    "fresh-scan-missing-covenant-anomaly",
                    _replace_once(
                        plan_bytes,
                        (
                            b"- covenant-anchor-anomaly: AGENTS.md "
                            b"(untracked)\n"
                        ),
                        b"",
                        label="fresh scan covenant anomaly",
                    ),
                ),
                (
                    "fresh-scan-bootstrap-required-header",
                    _replace_once(
                        plan_bytes,
                        b"- onboarding: blocked\n",
                        b"- onboarding: bootstrap-required\n",
                        label="fresh scan onboarding header",
                    ),
                ),
                (
                    "fresh-scan-invented-baseline",
                    _replace_once(
                        plan_bytes,
                        (
                            b"| onboarding/covenant | "
                            b"closure/decision/onboarding/covenant | "
                            b"selected | - | blocked |"
                        ),
                        (
                            b"| onboarding/covenant | "
                            b"closure/decision/onboarding/covenant | "
                            b"selected | "
                            + baseline
                            + b" | blocked |"
                        ),
                        label="fresh scan covenant baseline",
                    ),
                ),
            ]
        )
    return mutations


def _exercise_formal_plan_adversarials(
    scenario_id: str,
    expectation_id: str,
    *,
    replay_input: str,
    root: Path,
    lease: str,
    plan_path: Path,
    lifecycle: str,
    marker: Mapping[str, Any],
) -> int:
    mutations = _formal_adversarial_plans(
        scenario_id,
        expectation_id,
        plan_bytes=plan_path.read_bytes(),
        marker=marker,
    )
    checks = 0
    key = (scenario_id, expectation_id)
    tier_acceptance_keys = {
        ("closure-dependency-satisfied", "applied"),
        ("closure-dependency-unsatisfied", "blocked"),
        ("multi-unit-partial-selection", "selected"),
        ("scoped-project", "applied"),
        ("scoped-reverse", "applied"),
        ("semantic-neutralization", "deferred"),
    }
    if key in tier_acceptance_keys:
        accepted = _validate_plan_result(
            replay_input=replay_input,
            root=root,
            lease=lease,
            plan_path=plan_path,
            lifecycle=lifecycle,
        )
        if not accepted["pass"] or accepted["failures"]:
            raise FixtureError(
                f"formal validator rejected canonical tier case {key!r}"
            )
        checks += 1
    if key == ("empty-create", "applied"):
        accepted = _validate_plan_result(
            replay_input=replay_input,
            root=root,
            lease=lease,
            plan_path=plan_path,
            lifecycle="closed",
        )
        if not accepted["pass"] or accepted["failures"]:
            raise FixtureError(
                "formal validator rejected the closed empty-bootstrap "
                "operation result"
            )
        checks += 1
    elif key == ("empty-untracked-rescan", "blocked"):
        rejected = _validate_plan_result(
            replay_input=replay_input,
            root=root,
            lease=lease,
            plan_path=plan_path,
            lifecycle="closed",
        )
        if (
            rejected["pass"]
            or rejected["failures"] != ["phase-lifecycle"]
        ):
            raise FixtureError(
                "formal validator accepted a fresh-scan plan as a closed "
                "operation result"
            )
        checks += 1
    for index, (label, data) in enumerate(mutations, start=1):
        path = root / ".git" / (
            f"bridge-fixture-formal-adversarial-{index}.md"
        )
        try:
            path.write_bytes(data)
            refusal = _validate_plan_result(
                replay_input=replay_input,
                root=root,
                lease=lease,
                plan_path=path,
                lifecycle=lifecycle,
            )
            if refusal["pass"] or not refusal["failures"]:
                raise FixtureError(
                    f"formal validator accepted adversarial {label}"
                )
            checks += 1
            if label == "multi-unit-rule-tier":
                diagnostic = _explain_plan_result(
                    replay_input=replay_input,
                    root=root,
                    lease=lease,
                    plan_path=path,
                    lifecycle=lifecycle,
                )
                if (
                    diagnostic["failures"] != ["unit-closure"]
                    or not any(
                        item["kind"] == "generic"
                        and item["section"] == "plan"
                        and item["detail"] == "unit-closure"
                        for item in diagnostic["diagnostics"]
                    )
                ):
                    raise FixtureError(
                        "wrong public tier lacks a deterministic generic "
                        "diagnostic"
                    )
                checks += 1
        finally:
            if path.exists():
                os.unlink(path)
    return checks


def _exercise_plan_diagnostic_contract(
    *,
    replay_input: str,
    root: Path,
    lease: str,
    plan_path: Path,
    lifecycle: str,
) -> int:
    plan_bytes = plan_path.read_bytes()
    migration_line = b"- migration-transition-uncommitted: .\n"
    guarded_first = (
        b"- guarded-patch-non-cas: "
        b".agents/skills/fixture-legacy-repair/SKILL.md\n"
    )
    guarded_second = (
        b"- guarded-patch-non-cas: "
        b".claude/rules/bridge-covenant.md\n"
    )
    manual_guarded = b"- manual-zone-guarded: AGENTS.md\n"
    if any(
        plan_bytes.count(anchor) != 1
        for anchor in (
            migration_line,
            guarded_first,
            guarded_second,
            manual_guarded,
        )
    ):
        raise FixtureError(
            "migration diagnostic canonical warning anchors are not singular"
        )

    canonical = _explain_plan_result(
        replay_input=replay_input,
        root=root,
        lease=lease,
        plan_path=plan_path,
        lifecycle=lifecycle,
    )
    _validate_plan_diagnostic_result(canonical)
    validation = _validate_plan_result(
        replay_input=replay_input,
        root=root,
        lease=lease,
        plan_path=plan_path,
        lifecycle=lifecycle,
    )
    if (
        canonical["contract"] != PLAN_DIAGNOSTIC_SPEC
        or canonical["plan_sha256"] != validation["plan_sha256"]
        or canonical["context_sha256"] != validation["context_sha256"]
        or canonical["failures"]
        or canonical["diagnostics"]
    ):
        raise FixtureError(
            "canonical migration plan diagnostic did not close cleanly"
        )
    subprocess_result = _run_harness_subprocess(
        [
            "explain-plan",
            replay_input,
            str(root),
            "--lease",
            lease,
            "--plan",
            str(plan_path),
            "--operation-lifecycle",
            lifecycle,
        ],
        expect_success=True,
    )
    if subprocess_result != canonical:
        raise FixtureError(
            "public explain-plan subprocess differs from direct result"
        )

    forbidden_fragments = (
        "expectation",
        "expectations/",
        "golden",
        "oracle",
        "matrix",
        "planned_state",
        "post_state",
    )

    def assert_no_oracle(value: Mapping[str, Any]) -> None:
        serialized = json.dumps(
            value, ensure_ascii=False, sort_keys=True
        ).lower()
        leaked = [
            fragment
            for fragment in forbidden_fragments
            if fragment in serialized
        ]
        if leaked:
            raise FixtureError(
                "plan diagnostic leaked private authoring vocabulary: "
                + ", ".join(leaked)
            )

    assert_no_oracle(canonical)
    authoring_functions = {
        name: globals()[name]
        for name in ("_scenario", "_expectation", "validate_matrix")
    }

    def reject_authoring_access(*_: Any, **__: Any) -> Any:
        raise FixtureError(
            "public plan diagnostic touched authoring declarations"
        )

    try:
        for name in authoring_functions:
            globals()[name] = reject_authoring_access
        blind = _explain_plan_result(
            replay_input=replay_input,
            root=root,
            lease=lease,
            plan_path=plan_path,
            lifecycle=lifecycle,
        )
    finally:
        globals().update(authoring_functions)
    if blind != canonical:
        raise FixtureError(
            "plan diagnostic changed behind the blind replay boundary"
        )

    wrong_guarded = (
        b"- guarded-patch-non-cas: "
        b".agents/skills/fixture-other/SKILL.md\n"
    )
    manual_preserved = b"- manual-zone-preserved: AGENTS.md\n"
    unknown_token = b"- fixture-unknown-warning: .\n"
    mutations = [
        (
            "missing",
            _replace_once(
                plan_bytes,
                migration_line,
                b"",
                label="diagnostic missing migration warning",
            ),
            {
                "kind": "missing",
                "token": "migration-transition-uncommitted",
                "required_line": migration_line.decode("ascii").rstrip(),
            },
        ),
        (
            "path",
            _replace_once(
                plan_bytes,
                guarded_first,
                wrong_guarded,
                label="diagnostic wrong guarded path",
            ),
            {
                "kind": "path",
                "token": "guarded-patch-non-cas",
                "actual_line": wrong_guarded.decode("ascii").rstrip(),
            },
        ),
        (
            "invalid-order",
            _replace_once(
                plan_bytes,
                guarded_first + guarded_second,
                guarded_second + guarded_first,
                label="diagnostic warning order",
            ),
            {"kind": "invalid-order"},
        ),
        (
            "cardinality",
            _replace_once(
                plan_bytes,
                migration_line,
                migration_line + migration_line,
                label="diagnostic warning cardinality",
            ),
            {
                "kind": "cardinality",
                "actual_line": migration_line.decode("ascii").rstrip(),
                "actual_count": 2,
                "required_count": 1,
            },
        ),
        (
            "token",
            _replace_once(
                plan_bytes,
                migration_line,
                unknown_token,
                label="diagnostic warning token",
            ),
            {
                "kind": "token",
                "token": "fixture-unknown-warning",
            },
        ),
        (
            "extra",
            _replace_once(
                plan_bytes,
                manual_guarded,
                manual_guarded + manual_preserved,
                label="diagnostic extra warning",
            ),
            {
                "kind": "extra",
                "token": "manual-zone-preserved",
                "actual_line": manual_preserved.decode("ascii").rstrip(),
            },
        ),
        (
            "generic",
            _replace_once(
                plan_bytes,
                b"# Bridge Sync Plan\n",
                b"# Broken Plan\n",
                label="diagnostic generic plan failure",
            ),
            {
                "kind": "generic",
                "section": "plan",
                "detail": "document-grammar",
            },
        ),
    ]
    checks = 5
    for index, (label, data, wanted) in enumerate(mutations, start=1):
        mutation_path = root / ".git" / (
            f"bridge-fixture-plan-diagnostic-{index}.md"
        )
        try:
            mutation_path.write_bytes(data)
            result = _explain_plan_result(
                replay_input=replay_input,
                root=root,
                lease=lease,
                plan_path=mutation_path,
                lifecycle=lifecycle,
            )
            _validate_plan_diagnostic_result(result)
            assert_no_oracle(result)
            if (
                result["plan_sha256"] != _sha256(data)
                or result["context_sha256"]
                != canonical["context_sha256"]
                or not any(
                    all(item.get(key) == value for key, value in wanted.items())
                    for item in result["diagnostics"]
                )
            ):
                raise FixtureError(
                    f"plan diagnostic did not explain {label}: {result}"
                )
            checks += 3
        finally:
            if mutation_path.exists():
                os.unlink(mutation_path)
    return checks


def _exercise_replay_bundle_adversarials(
    root: Path,
    *,
    lease: str,
    replay_id: str,
    envelope: Mapping[str, Any],
    input_tree: Mapping[str, Any],
    full: bool,
    fault_full: bool,
) -> int:
    """Reject closed-schema, commitment, swap, and fault-byte attacks."""

    checks = 0

    def expect_rejection(label: str) -> None:
        nonlocal checks
        try:
            _validate_blind_installed_replay_input(
                root,
                lease=lease,
                replay_id=replay_id,
                require_input_tree=True,
            )
        except (FixtureError, OSError, UnicodeError, ValueError):
            checks += 1
        else:
            raise FixtureError(
                f"blind replay accepted bundle adversarial {label}"
            )

    try:
        _validate_blind_installed_replay_input(
            root,
            lease="wrong-lease",
            replay_id=replay_id,
            require_input_tree=True,
        )
    except FixtureError:
        checks += 1
    else:
        raise FixtureError("blind replay accepted a cross-lease call")
    try:
        _validate_blind_installed_replay_input(
            root,
            lease=lease,
            replay_id="wrong-replay-input",
            require_input_tree=True,
        )
    except FixtureError:
        checks += 1
    else:
        raise FixtureError("blind replay accepted a cross-replay call")

    git_directory = root / ".git"
    replay_path = git_directory / REPLAY_INPUT_TARGET
    commitment_path = git_directory / REPLAY_COMMITMENT_TARGET
    marker_path = git_directory / "bridge-fixture.json"
    capability_path = git_directory / WRITE_CAPABILITY_TARGET
    profile_path = git_directory / ACTIVATION_PROFILE_TARGET

    def mutate_bytes(path: Path, data: bytes, *, label: str) -> None:
        original = path.read_bytes()
        try:
            path.write_bytes(data)
            expect_rejection(label)
        finally:
            path.write_bytes(original)

    if full:
        for label, mutation in (
            (
                "envelope-missing",
                lambda value: value.pop("payload"),
            ),
            (
                "envelope-extra",
                lambda value: value.__setitem__("oracle", "private"),
            ),
            (
                "envelope-version",
                lambda value: value.__setitem__(
                    "version", "bridge-m3-replay-envelope/v1"
                ),
            ),
            (
                "envelope-hash",
                lambda value: value.__setitem__(
                    "commitment_sha256", "0" * 64
                ),
            ),
        ):
            candidate = copy.deepcopy(envelope)
            mutation(candidate)
            mutate_bytes(
                replay_path,
                _canonical_json_bytes(candidate),
                label=label,
            )
        replay_bytes = replay_path.read_bytes()
        mutate_bytes(
            replay_path,
            replay_bytes + b"\n",
            label="envelope-noncanonical",
        )
        duplicate = (
            b'{"version":"bridge-m3-replay-envelope/v2",'
            + replay_bytes[1:-1]
            + b',"version":"bridge-m3-replay-envelope/v2"}'
        )
        mutate_bytes(
            replay_path,
            duplicate,
            label="envelope-duplicate-key",
        )
        commitment = _read_canonical_json(
            commitment_path, label="replay commitment"
        )
        for label, mutation in (
            (
                "commitment-missing",
                lambda value: value.pop("components"),
            ),
            (
                "commitment-extra",
                lambda value: value.__setitem__("signature", "false"),
            ),
            (
                "commitment-version",
                lambda value: value.__setitem__(
                    "version", "replay-bundle-commitment/v0"
                ),
            ),
            (
                "commitment-binding",
                lambda value: value["binding"].__setitem__(
                    "nonce", "tampered-nonce"
                ),
            ),
        ):
            candidate = copy.deepcopy(commitment)
            mutation(candidate)
            mutate_bytes(
                commitment_path,
                _canonical_json_bytes(candidate),
                label=label,
            )
        commitment_bytes = commitment_path.read_bytes()
        mutate_bytes(
            commitment_path,
            commitment_bytes + b" ",
            label="commitment-noncanonical",
        )
        marker = _read_canonical_json(marker_path, label="fixture marker")
        marker["unexpected"] = "private"
        mutate_bytes(
            marker_path,
            _canonical_json_bytes(marker),
            label="marker-extra",
        )
        capability = _read_canonical_json(
            capability_path, label="write capability"
        )
        capability["binding"]["source_sha256"] = "0" * 64
        mutate_bytes(
            capability_path,
            _canonical_json_bytes(capability),
            label="capability-component",
        )
        profile = _read_canonical_json(
            profile_path, label="activation profile"
        )
        profile["budget_source"] = "tampered"
        mutate_bytes(
            profile_path,
            _canonical_json_bytes(profile),
            label="profile-component",
        )
        hardlink = git_directory / "bridge-fixture-hardlink-negative"
        try:
            os.link(commitment_path, hardlink)
            expect_rejection("commitment-hardlink")
        finally:
            if os.path.lexists(hardlink):
                os.unlink(hardlink)
        baseline = git_run(root, "rev-parse", "HEAD")
        git_run(root, "commit", "--allow-empty", "-m", "fixture head drift")
        try:
            expect_rejection("head-drift")
        finally:
            git_run(root, "update-ref", "refs/heads/main", baseline)

    wrapper = envelope["payload"]["fault_schedule"]
    if fault_full and wrapper is not None:
        schedule_path = git_directory / FAULT_SCHEDULE_TARGET
        original_schedule_bytes = schedule_path.read_bytes()
        original_document = copy.deepcopy(wrapper["facts"])
        marker = _read_canonical_json(marker_path, label="fixture marker")

        def reject_fault_document(
            label: str,
            mutation: Any,
        ) -> None:
            nonlocal checks
            candidate = copy.deepcopy(original_document)
            mutation(candidate)
            candidate_bytes = _canonical_json_bytes(candidate)
            candidate_marker = copy.deepcopy(marker)
            candidate_marker["fault_schedule_sha256"] = _sha256(
                candidate_bytes
            )
            candidate_payload = copy.deepcopy(envelope["payload"])
            candidate_payload["fault_schedule"] = {
                "version": FAULT_SCHEDULE_SPEC,
                "sha256": _sha256(candidate_bytes),
                "facts": candidate,
            }
            try:
                schedule_path.write_bytes(candidate_bytes)
                _validate_blind_fault_schedule(
                    root,
                    lease=lease,
                    replay_id=replay_id,
                    scenario_id=envelope["payload"]["binding"][
                        "scenario"
                    ],
                    marker=candidate_marker,
                    envelope=candidate_payload,
                    input_tree=input_tree,
                )
            except (FixtureError, OSError, UnicodeError, ValueError):
                checks += 1
            else:
                raise FixtureError(
                    f"fault schedule accepted adversarial {label}"
                )
            finally:
                schedule_path.write_bytes(original_schedule_bytes)

        reject_fault_document(
            "fault-extra",
            lambda value: value.__setitem__("oracle", "private"),
        )
        reject_fault_document(
            "fault-version",
            lambda value: value.__setitem__(
                "version", "fault-schedule-fixture/v0"
            ),
        )
        reject_fault_document(
            "fault-phase",
            lambda value: value.__setitem__(
                "phase", "after-final-preflight"
            ),
        )
        reject_fault_document(
            "fault-unsafe-target",
            lambda value: value.__setitem__(
                "target", "AGENTS.md:stream"
            ),
        )
        reject_fault_document(
            "fault-preimage-hash",
            lambda value: value.__setitem__(
                "expected_preimage_sha256", "0" * 64
            ),
        )
        reject_fault_document(
            "fault-base64",
            lambda value: value["injected"].__setitem__(
                "bytes_base64", "***"
            ),
        )
        reject_fault_document(
            "fault-injected-hash",
            lambda value: value["injected"].__setitem__(
                "sha256", "0" * 64
            ),
        )
        preimage = input_tree[original_document["target"]]["bytes"]

        def make_equal(value: Dict[str, Any]) -> None:
            value["injected"]["bytes_base64"] = base64.b64encode(
                preimage
            ).decode("ascii")
            value["injected"]["sha256"] = _sha256(preimage)

        reject_fault_document("fault-equal-preimage", make_equal)

        def make_mode_only(value: Dict[str, Any]) -> None:
            make_equal(value)
            value["injected"]["mode"] = (
                "100755"
                if input_tree[original_document["target"]]["mode"]
                == "100644"
                else "100644"
            )

        reject_fault_document("fault-mode-only-preimage", make_mode_only)

    if full or fault_full:
        scenario_id, _, parsed, replay_input = _replay_input_by_id(
            replay_id
        )
        donor = create_temp_git_project(
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
                None
                if parsed["history"] is None
                else parsed["history"]["head"]
            ),
        )
        donor_root = Path(donor["worktree"])
        try:
            _install_activation_profile(
                donor_root, parsed["activation_profile"]
            )
            _install_replay_input(
                donor_root,
                lease=donor["lease"],
                scenario_id=scenario_id,
                parsed=parsed,
                replay_input=replay_input,
            )
            names = [
                "bridge-fixture.json",
                WRITE_CAPABILITY_TARGET,
                REPLAY_COMMITMENT_TARGET,
                REPLAY_INPUT_TARGET,
            ]
            if wrapper is not None:
                names.append(FAULT_SCHEDULE_TARGET)
            for name in names:
                target_path = git_directory / name
                donor_path = donor_root / ".git" / name
                mutate_bytes(
                    target_path,
                    donor_path.read_bytes(),
                    label=f"cross-materialization-{name}",
                )
            originals = {
                name: (git_directory / name).read_bytes()
                for name in names
            }
            try:
                for name in names:
                    (git_directory / name).write_bytes(
                        (donor_root / ".git" / name).read_bytes()
                    )
                expect_rejection("combined-cross-materialization")
            finally:
                for name, data in originals.items():
                    (git_directory / name).write_bytes(data)
        finally:
            if donor_root.exists():
                cleanup_leased_project(
                    donor_root,
                    suite=SUITE,
                    scenario=scenario_id,
                    lease=donor["lease"],
                )
    return checks


def _run_harness_subprocess(
    arguments: Sequence[str],
    *,
    expect_success: bool,
) -> Dict[str, Any]:
    ambiguous_value_options = {
        "--lease",
        "--marker-sha256",
        "--nonce",
        "--operation-id",
    }
    normalized_arguments: List[str] = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if (
            argument in ambiguous_value_options
            and index + 1 < len(arguments)
        ):
            normalized_arguments.append(
                f"{argument}={arguments[index + 1]}"
            )
            index += 2
            continue
        normalized_arguments.append(argument)
        index += 1
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            *normalized_arguments,
        ],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise FixtureError(
            "fault CLI subprocess did not emit one JSON document: "
            f"exit={completed.returncode}; stderr={completed.stderr!r}"
        ) from error
    if not isinstance(output, dict):
        raise FixtureError("fault CLI subprocess output is not an object")
    if expect_success:
        if completed.returncode != 0 or output.get("pass") is False:
            raise FixtureError(
                f"fault CLI subprocess failed unexpectedly: {output}"
            )
    elif completed.returncode == 0 or output.get("pass") is not False:
        raise FixtureError(
            f"fault CLI subprocess accepted an adversarial call: {output}"
        )
    return output


def _run_journal_v2_suite() -> Dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(JOURNAL_VALIDATOR_TESTS_PATH),
            "--mode",
            "single",
        ],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise FixtureError(
            "journal v2 suite did not emit one JSON document: "
            f"exit={completed.returncode}; stderr={completed.stderr!r}"
        ) from error
    if (
        completed.returncode != 0
        or not isinstance(result, dict)
        or result.get("mode") != "single"
        or result.get("pass") is not True
        or result.get("cases") != JOURNAL_CASE_COUNT
        or result.get("journal_spec") != JOURNAL_SPEC
        or result.get("contract") != JOURNAL_VALIDATOR_SPEC
        or result.get("session_cleanup") is not True
    ):
        raise FixtureError(f"journal v2 suite contract drifted: {result}")
    return result


def _exercise_fault_phase_subprocess(
    root: Path,
    *,
    lease: str,
    replay_id: str,
    marker: Mapping[str, Any],
) -> int:
    confirmed_source = (
        HERE
        / "plans"
        / "guarded-preflight-mismatch-confirmed.md"
    )
    confirmed = parse_plan(confirmed_source, expectation=False)
    confirmed_bytes = _confirmed_plan_bytes(
        confirmed, marker["baseline_commit"]
    )
    confirmed_input = (
        root / ".git" / "bridge-fixture-fault-confirmed-input.md"
    )
    confirmed_input.write_bytes(confirmed_bytes)
    operation_id = "fault-operation-guarded-preflight-v1"
    common = [
        replay_id,
        str(root),
        "--lease",
        lease,
        "--operation-id",
        operation_id,
    ]
    _run_harness_subprocess(
        ["apply-fault", *common],
        expect_success=False,
    )
    if compare_tree(
        root,
        _facts_tree(
            _validate_blind_installed_replay_input(
                root,
                lease=lease,
                replay_id=replay_id,
                require_input_tree=True,
            )["payload"]["input"]["files"]
        ),
    ):
        raise FixtureError("early fault apply changed the input tree")
    armed = _run_harness_subprocess(
        [
            "arm-fault",
            replay_id,
            str(root),
            "--lease",
            lease,
            "--plan",
            str(confirmed_input),
            "--operation-id",
            operation_id,
        ],
        expect_success=True,
    )
    if (
        armed.get("state") != "confirmed-awaiting-final-preflight"
        or armed.get("bridge_writes") != 0
    ):
        raise FixtureError("fault arm did not emit exact zero-write evidence")
    _run_harness_subprocess(
        [
            "arm-fault",
            replay_id,
            str(root),
            "--lease",
            lease,
            "--plan",
            str(confirmed_input),
            "--operation-id",
            operation_id,
        ],
        expect_success=False,
    )
    wrong_operation = [
        replay_id,
        str(root),
        "--lease",
        lease,
        "--operation-id",
        "fault-operation-wrong-identity-v1",
    ]
    _run_harness_subprocess(
        ["apply-fault", *wrong_operation],
        expect_success=False,
    )
    injected = _run_harness_subprocess(
        ["apply-fault", *common],
        expect_success=True,
    )
    if (
        injected.get("state") != "injected"
        or injected.get("bridge_writes") != 0
        or injected.get("fixture_writes") != 1
    ):
        raise FixtureError(
            "fault apply did not emit exact injected/zero-write evidence"
        )
    _run_harness_subprocess(
        ["apply-fault", *common],
        expect_success=False,
    )
    return 7 + _exercise_fault_fail_closed_subprocesses(
        replay_id=replay_id
    )


def _exercise_declarative_fault_phase_subprocess(
    root: Path,
    *,
    lease: str,
    replay_id: str,
    marker: Mapping[str, Any],
) -> int:
    capability = root_child_capability()
    if capability["same-mode-root-child-mutation"]:
        raise FixtureError(
            "declarative fault test requires unavailable mutation capability"
        )
    confirmed_source = (
        HERE / "plans" / "guarded-preflight-mismatch-confirmed.md"
    )
    confirmed = parse_plan(confirmed_source, expectation=False)
    confirmed_input = (
        root / ".git" / "bridge-fixture-fault-confirmed-input.md"
    )
    confirmed_input.write_bytes(
        _confirmed_plan_bytes(confirmed, marker["baseline_commit"])
    )
    operation_id = "fault-operation-guarded-preflight-v1"
    common = [
        replay_id,
        str(root),
        "--lease",
        lease,
        "--operation-id",
        operation_id,
    ]
    input_tree = _facts_tree(
        _validate_blind_installed_replay_input(
            root,
            lease=lease,
            replay_id=replay_id,
            require_input_tree=True,
        )["payload"]["input"]["files"]
    )
    before = inspect_root_child(root, "AGENTS.md")
    _run_harness_subprocess(
        ["apply-fault", *common],
        expect_success=False,
    )
    if compare_tree(root, input_tree):
        raise FixtureError(
            "early declarative-only fault apply changed the input tree"
        )
    armed = _run_harness_subprocess(
        [
            "arm-fault",
            *common,
            "--plan",
            str(confirmed_input),
        ],
        expect_success=True,
    )
    if (
        armed.get("state") != "confirmed-awaiting-final-preflight"
        or armed.get("bridge_writes") != 0
        or armed.get("mutation_capability") != capability
    ):
        raise FixtureError(
            "declarative-only fault arm did not report its platform boundary"
        )
    paths = _phase_paths(root)
    if paths["claim"].exists() or paths["injected"].exists():
        raise FixtureError(
            "declarative-only fault arm created mutation-phase evidence"
        )
    _run_harness_subprocess(
        ["apply-fault", *common],
        expect_success=False,
    )
    after = inspect_root_child(root, "AGENTS.md")
    if (
        after != before
        or paths["claim"].exists()
        or paths["injected"].exists()
        or compare_tree(root, input_tree)
    ):
        raise FixtureError(
            "declarative-only fault apply did not preserve retained read state"
        )
    return 7


def _exercise_fault_fail_closed_subprocesses(
    *,
    replay_id: str,
) -> int:
    scenario_id, _, parsed, replay_input = _replay_input_by_id(replay_id)

    def materialize_bound() -> Tuple[Path, str, Dict[str, Any], Path]:
        materialized = create_temp_git_project(
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
                None
                if parsed["history"] is None
                else parsed["history"]["head"]
            ),
        )
        candidate_root = Path(materialized["worktree"])
        try:
            _install_activation_profile(
                candidate_root, parsed["activation_profile"]
            )
            _install_replay_input(
                candidate_root,
                lease=materialized["lease"],
                scenario_id=scenario_id,
                parsed=parsed,
                replay_input=replay_input,
            )
            candidate_marker = validate_marker(
                candidate_root,
                suite=SUITE,
                scenario=scenario_id,
                lease=materialized["lease"],
            )
            source = (
                HERE
                / "plans"
                / "guarded-preflight-mismatch-confirmed.md"
            )
            confirmed = parse_plan(source, expectation=False)
            plan_input = (
                candidate_root
                / ".git"
                / "bridge-fixture-fault-confirmed-input.md"
            )
            plan_input.write_bytes(
                _confirmed_plan_bytes(
                    confirmed, candidate_marker["baseline_commit"]
                )
            )
            return (
                candidate_root,
                materialized["lease"],
                candidate_marker,
                plan_input,
            )
        except Exception:
            if candidate_root.exists():
                cleanup_leased_project(
                    candidate_root,
                    suite=SUITE,
                    scenario=scenario_id,
                    lease=materialized["lease"],
                )
            raise

    def arm(
        candidate_root: Path,
        candidate_lease: str,
        candidate_plan: Path,
        operation_id: str,
    ) -> Dict[str, Any]:
        return _run_harness_subprocess(
            [
                "arm-fault",
                replay_id,
                str(candidate_root),
                "--lease",
                candidate_lease,
                "--plan",
                str(candidate_plan),
                "--operation-id",
                operation_id,
            ],
            expect_success=True,
        )

    def seed_valid_claim(
        candidate_root: Path,
        candidate_lease: str,
    ) -> Tuple[Mapping[str, Any], Mapping[str, Any]]:
        paths = _phase_paths(candidate_root)
        with RetainedRootDirectory(paths["plan"].parent) as store:
            armed, _, armed_evidence, _ = _read_phase_receipt_store(
                store,
                paths["armed"].name,
                lease=candidate_lease,
                state="confirmed-awaiting-final-preflight",
                label="seeded fault armed receipt",
            )
            claim = _phase_receipt(
                lease=candidate_lease,
                state="injecting",
                binding={
                    **copy.deepcopy(armed["binding"]),
                    "armed_receipt": armed_evidence,
                    "claim_nonce": "simulated-valid-claim-nonce",
                },
            )
            _, _, claim_evidence, _ = _write_phase_receipt_store(
                store,
                paths["claim"].name,
                claim,
                lease=candidate_lease,
                label="seeded valid fault claim",
            )
        return armed["binding"], claim_evidence

    checks = 0
    root, lease, _, plan_input = materialize_bound()
    operation_id = "fault-operation-plan-single-snapshot-v1"
    original_parser = parse_plan
    original_plan_bytes = plan_input.read_bytes()
    drifted = False

    def parse_after_source_drift(
        path: Path, *, expectation: bool
    ) -> Plan:
        nonlocal drifted
        if not drifted and path.name == "captured-plan.md":
            plan_input.write_bytes(original_plan_bytes + b"\n")
            drifted = True
        return original_parser(path, expectation=expectation)

    try:
        globals()["parse_plan"] = parse_after_source_drift
        result = _arm_bound_fault(
            root,
            lease=lease,
            replay_id=replay_id,
            plan_path=plan_input,
            operation_id=operation_id,
        )
        globals()["parse_plan"] = original_parser
        plan_snapshot = inspect_root_child(
            _phase_paths(root)["plan"].parent,
            _phase_paths(root)["plan"].name,
        )
        if (
            not drifted
            or result["plan_sha256"] != _sha256(original_plan_bytes)
            or plan_snapshot["bytes"] != original_plan_bytes
            or plan_input.read_bytes() == original_plan_bytes
        ):
            raise FixtureError(
                "fault arm did not retain one exact plan snapshot"
            )
        checks += 1
    finally:
        globals()["parse_plan"] = original_parser
        if root.exists():
            cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=lease,
            )

    root, lease, _, plan_input = materialize_bound()
    operation_id = "fault-operation-plan-tamper-v1"
    try:
        _run_harness_subprocess(
            [
                "arm-fault",
                replay_id,
                str(root),
                "--lease",
                lease,
                "--plan",
                str(plan_input),
                "--operation-id",
                operation_id,
            ],
            expect_success=True,
        )
        snapshot_path = _phase_paths(root)["plan"]
        snapshot_path.write_bytes(snapshot_path.read_bytes() + b"\n")
        _run_harness_subprocess(
            [
                "apply-fault",
                replay_id,
                str(root),
                "--lease",
                lease,
                "--operation-id",
                operation_id,
            ],
            expect_success=False,
        )
        if (
            _phase_paths(root)["claim"].exists()
            or compare_tree(root, parsed["input"])
        ):
            raise FixtureError(
                "plan-tamper refusal was not fail-closed before claim"
            )
        checks += 2
    finally:
        if root.exists():
            cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=lease,
            )
    root, lease, _, plan_input = materialize_bound()
    operation_id = "fault-operation-claim-crash-v1"
    try:
        _run_harness_subprocess(
            [
                "arm-fault",
                replay_id,
                str(root),
                "--lease",
                lease,
                "--plan",
                str(plan_input),
                "--operation-id",
                operation_id,
            ],
            expect_success=True,
        )
        paths = _phase_paths(root)
        armed, armed_sha256 = _read_phase_receipt(
            paths["armed"],
            lease=lease,
            state="confirmed-awaiting-final-preflight",
            label="fault armed receipt",
        )
        claim = _phase_receipt(
            lease=lease,
            state="injecting",
            binding={
                **copy.deepcopy(armed["binding"]),
                "armed_receipt_sha256": armed_sha256,
                "claim_nonce": "simulated-claim-crash-nonce",
            },
        )
        _write_phase_receipt(
            paths["claim"],
            claim,
            lease=lease,
            label="simulated fault claim",
        )
        _run_harness_subprocess(
            [
                "apply-fault",
                replay_id,
                str(root),
                "--lease",
                lease,
                "--operation-id",
                operation_id,
            ],
            expect_success=False,
        )
        if (
            paths["injected"].exists()
            or compare_tree(root, parsed["input"])
        ):
            raise FixtureError(
                "claim-crash refusal did not preserve exact input"
            )
        checks += 2
    finally:
        if root.exists():
            cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=lease,
            )

    root, lease, _, plan_input = materialize_bound()
    operation_id = "fault-operation-receipt-swap-v1"
    try:
        arm(root, lease, plan_input, operation_id)
        paths = _phase_paths(root)
        before = inspect_root_child(
            paths["armed"].parent, paths["armed"].name
        )
        replacement = paths["armed"].with_name(
            "bridge-fixture-fault-armed-replacement.tmp"
        )
        replacement.write_bytes(before["bytes"])
        os.replace(replacement, paths["armed"])
        after = inspect_root_child(
            paths["armed"].parent, paths["armed"].name
        )
        if after["identity"] == before["identity"]:
            raise FixtureError(
                "same-byte receipt replacement retained its identity"
            )
        _run_harness_subprocess(
            [
                "apply-fault",
                replay_id,
                str(root),
                "--lease",
                lease,
                "--operation-id",
                operation_id,
            ],
            expect_success=False,
        )
        if paths["claim"].exists() or compare_tree(root, parsed["input"]):
            raise FixtureError(
                "same-byte receipt swap escaped before claim"
            )
        checks += 2
    finally:
        if root.exists():
            cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=lease,
            )

    root, lease, _, plan_input = materialize_bound()
    operation_id = "fault-operation-receipt-identity-v1"
    try:
        arm(root, lease, plan_input, operation_id)
        paths = _phase_paths(root)
        armed, _ = _read_phase_receipt(
            paths["armed"],
            lease=lease,
            state="confirmed-awaiting-final-preflight",
            label="identity-mismatch source receipt",
        )
        forged_file = copy.deepcopy(armed["file"])
        identity_key = sorted(forged_file["identity"])[0]
        forged_file["identity"][identity_key] = "0"
        forged = _phase_receipt(
            lease=lease,
            state=armed["state"],
            binding=armed["binding"],
            file_evidence=forged_file,
        )
        replacement = paths["armed"].with_name(
            "bridge-fixture-fault-armed-forged.tmp"
        )
        replacement.write_bytes(_canonical_json_bytes(forged))
        os.replace(replacement, paths["armed"])
        _run_harness_subprocess(
            [
                "apply-fault",
                replay_id,
                str(root),
                "--lease",
                lease,
                "--operation-id",
                operation_id,
            ],
            expect_success=False,
        )
        if paths["claim"].exists() or compare_tree(root, parsed["input"]):
            raise FixtureError(
                "receipt identity mismatch escaped before claim"
            )
        checks += 2
    finally:
        if root.exists():
            cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=lease,
            )

    root, lease, _, plan_input = materialize_bound()
    operation_id = "fault-operation-exclusive-conflict-v1"
    try:
        arm(root, lease, plan_input, operation_id)
        paths = _phase_paths(root)
        with RetainedRootDirectory(paths["armed"].parent) as store:
            before = store.read(paths["armed"].name)
            try:
                store.create(paths["armed"].name, b"replacement")
            except (FixtureError, OSError):
                pass
            else:
                raise FixtureError(
                    "retained phase store accepted an O_EXCL conflict"
                )
            after = store.read(paths["armed"].name)
        if _phase_chain_evidence(before) != _phase_chain_evidence(after):
            raise FixtureError("O_EXCL conflict changed the receipt")
        checks += 1
    finally:
        if root.exists():
            cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=lease,
            )

    root, lease, _, plan_input = materialize_bound()
    operation_id = "fault-operation-partial-publish-v1"
    try:
        paths = _phase_paths(root)
        with RetainedRootDirectory(paths["armed"].parent) as store:
            try:
                store.create_bound(
                    paths["armed"].name,
                    lambda _: (_ for _ in ()).throw(
                        FixtureError("simulated partial publish")
                    ),
                )
            except FixtureError:
                pass
            else:
                raise FixtureError(
                    "simulated partial publish unexpectedly completed"
                )
            if not store.exists(paths["armed"].name):
                raise FixtureError(
                    "partial publish did not leave fail-closed evidence"
                )
        _run_harness_subprocess(
            [
                "arm-fault",
                replay_id,
                str(root),
                "--lease",
                lease,
                "--plan",
                str(plan_input),
                "--operation-id",
                operation_id,
            ],
            expect_success=False,
        )
        if paths["plan"].exists() or compare_tree(root, parsed["input"]):
            raise FixtureError(
                "partial publish did not stop arm before plan/target"
            )
        checks += 2
    finally:
        if root.exists():
            cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=lease,
            )

    root, lease, _, plan_input = materialize_bound()
    operation_id = "fault-operation-claim-resume-preimage-v1"
    try:
        arm(root, lease, plan_input, operation_id)
        seed_valid_claim(root, lease)
        recovered = _run_harness_subprocess(
            [
                "apply-fault",
                replay_id,
                str(root),
                "--lease",
                lease,
                "--operation-id",
                operation_id,
            ],
            expect_success=True,
        )
        if (
            recovered.get("state") != "injected"
            or recovered.get("fixture_writes") != 1
            or not _phase_paths(root)["injected"].is_file()
        ):
            raise FixtureError(
                "valid claim + preimage did not resume injection"
            )
        checks += 2
    finally:
        if root.exists():
            cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=lease,
            )

    root, lease, _, plan_input = materialize_bound()
    operation_id = "fault-operation-claim-finalize-postimage-v1"
    try:
        arm(root, lease, plan_input, operation_id)
        binding, _ = seed_valid_claim(root, lease)
        envelope = _validate_blind_installed_replay_input(
            root,
            lease=lease,
            replay_id=replay_id,
            require_input_tree=True,
        )
        document = envelope["payload"]["fault_schedule"]["facts"]
        injected = document["injected"]
        target = inspect_root_child(root, binding["target"])
        replace_root_child(
            root,
            binding["target"],
            expected_root_identity=target["root_identity"],
            expected_identity=target["identity"],
            expected_mode=target["mode"],
            expected_bytes=target["bytes"],
            injected_bytes=base64.b64decode(
                injected["bytes_base64"], validate=True
            ),
            injected_mode=injected["mode"],
        )
        recovered = _run_harness_subprocess(
            [
                "apply-fault",
                replay_id,
                str(root),
                "--lease",
                lease,
                "--operation-id",
                operation_id,
            ],
            expect_success=True,
        )
        if (
            recovered.get("state") != "injected"
            or recovered.get("fixture_writes") != 0
            or not _phase_paths(root)["injected"].is_file()
        ):
            raise FixtureError(
                "valid claim + postimage did not finalize evidence"
            )
        checks += 2
    finally:
        if root.exists():
            cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=lease,
            )

    with tempfile.TemporaryDirectory(
        prefix="bridge-fault-parent-drift-",
        dir=os_temp_root(),
    ) as temporary:
        base = Path(temporary)
        phase = base / "phase"
        phase.mkdir()
        store = RetainedRootDirectory(phase)
        moved = base / "moved-phase"
        try:
            try:
                os.rename(phase, moved)
            except OSError:
                store.verify()
            else:
                phase.mkdir()
                try:
                    store.verify()
                except FixtureError:
                    pass
                else:
                    raise FixtureError(
                        "retained phase parent replacement was accepted"
                    )
            checks += 1
        finally:
            store.close()
            if moved.exists() and not phase.exists():
                os.rename(moved, phase)
    return checks


def _exercise_safe_adapter_adversarials() -> int:
    checks = 0

    def reject(label: str, operation: Any) -> None:
        nonlocal checks
        try:
            operation()
        except (FixtureError, OSError):
            checks += 1
        else:
            raise FixtureError(
                f"safe root-child adapter accepted adversarial {label}"
            )

    for value in (
        "./AGENTS.md",
        "a//b",
        "a/./b",
        "AGENTS.md/",
        "C:/outside",
        "AGENTS.md:stream",
        "CON",
        "NUL.txt",
        "COM1",
        "trailing.",
        "trailing ",
        "control\x01name",
        ".GiT/private",
    ):
        reject(
            f"path-{value!r}",
            lambda candidate=value: safe_relative(
                candidate, field="adapter adversarial"
            ),
        )
    with tempfile.TemporaryDirectory(
        prefix="bridge-safe-root-child-", dir=os_temp_root()
    ) as temporary:
        base = Path(temporary)
        root = base / "root"
        root.mkdir()
        target = root / "AGENTS.md"
        preimage = b"before\n"
        injected = b"after\n"
        target.write_bytes(preimage)
        if os.name != "nt":
            os.chmod(target, 0o644)
        initial = inspect_root_child(root, "AGENTS.md")
        for unsafe in (
            "AGENTS.md:stream",
            "CON",
            "NUL.txt",
            "COM1.log",
            "LPT9.md",
            "AGENTS.md.",
            "AGENTS.md ",
            "bad\x01name",
        ):
            reject(
                f"root-child-{unsafe!r}",
                lambda candidate=unsafe: inspect_root_child(
                    root, candidate
                ),
            )
        hardlink = root / "hardlink"
        os.link(target, hardlink)
        try:
            reject(
                "hardlink-inspect",
                lambda: inspect_root_child(root, "AGENTS.md"),
            )
        finally:
            os.unlink(hardlink)
        leaf_snapshot = inspect_root_child(root, "AGENTS.md")
        moved_leaf = root / "moved-AGENTS.md"
        target.replace(moved_leaf)
        target.write_bytes(preimage)
        if os.name != "nt":
            os.chmod(target, 0o644)
        try:
            if os.name == "nt":
                reject(
                    "leaf-identity-swap",
                    lambda: replace_root_child(
                        root,
                        "AGENTS.md",
                        expected_root_identity=leaf_snapshot[
                            "root_identity"
                        ],
                        expected_identity=leaf_snapshot["identity"],
                        expected_mode=leaf_snapshot["mode"],
                        expected_bytes=preimage,
                        injected_bytes=injected,
                        injected_mode="100644",
                    ),
                )
                if target.read_bytes() != preimage:
                    raise FixtureError(
                        "leaf identity rejection changed target bytes"
                    )
        finally:
            moved_leaf.unlink()
        root_snapshot = inspect_root_child(root, "AGENTS.md")
        old_root = base / "old-root"
        root.replace(old_root)
        root.mkdir()
        (old_root / "AGENTS.md").replace(root / "AGENTS.md")
        try:
            if os.name == "nt":
                reject(
                    "root-identity-swap",
                    lambda: replace_root_child(
                        root,
                        "AGENTS.md",
                        expected_root_identity=root_snapshot[
                            "root_identity"
                        ],
                        expected_identity=root_snapshot["identity"],
                        expected_mode=root_snapshot["mode"],
                        expected_bytes=preimage,
                        injected_bytes=injected,
                        injected_mode="100644",
                    ),
                )
                if (root / "AGENTS.md").read_bytes() != preimage:
                    raise FixtureError(
                        "root identity rejection changed target bytes"
                    )
        finally:
            old_root.rmdir()
        link_target = root / "real-AGENTS.md"
        (root / "AGENTS.md").replace(link_target)
        try:
            try:
                os.symlink(link_target.name, root / "AGENTS.md")
            except OSError:
                pass
            else:
                try:
                    reject(
                        "leaf-symlink",
                        lambda: inspect_root_child(
                            root, "AGENTS.md"
                        ),
                    )
                finally:
                    os.unlink(root / "AGENTS.md")
        finally:
            link_target.replace(root / "AGENTS.md")
        real_root = base / "real-root"
        real_root.mkdir()
        (real_root / "AGENTS.md").write_bytes(preimage)
        root_link = base / "root-link"
        try:
            try:
                os.symlink(real_root, root_link, target_is_directory=True)
            except OSError:
                pass
            else:
                try:
                    reject(
                        "root-reparse",
                        lambda: inspect_root_child(
                            root_link, "AGENTS.md"
                        ),
                    )
                finally:
                    os.unlink(root_link)
        finally:
            (real_root / "AGENTS.md").unlink()
            real_root.rmdir()
        positive = inspect_root_child(root, "AGENTS.md")
        if os.name == "nt":
            reject(
                "windows-mode-change",
                lambda: replace_root_child(
                    root,
                    "AGENTS.md",
                    expected_root_identity=positive["root_identity"],
                    expected_identity=positive["identity"],
                    expected_mode="100644",
                    expected_bytes=preimage,
                    injected_bytes=injected,
                    injected_mode="100755",
                ),
            )
            if (root / "AGENTS.md").read_bytes() != preimage:
                raise FixtureError(
                    "unsupported Windows mode change wrote target bytes"
                )
            observed = replace_root_child(
                root,
                "AGENTS.md",
                expected_root_identity=positive["root_identity"],
                expected_identity=positive["identity"],
                expected_mode="100644",
                expected_bytes=preimage,
                injected_bytes=injected,
                injected_mode="100644",
            )
            if (
                observed["mode"] != "100644"
                or observed["bytes"] != injected
                or observed["identity"] != positive["identity"]
            ):
                raise FixtureError(
                    "Windows same-mode retained mutation was not verified"
                )
            checks += 1
        else:
            reject(
                "posix-root-child-mutation-declarative-only",
                lambda: replace_root_child(
                    root,
                    "AGENTS.md",
                    expected_root_identity=positive["root_identity"],
                    expected_identity=positive["identity"],
                    expected_mode="100644",
                    expected_bytes=preimage,
                    injected_bytes=injected,
                    injected_mode="100644",
                ),
            )
            retained = inspect_root_child(root, "AGENTS.md")
            if retained != positive:
                raise FixtureError(
                    "POSIX declarative-only refusal changed retained read state"
                )
            checks += 1
    return checks


def _exercise_stale_recovery_adversarials() -> Dict[str, Any]:
    if os.name != "nt":
        if windows_root_quarantine_capability()["available"]:
            raise FixtureError(
                "stale recovery platform capability is inconsistent"
            )
        return {
            "checks": 1,
            "cases": ["platform-fail-closed"],
            "capability": windows_root_quarantine_capability(),
        }

    scenario_id = "active-import"
    _, parsed = _scenario(scenario_id)
    replay_input = parsed["replay_inputs"][scenario_id]
    checks = 0
    cases: List[str] = []
    sibling = os_temp_root() / (
        f"bridge-{SUITE}-recovery-sibling-"
        + secrets.token_urlsafe(12)
    )
    sibling.mkdir()

    def checked(name: str) -> None:
        nonlocal checks
        if not sibling.is_dir():
            raise FixtureError(
                f"stale recovery enumerated/deleted sibling in {name}"
            )
        checks += 1
        cases.append(name)

    def fixture(*, extended: bool) -> Dict[str, Any]:
        materialized = create_temp_git_project(
            suite=SUITE,
            scenario=scenario_id,
            baseline=parsed["baseline"],
            input_tree=parsed["input"],
        )
        root = Path(materialized["worktree"])
        try:
            if extended:
                _install_activation_profile(
                    root, parsed["activation_profile"]
                )
                _install_replay_input(
                    root,
                    lease=materialized["lease"],
                    scenario_id=scenario_id,
                    parsed=parsed,
                    replay_input=replay_input,
                )
            marker = root / ".git" / MARKER_NAME
            raw = marker.read_bytes()
            return {
                **materialized,
                "root": root,
                "marker": marker,
                "raw": raw,
                "sha256": _sha256(raw),
                "nonce": root.name[
                    len(f"bridge-{SUITE}-{scenario_id}-") :
                ],
            }
        except Exception:
            cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=materialized["lease"],
            )
            raise

    def stale_arguments(
        item: Mapping[str, Any],
        *,
        scenario: Optional[str] = None,
        root: Optional[str] = None,
        marker_sha256: Optional[str] = None,
        nonce: Optional[str] = None,
    ) -> List[str]:
        return [
            "cleanup-stale",
            scenario or scenario_id,
            root or str(item["root"]),
            "--marker-sha256",
            marker_sha256 or str(item["sha256"]),
            "--nonce",
            nonce or str(item["nonce"]),
            "--acknowledge-lost-lease",
            "--acknowledge-no-active-external-operation",
        ]

    def reject(
        name: str,
        item: Mapping[str, Any],
        **overrides: Any,
    ) -> Dict[str, Any]:
        output = _run_harness_subprocess(
            stale_arguments(item, **overrides),
            expect_success=False,
        )
        if not Path(item["root"]).is_dir():
            raise FixtureError(
                f"stale recovery rejection removed root in {name}"
            )
        checked(name)
        return output

    def cleanup_fixture(item: Mapping[str, Any]) -> None:
        root = Path(item["root"])
        if root.exists():
            cleanup_leased_project(
                root,
                suite=SUITE,
                scenario=scenario_id,
                lease=str(item["lease"]),
            )

    try:
        standard = fixture(extended=False)
        try:
            root = standard["root"]
            marker = standard["marker"]
            raw = standard["raw"]
            reject(
                "wrong-marker-hash",
                standard,
                marker_sha256=("0" * 64),
            )
            reject(
                "wrong-nonce",
                standard,
                nonce="WrongNonce88",
            )
            reject(
                "wrong-scenario",
                standard,
                scenario="budget-boundary",
            )
            reject(
                "noncanonical-root",
                standard,
                root=str(root) + "\\.",
            )
            _run_harness_subprocess(
                stale_arguments(
                    standard,
                    root=str(REPO_ROOT),
                ),
                expect_success=False,
            )
            checked("non-temp-root")

            for field, value in (
                ("acknowledge_lost_lease", False),
                (
                    "acknowledge_no_active_external_operation",
                    False,
                ),
            ):
                arguments = {
                    "scenario": scenario_id,
                    "raw_root": str(root),
                    "marker_sha256": standard["sha256"],
                    "nonce": standard["nonce"],
                    "acknowledge_lost_lease": True,
                    "acknowledge_no_active_external_operation": True,
                }
                arguments[field] = value
                try:
                    _cleanup_stale_exact(**arguments)
                except FixtureError:
                    pass
                else:
                    raise FixtureError(
                        f"stale recovery accepted false {field}"
                    )
                if not root.is_dir():
                    raise FixtureError(
                        f"false {field} removed stale root"
                    )
                checked(f"wrong-attestation-{field}")

            original_marker = _closed_json_object(
                raw, label="stale test marker"
            )
            marker_variants = {
                "marker-extra-field": {
                    **original_marker,
                    "unexpected": "closed-set-violation",
                },
                "marker-missing-field": {
                    key: value
                    for key, value in original_marker.items()
                    if key != "spec"
                },
            }
            for name, value in marker_variants.items():
                candidate = _pretty_marker_bytes(value)
                marker.write_bytes(candidate)
                try:
                    reject(
                        name,
                        {
                            **standard,
                            "sha256": _sha256(candidate),
                        },
                    )
                finally:
                    marker.write_bytes(raw)
            compact = _canonical_json_bytes(original_marker)
            marker.write_bytes(compact)
            try:
                reject(
                    "marker-noncanonical",
                    {
                        **standard,
                        "sha256": _sha256(compact),
                    },
                )
            finally:
                marker.write_bytes(raw)
            numeric_hash_marker = copy.deepcopy(original_marker)
            numeric_hash_marker["lease_sha256"] = int("1" * 64)
            numeric_hash_raw = _pretty_marker_bytes(
                numeric_hash_marker
            )
            marker.write_bytes(numeric_hash_raw)
            try:
                reject(
                    "marker-numeric-hash",
                    {
                        **standard,
                        "sha256": _sha256(numeric_hash_raw),
                    },
                )
            finally:
                marker.write_bytes(raw)
            duplicate = (
                b'{"spec":"bridge-fixture-marker/v1",'
                b'"spec":"bridge-fixture-marker/v1"}'
            )
            marker.write_bytes(duplicate)
            try:
                reject(
                    "marker-duplicate-key",
                    {
                        **standard,
                        "sha256": _sha256(duplicate),
                    },
                )
            finally:
                marker.write_bytes(raw)
            wrong_root_marker = copy.deepcopy(original_marker)
            wrong_root_marker["resolved_root"] = str(
                os_temp_root()
                / (
                    f"bridge-{SUITE}-{scenario_id}-"
                    + secrets.token_urlsafe(12)
                )
            )
            wrong_root_raw = _pretty_marker_bytes(
                wrong_root_marker
            )
            marker.write_bytes(wrong_root_raw)
            try:
                reject(
                    "marker-wrong-root",
                    {
                        **standard,
                        "sha256": _sha256(wrong_root_raw),
                    },
                )
            finally:
                marker.write_bytes(raw)

            phase_targets = [
                *_phase_paths(root).values(),
                root / ".git" / "journal.json",
                root / ".git" / "index.lock",
            ]
            for target in phase_targets:
                target.write_bytes(b"active\n")
                try:
                    reject(
                        f"active-{target.name}",
                        standard,
                    )
                finally:
                    target.unlink()
            fake_claim = _recovery_claim_path(root)
            fake_claim.write_bytes(b"existing recovery claim\n")
            try:
                reject("active-recovery-claim", standard)
            finally:
                fake_claim.unlink()

            hardlink = root / "stale-hardlink-probe"
            os.link(root / "AGENTS.md", hardlink)
            try:
                reject("hardlink-entry", standard)
            finally:
                hardlink.unlink()
            symlink = root / "stale-symlink-probe"
            os.symlink(root / "AGENTS.md", symlink)
            try:
                reject("symlink-reparse-entry", standard)
            finally:
                symlink.unlink()

            alternates = (
                root / ".git" / "objects" / "info" / "alternates"
            )
            alternates.write_bytes(
                b"C:\\definitely-not-a-fixture-object-store\n"
            )
            try:
                reject("git-alternates", standard)
            finally:
                alternates.unlink()

            nested_bare = root / "cache.git"
            (nested_bare / "objects").mkdir(parents=True)
            (nested_bare / "refs").mkdir()
            (nested_bare / "HEAD").write_bytes(
                b"ref: refs/heads/main\n"
            )
            try:
                reject("nested-bare-git", standard)
            finally:
                strict_remove_tree(nested_bare)

            git_run(
                root,
                "commit",
                "--quiet",
                "--allow-empty",
                "-m",
                "stale recovery head drift",
            )
            try:
                reject("head-drift", standard)
            finally:
                git_run(
                    root,
                    "update-ref",
                    "HEAD",
                    str(standard["baseline_commit"]),
                )

            os.chmod(root, 0o444)
            positive = _run_harness_subprocess(
                stale_arguments(standard),
                expect_success=True,
            )
            if (
                positive.get("contract") != STALE_RECOVERY_SPEC
                or positive.get("state") != "closed"
                or positive.get("marker_kind") != "base"
                or positive.get("recoverable") is not False
                or positive.get("siblings_enumerated") is not False
                or root.exists()
                or os.path.lexists(positive["tombstone"])
            ):
                raise FixtureError(
                    f"base stale recovery contract drifted: {positive}"
                )
            if (
                not positive["quarantine_capability"][
                    "descendant_handles_retained"
                ]
                or not positive["deletion_evidence"][
                    "handle_bound"
                ]
            ):
                raise FixtureError(
                    "readonly-root handle cleanup lacked pinned evidence"
                )
            checked("readonly-root-handle-clear")
            checked("base-positive")
        finally:
            cleanup_fixture(standard)

        extended = fixture(extended=True)
        try:
            root = extended["root"]
            fake_claim = _recovery_claim_path(root)
            fake_claim.write_bytes(b"entry gate\n")
            try:
                entry_calls = [
                    [
                        "replay-input",
                        scenario_id,
                        str(root),
                        "--lease",
                        extended["lease"],
                    ],
                    [
                        "arm-fault",
                        scenario_id,
                        str(root),
                        "--lease",
                        extended["lease"],
                        "--plan",
                        str(extended["marker"]),
                        "--operation-id",
                        "recovery-gate-operation",
                    ],
                    [
                        "apply-fault",
                        scenario_id,
                        str(root),
                        "--lease",
                        extended["lease"],
                        "--operation-id",
                        "recovery-gate-operation",
                    ],
                ]
                for index, arguments in enumerate(entry_calls):
                    _run_harness_subprocess(
                        arguments, expect_success=False
                    )
                    checked(f"claim-entry-gate-{index}")
                try:
                    _allocate_journal_path(
                        root, "recovery-gate-operation"
                    )
                except FixtureError:
                    pass
                else:
                    raise FixtureError(
                        "journal allocation ignored recovery claim"
                    )
                checked("claim-journal-gate")
            finally:
                fake_claim.unlink()
            positive = _run_harness_subprocess(
                stale_arguments(extended),
                expect_success=True,
            )
            if (
                positive.get("marker_kind") != "extended"
                or positive.get("state") != "closed"
                or root.exists()
                or os.path.lexists(positive["tombstone"])
            ):
                raise FixtureError(
                    f"extended stale recovery drifted: {positive}"
                )
            checked("extended-positive")
        finally:
            cleanup_fixture(extended)

        collision = fixture(extended=False)
        collision_name = (
            f"bridge-{SUITE}-recovery-tombstone-"
            + secrets.token_urlsafe(24)
        )
        collision_path = os_temp_root() / collision_name
        collision_path.mkdir()
        try:
            try:
                _cleanup_stale_exact(
                    scenario=scenario_id,
                    raw_root=str(collision["root"]),
                    marker_sha256=collision["sha256"],
                    nonce=collision["nonce"],
                    acknowledge_lost_lease=True,
                    acknowledge_no_active_external_operation=True,
                    tombstone_name=collision_name,
                )
            except FixtureError:
                pass
            else:
                raise FixtureError(
                    "stale recovery replaced tombstone collision"
                )
            if (
                not collision["root"].is_dir()
                or not collision_path.is_dir()
            ):
                raise FixtureError(
                    "tombstone collision changed exact roots"
                )
            checked("tombstone-collision")
        finally:
            if collision_path.exists():
                os.rmdir(collision_path)
            cleanup_fixture(collision)

        rename_postverify = fixture(extended=False)
        rename_postverify_tombstone: Optional[Path] = None

        def fail_after_handle_rename(_: Path, __: Path) -> None:
            raise FixtureError(
                "injected handle-rename postverify failure"
            )

        try:
            try:
                _cleanup_stale_exact(
                    scenario=scenario_id,
                    raw_root=str(rename_postverify["root"]),
                    marker_sha256=rename_postverify["sha256"],
                    nonce=rename_postverify["nonce"],
                    acknowledge_lost_lease=True,
                    acknowledge_no_active_external_operation=True,
                    after_handle_rename=fail_after_handle_rename,
                )
            except _QuarantinedCleanupError as error:
                rename_postverify_tombstone = Path(
                    error.result["tombstone"]
                )
                if (
                    error.result["state"] != "quarantined"
                    or error.result["partial_deletion"]
                    or error.result["recoverable"] is not False
                ):
                    raise FixtureError(
                        "rename postverify structured state drifted"
                    )
            if (
                rename_postverify_tombstone is None
                or not rename_postverify_tombstone.is_dir()
                or rename_postverify["root"].exists()
            ):
                raise FixtureError(
                    "rename postverify failure lost tombstone context"
                )
            checked("quarantined-schema-after-handle-rename")
        finally:
            if (
                rename_postverify_tombstone is not None
                and rename_postverify_tombstone.exists()
            ):
                strict_remove_tree(rename_postverify_tombstone)

        replacement = fixture(extended=False)
        holding = os_temp_root() / (
            "bridge-m3-rules-recovery-held-"
            + secrets.token_urlsafe(18)
        )

        def replace_before_quarantine(root: Path) -> None:
            os.rename(root, holding)
            root.mkdir()

        try:
            try:
                _cleanup_stale_exact(
                    scenario=scenario_id,
                    raw_root=str(replacement["root"]),
                    marker_sha256=replacement["sha256"],
                    nonce=replacement["nonce"],
                    acknowledge_lost_lease=True,
                    acknowledge_no_active_external_operation=True,
                    before_quarantine=replace_before_quarantine,
                )
            except FixtureError:
                pass
            else:
                raise FixtureError(
                    "stale recovery accepted root replacement"
                )
            if (
                not replacement["root"].is_dir()
                or not holding.is_dir()
            ):
                raise FixtureError(
                    "root replacement refusal lost an exact tree"
                )
            checked("root-path-identity-replacement")
        finally:
            if replacement["root"].exists():
                os.rmdir(replacement["root"])
            if holding.exists():
                os.rename(holding, replacement["root"])
                claim = _recovery_claim_path(replacement["root"])
                if claim.exists():
                    claim.unlink()
            cleanup_fixture(replacement)

        recreated = fixture(extended=False)

        def recreate_old_name(
            original: Path, _: Path
        ) -> None:
            original.mkdir()

        try:
            error: Optional[_QuarantinedCleanupError] = None
            try:
                _cleanup_stale_exact(
                    scenario=scenario_id,
                    raw_root=str(recreated["root"]),
                    marker_sha256=recreated["sha256"],
                    nonce=recreated["nonce"],
                    acknowledge_lost_lease=True,
                    acknowledge_no_active_external_operation=True,
                    after_quarantine=recreate_old_name,
                )
            except _QuarantinedCleanupError as caught:
                error = caught
            if (
                error is None
                or not recreated["root"].is_dir()
                or os.path.lexists(error.result["tombstone"])
            ):
                raise FixtureError(
                    "old-name recreation was not preserved/refused"
                )
            checked("old-name-recreation")
        finally:
            if recreated["root"].exists():
                os.rmdir(recreated["root"])

        quarantined_fixture = fixture(extended=False)

        def fail_cleanup(*_: Any, **__: Any) -> None:
            raise FixtureError("injected tombstone cleanup failure")

        tombstone: Optional[Path] = None
        quarantined_error: Optional[_QuarantinedCleanupError] = None
        try:
            try:
                _cleanup_stale_exact(
                    scenario=scenario_id,
                    raw_root=str(quarantined_fixture["root"]),
                    marker_sha256=quarantined_fixture["sha256"],
                    nonce=quarantined_fixture["nonce"],
                    acknowledge_lost_lease=True,
                    acknowledge_no_active_external_operation=True,
                    cleanup=fail_cleanup,
                )
            except _QuarantinedCleanupError as error:
                quarantined_error = error
                tombstone = Path(error.result["tombstone"])
            if (
                tombstone is None
                or quarantined_fixture["root"].exists()
                or not tombstone.is_dir()
                or quarantined_error is None
                or quarantined_error.result["state"]
                != "quarantined"
                or quarantined_error.result["recoverable"] is not False
                or quarantined_error.result["partial_deletion"]
            ):
                raise FixtureError(
                    "quarantined failure schema/retention drifted"
                )
            checked("quarantined-schema-retains-tombstone")
        finally:
            if tombstone is not None and tombstone.exists():
                strict_remove_tree(tombstone)

        partial_fixture = fixture(extended=False)
        partial_tombstone: Optional[Path] = None
        partial_error: Optional[_QuarantinedCleanupError] = None

        def fail_after_first_disposition(
            _: str, count: int
        ) -> None:
            if count == 1:
                raise FixtureError(
                    "injected failure after first handle disposition"
                )

        try:
            try:
                _cleanup_stale_exact(
                    scenario=scenario_id,
                    raw_root=str(partial_fixture["root"]),
                    marker_sha256=partial_fixture["sha256"],
                    nonce=partial_fixture["nonce"],
                    acknowledge_lost_lease=True,
                    acknowledge_no_active_external_operation=True,
                    after_disposition=(
                        fail_after_first_disposition
                    ),
                )
            except _QuarantinedCleanupError as error:
                partial_error = error
                partial_tombstone = Path(
                    error.result["tombstone"]
                )
            if (
                partial_error is None
                or partial_tombstone is None
                or not partial_tombstone.is_dir()
                or partial_error.result["state"] != "partial"
                or partial_error.result["recoverable"] is not False
                or not partial_error.result["partial_deletion"]
                or len(partial_error.result["removed_entries"]) != 1
            ):
                raise FixtureError(
                    "partial handle disposition schema drifted"
                )
            checked("partial-schema-after-handle-disposition")
        finally:
            if (
                partial_tombstone is not None
                and partial_tombstone.exists()
            ):
                strict_remove_tree(partial_tombstone)

        new_child_fixture = fixture(extended=False)
        new_child_tombstone: Optional[Path] = None

        def add_after_pin(root: Path, _: Any) -> None:
            (root / "unexpected-after-pin.txt").write_bytes(
                b"new child\n"
            )

        try:
            try:
                _cleanup_stale_exact(
                    scenario=scenario_id,
                    raw_root=str(new_child_fixture["root"]),
                    marker_sha256=new_child_fixture["sha256"],
                    nonce=new_child_fixture["nonce"],
                    acknowledge_lost_lease=True,
                    acknowledge_no_active_external_operation=True,
                    after_pin=add_after_pin,
                )
            except _QuarantinedCleanupError as error:
                new_child_tombstone = Path(
                    error.result["tombstone"]
                )
                if (
                    error.result["state"] != "quarantined"
                    or error.result["partial_deletion"]
                ):
                    raise FixtureError(
                        "new-child refusal reported wrong state"
                    )
            if (
                new_child_tombstone is None
                or not new_child_tombstone.is_dir()
            ):
                raise FixtureError(
                    "new child after pin was not retained/refused"
                )
            checked("pinned-new-child-refusal")
        finally:
            if (
                new_child_tombstone is not None
                and new_child_tombstone.exists()
            ):
                strict_remove_tree(new_child_tombstone)

        swap_fixture = fixture(extended=False)
        swap_tombstone: Optional[Path] = None
        swap_donor = os_temp_root() / (
            "bridge-m3-rules-recovery-swap-donor-"
            + secrets.token_urlsafe(18)
        )
        swap_donor.write_bytes(b"replacement\n")

        def swap_after_pin(root: Path, _: Any) -> None:
            os.replace(swap_donor, root / "AGENTS.md")

        try:
            try:
                _cleanup_stale_exact(
                    scenario=scenario_id,
                    raw_root=str(swap_fixture["root"]),
                    marker_sha256=swap_fixture["sha256"],
                    nonce=swap_fixture["nonce"],
                    acknowledge_lost_lease=True,
                    acknowledge_no_active_external_operation=True,
                    after_pin=swap_after_pin,
                )
            except _QuarantinedCleanupError as error:
                swap_tombstone = Path(error.result["tombstone"])
                if (
                    error.result["state"] != "quarantined"
                    or error.result["partial_deletion"]
                ):
                    raise FixtureError(
                        "same-name swap refusal reported wrong state"
                    )
            if swap_tombstone is None or not swap_tombstone.is_dir():
                raise FixtureError(
                    "pinned same-name swap did not fail closed"
                )
            checked("pinned-same-name-swap-refusal")
        finally:
            if swap_donor.exists():
                swap_donor.unlink()
            if swap_tombstone is not None and swap_tombstone.exists():
                strict_remove_tree(swap_tombstone)

        held_fixture = fixture(extended=False)
        held_tombstone: Optional[Path] = None
        held_stream: Optional[Any] = None

        def hold_after_quarantine(_: Path, root: Path) -> None:
            nonlocal held_stream
            held_stream = (root / "AGENTS.md").open("rb")

        try:
            try:
                _cleanup_stale_exact(
                    scenario=scenario_id,
                    raw_root=str(held_fixture["root"]),
                    marker_sha256=held_fixture["sha256"],
                    nonce=held_fixture["nonce"],
                    acknowledge_lost_lease=True,
                    acknowledge_no_active_external_operation=True,
                    after_quarantine=hold_after_quarantine,
                )
            except _QuarantinedCleanupError as error:
                held_tombstone = Path(error.result["tombstone"])
                if (
                    error.result["state"] != "quarantined"
                    or error.result["partial_deletion"]
                ):
                    raise FixtureError(
                        "held-handle refusal reported wrong state"
                    )
            if held_tombstone is None or not held_tombstone.is_dir():
                raise FixtureError(
                    "held descendant handle did not retain tombstone"
                )
            checked("held-descendant-handle-refusal")
        finally:
            if held_stream is not None:
                held_stream.close()
            if held_tombstone is not None and held_tombstone.exists():
                strict_remove_tree(held_tombstone)

        reparse_fixture = fixture(extended=False)
        reparse_root = reparse_fixture["root"]
        reparse_holding = os_temp_root() / (
            "bridge-m3-rules-recovery-reparse-held-"
            + secrets.token_urlsafe(18)
        )
        try:
            os.rename(reparse_root, reparse_holding)
            try:
                os.symlink(
                    reparse_holding,
                    reparse_root,
                    target_is_directory=True,
                )
            except Exception:
                os.rename(reparse_holding, reparse_root)
                raise
            reject("root-reparse", reparse_fixture)
        finally:
            if os.path.lexists(reparse_root):
                status = os.lstat(reparse_root)
                if stat.S_ISLNK(status.st_mode) or is_reparse(
                    reparse_root
                ):
                    os.rmdir(reparse_root)
            if reparse_holding.exists():
                os.rename(reparse_holding, reparse_root)
            cleanup_fixture(reparse_fixture)

        capability = windows_root_quarantine_capability()
        if (
            capability["contract"]
            != "windows-root-handle-quarantine/v1"
            or not capability["available"]
            or not capability[
                "root_handle_retained_through_cleanup"
            ]
            or capability["root_handle_share_delete"] is not False
            or not capability["descendant_handles_retained"]
            or not capability["descendant_handle_delete_access"]
            or capability["descendant_handle_share_delete"] is not False
        ):
            raise FixtureError(
                f"stale recovery capability drifted: {capability}"
            )
        checked("windows-handle-capability")
    finally:
        if sibling.exists():
            os.rmdir(sibling)
    return {
        "checks": checks,
        "cases": cases,
        "capability": windows_root_quarantine_capability(),
        "contract": STALE_RECOVERY_SPEC,
    }


def run_self_test() -> Dict[str, Any]:
    _validate_covenant_assets()
    matrix, scenarios = validate_matrix()
    journal_result = _run_journal_v2_suite()
    scenario_count = len(scenarios)
    expectation_count = sum(
        len(item["expectations"]) for item in scenarios.values()
    )
    replay_counts = {
        mode: sum(
            item["definition"]["replay"] == mode
            for item in scenarios.values()
        )
        for mode in sorted(REPLAY_MODES)
    }
    fault_capability = root_child_capability()
    adapter_checks = _exercise_safe_adapter_adversarials()
    stale_recovery = _exercise_stale_recovery_adversarials()
    stale_recovery_checks = stale_recovery["checks"]
    journal_gate_checks = 1
    hook_section_checks = _exercise_hook_section_contract()
    checks = (
        1
        + _exercise_contract_adversarials()
        + _exercise_public_tier_contract()
        + hook_section_checks
        + adapter_checks
        + stale_recovery_checks
        + journal_gate_checks
    )
    lease_refusal_checked = False
    formal_refusal_checked = False
    bundle_full_checked = False
    fault_bundle_checked = False
    diagnostic_checked = False
    for scenario_id, parsed in scenarios.items():
        for replay_input in parsed["replay_inputs"].values():
            materialized = create_temp_git_project(
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
                    None
                    if parsed["history"] is None
                    else parsed["history"]["head"]
                ),
            )
            root = Path(materialized["worktree"])
            lease = materialized["lease"]
            try:
                _install_activation_profile(
                    root, parsed["activation_profile"]
                )
                _install_replay_input(
                    root,
                    lease=lease,
                    scenario_id=scenario_id,
                    parsed=parsed,
                    replay_input=replay_input,
                )
                input_errors = compare_tree(root, parsed["input"])
                if input_errors:
                    raise FixtureError(
                        f"{scenario_id}: input materialization mismatch: "
                        + "; ".join(input_errors)
                    )
                marker = validate_marker(
                    root,
                    suite=SUITE,
                    scenario=scenario_id,
                    lease=lease,
                )
                envelope = _validate_installed_replay_input(
                    root,
                    lease=lease,
                    scenario_id=scenario_id,
                    parsed=parsed,
                    replay_input=replay_input,
                )
                blind_envelope = _validate_blind_installed_replay_input(
                    root,
                    lease=lease,
                    replay_id=replay_input["id"],
                    require_input_tree=True,
                )
                if blind_envelope != envelope:
                    raise FixtureError(
                        "blind and authoring replay validators disagree"
                    )
                exercise_full_bundle = not bundle_full_checked
                exercise_full_fault = (
                    blind_envelope["payload"]["fault_schedule"] is not None
                    and not fault_bundle_checked
                )
                checks += _exercise_replay_bundle_adversarials(
                    root,
                    lease=lease,
                    replay_id=replay_input["id"],
                    envelope=blind_envelope,
                    input_tree=parsed["input"],
                    full=exercise_full_bundle,
                    fault_full=exercise_full_fault,
                )
                bundle_full_checked = (
                    bundle_full_checked or exercise_full_bundle
                )
                fault_bundle_checked = (
                    fault_bundle_checked or exercise_full_fault
                )
                public_replay = _public_replay_dto(envelope)
                forbidden_public_keys = {
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

                def contains_forbidden_key(value: Any) -> bool:
                    if isinstance(value, dict):
                        return bool(
                            forbidden_public_keys & set(value)
                        ) or any(
                            contains_forbidden_key(item)
                            for item in value.values()
                        )
                    if isinstance(value, list):
                        return any(
                            contains_forbidden_key(item)
                            for item in value
                        )
                    return False

                tainted = copy.deepcopy(envelope)
                tainted["oracle"] = "outer"
                tainted["payload"]["profile"]["facts"][
                    "expected_plan_path"
                ] = "expectations/private.md"
                tainted["payload"]["binding"]["result_state"] = "applied"
                if _public_replay_dto(tainted) != public_replay:
                    raise FixtureError(
                        "public replay allowlist admitted injected fields"
                    )
                if contains_forbidden_key(public_replay):
                    raise FixtureError(
                        "self-test blind replay input leaked expectation material"
                    )
                checks += 8
                fault_executed = (
                    blind_envelope["payload"]["fault_schedule"] is not None
                )
                if fault_executed:
                    if fault_capability[
                        "same-mode-root-child-mutation"
                    ]:
                        checks += _exercise_fault_phase_subprocess(
                            root,
                            lease=lease,
                            replay_id=replay_input["id"],
                            marker=marker,
                        )
                    else:
                        checks += (
                            _exercise_declarative_fault_phase_subprocess(
                                root,
                                lease=lease,
                                replay_id=replay_input["id"],
                                marker=marker,
                            )
                        )
                fault_mutation_executed = (
                    fault_executed
                    and fault_capability[
                        "same-mode-root-child-mutation"
                    ]
                )
                if not lease_refusal_checked:
                    try:
                        cleanup_leased_project(
                            root,
                            suite=SUITE,
                            scenario=scenario_id,
                            lease="wrong-lease",
                        )
                    except FixtureError:
                        pass
                    else:
                        raise FixtureError(
                            "wrong lease unexpectedly authorized cleanup"
                        )
                    if not root.is_dir():
                        raise FixtureError(
                            "wrong-lease refusal removed the fixture"
                        )
                    lease_refusal_checked = True
                    checks += 1
                matching_expectations = [
                    item
                    for item in parsed["expectations"]
                    if item["replay_input"]["id"] == replay_input["id"]
                ]
                if not matching_expectations:
                    raise FixtureError(
                        f"{scenario_id}/{replay_input['id']}: replay input "
                        "has no expectation binding"
                    )
                for item in matching_expectations:
                    expectation = item["definition"]
                    if not fault_mutation_executed:
                        materialize_tree(root, item["tree"])
                    tree_errors = compare_tree(root, item["tree"])
                    if tree_errors:
                        raise FixtureError(
                            f"{scenario_id}/{expectation['id']}: expected tree "
                            "does not round-trip: " + "; ".join(tree_errors)
                        )
                    actual_path = (
                        root
                        / ".git"
                        / f"bridge-fixture-plan-{expectation['id']}.md"
                    )
                    actual_path.write_bytes(
                        _actual_plan_bytes(
                            item["plan"],
                            marker["baseline_commit"],
                            commit_refs=_resolved_commit_refs(
                                expectation,
                                baseline_commit=marker["baseline_commit"],
                                history_commits=marker.get(
                                    "history_commits"
                                ),
                            ),
                        )
                    )
                    actual = parse_plan(actual_path, expectation=False)
                    expected = bind_expected_baselines(
                        parsed["definition"],
                        expectation,
                        item["plan"],
                        initial_commit=marker["baseline_commit"],
                        history_commits=marker.get("history_commits"),
                    )
                    differences = compare_plans(expected, actual)
                    if differences:
                        raise FixtureError(
                            f"{scenario_id}/{expectation['id']}: plan "
                            "self-compare failed: " + "; ".join(differences)
                        )
                    lifecycle = (
                        (
                            "failed"
                            if fault_executed
                            else "verified"
                        )
                        if actual["headers"]["phase"] == "post-write"
                        else "prepared"
                    )
                    if fault_mutation_executed:
                        subprocess_validation = _run_harness_subprocess(
                            [
                                "validate-plan",
                                replay_input["id"],
                                str(root),
                                "--lease",
                                lease,
                                "--plan",
                                str(actual_path),
                                "--operation-lifecycle",
                                lifecycle,
                            ],
                            expect_success=True,
                        )
                        if subprocess_validation.get("pass") is not True:
                            raise FixtureError(
                                "new-process fault persistence validation "
                                "did not pass"
                            )
                        checks += 1
                    elif fault_executed:
                        subprocess_validation = _run_harness_subprocess(
                            [
                                "validate-plan",
                                replay_input["id"],
                                str(root),
                                "--lease",
                                lease,
                                "--plan",
                                str(actual_path),
                                "--operation-lifecycle",
                                lifecycle,
                            ],
                            expect_success=False,
                        )
                        if subprocess_validation.get("failures") != [
                            "fixture-attestation"
                        ]:
                            raise FixtureError(
                                "declarative-only POSIX fault result was not "
                                "rejected by the formal attestation gate"
                            )
                        checks += 1
                    validation = _validate_plan_result(
                        replay_input=replay_input["id"],
                        root=root,
                        lease=lease,
                        plan_path=actual_path,
                        lifecycle=lifecycle,
                    )
                    if fault_executed and not fault_mutation_executed:
                        if (
                            validation["contract"] != PLAN_VALIDATOR_SPEC
                            or validation["plan_sha256"]
                            != _sha256(actual_path.read_bytes())
                            or validation["context_sha256"] is None
                            or validation["pass"]
                            or validation["failures"]
                            != ["fixture-attestation"]
                        ):
                            raise FixtureError(
                                f"{scenario_id}/{expectation['id']}: "
                                "declarative-only fault gate drifted: "
                                f"{validation}"
                            )
                        checks += 1
                    else:
                        if (
                            validation["contract"] != PLAN_VALIDATOR_SPEC
                            or validation["plan_sha256"]
                            != _sha256(actual_path.read_bytes())
                            or validation["context_sha256"] is None
                            or not validation["pass"]
                            or validation["failures"]
                        ):
                            raise FixtureError(
                                f"{scenario_id}/{expectation['id']}: formal "
                                "validator rejected canonical plan: "
                                f"{validation}"
                            )
                        checks += 1
                        checks += _exercise_formal_plan_adversarials(
                            scenario_id,
                            expectation["id"],
                            replay_input=replay_input["id"],
                            root=root,
                            lease=lease,
                            plan_path=actual_path,
                            lifecycle=lifecycle,
                            marker=marker,
                        )
                    if (
                        scenario_id == "migration-v1-v3"
                        and expectation["id"] == "applied"
                    ):
                        checks += _exercise_plan_diagnostic_contract(
                            replay_input=replay_input["id"],
                            root=root,
                            lease=lease,
                            plan_path=actual_path,
                            lifecycle=lifecycle,
                        )
                        diagnostic_checked = True
                    if (
                        not formal_refusal_checked
                        and not (
                            fault_executed
                            and not fault_mutation_executed
                        )
                    ):
                        wrong_lifecycle = (
                            "verified"
                            if lifecycle == "prepared"
                            else "prepared"
                        )
                        refusal = _validate_plan_result(
                            replay_input=replay_input["id"],
                            root=root,
                            lease=lease,
                            plan_path=actual_path,
                            lifecycle=wrong_lifecycle,
                        )
                        if (
                            refusal["contract"] != PLAN_VALIDATOR_SPEC
                            or refusal["plan_sha256"]
                            != validation["plan_sha256"]
                            or refusal["context_sha256"]
                            == validation["context_sha256"]
                            or refusal["pass"]
                            or refusal["failures"] != ["phase-lifecycle"]
                        ):
                            raise FixtureError(
                                "formal validator failed to reject the "
                                "opposite operation lifecycle deterministically"
                            )
                        formal_refusal_checked = True
                        checks += 1
                    checks += 2
            finally:
                if root.exists():
                    cleanup_leased_project(
                        root,
                        suite=SUITE,
                        scenario=scenario_id,
                        lease=lease,
                    )
                    checks += 1
    if not diagnostic_checked:
        raise FixtureError(
            "migration plan diagnostic contract was not exercised"
        )
    check_accounting = {
        "adapter": adapter_checks,
        "hook_sections": hook_section_checks,
        "stale_recovery": stale_recovery_checks,
        "journal_suite_gate": journal_gate_checks,
        "other": (
            checks
            - adapter_checks
            - hook_section_checks
            - stale_recovery_checks
            - journal_gate_checks
        ),
    }
    if sum(check_accounting.values()) != checks:
        raise FixtureError("self-test check accounting is inconsistent")
    return {
        "pass": True,
        "spec": MATRIX_SPEC,
        "checks": checks,
        "check_accounting": check_accounting,
        "scenarios": scenario_count,
        "expectations": expectation_count,
        "coverage_tokens": len(matrix["required_coverage"]),
        "journal_cases": journal_result["cases"],
        "journal_result": journal_result["pass"],
        "journal_spec": journal_result["journal_spec"],
        "journal_validator_spec": journal_result["contract"],
        "validator_spec": PLAN_VALIDATOR_SPEC,
        "diagnostic_spec": PLAN_DIAGNOSTIC_SPEC,
        "adapter_negative_checks": adapter_checks,
        "hook_section_checks": hook_section_checks,
        "stale_recovery": stale_recovery,
        "fault_adapter_capability": fault_capability,
        "safeguards": len(matrix["required_safeguards"]),
        "replay": replay_counts,
        "workflow_executed": False,
        "replay_boundary": (
            "The harness validates declarations, leased materialization, "
            "expected trees, sync-plan/v3 shape, and the fixture-only "
            "guarded-preflight fault adapter. It never runs bridge-sync; "
            "an agent must run $bridge-sync for agent scenarios."
        ),
    }


def _scenario(
    scenario_id: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    _, scenarios = validate_matrix()
    try:
        return scenarios[scenario_id]["definition"], scenarios[scenario_id]
    except KeyError as error:
        raise FixtureError(f"unknown scenario {scenario_id!r}") from error


def _replay_input_by_id(
    replay_id: str,
) -> Tuple[str, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    _, scenarios = validate_matrix()
    matches = [
        (
            scenario_id,
            parsed["definition"],
            parsed,
            replay_input,
        )
        for scenario_id, parsed in scenarios.items()
        for candidate_id, replay_input in parsed["replay_inputs"].items()
        if candidate_id == replay_id
    ]
    if len(matches) != 1:
        raise FixtureError(
            f"expected one replay input {replay_id!r}, found {len(matches)}"
        )
    return matches[0]


def _expectation(
    parsed: Mapping[str, Any], expectation_id: str
) -> Mapping[str, Any]:
    matches = [
        item
        for item in parsed["expectations"]
        if item["definition"]["id"] == expectation_id
    ]
    if len(matches) != 1:
        raise FixtureError(
            f"expected one expectation {expectation_id!r}"
        )
    return matches[0]


def command_list(_: argparse.Namespace) -> int:
    _, scenarios = validate_matrix()
    _json_output(
        {
            "spec": MATRIX_SPEC,
            "fault_adapter_capability": root_child_capability(),
            "journal_cases": JOURNAL_CASE_COUNT,
            "journal_spec": JOURNAL_SPEC,
            "journal_validator_spec": JOURNAL_VALIDATOR_SPEC,
            "scenarios": [
                {
                    "id": scenario_id,
                    "summary": parsed["definition"]["summary"],
                    "replay": parsed["definition"]["replay"],
                    "replay_inputs": sorted(parsed["replay_inputs"]),
                    "safeguards": parsed["definition"]["safeguards"],
                }
                for scenario_id, parsed in scenarios.items()
            ],
        }
    )
    return 0


def command_self_test(_: argparse.Namespace) -> int:
    _json_output(run_self_test())
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
    result = create_temp_git_project(
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
            None
            if parsed["history"] is None
            else parsed["history"]["head"]
        ),
    )
    root = Path(result["worktree"])
    try:
        profile_path = _install_activation_profile(
            root, parsed["activation_profile"]
        )
        (
            capability_path,
            replay_path,
            fault_schedule_path,
            commitment_path,
        ) = _install_replay_input(
            root,
            lease=result["lease"],
            scenario_id=scenario_id,
            parsed=parsed,
            replay_input=replay_input,
        )
    except Exception:
        cleanup_leased_project(
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
                "spec": ACTIVATION_PROFILE_SPEC,
            },
            "write_capability": {
                "path": str(capability_path),
                "sha256": _sha256(capability_path.read_bytes()),
                "spec": WRITE_CAPABILITY_SPEC,
            },
            "fault_schedule": (
                None
                if fault_schedule_path is None
                else {
                    "path": str(fault_schedule_path),
                    "sha256": _sha256(
                        fault_schedule_path.read_bytes()
                    ),
                    "spec": FAULT_SCHEDULE_SPEC,
                }
            ),
            "replay_commitment": {
                "path": str(commitment_path),
                "sha256": _sha256(commitment_path.read_bytes()),
                "spec": REPLAY_COMMITMENT_SPEC,
            },
            "replay_input": arguments.replay_input,
            "replay_input_path": str(replay_path),
            "replay_input_sha256": _sha256(replay_path.read_bytes()),
            "scenario": scenario_id,
            "workflow_executed": False,
        }
    )
    _json_output(result)
    return 0


def _public_file_fact(fact: Mapping[str, Any]) -> Dict[str, Any]:
    if fact["type"] == "file":
        return {
            "path": fact["path"],
            "type": fact["type"],
            "mode": fact["mode"],
            "sha256": fact["sha256"],
            "bytes_base64": fact["bytes_base64"],
        }
    return {
        "path": fact["path"],
        "type": fact["type"],
        "target": fact["target"],
    }


def _public_render_operation(
    operation: Mapping[str, Any],
) -> Dict[str, Any]:
    if operation["operation"] == "delete":
        return {
            "operation": operation["operation"],
            "path": operation["path"],
        }
    return {
        "operation": operation["operation"],
        **_public_file_fact(operation),
    }


def _public_replay_dto(
    envelope: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build the public replay contract from a closed field allowlist."""

    payload = envelope["payload"]
    profile = payload["profile"]
    profile_facts = profile["facts"]
    capability = payload["capability"]
    capability_facts = capability["facts"]
    capability_binding = capability_facts["binding"]
    public_profiles = []
    for item in capability_facts["profiles"]:
        public_profiles.append(
            {
                "binding": item["binding"],
                "profile": item["profile"],
                "host": item["host"],
                "host_version": item["host_version"],
                "tool_surface": item["tool_surface"],
                "platform": item["platform"],
                "filesystem_assumptions": list(
                    item["filesystem_assumptions"]
                ),
                "attestations": [
                    {
                        "protocol": attestation["protocol"],
                        "proof": attestation["proof"],
                        "operations": list(attestation["operations"]),
                        "paths": list(attestation["paths"]),
                    }
                    for attestation in item["attestations"]
                ],
            }
        )
    public_operations = [
        {
            "closure": item["closure"],
            "path": item["path"],
            "operation": item["operation"],
            "protocol": item["protocol"],
            "binding": item["binding"],
            "inverse_protocol": item["inverse_protocol"],
            "inverse_binding": item["inverse_binding"],
        }
        for item in capability_facts["operations"]
    ]
    fault_wrapper = payload["fault_schedule"]
    public_fault: Optional[Dict[str, Any]] = None
    if fault_wrapper is not None:
        fault = fault_wrapper["facts"]
        fault_binding = fault["binding"]
        injected = fault["injected"]
        public_fault = {
            "version": fault_wrapper["version"],
            "sha256": fault_wrapper["sha256"],
            "facts": {
                "version": fault["version"],
                "binding": {
                    "marker_spec": fault_binding["marker_spec"],
                    "suite": fault_binding["suite"],
                    "scenario": fault_binding["scenario"],
                    "replay_input": fault_binding["replay_input"],
                    "resolved_root": fault_binding["resolved_root"],
                    "baseline_commit": fault_binding["baseline_commit"],
                    "lease_sha256": fault_binding["lease_sha256"],
                    "source_sha256": fault_binding["source_sha256"],
                },
                "phase": fault["phase"],
                "target": fault["target"],
                "expected_preimage_sha256": fault[
                    "expected_preimage_sha256"
                ],
                "injected": {
                    "type": injected["type"],
                    "mode": injected["mode"],
                    "sha256": injected["sha256"],
                    "bytes_base64": injected["bytes_base64"],
                },
                "persistence": fault["persistence"],
                "zero_bridge_write": fault["zero_bridge_write"],
            },
        }
    decision = payload["decision"]
    public_decision: Optional[Dict[str, Any]] = None
    if decision is not None:
        public_decision = {
            "version": decision["version"],
            "status": decision["status"],
            "motivation": decision["motivation"],
            "intent": decision["intent"],
            "authorized_closures": list(
                decision["authorized_closures"]
            ),
            "source_bindings": [
                {
                    "path": item["path"],
                    "sha256": item["sha256"],
                    "bytes_base64": item["bytes_base64"],
                }
                for item in decision["source_bindings"]
            ],
            "segments": [
                {
                    "id": item["id"],
                    "lines": item["lines"],
                    "disposition": item["disposition"],
                    "destination": item["destination"],
                    "decision": item["decision"],
                }
                for item in decision["segments"]
            ],
            "sha256": decision["sha256"],
        }
    binding = payload["binding"]
    return {
        "spec": REPLAY_INPUT_SPEC,
        "canonicalization": payload["canonicalization"],
        "commitment_sha256": envelope["commitment_sha256"],
        "binding": {
            "suite": binding["suite"],
            "scenario": binding["scenario"],
            "replay_input": binding["replay_input"],
            "resolved_root": binding["resolved_root"],
            "nonce": binding["nonce"],
            "lease_sha256": binding["lease_sha256"],
            "baseline_commit": binding["baseline_commit"],
            "head": binding["head"],
            "marker_identity_sha256": binding[
                "marker_identity_sha256"
            ],
            "input_tree_sha256": binding["input_tree_sha256"],
        },
        "profile": {
            "version": profile["version"],
            "sha256": profile["sha256"],
            "facts": {
                "version": profile_facts["version"],
                "root_markers": copy.deepcopy(
                    profile_facts["root_markers"]
                ),
                "fallback_filenames": copy.deepcopy(
                    profile_facts["fallback_filenames"]
                ),
                "project_doc_max_bytes": profile_facts[
                    "project_doc_max_bytes"
                ],
                "budget_source": profile_facts["budget_source"],
                "codex_project_trust": profile_facts[
                    "codex_project_trust"
                ],
                "codex_hooks_feature": profile_facts[
                    "codex_hooks_feature"
                ],
            },
        },
        "capability": {
            "version": capability["version"],
            "sha256": capability["sha256"],
            "facts": {
                "version": capability_facts["version"],
                "binding": {
                    "marker_spec": capability_binding["marker_spec"],
                    "suite": capability_binding["suite"],
                    "scenario": capability_binding["scenario"],
                    "replay_input": capability_binding["replay_input"],
                    "resolved_root": capability_binding["resolved_root"],
                    "baseline_commit": capability_binding[
                        "baseline_commit"
                    ],
                    "lease_sha256": capability_binding["lease_sha256"],
                    "source_sha256": capability_binding["source_sha256"],
                },
                "profiles": public_profiles,
                "operations": public_operations,
            },
        },
        "fault_schedule": public_fault,
        "decision": public_decision,
        "input": {
            "files": [
                _public_file_fact(item)
                for item in payload["input"]["files"]
            ],
            "sha256": payload["input"]["sha256"],
        },
        "render": {
            "operations": [
                _public_render_operation(item)
                for item in payload["render"]["operations"]
            ]
        },
        "workflow_executed": False,
    }


def command_replay_input(arguments: argparse.Namespace) -> int:
    _reject_recovery_claim(Path(arguments.worktree))
    envelope = _validate_blind_installed_replay_input(
        Path(arguments.worktree),
        lease=arguments.lease,
        replay_id=arguments.replay_input,
        require_input_tree=True,
    )
    _json_output(_public_replay_dto(envelope))
    return 0


def _phase_paths(root: Path) -> Dict[str, Path]:
    git_directory = root / ".git"
    return {
        "plan": git_directory / "bridge-fixture-fault-plan.md",
        "armed": git_directory / FAULT_PHASE_ARMED_TARGET,
        "claim": git_directory / FAULT_PHASE_CLAIM_TARGET,
        "injected": git_directory / FAULT_PHASE_INJECTED_TARGET,
    }


def _recovery_claim_path(root: Path) -> Path:
    return root / ".git" / RECOVERY_CLAIM_TARGET


def _reject_recovery_claim(root: Path) -> None:
    claim = _recovery_claim_path(root)
    with RetainedRootDirectory(claim.parent) as phase_store:
        if phase_store.exists(claim.name):
            raise FixtureError(
                "fixture is exclusively claimed for stale recovery"
            )


def _write_exclusive_bytes(path: Path, data: bytes, *, label: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags, 0o600)
        written = 0
        while written < len(data):
            count = os.write(descriptor, data[written:])
            if count <= 0:
                raise FixtureError(f"cannot write complete {label}")
            written += count
        os.fsync(descriptor)
    except OSError as error:
        raise FixtureError(f"cannot create exclusive {label}: {error}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    snapshot = inspect_root_child(path.parent, path.name)
    if snapshot["bytes"] != data:
        raise FixtureError(f"created {label} is not a stable regular file")


def _phase_self_evidence(
    snapshot: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "identity": {
            key: str(value)
            for key, value in sorted(snapshot["identity"].items())
        },
        "mode": snapshot["mode"],
        "nlink": str(snapshot["nlink"]),
        "parent_identity": {
            key: str(value)
            for key, value in sorted(
                snapshot["root_identity"].items()
            )
        },
        "reparse": snapshot["reparse"],
    }


def _phase_chain_evidence(
    snapshot: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        **_phase_self_evidence(snapshot),
        "raw_sha256": snapshot["raw_sha256"],
    }


def _phase_receipt(
    *,
    lease: str,
    state: str,
    binding: Mapping[str, Any],
    file_evidence: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    unsigned = {
        "version": FAULT_PHASE_EVIDENCE_SPEC,
        "canonicalization": CANONICAL_JSON_SPEC,
        "state": state,
        "binding": copy.deepcopy(binding),
    }
    if file_evidence is not None:
        unsigned["file"] = copy.deepcopy(file_evidence)
    return {
        **unsigned,
        "authentication": {
            "algorithm": "hmac-sha256/v1",
            "sha256": hmac.new(
                lease.encode("ascii"),
                _canonical_json_bytes(unsigned),
                hashlib.sha256,
            ).hexdigest(),
        },
    }


def _write_phase_receipt(
    path: Path,
    receipt: Mapping[str, Any],
    *,
    lease: str,
    label: str,
) -> str:
    with RetainedRootDirectory(path.parent) as store:
        _, digest, _, _ = _write_phase_receipt_store(
            store,
            path.name,
            receipt,
            lease=lease,
            label=label,
        )
        return digest


def _write_phase_receipt_store(
    store: RetainedRootDirectory,
    name: str,
    receipt: Mapping[str, Any],
    *,
    lease: str,
    label: str,
) -> Tuple[Dict[str, Any], str, Dict[str, Any], Dict[str, Any]]:
    if (
        not isinstance(receipt, dict)
        or not isinstance(receipt.get("state"), str)
        or not isinstance(receipt.get("binding"), dict)
    ):
        raise FixtureError(f"{label} draft is invalid")
    created_receipt: Dict[str, Any] = {}

    def build(file_evidence: Mapping[str, Any]) -> bytes:
        nonlocal created_receipt
        created_receipt = _phase_receipt(
            lease=lease,
            state=receipt["state"],
            binding=receipt["binding"],
            file_evidence=file_evidence,
        )
        return _canonical_json_bytes(created_receipt)

    snapshot = store.create_bound(name, build)
    evidence = _phase_chain_evidence(snapshot)
    if created_receipt.get("file") != _phase_self_evidence(snapshot):
        raise FixtureError(f"{label} created identity binding drifted")
    return (
        created_receipt,
        snapshot["raw_sha256"],
        evidence,
        snapshot,
    )


def _read_phase_receipt(
    path: Path,
    *,
    lease: str,
    state: str,
    label: str,
) -> Tuple[Dict[str, Any], str]:
    with RetainedRootDirectory(path.parent) as store:
        receipt, digest, _, _ = _read_phase_receipt_store(
            store,
            path.name,
            lease=lease,
            state=state,
            label=label,
        )
        return receipt, digest


def _read_phase_receipt_store(
    store: RetainedRootDirectory,
    name: str,
    *,
    lease: str,
    state: str,
    label: str,
    expected: Optional[Mapping[str, Any]] = None,
) -> Tuple[Dict[str, Any], str, Dict[str, Any], Dict[str, Any]]:
    snapshot = store.read(name)
    evidence = _phase_chain_evidence(snapshot)
    if expected is not None and evidence != expected:
        raise FixtureError(f"{label} retained identity/digest mismatch")
    receipt = _parse_canonical_json_bytes(
        snapshot["bytes"], label=label
    )
    if not isinstance(receipt, dict) or set(receipt) != {
        "version",
        "canonicalization",
        "state",
        "binding",
        "file",
        "authentication",
    }:
        raise FixtureError(f"{label} fields are not closed")
    if (
        receipt["version"] != FAULT_PHASE_EVIDENCE_SPEC
        or receipt["canonicalization"] != CANONICAL_JSON_SPEC
        or receipt["state"] != state
        or not isinstance(receipt["binding"], dict)
        or receipt["file"] != _phase_self_evidence(snapshot)
    ):
        raise FixtureError(f"{label} spec/state mismatch")
    authentication = receipt["authentication"]
    if not isinstance(authentication, dict) or set(authentication) != {
        "algorithm",
        "sha256",
    }:
        raise FixtureError(f"{label} authentication fields are not closed")
    unsigned = {
        key: value
        for key, value in receipt.items()
        if key != "authentication"
    }
    wanted = hmac.new(
        lease.encode("ascii"),
        _canonical_json_bytes(unsigned),
        hashlib.sha256,
    ).hexdigest()
    if (
        authentication["algorithm"] != "hmac-sha256/v1"
        or not hmac.compare_digest(str(authentication["sha256"]), wanted)
    ):
        raise FixtureError(f"{label} authentication mismatch")
    return receipt, snapshot["raw_sha256"], evidence, snapshot


def _fault_trees(
    payload: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    input_tree = _facts_tree(payload["input"]["files"])
    wrapper = payload["fault_schedule"]
    if not isinstance(wrapper, dict):
        raise FixtureError("replay input has no executable fault schedule")
    document = wrapper["facts"]
    injected = document["injected"]
    injected_bytes = base64.b64decode(
        injected["bytes_base64"], validate=True
    )
    post_tree = copy.deepcopy(input_tree)
    post_tree[document["target"]] = {
        "type": "file",
        "mode": injected["mode"],
        "bytes": injected_bytes,
    }
    return input_tree, post_tree


def _arm_bound_fault(
    root: Path,
    *,
    lease: str,
    replay_id: str,
    plan_path: Path,
    operation_id: str,
) -> Dict[str, Any]:
    if not _operation_id_valid(operation_id):
        raise FixtureError("fault operation-id is invalid")
    envelope = _validate_blind_installed_replay_input(
        root,
        lease=lease,
        replay_id=replay_id,
        require_input_tree=True,
    )
    payload = envelope["payload"]
    wrapper = payload["fault_schedule"]
    if not isinstance(wrapper, dict):
        raise FixtureError("replay input has no executable fault schedule")
    document = wrapper["facts"]
    if (
        document["phase"]
        != "after-confirmation-before-final-preflight"
        or document["target"] != "AGENTS.md"
    ):
        raise FixtureError(
            "fault adapter admits only the confirmed root AGENTS preflight"
        )
    paths = _phase_paths(root)
    try:
        captured_plan = inspect_root_child(
            plan_path.parent, plan_path.name
        )
    except (FixtureError, OSError) as error:
        raise FixtureError(f"cannot read fault plan bytes: {error}") from error
    plan_bytes = captured_plan["bytes"]
    validation, plan = _validate_plan_snapshot(
        replay_input=replay_id,
        root=root,
        lease=lease,
        plan_bytes=plan_bytes,
        lifecycle="prepared",
    )
    if (
        plan is None
        or not validation["pass"]
        or validation["plan_sha256"] != _sha256(plan_bytes)
    ):
        raise FixtureError("fault arm rejected the exact confirmed plan")
    _validate_confirmed_prewrite_plan(plan)
    plan_phase_snapshot: Optional[Dict[str, Any]] = None
    with RetainedRootDirectory(paths["plan"].parent) as phase_store:
        if any(
            phase_store.exists(path.name)
            for path in paths.values()
        ):
            raise FixtureError(
                "fault phase already armed, claimed, or injected"
            )
        plan_phase_snapshot = phase_store.create(
            paths["plan"].name, plan_bytes
        )
        target_steps = [
            row
            for row in plan["write_capabilities"]
            if row[2] == document["target"]
            and row[4] == "guarded-patch/v1"
        ]
        if len(target_steps) != 1:
            raise FixtureError(
                "fault arm plan lacks one exact guarded target step"
            )
        snapshot = inspect_root_child(root, document["target"])
        input_tree, post_tree = _fault_trees(payload)
        if (
            snapshot["mode"]
            != input_tree[document["target"]]["mode"]
            or _sha256(snapshot["bytes"])
            != document["expected_preimage_sha256"]
        ):
            raise FixtureError(
                "fault arm target differs from committed preimage"
            )
        if os.name == "nt" and (
            snapshot["mode"] != "100644"
            or document["injected"]["mode"] != "100644"
        ):
            raise FixtureError(
                "fault adapter is declarative-only for Windows mode changes"
            )
        identity = {
            key: str(value)
            for key, value in sorted(snapshot["identity"].items())
        }
        root_identity = {
            key: str(value)
            for key, value in sorted(snapshot["root_identity"].items())
        }
        plan_snapshot = plan_phase_snapshot
        plan_identity = {
            key: str(value)
            for key, value in sorted(
                plan_snapshot["identity"].items()
            )
        }
        plan_root_identity = {
            key: str(value)
            for key, value in sorted(
                plan_snapshot["root_identity"].items()
            )
        }
        binding = {
            "commitment_sha256": envelope["commitment_sha256"],
            "operation_id": operation_id,
            "suite": SUITE,
            "scenario": payload["binding"]["scenario"],
            "replay_input": replay_id,
            "resolved_root": str(root.resolve()),
            "nonce": payload["binding"]["nonce"],
            "lease_sha256": _sha256(lease.encode("ascii")),
            "baseline_commit": payload["binding"]["baseline_commit"],
            "head": payload["binding"]["head"],
            "plan_sha256": _sha256(plan_bytes),
            "source_plan_mode": captured_plan["mode"],
            "source_plan_root_identity": {
                key: str(value)
                for key, value in sorted(
                    captured_plan["root_identity"].items()
                )
            },
            "source_plan_identity": {
                key: str(value)
                for key, value in sorted(
                    captured_plan["identity"].items()
                )
            },
            "plan_mode": plan_snapshot["mode"],
            "plan_root_identity": plan_root_identity,
            "plan_identity": plan_identity,
            "target": document["target"],
            "expected_preimage_sha256": document[
                "expected_preimage_sha256"
            ],
            "target_type": "file",
            "expected_mode": snapshot["mode"],
            "injected_mode": document["injected"]["mode"],
            "target_root_identity": root_identity,
            "target_identity": identity,
            "phase_nonce": secrets.token_urlsafe(24),
            "pre_tree_sha256": _tree_digest(input_tree),
            "post_tree_sha256": _tree_digest(post_tree),
        }
        receipt = _phase_receipt(
            lease=lease,
            state="confirmed-awaiting-final-preflight",
            binding=binding,
        )
        (
            receipt,
            receipt_sha256,
            _,
            _,
        ) = _write_phase_receipt_store(
            phase_store,
            paths["armed"].name,
            receipt,
            lease=lease,
            label="fault armed receipt",
        )
        return {
            "spec": FAULT_PHASE_EVIDENCE_SPEC,
            "mutation_capability": root_child_capability(),
            "state": receipt["state"],
            "operation_id": operation_id,
            "commitment_sha256": envelope["commitment_sha256"],
            "plan_sha256": binding["plan_sha256"],
            "receipt_sha256": receipt_sha256,
            "phase": document["phase"],
            "target": document["target"],
            "bridge_writes": 0,
            "workflow_executed": False,
        }


def _validate_fault_binding(
    binding: Mapping[str, Any],
    *,
    envelope: Mapping[str, Any],
    lease: str,
    replay_id: str,
    operation_id: str,
) -> None:
    payload = envelope["payload"]
    input_tree, post_tree = _fault_trees(payload)
    target = payload["fault_schedule"]["facts"]["target"]
    expected_identity_keys = (
        {"volume", "index_high", "index_low", "links"}
        if os.name == "nt"
        else {"device", "inode", "links"}
    )
    expected_root_identity_keys = (
        {"volume", "index_high", "index_low"}
        if os.name == "nt"
        else {"device", "inode"}
    )
    if not isinstance(binding, dict) or set(binding) != {
        "commitment_sha256",
        "operation_id",
        "suite",
        "scenario",
        "replay_input",
        "resolved_root",
        "nonce",
        "lease_sha256",
        "baseline_commit",
        "head",
        "plan_sha256",
        "source_plan_mode",
        "source_plan_root_identity",
        "source_plan_identity",
        "plan_mode",
        "plan_root_identity",
        "plan_identity",
        "target",
        "expected_preimage_sha256",
        "target_type",
        "expected_mode",
        "injected_mode",
        "target_root_identity",
        "target_identity",
        "phase_nonce",
        "pre_tree_sha256",
        "post_tree_sha256",
    }:
        raise FixtureError("fault armed binding fields are not closed")
    if (
        binding["commitment_sha256"] != envelope["commitment_sha256"]
        or SHA256_PATTERN.fullmatch(
            str(binding["commitment_sha256"])
        )
        is None
        or binding["operation_id"] != operation_id
        or not _operation_id_valid(str(binding["operation_id"]))
        or binding["suite"] != SUITE
        or binding["scenario"] != payload["binding"]["scenario"]
        or binding["replay_input"] != replay_id
        or binding["resolved_root"] != payload["binding"]["resolved_root"]
        or binding["nonce"] != payload["binding"]["nonce"]
        or binding["lease_sha256"] != _sha256(lease.encode("ascii"))
        or binding["baseline_commit"]
        != payload["binding"]["baseline_commit"]
        or binding["head"] != payload["binding"]["head"]
        or binding["target"] != target
        or binding["expected_preimage_sha256"]
        != payload["fault_schedule"]["facts"][
            "expected_preimage_sha256"
        ]
        or binding["target_type"] != "file"
        or binding["expected_mode"] != input_tree[target]["mode"]
        or binding["injected_mode"]
        != payload["fault_schedule"]["facts"]["injected"]["mode"]
        or not isinstance(binding["target_root_identity"], dict)
        or set(binding["target_root_identity"])
        != expected_root_identity_keys
        or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in binding["target_root_identity"].items()
        )
        or not isinstance(binding["target_identity"], dict)
        or set(binding["target_identity"]) != expected_identity_keys
        or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in binding["target_identity"].items()
        )
        or SHA256_PATTERN.fullmatch(str(binding["plan_sha256"])) is None
        or binding["source_plan_mode"] not in {"100644", "100755"}
        or not isinstance(binding["source_plan_root_identity"], dict)
        or set(binding["source_plan_root_identity"])
        != expected_root_identity_keys
        or not isinstance(binding["source_plan_identity"], dict)
        or set(binding["source_plan_identity"]) != expected_identity_keys
        or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in binding[
                "source_plan_root_identity"
            ].items()
        )
        or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in binding["source_plan_identity"].items()
        )
        or binding["plan_mode"] not in {"100644", "100755"}
        or not isinstance(binding["plan_root_identity"], dict)
        or set(binding["plan_root_identity"])
        != expected_root_identity_keys
        or not isinstance(binding["plan_identity"], dict)
        or set(binding["plan_identity"]) != expected_identity_keys
        or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in binding["plan_root_identity"].items()
        )
        or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in binding["plan_identity"].items()
        )
        or SHA256_PATTERN.fullmatch(
            str(binding["expected_preimage_sha256"])
        )
        is None
        or SHA256_PATTERN.fullmatch(str(binding["pre_tree_sha256"]))
        is None
        or SHA256_PATTERN.fullmatch(str(binding["post_tree_sha256"]))
        is None
        or binding["pre_tree_sha256"] != _tree_digest(input_tree)
        or binding["post_tree_sha256"] != _tree_digest(post_tree)
        or not isinstance(binding["phase_nonce"], str)
        or re.fullmatch(r"[A-Za-z0-9_-]{8,64}", binding["phase_nonce"])
        is None
    ):
        raise FixtureError("fault armed binding differs from replay bundle")


def _apply_bound_fault(
    root: Path,
    *,
    lease: str,
    replay_id: str,
    operation_id: str,
) -> Dict[str, Any]:
    capability = root_child_capability()
    if not capability["same-mode-root-child-mutation"]:
        raise FixtureError(
            "fault root-child mutation is declarative-only on this platform: "
            "no mutation-bound current name-to-leaf authority is available"
        )
    envelope = _validate_blind_installed_replay_input(
        root,
        lease=lease,
        replay_id=replay_id,
        require_input_tree=False,
    )
    payload = envelope["payload"]
    input_tree, recovery_post_tree = _fault_trees(payload)
    input_differences = compare_tree(root, input_tree)
    post_differences = compare_tree(root, recovery_post_tree)
    if input_differences and post_differences:
        raise FixtureError(
            "fault apply root is neither the bound preimage nor postimage"
        )
    paths = _phase_paths(root)
    document = payload["fault_schedule"]["facts"]
    injected = document["injected"]
    injected_bytes = base64.b64decode(
        injected["bytes_base64"], validate=True
    )
    with RetainedRootDirectory(paths["plan"].parent) as phase_store:
        present = {
            key: phase_store.exists(path.name)
            for key, path in paths.items()
        }
        if not present["plan"] or not present["armed"]:
            raise FixtureError(
                "fault apply requires a complete exclusive armed state"
            )
        if present["injected"]:
            raise FixtureError(
                "fault apply is single-consumption and already injected"
            )
        armed, armed_sha256, armed_evidence, _ = (
            _read_phase_receipt_store(
                phase_store,
                paths["armed"].name,
                lease=lease,
                state="confirmed-awaiting-final-preflight",
                label="fault armed receipt",
            )
        )
        binding = armed["binding"]
        _validate_fault_binding(
            binding,
            envelope=envelope,
            lease=lease,
            replay_id=replay_id,
            operation_id=operation_id,
        )
        try:
            plan_snapshot = phase_store.read(paths["plan"].name)
        except FixtureError as error:
            raise FixtureError("fault plan snapshot is unsafe") from error
        plan_root_identity = {
            key: str(value)
            for key, value in sorted(
                plan_snapshot["root_identity"].items()
            )
        }
        plan_identity = {
            key: str(value)
            for key, value in sorted(
                plan_snapshot["identity"].items()
            )
        }
        if (
            plan_snapshot["raw_sha256"] != binding["plan_sha256"]
            or plan_snapshot["mode"] != binding["plan_mode"]
            or plan_root_identity != binding["plan_root_identity"]
            or plan_identity != binding["plan_identity"]
        ):
            raise FixtureError("fault plan snapshot changed after arm")
        snapshot = inspect_root_child(root, binding["target"])
        current_identity = {
            key: str(value)
            for key, value in sorted(snapshot["identity"].items())
        }
        current_root_identity = {
            key: str(value)
            for key, value in sorted(
                snapshot["root_identity"].items()
            )
        }
        identity_matches = (
            current_root_identity == binding["target_root_identity"]
            and current_identity == binding["target_identity"]
        )
        is_preimage = (
            identity_matches
            and snapshot["mode"] == binding["expected_mode"]
            and _sha256(snapshot["bytes"])
            == binding["expected_preimage_sha256"]
        )
        is_postimage = (
            identity_matches
            and snapshot["mode"] == injected["mode"]
            and _sha256(snapshot["bytes"]) == injected["sha256"]
        )
        if not is_preimage and not is_postimage:
            raise FixtureError("fault target changed after arm or claim")
        if is_postimage and not present["claim"]:
            raise FixtureError(
                "fault postimage recovery requires an existing valid claim"
            )
        if present["claim"]:
            claim, claim_sha256, claim_evidence, _ = (
                _read_phase_receipt_store(
                    phase_store,
                    paths["claim"].name,
                    lease=lease,
                    state="injecting",
                    label="fault claim receipt",
                )
            )
            claim_binding = claim["binding"]
            if (
                not isinstance(claim_binding, dict)
                or set(claim_binding)
                != set(binding) | {"armed_receipt", "claim_nonce"}
                or any(
                    claim_binding.get(key) != value
                    for key, value in binding.items()
                )
                or claim_binding.get("armed_receipt")
                != armed_evidence
                or not isinstance(
                    claim_binding.get("claim_nonce"), str
                )
                or re.fullmatch(
                    r"[A-Za-z0-9_-]{8,64}",
                    claim_binding["claim_nonce"],
                )
                is None
            ):
                raise FixtureError(
                    "fault interrupted claim binding is not exact"
                )
        else:
            claim_binding = {
                **copy.deepcopy(binding),
                "armed_receipt": armed_evidence,
                "claim_nonce": secrets.token_urlsafe(24),
            }
            claim_draft = _phase_receipt(
                lease=lease,
                state="injecting",
                binding=claim_binding,
            )
            (
                claim,
                claim_sha256,
                claim_evidence,
                _,
            ) = _write_phase_receipt_store(
                phase_store,
                paths["claim"].name,
                claim_draft,
                lease=lease,
                label="fault claim receipt",
            )
        if is_preimage:
            performed_injection = True
            observed = replace_root_child(
                root,
                document["target"],
                expected_root_identity=snapshot["root_identity"],
                expected_identity=snapshot["identity"],
                expected_mode=snapshot["mode"],
                expected_bytes=snapshot["bytes"],
                injected_bytes=injected_bytes,
                injected_mode=injected["mode"],
            )
        else:
            performed_injection = False
            observed = snapshot
        if (
            _sha256(observed["bytes"]) != injected["sha256"]
            or observed["mode"] != injected["mode"]
            or {
                key: str(value)
                for key, value in sorted(
                    observed["root_identity"].items()
                )
            }
            != binding["target_root_identity"]
            or {
                key: str(value)
                for key, value in sorted(
                    observed["identity"].items()
                )
            }
            != binding["target_identity"]
        ):
            raise FixtureError(
                "fault injection retained-handle evidence mismatch"
            )
        _, post_tree = _fault_trees(payload)
        differences = compare_tree(root, post_tree)
        if differences:
            raise FixtureError(
                "fault injection changed more than the bound target: "
                + "; ".join(differences)
            )
        injected_binding = {
            **copy.deepcopy(binding),
            "armed_receipt": armed_evidence,
            "claim_receipt": claim_evidence,
            "observed_injected_sha256": injected["sha256"],
            "observed_post_tree_sha256": _tree_digest(post_tree),
        }
        injected_draft = _phase_receipt(
            lease=lease,
            state="injected",
            binding=injected_binding,
        )
        (
            _,
            injected_receipt_sha256,
            _,
            _,
        ) = _write_phase_receipt_store(
            phase_store,
            paths["injected"].name,
            injected_draft,
            lease=lease,
            label="fault injected receipt",
        )
    return {
        "spec": FAULT_PHASE_EVIDENCE_SPEC,
        "mutation_capability": capability,
        "state": "injected",
        "operation_id": operation_id,
        "commitment_sha256": envelope["commitment_sha256"],
        "plan_sha256": binding["plan_sha256"],
        "armed_receipt_sha256": armed_sha256,
        "claim_receipt_sha256": claim_sha256,
        "injected_receipt_sha256": injected_receipt_sha256,
        "pre_tree_sha256": binding["pre_tree_sha256"],
        "post_tree_sha256": binding["post_tree_sha256"],
        "target": document["target"],
        "expected_preimage_sha256": binding[
            "expected_preimage_sha256"
        ],
        "injected_sha256": injected["sha256"],
        "persistence": document["persistence"],
        "bridge_writes": 0,
        "fixture_writes": 1 if performed_injection else 0,
        "workflow_executed": False,
    }


def command_arm_fault(arguments: argparse.Namespace) -> int:
    _reject_recovery_claim(Path(arguments.worktree))
    result = _arm_bound_fault(
        Path(arguments.worktree),
        lease=arguments.lease,
        replay_id=arguments.replay_input,
        plan_path=Path(arguments.plan),
        operation_id=arguments.operation_id,
    )
    _json_output(result)
    return 0


def command_apply_fault(arguments: argparse.Namespace) -> int:
    _reject_recovery_claim(Path(arguments.worktree))
    result = _apply_bound_fault(
        Path(arguments.worktree),
        lease=arguments.lease,
        replay_id=arguments.replay_input,
        operation_id=arguments.operation_id,
    )
    _json_output(result)
    return 0


def _validate_injected_fault_evidence(
    plan: Plan,
    *,
    root: Path,
    lease: str,
    envelope: Mapping[str, Any],
) -> None:
    payload = envelope["payload"]
    document = payload["fault_schedule"]["facts"]
    paths = _phase_paths(root)
    with RetainedRootDirectory(paths["plan"].parent) as phase_store:
        armed, _, armed_evidence, _ = _read_phase_receipt_store(
            phase_store,
            paths["armed"].name,
            lease=lease,
            state="confirmed-awaiting-final-preflight",
            label="fault armed receipt",
        )
        binding = armed["binding"]
        operation_id = binding.get("operation_id")
        if not isinstance(operation_id, str):
            raise FixtureError(
                "fault armed receipt lacks operation identity"
            )
        _validate_fault_binding(
            binding,
            envelope=envelope,
            lease=lease,
            replay_id=payload["binding"]["replay_input"],
            operation_id=operation_id,
        )
        claim, _, claim_evidence, _ = _read_phase_receipt_store(
            phase_store,
            paths["claim"].name,
            lease=lease,
            state="injecting",
            label="fault claim receipt",
        )
        claim_binding = claim["binding"]
        if (
            not isinstance(claim_binding, dict)
            or set(claim_binding)
            != set(binding) | {"armed_receipt", "claim_nonce"}
            or any(
                claim_binding.get(key) != value
                for key, value in binding.items()
            )
            or claim_binding.get("armed_receipt") != armed_evidence
            or not isinstance(claim_binding.get("claim_nonce"), str)
            or re.fullmatch(
                r"[A-Za-z0-9_-]{8,64}",
                claim_binding["claim_nonce"],
            )
            is None
        ):
            raise FixtureError(
                "fault claim receipt binding is not exact"
            )
        injected_receipt, _, _, _ = _read_phase_receipt_store(
            phase_store,
            paths["injected"].name,
            lease=lease,
            state="injected",
            label="fault injected receipt",
        )
        injected_binding = injected_receipt["binding"]
        if (
            not isinstance(injected_binding, dict)
            or set(injected_binding)
            != set(binding)
            | {
                "armed_receipt",
                "claim_receipt",
                "observed_injected_sha256",
                "observed_post_tree_sha256",
            }
            or any(
                injected_binding.get(key) != value
                for key, value in binding.items()
            )
            or injected_binding.get("armed_receipt")
            != armed_evidence
            or injected_binding.get("claim_receipt")
            != claim_evidence
            or injected_binding.get("observed_injected_sha256")
            != document["injected"]["sha256"]
            or injected_binding.get("observed_post_tree_sha256")
            != binding["post_tree_sha256"]
        ):
            raise FixtureError(
                "fault injected receipt binding is not exact"
            )
        plan_snapshot = phase_store.read(paths["plan"].name)
    if (
        plan_snapshot["raw_sha256"] != binding["plan_sha256"]
        or plan_snapshot["mode"] != binding["plan_mode"]
        or {
            key: str(value)
            for key, value in sorted(
                plan_snapshot["root_identity"].items()
            )
        }
        != binding["plan_root_identity"]
        or {
            key: str(value)
            for key, value in sorted(
                plan_snapshot["identity"].items()
            )
        }
        != binding["plan_identity"]
    ):
        raise FixtureError("fault confirmed plan snapshot is no longer exact")
    live = inspect_root_child(root, document["target"])
    live_root_identity = {
        key: str(value)
        for key, value in sorted(live["root_identity"].items())
    }
    live_identity = {
        key: str(value)
        for key, value in sorted(live["identity"].items())
    }
    if (
        live_root_identity != binding["target_root_identity"]
        or live_identity != binding["target_identity"]
        or live["mode"] != document["injected"]["mode"]
        or _sha256(live["bytes"]) != document["injected"]["sha256"]
    ):
        raise FixtureError("fault injected target evidence is not exact")
    _, post_tree = _fault_trees(payload)
    differences = compare_tree(root, post_tree)
    if differences or _tree_digest(post_tree) != binding["post_tree_sha256"]:
        raise FixtureError(
            "fault persistent post-tree differs from the bound schedule"
        )
    affected_closures = {
        operation["closure"]
        for operation in payload["capability"]["facts"]["operations"]
        if operation["path"] == document["target"]
    }
    affected_units = [
        row for row in plan["rows"] if row[1] in affected_closures
    ]
    affected_closure_rows = [
        row for row in plan["closures"] if row[0] in affected_closures
    ]
    if (
        not affected_closures
        or not affected_units
        or len(affected_closure_rows) != len(affected_closures)
        or any(row[8] != "failed" for row in affected_units)
        or any(row[5] != "failed" for row in affected_closure_rows)
        or any(row[8] == "applied" for row in plan["rows"])
    ):
        raise FixtureError(
            "post-fault affected closure is not exact failed/zero-write"
        )


def _capability_rows_from_envelope(
    envelope: Mapping[str, Any],
) -> Tuple[List[Tuple[str, ...]], List[Tuple[str, ...]]]:
    payload = envelope["payload"]
    document = payload["capability"]["facts"]
    profiles = document.get("profiles")
    operations = document.get("operations")
    if not isinstance(profiles, list) or not isinstance(operations, list):
        raise FixtureError("fixture capability profiles/operations are invalid")
    profile_rows: List[Tuple[str, ...]] = []
    profile_map: Dict[str, Mapping[str, Any]] = {}
    for index, profile in enumerate(profiles, start=1):
        if not isinstance(profile, dict) or set(profile) != {
            "binding",
            "profile",
            "host",
            "host_version",
            "tool_surface",
            "platform",
            "filesystem_assumptions",
            "attestations",
        }:
            raise FixtureError("fixture capability profile fields are not closed")
        binding = profile["binding"]
        assumptions = profile["filesystem_assumptions"]
        if (
            binding != f"capability/{index}"
            or profile["profile"] != "capability-profile/v1"
            or profile["host"] != "other"
            or profile["platform"] != "other"
            or not isinstance(profile["host_version"], str)
            or not profile["host_version"].startswith("fixture-")
            or not isinstance(assumptions, list)
            or not assumptions
            or assumptions != sorted(set(assumptions))
            or not isinstance(profile["attestations"], list)
            or not profile["attestations"]
        ):
            raise FixtureError("fixture capability profile is invalid")
        for attestation in profile["attestations"]:
            if (
                not isinstance(attestation, dict)
                or set(attestation)
                != {"protocol", "proof", "operations", "paths"}
                or attestation["protocol"] not in WRITE_PROTOCOLS
                - {"unavailable"}
                or not isinstance(attestation["proof"], str)
                or not attestation["proof"].startswith("fixture-")
                or not isinstance(attestation["operations"], list)
                or not attestation["operations"]
                or attestation["operations"]
                != sorted(set(attestation["operations"]))
                or any(
                    operation not in {"create", "delete", "replace"}
                    for operation in attestation["operations"]
                )
                or not isinstance(attestation["paths"], list)
                or not attestation["paths"]
                or attestation["paths"]
                != sorted(set(attestation["paths"]))
            ):
                raise FixtureError(
                    "fixture capability attestation fields are not closed"
                )
            for path in attestation["paths"]:
                safe_relative(
                    path, field="fixture capability attestation path"
                )
        profile_map[binding] = profile
        profile_rows.append(
            (
                binding,
                profile["profile"],
                profile["host"],
                profile["host_version"],
                profile["tool_surface"],
                profile["platform"],
                "; ".join(assumptions),
            )
        )
    operation_rows: List[Tuple[str, ...]] = []
    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict) or set(operation) != {
            "closure",
            "path",
            "operation",
            "protocol",
            "binding",
            "inverse_protocol",
            "inverse_binding",
        }:
            raise FixtureError("fixture write operation fields are not closed")
        relative = safe_relative(
            operation["path"], field="fixture write operation path"
        )
        operation_name = operation["operation"]
        if operation_name not in {"create", "delete", "replace"}:
            raise FixtureError("fixture write operation kind is invalid")
        for protocol_key, binding_key in (
            ("protocol", "binding"),
            ("inverse_protocol", "inverse_binding"),
        ):
            protocol = operation[protocol_key]
            binding = operation[binding_key]
            if protocol not in WRITE_PROTOCOLS:
                raise FixtureError("fixture write protocol is invalid")
            if protocol == "unavailable":
                if binding is not None:
                    raise FixtureError(
                        "unavailable fixture protocol has a binding"
                    )
                continue
            profile = profile_map.get(binding)
            if profile is None or not any(
                isinstance(attestation, dict)
                and set(attestation)
                == {"protocol", "proof", "operations", "paths"}
                and attestation["protocol"] == protocol
                and isinstance(attestation["proof"], str)
                and attestation["proof"].startswith("fixture-")
                and operation_name in attestation["operations"]
                and relative in attestation["paths"]
                for attestation in profile["attestations"]
            ):
                raise FixtureError(
                    "fixture protocol lacks exact path/operation proof"
                )
        operation_rows.append(
            (
                str(index),
                operation["closure"],
                relative,
                operation_name,
                operation["protocol"],
                "-" if operation["binding"] is None else operation["binding"],
                operation["inverse_protocol"],
                (
                    "-"
                    if operation["inverse_binding"] is None
                    else operation["inverse_binding"]
                ),
            )
        )
    return profile_rows, operation_rows


def _legacy_marker_warnings(
    input_tree: Mapping[str, Any],
) -> List[str]:
    warnings: List[str] = []
    for relative in sorted(input_tree):
        entry = input_tree[relative]
        if entry.get("type") != "file":
            continue
        data = entry.get("bytes")
        if not isinstance(data, bytes):
            continue
        try:
            lines = data.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines, start=1):
            if (
                line.startswith("<!-- bridge:managed:start ")
                and " mode=" in line
                and line.endswith(" -->")
            ):
                warnings.append(
                    f"- legacy-managed-mode: {relative} (line {index})"
                )
                end_line = next(
                    (
                        candidate
                        for candidate in range(index + 1, len(lines) + 1)
                        if lines[candidate - 1]
                        == "<!-- bridge:managed:end -->"
                    ),
                    None,
                )
                if end_line is None:
                    end_line = index
                warnings.append(
                    f"- marker-anomaly: {relative} (line {end_line})"
                )
    return sorted(set(warnings))


def _live_untracked_paths(root: Path) -> List[str]:
    return sorted(
        line.replace("\\", "/")
        for line in git_run(
            root,
            "ls-files",
            "--others",
            "--exclude-standard",
        ).splitlines()
        if line
    )


def _has_exact_current_covenant_pair(
    tree: Mapping[str, Any],
) -> bool:
    for relative in COVENANT_CARRIERS:
        entry = tree.get(relative)
        if (
            not isinstance(entry, dict)
            or entry.get("type") != "file"
            or entry.get("mode") != "100644"
            or entry.get("bytes") != COVENANT_TEMPLATES[relative].read_bytes()
        ):
            return False
    return True


def _is_exact_empty_bootstrap_capability(
    operations: Any,
) -> bool:
    if not isinstance(operations, list) or len(operations) != 2:
        return False
    return [
        (
            operation.get("path"),
            operation.get("operation"),
            operation.get("protocol"),
            operation.get("closure"),
        )
        for operation in operations
    ] == [
        (
            ".claude/rules/bridge-covenant.md",
            "create",
            "strict-create/v1",
            "closure/agents-md",
        ),
        (
            "AGENTS.md",
            "create",
            "strict-create/v1",
            "closure/agents-md",
        ),
    ]


def _is_exact_empty_bootstrap_render(
    operations: Any,
) -> bool:
    if not isinstance(operations, list) or len(operations) != 2:
        return False
    return [
        (operation.get("path"), operation.get("operation"))
        for operation in operations
    ] == [
        (".claude/rules/bridge-covenant.md", "create"),
        ("AGENTS.md", "create"),
    ]


def _derive_plan_temporal_context(
    *,
    envelope: Mapping[str, Any],
    lifecycle: str,
    actual_untracked: Sequence[str],
) -> str:
    payload = envelope["payload"]
    input_tree = _facts_tree(payload["input"]["files"])
    rendered_tree = _rendered_tree_from_envelope(
        input_tree, payload["render"]["operations"]
    )
    capability_operations = payload["capability"]["facts"].get(
        "operations", []
    )
    carrier_set = set(COVENANT_CARRIERS)
    carriers_untracked = carrier_set.issubset(actual_untracked)
    input_has_no_carriers = carrier_set.isdisjoint(input_tree)
    rendered_additions = set(rendered_tree) - set(input_tree)
    operation_post = (
        lifecycle in {"verified", "closed"}
        and carriers_untracked
        and input_has_no_carriers
        and rendered_additions == carrier_set
        and _has_exact_current_covenant_pair(rendered_tree)
        and _is_exact_empty_bootstrap_render(
            payload["render"]["operations"]
        )
        and _is_exact_empty_bootstrap_capability(capability_operations)
        and isinstance(payload["decision"], dict)
        and payload["decision"].get("status") == "confirmed"
        and payload["decision"].get("authorized_closures")
        == ["closure/agents-md"]
    )
    if operation_post:
        return EMPTY_BOOTSTRAP_POST_CONTEXT
    independent_scan = (
        lifecycle == "prepared"
        and carriers_untracked
        and _has_exact_current_covenant_pair(input_tree)
        and not payload["render"]["operations"]
        and not capability_operations
        and payload["decision"] is None
    )
    if independent_scan:
        return EMPTY_UNTRACKED_SCAN_CONTEXT
    return GENERAL_PLAN_CONTEXT


def _warning_rows(
    plan: Plan, token: str
) -> List[Tuple[str, Optional[str]]]:
    return sorted(
        (relative, detail)
        for line in plan["warnings"]
        if line != "- (none)"
        for warning_token, relative, detail in [
            _validate_warning_line(Path(plan["path"]), line)
        ]
        if warning_token == token
    )


def _validate_empty_bootstrap_temporal_plan(
    plan: Plan,
    *,
    temporal_context: str,
) -> None:
    if temporal_context == EMPTY_BOOTSTRAP_POST_CONTEXT:
        if (
            plan["headers"]["onboarding"] != "bootstrap-required"
            or plan["headers"]["authorization"] != "confirmed"
            or plan["rows"]
            != [
                (
                    "onboarding/covenant",
                    "closure/agents-md",
                    "selected",
                    "-",
                    "no-baseline",
                    "create",
                    "source-to-projection",
                    "confirmed",
                    "applied",
                    "-",
                    "live-activation-unknown; restart-may-be-required",
                )
            ]
            or plan["closures"]
            != [
                (
                    "closure/agents-md",
                    "onboarding/covenant",
                    "-",
                    "selected",
                    "confirmed",
                    "applied",
                )
            ]
            or plan["migration"]
            or plan["migration_candidates"]
            or plan["adoption"]
        ):
            raise FixtureError(
                "operation-scoped empty bootstrap post has a non-canonical "
                "unit, closure, onboarding, or authorization shape"
            )
        if _warning_rows(plan, "covenant-anchor-anomaly"):
            raise FixtureError(
                "operation-scoped empty bootstrap post cannot carry a "
                "covenant-anchor-anomaly warning"
            )
        return
    if temporal_context != EMPTY_UNTRACKED_SCAN_CONTEXT:
        return
    if (
        plan["headers"]["onboarding"] != "blocked"
        or plan["headers"]["authorization"] != "not-applicable"
        or plan["rows"]
        != [
            (
                "onboarding/covenant",
                "closure/decision/onboarding/covenant",
                "selected",
                "-",
                "blocked",
                "resolve-blocker",
                "user-decision",
                "not-applicable",
                "blocked",
                "-",
                "-",
            )
        ]
        or plan["closures"]
        != [
            (
                "closure/decision/onboarding/covenant",
                "onboarding/covenant",
                "-",
                "selected",
                "not-applicable",
                "blocked",
            )
        ]
        or plan["capability_profiles"]
        or plan["write_capabilities"]
        or plan["migration"]
        or plan["migration_candidates"]
        or plan["adoption"]
    ):
        raise FixtureError(
            "independent empty-untracked scan has a non-canonical blocked "
            "unit, closure, onboarding, or authorization shape"
        )
    wanted_anomalies = sorted(
        (relative, "(untracked)") for relative in COVENANT_CARRIERS
    )
    if _warning_rows(plan, "covenant-anchor-anomaly") != wanted_anomalies:
        raise FixtureError(
            "independent empty-untracked scan covenant warning set differs "
            "from its two untracked carriers"
        )


def _rule_tier_from_public_source(
    unit: str,
    entry: Mapping[str, Any],
) -> str:
    if entry.get("type") != "file" or not isinstance(
        entry.get("bytes"), bytes
    ):
        raise FixtureError(
            f"unit {unit!r} tier mapping requires a regular source document"
        )
    frontmatter = recognized_frontmatter_span(
        source_byte_records(entry["bytes"]),
        kind="rule",
    )
    # source-tree/v5 permits only the paths map in recognized rule
    # frontmatter. YAML validity is an agent-supplied semantic fact and is not
    # reparsed here. A recognized but invalid scope remains the semantic
    # candidate blocked by invalid-rule-paths; it never becomes unscoped.
    return "semantic" if frontmatter is not None else "structural"


def _rule_tier_from_public_projection(
    unit: str,
    tree: Mapping[str, Any],
) -> Optional[str]:
    agents = tree.get("AGENTS.md")
    if (
        not isinstance(agents, dict)
        or agents.get("type") != "file"
        or not isinstance(agents.get("bytes"), bytes)
    ):
        return None
    block_map = inspect_managed_blocks(
        agents["bytes"],
        owned_ids=[unit],
    )
    blocks = [
        block
        for block in block_map["blocks"]
        if block["id"] == unit
        and block["source_matches"]
    ]
    if len(blocks) > 1:
        raise FixtureError(
            f"unit {unit!r} has duplicate public projection mappings"
        )
    if not blocks:
        return None
    block = blocks[0]
    preamble = parse_preamble(
        agents["bytes"][block["body_start"] : block["body_end"]]
    )
    if preamble["present"] and not preamble["valid"]:
        raise FixtureError(
            f"unit {unit!r} has an invalid public projection preamble"
        )
    return "semantic" if preamble["present"] else "structural"


def _validate_public_unit_tiers(
    plan: Plan,
    *,
    input_tree: Mapping[str, Any],
    rendered_tree: Mapping[str, Any],
) -> None:
    for row in plan["rows"]:
        unit = row[0]
        actual_tier = row[9]
        if unit.startswith("onboarding/"):
            expected_tier = "-"
        elif unit == "entry":
            expected_tier = "structural"
        elif unit.startswith("skills/"):
            expected_tier = (
                "-"
                if row[5] in {"annex-or-keep", "keep"}
                else "native"
            )
        else:
            source_path = (
                ".claude/rules/" + unit[len("rules/") :] + ".md"
            )
            if source_path in rendered_tree:
                expected_tier = _rule_tier_from_public_source(
                    unit, rendered_tree[source_path]
                )
            elif source_path in input_tree:
                expected_tier = _rule_tier_from_public_source(
                    unit, input_tree[source_path]
                )
            else:
                expected_tier = (
                    _rule_tier_from_public_projection(unit, rendered_tree)
                    or _rule_tier_from_public_projection(unit, input_tree)
                )
            if expected_tier is None:
                raise FixtureError(
                    f"unit {unit!r} has no authenticated public tier mapping"
                )
        if actual_tier != expected_tier:
            raise FixtureError(
                f"unit {unit!r} tier {actual_tier!r} differs from "
                f"authenticated public tier {expected_tier!r}"
            )


def _validate_plan_replay_context(
    plan: Plan,
    *,
    envelope: Mapping[str, Any],
    root: Path,
    lease: str,
    lifecycle: str,
    temporal_context: str,
    actual_untracked: Sequence[str],
) -> None:
    payload = envelope["payload"]
    pre_lifecycles = {"prepared"}
    post_lifecycles = {
        "executing",
        "compensating",
        "verified",
        "failed",
        "partial",
        "closed",
    }
    if lifecycle not in pre_lifecycles | post_lifecycles:
        raise FixtureError("operation lifecycle is invalid")
    wanted_phase = (
        "pre-write" if lifecycle in pre_lifecycles else "post-write"
    )
    if plan["headers"]["phase"] != wanted_phase:
        raise FixtureError("phase disagrees with operation lifecycle")
    if (
        plan["headers"]["project"] != payload["binding"]["scenario"]
        or plan["headers"]["scan root"] != "."
    ):
        raise FixtureError("plan project/root differs from replay binding")
    input_tree = _facts_tree(payload["input"]["files"])
    rendered_tree = _rendered_tree_from_envelope(
        input_tree, payload["render"]["operations"]
    )
    _validate_public_unit_tiers(
        plan,
        input_tree=input_tree,
        rendered_tree=rendered_tree,
    )
    if temporal_context == EMPTY_UNTRACKED_SCAN_CONTEXT:
        differences = compare_tree(root, input_tree)
        if differences:
            raise FixtureError(
                "independent empty-untracked scan differs from its bound "
                "fresh input: " + "; ".join(differences)
            )
    profile_rows, operation_rows = _capability_rows_from_envelope(envelope)
    if plan["write_capabilities"]:
        if plan["write_capabilities"] != operation_rows:
            raise FixtureError(
                "write capabilities differ from fixture attestation"
            )
        if plan["capability_profiles"] != profile_rows:
            raise FixtureError(
                "capability profiles differ from fixture attestation"
            )
    decision = payload["decision"]
    confirmed_closures = {
        row[1]
        for row in plan["rows"]
        if row[2] == "selected"
        and row[5] in MUTATING_ACTIONS
        and row[7] == "confirmed"
    }
    if confirmed_closures:
        if (
            not isinstance(decision, dict)
            or decision.get("status") != "confirmed"
            or set(decision.get("authorized_closures", []))
            != confirmed_closures
        ):
            raise FixtureError(
                "confirmed closures are absent from replay decision"
            )
    if isinstance(decision, dict):
        decision_segments = [
            (
                segment["id"],
                segment["lines"],
                segment["disposition"],
                segment["destination"],
                segment["decision"],
            )
            for segment in decision.get("segments", [])
        ]
        if plan["adoption"] != decision_segments:
            raise FixtureError(
                "adoption decisions differ from replay decision"
            )
    legacy_warnings = _legacy_marker_warnings(input_tree)
    if legacy_warnings:
        serialized_legacy = sorted(
            line
            for line in plan["warnings"]
            if line.startswith("- legacy-managed-mode: ")
            or line.startswith("- marker-anomaly: ")
        )
        if serialized_legacy != legacy_warnings:
            raise FixtureError(
                "legacy marker warning set differs from exact input lines"
            )
    fallback_warnings = [
        _validate_warning_line(Path(plan["path"]), line)
        for line in plan["warnings"]
        if line != "- (none)"
        and line.startswith("- fallback-shadow: ")
    ]
    if fallback_warnings:
        if len(fallback_warnings) != 1:
            raise FixtureError("fallback shadow warning must be singular")
        fallback_path = fallback_warnings[0][1]
        fallback_names = payload["profile"]["facts"].get(
            "fallback_filenames"
        )
        if (
            not isinstance(fallback_names, list)
            or fallback_path not in fallback_names
            or fallback_path not in input_tree
            or "AGENTS.md" in input_tree
            or len(plan["rows"]) != 1
            or plan["rows"][0][0] != "onboarding/covenant"
            or plan["rows"][0][1]
            != "closure/decision/onboarding/covenant"
            or plan["rows"][0][2] != "selected"
            or plan["rows"][0][4] != "blocked"
            or plan["rows"][0][5] != "resolve-blocker"
            or plan["rows"][0][7] != "not-applicable"
            or plan["rows"][0][8] != "blocked"
            or plan["write_capabilities"]
            or plan["adoption"]
        ):
            raise FixtureError(
                "fallback shadow plan escaped the covenant blocker scope"
            )
    capability_facts = payload["capability"]["facts"]
    capability_operations = capability_facts.get("operations", [])
    unavailable_empty_bootstrap = (
        set(COVENANT_CARRIERS).isdisjoint(input_tree)
        and len(capability_operations) == 2
        and {
            (
                operation.get("path"),
                operation.get("operation"),
                operation.get("protocol"),
            )
            for operation in capability_operations
        }
        == {
            (
                ".claude/rules/bridge-covenant.md",
                "create",
                "unavailable",
            ),
            ("AGENTS.md", "create", "unavailable"),
        }
    )
    if unavailable_empty_bootstrap and (
        [row[0] for row in plan["rows"]] != ["onboarding/covenant"]
        or plan["adoption"]
    ):
        raise FixtureError(
            "empty unavailable bootstrap may not invent "
            "onboarding/agents-md segmentation"
        )
    _validate_empty_bootstrap_temporal_plan(
        plan,
        temporal_context=temporal_context,
    )
    if lifecycle in {"verified", "closed"} and any(
        row[8] == "applied" for row in plan["rows"]
    ):
        differences = compare_tree(root, rendered_tree)
        if differences:
            raise FixtureError(
                "verified applied plan differs from bound render: "
                + "; ".join(differences)
            )
    fault_schedule = payload["fault_schedule"]
    if fault_schedule is not None and lifecycle in post_lifecycles:
        document = fault_schedule["facts"]
        if document["phase"] != (
            "after-confirmation-before-final-preflight"
        ):
            raise FixtureError("post-fault evidence has the wrong phase")
        if lifecycle != "failed":
            raise FixtureError(
                "preflight fault evidence requires failed lifecycle"
            )
        try:
            _validate_injected_fault_evidence(
                plan,
                root=root,
                lease=lease,
                envelope=envelope,
            )
        except (FixtureError, OSError) as error:
            raise FixtureError(
                f"fault receipt evidence is invalid: {error}"
            ) from error
    serialized_untracked = sorted(
        warning_path
        for line in plan["warnings"]
        if line != "- (none)"
        for warning_token, warning_path, _ in [
            _validate_warning_line(Path(plan["path"]), line)
        ]
        if warning_token == "untracked-files-included"
    )
    if actual_untracked != serialized_untracked:
        raise FixtureError(
            "untracked warning set differs from live scan context"
        )


def _validator_failure(error: Exception) -> str:
    failure = _validator_failure_token(error)
    if failure not in PLAN_VALIDATOR_FAILURES:
        raise FixtureError(
            f"unregistered plan validator failure id {failure!r}"
        )
    return failure


def _validator_failure_token(error: Exception) -> str:
    message = str(error).lower()
    if "composition" in message:
        return "hooks-carrier-composition"
    if "warning" in message or "untracked" in message:
        return "warning-grammar"
    if (
        "fixture" in message
        and (
            "attest" in message
            or "marker" in message
            or "lease" in message
            or "capability" in message
        )
    ) or any(
        token in message
        for token in ("commitment", "fault armed", "fault claim", "receipt")
    ):
        return "fixture-attestation"
    if "capability" in message or "protocol" in message:
        return "write-capability"
    if any(
        token in message
        for token in ("phase", "lifecycle", "restart", "live-activation")
    ):
        return "phase-lifecycle"
    if "migration" in message:
        return "migration-candidates"
    if "adoption" in message or "segment" in message:
        return "adoption-consistency"
    if "decision" in message:
        return "decision-transition"
    if any(
        token in message
        for token in ("unit", "closure", "authorization", "selection")
    ):
        return "unit-closure"
    return "document-grammar"


def _validate_plan_bytes_core(
    *,
    replay_input: str,
    root: Path,
    lease: str,
    plan_bytes: bytes,
    lifecycle: str,
    envelope: Mapping[str, Any],
    actual_untracked: Sequence[str],
) -> Tuple[Dict[str, Any], Optional[Plan]]:
    context: Dict[str, Any] = {
        "replay_input": replay_input,
        "resolved_root": str(root.resolve()),
        "lifecycle": lifecycle,
        "binding": copy.deepcopy(envelope["payload"]["binding"]),
        "live_untracked": list(actual_untracked),
    }
    failures: List[str] = []
    plan: Optional[Plan] = None
    scratch = Path(
        tempfile.mkdtemp(
            prefix="bridge-formal-plan-",
            dir=str(os_temp_root()),
        )
    )
    scratch_path = scratch / "captured-plan.md"
    primary_error: Optional[BaseException] = None
    try:
        os.chmod(scratch, 0o700)
        _write_exclusive_bytes(
            scratch_path,
            plan_bytes,
            label="formal plan snapshot",
        )
        temporal_context = _derive_plan_temporal_context(
            envelope=envelope,
            lifecycle=lifecycle,
            actual_untracked=actual_untracked,
        )
        context["temporal_context"] = temporal_context
        plan = parse_plan(scratch_path, expectation=False)
        _validate_plan_replay_context(
            plan,
            envelope=envelope,
            root=root,
            lease=lease,
            lifecycle=lifecycle,
            temporal_context=temporal_context,
            actual_untracked=actual_untracked,
        )
    except (FixtureError, OSError, UnicodeError, ValueError) as error:
        failures.append(_validator_failure(error))
    except BaseException as error:
        primary_error = error
        raise
    finally:
        try:
            strict_remove_tree(scratch)
        except (FixtureError, OSError) as cleanup_error:
            if primary_error is not None:
                primary_error.add_note(
                    "formal plan core cleanup also failed: "
                    + str(cleanup_error)
                )
            else:
                raise
    result = {
        "contract": PLAN_VALIDATOR_SPEC,
        "plan_sha256": _sha256(plan_bytes),
        "context_sha256": _sha256(_canonical_json_bytes(context)),
        "pass": not failures,
        "failures": sorted(set(failures)),
    }
    return result, plan


def _validate_plan_snapshot(
    *,
    replay_input: str,
    root: Path,
    lease: str,
    plan_bytes: bytes,
    lifecycle: str,
) -> Tuple[Dict[str, Any], Optional[Plan]]:
    context: Dict[str, Any] = {
        "replay_input": replay_input,
        "resolved_root": str(root.resolve()),
        "lifecycle": lifecycle,
    }
    try:
        envelope = _validate_blind_installed_replay_input(
            root,
            lease=lease,
            replay_id=replay_input,
            require_input_tree=False,
        )
        actual_untracked = _live_untracked_paths(root)
    except (FixtureError, OSError, UnicodeError, ValueError) as error:
        return (
            {
                "contract": PLAN_VALIDATOR_SPEC,
                "plan_sha256": _sha256(plan_bytes),
                "context_sha256": _sha256(
                    _canonical_json_bytes(context)
                ),
                "pass": False,
                "failures": [_validator_failure(error)],
            },
            None,
        )
    return _validate_plan_bytes_core(
        replay_input=replay_input,
        root=root,
        lease=lease,
        plan_bytes=plan_bytes,
        lifecycle=lifecycle,
        envelope=envelope,
        actual_untracked=actual_untracked,
    )


def _validate_plan_result(
    *,
    replay_input: str,
    root: Path,
    lease: str,
    plan_path: Path,
    lifecycle: str,
) -> Dict[str, Any]:
    try:
        captured_plan = inspect_root_child(
            plan_path.parent, plan_path.name
        )
    except (FixtureError, OSError):
        return {
            "contract": PLAN_VALIDATOR_SPEC,
            "plan_sha256": None,
            "context_sha256": None,
            "pass": False,
            "failures": ["document-grammar"],
        }
    result, _ = _validate_plan_snapshot(
        replay_input=replay_input,
        root=root,
        lease=lease,
        plan_bytes=captured_plan["bytes"],
        lifecycle=lifecycle,
    )
    return result


def _diagnostic_item(
    kind: str,
    *,
    section: str,
    token: Optional[str] = None,
    path: Optional[str] = None,
    detail: Optional[str] = None,
    actual_line: Optional[str] = None,
    required_line: Optional[str] = None,
    actual_count: Optional[int] = None,
    required_count: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "actual_count": actual_count,
        "actual_line": actual_line,
        "detail": detail,
        "kind": kind,
        "path": path,
        "required_count": required_count,
        "required_line": required_line,
        "section": section,
        "token": token,
    }


def _diagnostic_sort_key(item: Mapping[str, Any]) -> Tuple[bytes, ...]:
    return tuple(
        (
            ""
            if item.get(field) is None
            else str(item[field])
        ).encode("utf-8")
        for field in (
            "section",
            "kind",
            "token",
            "path",
            "actual_line",
            "required_line",
            "detail",
            "actual_count",
            "required_count",
        )
    )


def _warning_section_lines(plan_bytes: bytes) -> List[str]:
    lines = normalize_n(plan_bytes).decode("utf-8").split("\n")
    headings = [
        index for index, line in enumerate(lines) if line == "## Warnings"
    ]
    if len(headings) != 1:
        raise FixtureError(
            "diagnostic plan must contain one exact Warnings section"
        )
    start = headings[0] + 1
    end = next(
        (
            index
            for index in range(start, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    content = [line for line in lines[start:end] if line]
    if not content:
        raise FixtureError("diagnostic Warnings section is empty")
    return content


def _live_tracked_changes(root: Path) -> List[str]:
    return sorted(
        {
            line.replace("\\", "/")
            for line in git_run(
                root,
                "diff",
                "--name-only",
                "HEAD",
                "--",
            ).splitlines()
            if line
        },
        key=lambda value: value.encode("utf-8"),
    )


def _migration_transition_is_uncommitted(
    *,
    envelope: Mapping[str, Any],
    root: Path,
    lifecycle: str,
) -> bool:
    if lifecycle not in {"verified", "closed"}:
        return False
    payload = envelope["payload"]
    capability_operations = payload["capability"]["facts"].get(
        "operations", []
    )
    render_operations = payload["render"].get("operations", [])
    decision = payload["decision"]
    if (
        not capability_operations
        or not isinstance(render_operations, list)
        or len(render_operations) != len(capability_operations)
        or any(
            operation.get("closure") != "closure/migration"
            for operation in capability_operations
        )
        or not isinstance(decision, dict)
        or decision.get("status") != "confirmed"
        or "closure/migration"
        not in decision.get("authorized_closures", [])
    ):
        return False
    capability_shape = {
        (operation.get("path"), operation.get("operation"))
        for operation in capability_operations
    }
    render_shape = {
        (operation.get("path"), operation.get("operation"))
        for operation in render_operations
    }
    if capability_shape != render_shape:
        return False
    input_tree = _facts_tree(payload["input"]["files"])
    rendered_tree = _rendered_tree_from_envelope(
        input_tree, render_operations
    )
    if compare_tree(root, rendered_tree):
        return False
    operation_paths = {
        str(operation["path"]) for operation in capability_operations
    }
    return bool(operation_paths & set(_live_tracked_changes(root)))


def _required_public_warning_lines(
    *,
    envelope: Mapping[str, Any],
    root: Path,
    lifecycle: str,
    temporal_context: str,
    actual_untracked: Sequence[str],
) -> List[str]:
    payload = envelope["payload"]
    input_tree = _facts_tree(payload["input"]["files"])
    operations = payload["capability"]["facts"].get("operations", [])
    warnings = set(_legacy_marker_warnings(input_tree))
    unavailable_conditional_closures = {
        operation["closure"]
        for operation in operations
        if operation.get("protocol") == "unavailable"
        and operation.get("operation") in {"create", "delete"}
    }
    operation_closures = {
        operation["closure"] for operation in operations
    }
    decision = payload["decision"]
    authorized_closures = (
        set(decision.get("authorized_closures", []))
        if isinstance(decision, dict)
        and decision.get("status") == "confirmed"
        else set()
    )
    if operations and not operation_closures.issubset(
        authorized_closures
    ):
        warnings.add("- authorization-incomplete: .")
    for operation in operations:
        relative = operation["path"]
        protocol = operation["protocol"]
        if protocol == "guarded-patch/v1":
            warnings.add(f"- guarded-patch-non-cas: {relative}")
            if relative == "AGENTS.md":
                warnings.add("- manual-zone-guarded: AGENTS.md")
        elif protocol == "strict-replace/v1" and relative == "AGENTS.md":
            warnings.add("- manual-zone-preserved: AGENTS.md")
        if (
            operation["inverse_protocol"] == "unavailable"
            and protocol != "unavailable"
        ):
            warnings.add(
                f"- strict-compensation-unavailable: {relative}"
            )
        if protocol == "unavailable":
            token = (
                "conditional-write-unavailable"
                if operation["closure"] in unavailable_conditional_closures
                else "guarded-patch-unavailable"
            )
            warnings.add(f"- {token}: {relative}")
    for relative in actual_untracked:
        warnings.add(f"- untracked-files-included: {relative}")
    if temporal_context == EMPTY_UNTRACKED_SCAN_CONTEXT:
        for relative in COVENANT_CARRIERS:
            warnings.add(
                f"- covenant-anchor-anomaly: {relative} (untracked)"
            )
    if _migration_transition_is_uncommitted(
        envelope=envelope,
        root=root,
        lifecycle=lifecycle,
    ):
        warnings.add("- migration-transition-uncommitted: .")
    return sorted(warnings, key=lambda value: value.encode("utf-8"))


def _warning_diagnostics(
    plan_bytes: bytes,
    *,
    required_lines: Sequence[str],
) -> List[Dict[str, Any]]:
    try:
        actual_lines = _warning_section_lines(plan_bytes)
    except (FixtureError, UnicodeError):
        return [
            _diagnostic_item(
                "generic",
                section="warnings",
                detail="warning-section",
            )
        ]
    if actual_lines == ["- (none)"]:
        actual_lines = []
    elif "- (none)" in actual_lines:
        return [
            _diagnostic_item(
                "cardinality",
                section="warnings",
                detail="warning-sentinel",
                actual_line="- (none)",
                actual_count=actual_lines.count("- (none)"),
                required_count=0,
            )
        ]

    diagnostics: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    for line in actual_lines:
        counts[line] = counts.get(line, 0) + 1
    for line, count in counts.items():
        if count > 1:
            diagnostics.append(
                _diagnostic_item(
                    "cardinality",
                    section="warnings",
                    detail="duplicate-warning",
                    actual_line=line,
                    required_line=(
                        line if line in required_lines else None
                    ),
                    actual_count=count,
                    required_count=1,
                )
            )

    valid_by_line: Dict[str, Tuple[str, str, Optional[str]]] = {}
    malformed = False
    for line in counts:
        loose = WARNING_DIAGNOSTIC_PATTERN.fullmatch(line)
        if loose is None:
            malformed = True
            diagnostics.append(
                _diagnostic_item(
                    "generic",
                    section="warnings",
                    detail="malformed-warning",
                    actual_line=line,
                    actual_count=counts[line],
                )
            )
            continue
        token, remainder = loose.groups()
        if token not in PLAN_WARNINGS:
            malformed = True
            diagnostics.append(
                _diagnostic_item(
                    "token",
                    section="warnings",
                    token=token,
                    detail="unknown-warning-token",
                    actual_line=line,
                    actual_count=counts[line],
                    required_count=0,
                )
            )
            continue
        try:
            parsed = _validate_warning_line(
                Path("captured-plan.md"), line
            )
        except FixtureError:
            malformed = True
            strict = WARNING_LINE_PATTERN.fullmatch(line)
            relative = None if strict is None else strict.group(2)
            path_invalid = False
            if strict is not None:
                if token in ROOT_PATH_WARNING_TOKENS:
                    path_invalid = relative != "."
                elif relative == ".":
                    path_invalid = True
                else:
                    try:
                        safe_relative(
                            relative,
                            field="diagnostic warning path",
                        )
                    except FixtureError:
                        path_invalid = True
            diagnostics.append(
                _diagnostic_item(
                    "path" if path_invalid else "generic",
                    section="warnings",
                    token=token,
                    path=relative,
                    detail=(
                        "invalid-warning-path"
                        if path_invalid
                        else "malformed-warning"
                    ),
                    actual_line=line,
                    actual_count=counts[line],
                )
            )
            continue
        valid_by_line[line] = parsed

    unique_actual_lines = list(dict.fromkeys(actual_lines))
    if (
        not malformed
        and not any(count > 1 for count in counts.values())
        and unique_actual_lines
        != sorted(
            unique_actual_lines,
            key=lambda value: value.encode("utf-8"),
        )
    ):
        ordered = sorted(
            unique_actual_lines,
            key=lambda value: value.encode("utf-8"),
        )
        mismatch = next(
            index
            for index, (actual, required) in enumerate(
                zip(unique_actual_lines, ordered)
            )
            if actual != required
        )
        diagnostics.append(
            _diagnostic_item(
                "invalid-order",
                section="warnings",
                detail="byte-wise-whole-line-order",
                actual_line=unique_actual_lines[mismatch],
                required_line=ordered[mismatch],
                actual_count=1,
                required_count=1,
            )
        )

    required_by_line = {
        line: _validate_warning_line(Path("public-context"), line)
        for line in required_lines
    }
    matched = set(valid_by_line) & set(required_by_line)
    for token in sorted(PUBLIC_DERIVED_WARNING_TOKENS):
        actual_for_token = sorted(
            (
                line
                for line, parsed in valid_by_line.items()
                if parsed[0] == token and line not in matched
            ),
            key=lambda value: value.encode("utf-8"),
        )
        required_for_token = sorted(
            (
                line
                for line, parsed in required_by_line.items()
                if parsed[0] == token and line not in matched
            ),
            key=lambda value: value.encode("utf-8"),
        )
        paired = min(len(actual_for_token), len(required_for_token))
        for index in range(paired):
            actual_line = actual_for_token[index]
            required_line = required_for_token[index]
            actual_path = valid_by_line[actual_line][1]
            diagnostics.append(
                _diagnostic_item(
                    "path",
                    section="warnings",
                    token=token,
                    path=actual_path,
                    detail="warning-path-binding",
                    actual_line=actual_line,
                    required_line=required_line,
                    actual_count=counts[actual_line],
                    required_count=1,
                )
            )
        for required_line in required_for_token[paired:]:
            diagnostics.append(
                _diagnostic_item(
                    "missing",
                    section="warnings",
                    token=token,
                    path=required_by_line[required_line][1],
                    detail="public-context-warning",
                    required_line=required_line,
                    actual_count=0,
                    required_count=1,
                )
            )
        for actual_line in actual_for_token[paired:]:
            diagnostics.append(
                _diagnostic_item(
                    "extra",
                    section="warnings",
                    token=token,
                    path=valid_by_line[actual_line][1],
                    detail="public-context-warning",
                    actual_line=actual_line,
                    actual_count=counts[actual_line],
                    required_count=0,
                )
            )
    return sorted(diagnostics, key=_diagnostic_sort_key)


def _validate_plan_diagnostic_result(
    result: Mapping[str, Any],
) -> None:
    if set(result) != {
        "contract",
        "plan_sha256",
        "context_sha256",
        "failures",
        "diagnostics",
    } or result.get("contract") != PLAN_DIAGNOSTIC_SPEC:
        raise FixtureError("plan diagnostic result fields are not closed")
    for field in ("plan_sha256", "context_sha256"):
        value = result[field]
        if value is not None and (
            not isinstance(value, str)
            or SHA256_PATTERN.fullmatch(value) is None
        ):
            raise FixtureError(
                f"plan diagnostic {field} is not a SHA-256 or null"
            )
    failures = result["failures"]
    diagnostics = result["diagnostics"]
    if (
        not isinstance(failures, list)
        or failures != sorted(set(failures))
        or any(
            not isinstance(failure, str)
            or TOKEN_PATTERN.fullmatch(failure) is None
            for failure in failures
        )
        or not isinstance(diagnostics, list)
        or diagnostics
        != sorted(diagnostics, key=_diagnostic_sort_key)
    ):
        raise FixtureError(
            "plan diagnostic failures/diagnostics are not canonical"
        )
    for item in diagnostics:
        if (
            not isinstance(item, dict)
            or set(item) != PLAN_DIAGNOSTIC_FIELDS
            or item["kind"] not in PLAN_DIAGNOSTIC_KINDS
            or item["section"] not in {"plan", "warnings"}
        ):
            raise FixtureError(
                "plan diagnostic item fields are not closed"
            )
        for field in (
            "actual_line",
            "detail",
            "path",
            "required_line",
            "token",
        ):
            if item[field] is not None and not isinstance(
                item[field], str
            ):
                raise FixtureError(
                    f"plan diagnostic {field} must be text or null"
                )
        for field in ("actual_count", "required_count"):
            if item[field] is not None and (
                not isinstance(item[field], int) or item[field] < 0
            ):
                raise FixtureError(
                    f"plan diagnostic {field} must be non-negative or null"
                )


def _explain_plan_result(
    *,
    replay_input: str,
    root: Path,
    lease: str,
    plan_path: Path,
    lifecycle: str,
) -> Dict[str, Any]:
    try:
        captured_plan = inspect_root_child(
            plan_path.parent, plan_path.name
        )
    except (FixtureError, OSError):
        result = {
            "contract": PLAN_DIAGNOSTIC_SPEC,
            "plan_sha256": None,
            "context_sha256": None,
            "failures": ["document-grammar"],
            "diagnostics": [
                _diagnostic_item(
                    "generic",
                    section="plan",
                    detail="document-grammar",
                )
            ],
        }
        _validate_plan_diagnostic_result(result)
        return result

    validation, _ = _validate_plan_snapshot(
        replay_input=replay_input,
        root=root,
        lease=lease,
        plan_bytes=captured_plan["bytes"],
        lifecycle=lifecycle,
    )
    diagnostics: List[Dict[str, Any]] = []
    try:
        envelope = _validate_blind_installed_replay_input(
            root,
            lease=lease,
            replay_id=replay_input,
            require_input_tree=False,
        )
        actual_untracked = _live_untracked_paths(root)
        temporal_context = _derive_plan_temporal_context(
            envelope=envelope,
            lifecycle=lifecycle,
            actual_untracked=actual_untracked,
        )
        required_lines = _required_public_warning_lines(
            envelope=envelope,
            root=root,
            lifecycle=lifecycle,
            temporal_context=temporal_context,
            actual_untracked=actual_untracked,
        )
        diagnostics.extend(
            _warning_diagnostics(
                captured_plan["bytes"],
                required_lines=required_lines,
            )
        )
    except (FixtureError, OSError, UnicodeError, ValueError):
        diagnostics.append(
            _diagnostic_item(
                "generic",
                section="plan",
                detail="fixture-attestation",
            )
        )
    warning_explained = any(
        item["section"] == "warnings" for item in diagnostics
    )
    for failure in validation["failures"]:
        if failure == "warning-grammar" and warning_explained:
            continue
        generic = _diagnostic_item(
            "generic",
            section="plan",
            detail=failure,
        )
        if generic not in diagnostics:
            diagnostics.append(generic)
    result = {
        "contract": PLAN_DIAGNOSTIC_SPEC,
        "plan_sha256": validation["plan_sha256"],
        "context_sha256": validation["context_sha256"],
        "failures": validation["failures"],
        "diagnostics": sorted(
            diagnostics, key=_diagnostic_sort_key
        ),
    }
    _validate_plan_diagnostic_result(result)
    return result


def command_validate_plan(arguments: argparse.Namespace) -> int:
    _reject_recovery_claim(Path(arguments.worktree))
    result = _validate_plan_result(
        replay_input=arguments.replay_input,
        root=Path(arguments.worktree),
        lease=arguments.lease,
        plan_path=Path(arguments.plan),
        lifecycle=arguments.operation_lifecycle,
    )
    _json_output(result)
    return 0 if result["pass"] else 1


def command_explain_plan(arguments: argparse.Namespace) -> int:
    _reject_recovery_claim(Path(arguments.worktree))
    result = _explain_plan_result(
        replay_input=arguments.replay_input,
        root=Path(arguments.worktree),
        lease=arguments.lease,
        plan_path=Path(arguments.plan),
        lifecycle=arguments.operation_lifecycle,
    )
    _json_output(result)
    return 0 if not result["failures"] and not result["diagnostics"] else 1


def command_compare(arguments: argparse.Namespace) -> int:
    _reject_recovery_claim(Path(arguments.worktree))
    definition, parsed = _scenario(arguments.scenario)
    item = _expectation(parsed, arguments.expectation)
    marker = validate_marker(
        Path(arguments.worktree),
        suite=SUITE,
        scenario=arguments.scenario,
        lease=arguments.lease,
    )
    _validate_installed_activation_profile(
        Path(arguments.worktree), parsed["activation_profile"]
    )
    _validate_installed_replay_input(
        Path(arguments.worktree),
        lease=arguments.lease,
        scenario_id=arguments.scenario,
        parsed=parsed,
        replay_input=item["replay_input"],
    )
    actual = parse_plan(Path(arguments.actual_plan), expectation=False)
    expected = bind_expected_baselines(
        definition,
        item["definition"],
        item["plan"],
        initial_commit=marker["baseline_commit"],
        history_commits=marker.get("history_commits"),
    )
    plan_errors = compare_plans(expected, actual)
    tree_errors = compare_tree(Path(arguments.worktree), item["tree"])
    passed = not plan_errors and not tree_errors
    _json_output(
        {
            "pass": passed,
            "scenario": arguments.scenario,
            "expectation": arguments.expectation,
            "plan_differences": plan_errors,
            "tree_differences": tree_errors,
            "coverage": item["definition"]["covers"],
        }
    )
    return 0 if passed else 1


class _QuarantinedCleanupError(FixtureError):
    def __init__(
        self,
        message: str,
        *,
        original: Path,
        tombstone: Path,
        root_identity: Mapping[str, Any],
        state: str,
        partial_deletion: bool,
        removed_entries: Optional[Sequence[str]] = None,
    ) -> None:
        super().__init__(message)
        tombstone_retained = os.path.lexists(tombstone)
        if state not in {"quarantined", "partial"}:
            raise FixtureError(
                "stale recovery failure state is invalid"
            )
        self.result = {
            "pass": False,
            "contract": STALE_RECOVERY_SPEC,
            "state": state,
            "error": message,
            "original_root": str(original),
            "tombstone": str(tombstone),
            "root_identity": dict(root_identity),
            "original_preserved_if_recreated": True,
            "siblings_enumerated": False,
            "recoverable": False,
            "tombstone_retained": tombstone_retained,
            "partial_deletion": partial_deletion,
            "removed_entries": list(removed_entries or []),
            "product_cleanup": False,
            "synthetic_fixture_data_only": True,
        }


def _stale_canonical_root(
    raw_root: str,
    *,
    scenario: str,
    nonce: str,
) -> Path:
    if (
        not isinstance(raw_root, str)
        or "\x00" in raw_root
        or not Path(raw_root).is_absolute()
    ):
        raise FixtureError(
            "stale recovery root must be one explicit absolute path"
        )
    absolute = Path(os.path.abspath(raw_root))
    if raw_root != str(absolute):
        raise FixtureError(
            "stale recovery root must already be lexically canonical"
        )
    if (
        not isinstance(nonce, str)
        or NONCE_PATTERN.fullmatch(nonce) is None
    ):
        raise FixtureError("stale recovery nonce is invalid")
    resolved, observed_nonce = validate_temp_root(
        absolute,
        suite=SUITE,
        scenario=scenario,
    )
    if (
        observed_nonce != nonce
        or str(resolved) != raw_root
        or str(absolute.resolve(strict=True)) != raw_root
    ):
        raise FixtureError(
            "stale recovery root/basename/nonce identity is not exact"
        )
    return resolved


def _closed_json_object(raw: bytes, *, label: str) -> Dict[str, Any]:
    def pairs(items: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
        value: Dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise FixtureError(
                    f"{label} contains duplicate key {key!r}"
                )
            value[key] = item
        return value

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise FixtureError(f"cannot parse {label}: {error}") from error
    if not isinstance(value, dict):
        raise FixtureError(f"{label} must be one JSON object")
    return value


def _pretty_marker_bytes(marker: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            marker,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _validate_stale_marker(
    *,
    root: Path,
    scenario: str,
    nonce: str,
    marker_snapshot: Mapping[str, Any],
    expected_sha256: str,
    git_store: RetainedRootDirectory,
) -> Dict[str, Any]:
    if (
        not isinstance(expected_sha256, str)
        or SHA256_PATTERN.fullmatch(expected_sha256) is None
    ):
        raise FixtureError(
            "stale recovery marker SHA-256 must be lowercase 64-hex"
        )
    raw = marker_snapshot["bytes"]
    observed_sha256 = _sha256(raw)
    if not hmac.compare_digest(observed_sha256, expected_sha256):
        raise FixtureError("stale recovery raw marker SHA-256 mismatch")
    marker = _closed_json_object(raw, label="stale recovery marker")
    base_required = {
        "spec",
        "suite",
        "scenario",
        "nonce",
        "resolved_root",
        "lease_sha256",
        "baseline_commit",
    }
    base_optional = {"history_commits"}
    extended_required = {
        "replay_input",
        "write_capability_sha256",
        "commitment_sha256",
    }
    extended_optional = {"fault_schedule_sha256"}
    fields = set(marker)
    if base_required.issubset(fields) and fields <= (
        base_required | base_optional
    ):
        marker_kind = "base"
        canonical = _pretty_marker_bytes(marker)
    elif (base_required | extended_required).issubset(fields) and fields <= (
        base_required
        | base_optional
        | extended_required
        | extended_optional
    ):
        marker_kind = "extended"
        canonical = _canonical_json_bytes(marker)
    else:
        raise FixtureError("stale recovery marker fields are not closed")
    if raw != canonical:
        raise FixtureError(
            f"stale recovery {marker_kind} marker is not canonical"
        )
    expected = {
        "spec": MARKER_SPEC,
        "suite": SUITE,
        "scenario": scenario,
        "nonce": nonce,
        "resolved_root": str(root),
    }
    for key, value in expected.items():
        if marker.get(key) != value:
            raise FixtureError(
                f"stale recovery marker mismatch for {key}"
            )
    if (
        not isinstance(marker["lease_sha256"], str)
        or SHA256_PATTERN.fullmatch(marker["lease_sha256"]) is None
        or not isinstance(marker["baseline_commit"], str)
        or HASH_PATTERN.fullmatch(marker["baseline_commit"]) is None
    ):
        raise FixtureError("stale recovery marker hashes are invalid")
    history = marker.get("history_commits")
    if history is not None and (
        not isinstance(history, dict)
        or not history
        or any(
            not isinstance(name, str)
            or TOKEN_PATTERN.fullmatch(name) is None
            or not isinstance(commit, str)
            or HASH_PATTERN.fullmatch(commit) is None
            for name, commit in history.items()
        )
    ):
        raise FixtureError(
            "stale recovery marker history fields are invalid"
        )
    if marker_kind == "extended":
        if (
            not isinstance(marker["replay_input"], str)
            or TOKEN_PATTERN.fullmatch(marker["replay_input"]) is None
            or any(
                not isinstance(marker[field], str)
                or SHA256_PATTERN.fullmatch(marker[field]) is None
                for field in (
                    "write_capability_sha256",
                    "commitment_sha256",
                )
            )
            or (
                "fault_schedule_sha256" in marker
                and (
                    not isinstance(
                        marker["fault_schedule_sha256"], str
                    )
                    or SHA256_PATTERN.fullmatch(
                        marker["fault_schedule_sha256"]
                    )
                    is None
                )
            )
        ):
            raise FixtureError(
                "stale recovery extended marker fields are invalid"
            )
        referenced = {
            WRITE_CAPABILITY_TARGET: marker[
                "write_capability_sha256"
            ],
            REPLAY_COMMITMENT_TARGET: marker["commitment_sha256"],
        }
        if "fault_schedule_sha256" in marker:
            referenced[FAULT_SCHEDULE_TARGET] = marker[
                "fault_schedule_sha256"
            ]
        for name, digest in referenced.items():
            snapshot = git_store.read(name)
            if not hmac.compare_digest(
                snapshot["raw_sha256"], digest
            ):
                raise FixtureError(
                    f"stale recovery referenced digest mismatch: {name}"
                )
            _parse_canonical_json_bytes(
                snapshot["bytes"], label=f"stale recovery {name}"
            )
        replay_snapshot = git_store.read(REPLAY_INPUT_TARGET)
        _parse_canonical_json_bytes(
            replay_snapshot["bytes"],
            label="stale recovery replay input",
        )
    return {
        "kind": marker_kind,
        "marker": marker,
        "raw_sha256": observed_sha256,
        "snapshot": copy.deepcopy(marker_snapshot),
    }


def _stale_git(
    root: Path, *arguments: str, allow_empty: bool = False
) -> bytes:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        }
    )
    process = subprocess.run(
        ["git", "-C", str(root), *arguments],
        cwd=os_temp_root(),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise FixtureError(
            "stale recovery Git validation failed for "
            f"{' '.join(arguments)}: "
            + process.stderr.decode("utf-8", errors="replace").strip()
        )
    if not allow_empty and not process.stdout:
        raise FixtureError(
            f"stale recovery Git {' '.join(arguments)} returned no evidence"
        )
    return process.stdout


def _git_path(root: Path, raw: bytes, *, label: str) -> Path:
    try:
        text = raw.decode("utf-8", errors="strict").strip()
    except UnicodeError as error:
        raise FixtureError(
            f"stale recovery {label} is not UTF-8"
        ) from error
    value = Path(text)
    if not value.is_absolute():
        value = root / value
    try:
        return value.resolve(strict=True)
    except OSError as error:
        raise FixtureError(
            f"stale recovery cannot resolve {label}: {error}"
        ) from error


def _validate_stale_git(
    root: Path,
    *,
    marker: Mapping[str, Any],
) -> Dict[str, Any]:
    expected_git = (root / ".git").resolve(strict=True)
    top = _git_path(
        root,
        _stale_git(root, "rev-parse", "--show-toplevel"),
        label="Git top-level",
    )
    git_directory = _git_path(
        root,
        _stale_git(root, "rev-parse", "--absolute-git-dir"),
        label="Git directory",
    )
    common_directory = _git_path(
        root,
        _stale_git(root, "rev-parse", "--git-common-dir"),
        label="Git common directory",
    )
    object_directory = _git_path(
        root,
        _stale_git(root, "rev-parse", "--git-path", "objects"),
        label="Git object directory",
    )
    if (
        top != root
        or git_directory != expected_git
        or common_directory != expected_git
        or object_directory != (expected_git / "objects").resolve(
            strict=True
        )
    ):
        raise FixtureError(
            "stale recovery Git topology escaped the exact root"
        )
    if (
        _stale_git(root, "rev-parse", "--is-inside-work-tree").strip()
        != b"true"
        or _stale_git(root, "rev-parse", "--is-bare-repository").strip()
        != b"false"
    ):
        raise FixtureError(
            "stale recovery requires one non-bare worktree"
        )
    superproject = _stale_git(
        root,
        "rev-parse",
        "--show-superproject-working-tree",
        allow_empty=True,
    ).strip()
    if superproject:
        raise FixtureError(
            "stale recovery rejects a submodule worktree"
        )
    object_format = _stale_git(
        root, "rev-parse", "--show-object-format"
    ).decode("ascii", errors="strict").strip()
    hash_length = {"sha1": 40, "sha256": 64}.get(object_format)
    baseline = marker["baseline_commit"]
    if hash_length is None or len(baseline) != hash_length:
        raise FixtureError(
            "stale recovery Git object format/baseline mismatch"
        )
    head = _stale_git(root, "rev-parse", "HEAD").decode(
        "ascii", errors="strict"
    ).strip()
    verified = _stale_git(
        root, "rev-parse", "--verify", f"{baseline}^{{commit}}"
    ).decode("ascii", errors="strict").strip()
    if head != baseline or verified != baseline:
        raise FixtureError(
            "stale recovery HEAD no longer equals the marker baseline"
        )
    if os.path.lexists(expected_git / "commondir"):
        raise FixtureError("stale recovery rejects Git commondir")
    alternates = expected_git / "objects" / "info" / "alternates"
    if os.path.lexists(alternates):
        raise FixtureError("stale recovery rejects Git alternates")
    if os.path.lexists(expected_git / "worktrees"):
        raise FixtureError("stale recovery rejects linked Git worktrees")
    if os.path.lexists(expected_git / "modules"):
        raise FixtureError("stale recovery rejects nested Git modules")
    for record in _stale_git(
        root, "ls-files", "--stage", "-z", allow_empty=True
    ).split(b"\0"):
        if not record:
            continue
        metadata = record.split(b"\t", 1)[0].split()
        if (
            len(metadata) != 3
            or metadata[0] in {b"120000", b"160000"}
            or metadata[2] != b"0"
        ):
            raise FixtureError(
                "stale recovery rejects gitlinks, symlinks, and "
                "unmerged index entries"
            )
    for record in _stale_git(
        root, "ls-tree", "-r", "-z", "HEAD", allow_empty=True
    ).split(b"\0"):
        if not record:
            continue
        metadata = record.split(b"\t", 1)[0].split()
        if len(metadata) < 1 or metadata[0] in {b"120000", b"160000"}:
            raise FixtureError(
                "stale recovery rejects HEAD gitlinks and symlinks"
            )
    history = marker.get("history_commits")
    if history is not None:
        reachable = set(
            _stale_git(root, "rev-list", baseline)
            .decode("ascii", errors="strict")
            .splitlines()
        )
        for name, commit in history.items():
            exact = _stale_git(
                root,
                "rev-parse",
                "--verify",
                f"{commit}^{{commit}}",
            ).decode("ascii", errors="strict").strip()
            if exact != commit or commit not in reachable:
                raise FixtureError(
                    f"stale recovery history commit is invalid: {name}"
                )
    return {
        "top_level": str(top),
        "git_directory": str(git_directory),
        "common_directory": str(common_directory),
        "object_directory": str(object_directory),
        "object_format": object_format,
        "baseline": baseline,
        "head": head,
    }


def _stale_status_identity(
    status: os.stat_result,
) -> Dict[str, int]:
    identity_attributes = (
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        | getattr(stat, "FILE_ATTRIBUTE_DIRECTORY", 0)
    )
    return {
        "device": int(status.st_dev),
        "inode": int(status.st_ino),
        "type": int(stat.S_IFMT(status.st_mode)),
        "attributes": int(
            getattr(status, "st_file_attributes", 0)
            & identity_attributes
        ),
    }


def _stale_status_record(
    status: os.stat_result,
) -> Dict[str, int]:
    return {
        **_stale_status_identity(status),
        "mode": int(status.st_mode),
        "links": int(status.st_nlink),
        "size": int(status.st_size),
        "mtime_ns": int(status.st_mtime_ns),
    }


def _stable_file_digest(
    path: Path,
    *,
    expected_status: os.stat_result,
) -> str:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if (
            _stale_status_record(opened)
            != _stale_status_record(expected_status)
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
        ):
            raise FixtureError(
                f"stale recovery file identity drifted: {path}"
            )
        digest = hashlib.sha256()
        observed = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            observed += len(chunk)
            digest.update(chunk)
        after = os.fstat(descriptor)
        visible = os.lstat(path)
        if (
            observed != opened.st_size
            or _stale_status_record(after)
            != _stale_status_record(opened)
            or _stale_status_record(visible)
            != _stale_status_record(opened)
        ):
            raise FixtureError(
                f"stale recovery file changed while read: {path}"
            )
        return digest.hexdigest()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _snapshot_stale_tree(
    root: Path,
    *,
    recovery_claim: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    try:
        root_status = os.lstat(root)
    except OSError as error:
        raise FixtureError(
            f"cannot inspect stale recovery root: {error}"
        ) from error
    root_attributes = getattr(root_status, "st_file_attributes", 0)
    if (
        not stat.S_ISDIR(root_status.st_mode)
        or stat.S_ISLNK(root_status.st_mode)
        or root_attributes
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    ):
        raise FixtureError(
            "stale recovery root must remain a non-reparse directory"
        )
    device = root_status.st_dev
    records: Dict[str, Dict[str, Any]] = {
        "": {
            "kind": "directory",
            "identity": _stale_status_identity(root_status),
        }
    }
    active_names = {
        "journal.json",
        "bridge-fixture-fault-plan.md",
        FAULT_PHASE_ARMED_TARGET.casefold(),
        FAULT_PHASE_CLAIM_TARGET.casefold(),
        FAULT_PHASE_INJECTED_TARGET.casefold(),
    }
    claim_relative = f".git/{RECOVERY_CLAIM_TARGET}"

    def visit(directory: Path, parts: Tuple[str, ...]) -> None:
        before = os.lstat(directory)
        before_identity = _stale_status_identity(before)
        try:
            with os.scandir(directory) as iterator:
                children = sorted(
                    list(iterator), key=lambda item: item.name
                )
        except OSError as error:
            raise FixtureError(
                f"cannot enumerate exact stale tree {directory}: {error}"
            ) from error
        if _stale_status_identity(os.lstat(directory)) != before_identity:
            raise FixtureError(
                f"stale recovery directory drifted: {directory}"
            )
        for item in children:
            path = Path(item.path)
            relative_parts = (*parts, item.name)
            relative = "/".join(relative_parts)
            try:
                status = os.lstat(path)
            except OSError as error:
                raise FixtureError(
                    f"cannot inspect stale tree entry {relative}: {error}"
                ) from error
            attributes = getattr(
                status, "st_file_attributes", 0
            )
            linked = stat.S_ISLNK(status.st_mode) or bool(
                attributes
                & getattr(
                    stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
                )
            )
            if linked or status.st_dev != device:
                raise FixtureError(
                    f"stale recovery rejects link/reparse/escape: {relative}"
                )
            if item.name.casefold() == ".git" and relative != ".git":
                raise FixtureError(
                    f"stale recovery rejects nested Git entry: {relative}"
                )
            lowered = item.name.casefold()
            if (
                lowered in active_names
                or lowered.endswith(".lock")
            ):
                raise FixtureError(
                    f"stale recovery rejects active artifact: {relative}"
                )
            if stat.S_ISDIR(status.st_mode):
                record = {
                    "kind": "directory",
                    "identity": _stale_status_identity(status),
                }
                records[relative] = record
                visit(path, relative_parts)
                if (
                    _stale_status_identity(os.lstat(path))
                    != record["identity"]
                ):
                    raise FixtureError(
                        "stale recovery directory identity changed: "
                        f"{relative}"
                    )
                continue
            if (
                not stat.S_ISREG(status.st_mode)
                or status.st_nlink != 1
            ):
                raise FixtureError(
                    f"stale recovery rejects special/hardlinked entry: "
                    f"{relative}"
                )
            record = {
                "kind": "file",
                "status": _stale_status_record(status),
                "sha256": _stable_file_digest(
                    path, expected_status=status
                ),
            }
            if relative == claim_relative:
                if (
                    record["sha256"]
                    != recovery_claim["raw_sha256"]
                    or record["status"]["links"] != 1
                ):
                    raise FixtureError(
                        "stale recovery claim identity changed"
                    )
            records[relative] = record
        directory_relative = "/".join(parts)
        if directory_relative and directory_relative != ".git":
            children_by_name = {
                item.name.casefold(): (
                    f"{directory_relative}/{item.name}"
                )
                for item in children
            }
            bare_signature = {
                "head": "file",
                "objects": "directory",
                "refs": "directory",
            }
            if all(
                name in children_by_name
                and records[children_by_name[name]]["kind"] == kind
                for name, kind in bare_signature.items()
            ):
                raise FixtureError(
                    "stale recovery rejects nested bare Git repository: "
                    f"{directory_relative}"
                )
        if _stale_status_identity(os.lstat(directory)) != before_identity:
            raise FixtureError(
                f"stale recovery directory changed after scan: {directory}"
            )

    visit(root, ())
    if ".git" not in records or claim_relative not in records:
        raise FixtureError(
            "stale recovery tree lacks exact Git/claim boundary"
        )
    return records


def _create_stale_recovery_claim(
    store: RetainedRootDirectory,
    *,
    root: Path,
    scenario: str,
    nonce: str,
    marker_sha256: str,
) -> Dict[str, Any]:
    paths = _phase_paths(root)
    forbidden = [path.name for path in paths.values()]
    forbidden.append(RECOVERY_CLAIM_TARGET)
    if any(store.exists(name) for name in forbidden):
        raise FixtureError(
            "stale recovery found an active phase or recovery claim"
        )
    created: Dict[str, Any] = {}

    def build(file_evidence: Mapping[str, Any]) -> bytes:
        nonlocal created
        created = {
            "version": RECOVERY_CLAIM_SPEC,
            "canonicalization": CANONICAL_JSON_SPEC,
            "state": "exclusive-stale-recovery",
            "binding": {
                "suite": SUITE,
                "scenario": scenario,
                "resolved_root": str(root),
                "nonce": nonce,
                "marker_sha256": marker_sha256,
                "claim_nonce": secrets.token_urlsafe(24),
                "caller_acknowledged_lost_lease": True,
                "caller_acknowledged_no_active_external_operation": True,
            },
            "file": copy.deepcopy(file_evidence),
        }
        return _canonical_json_bytes(created)

    snapshot = store.create_bound(RECOVERY_CLAIM_TARGET, build)
    parsed = _parse_canonical_json_bytes(
        snapshot["bytes"], label="stale recovery claim"
    )
    if (
        parsed != created
        or parsed.get("file") != _phase_self_evidence(snapshot)
    ):
        raise FixtureError(
            "stale recovery claim self-identity did not close"
        )
    return {
        "document": created,
        "snapshot": snapshot,
        "raw_sha256": snapshot["raw_sha256"],
    }


def _remove_exact_recovery_claim(
    root: Path,
    *,
    expected_root_identity: Mapping[str, Any],
    claim: Mapping[str, Any],
) -> bool:
    try:
        with RetainedRootDirectory(root) as root_store:
            if root_store.identity != dict(expected_root_identity):
                return False
            with RetainedRootDirectory(root / ".git") as phase_store:
                phase_store.unlink(
                    RECOVERY_CLAIM_TARGET,
                    expected=claim["snapshot"],
                )
            root_store.verify()
            return True
    except (FixtureError, OSError):
        return False


def _strict_remove_stale_tombstone(
    root: Path,
    *,
    expected_snapshot: Mapping[str, Mapping[str, Any]],
    expected_root_identity: Mapping[str, Any],
    quarantine: Any,
    after_pin: Optional[Any] = None,
    after_disposition: Optional[Any] = None,
) -> Dict[str, Any]:
    if os.name != "nt":
        raise FixtureError(
            "stale tombstone deletion requires Windows"
        )
    if (
        not root.is_absolute()
        or root.parent != os_temp_root()
        or not root.name.startswith(
            f"bridge-{SUITE}-recovery-tombstone-"
        )
    ):
        raise FixtureError(
            "stale tombstone is not one exact OS-temp child"
        )
    quarantine.verify()
    if quarantine["root_identity"] != dict(expected_root_identity):
        raise FixtureError(
            "stale tombstone retained identity mismatch"
        )
    observed = _snapshot_stale_tree(
        root,
        recovery_claim={
            "raw_sha256": expected_snapshot[
                f".git/{RECOVERY_CLAIM_TARGET}"
            ]["sha256"]
        },
    )
    if observed != expected_snapshot:
        raise FixtureError(
            "stale tombstone tree changed before deletion"
        )
    expected_entries = {
        relative: record["kind"]
        for relative, record in expected_snapshot.items()
    }
    pinned = pin_quarantined_tree_windows(
        quarantine, expected_entries
    )
    try:
        if after_pin is not None:
            after_pin(root, pinned)
        pinned.revalidate()
        result = pinned.dispose(
            after_disposition=after_disposition
        )
    finally:
        pinned.close()
    if os.path.lexists(root):
        raise FixtureError(
            "stale tombstone still exists after exact deletion"
        )
    return result


def _cleanup_stale_exact(
    *,
    scenario: str,
    raw_root: str,
    marker_sha256: str,
    nonce: str,
    acknowledge_lost_lease: bool,
    acknowledge_no_active_external_operation: bool,
    tombstone_name: Optional[str] = None,
    before_quarantine: Optional[Any] = None,
    after_handle_rename: Optional[Any] = None,
    after_quarantine: Optional[Any] = None,
    after_pin: Optional[Any] = None,
    after_disposition: Optional[Any] = None,
    cleanup: Optional[Any] = None,
) -> Dict[str, Any]:
    if os.name != "nt":
        raise FixtureError(
            "stale recovery is Windows-only and fails closed elsewhere"
        )
    capability = windows_root_quarantine_capability()
    if not capability["available"]:
        raise FixtureError(
            "Windows exact-root quarantine capability is unavailable"
        )
    if not acknowledge_lost_lease:
        raise FixtureError(
            "stale recovery requires --acknowledge-lost-lease"
        )
    if not acknowledge_no_active_external_operation:
        raise FixtureError(
            "stale recovery requires "
            "--acknowledge-no-active-external-operation"
        )
    _scenario(scenario)
    root = _stale_canonical_root(
        raw_root, scenario=scenario, nonce=nonce
    )
    parent = os_temp_root()
    marker_digest = marker_sha256
    claim: Optional[Dict[str, Any]] = None
    root_identity: Dict[str, Any] = {}
    marker_result: Dict[str, Any] = {}
    git_evidence: Dict[str, Any] = {}
    tree_snapshot: Dict[str, Dict[str, Any]] = {}
    with RetainedRootDirectory(root) as root_store:
        root_identity = dict(root_store.identity)
        with RetainedRootDirectory(root / ".git") as phase_store:
            marker_snapshot = phase_store.read(MARKER_NAME)
            marker_result = _validate_stale_marker(
                root=root,
                scenario=scenario,
                nonce=nonce,
                marker_snapshot=marker_snapshot,
                expected_sha256=marker_digest,
                git_store=phase_store,
            )
            claim = _create_stale_recovery_claim(
                phase_store,
                root=root,
                scenario=scenario,
                nonce=nonce,
                marker_sha256=marker_digest,
            )
            try:
                first_git = _validate_stale_git(
                    root, marker=marker_result["marker"]
                )
                first_tree = _snapshot_stale_tree(
                    root, recovery_claim=claim
                )
                root_store.verify()
                phase_store.verify()
                second_git = _validate_stale_git(
                    root, marker=marker_result["marker"]
                )
                second_tree = _snapshot_stale_tree(
                    root, recovery_claim=claim
                )
                root_store.verify()
                phase_store.verify()
                if first_git != second_git:
                    raise FixtureError(
                        "stale recovery Git evidence drifted"
                    )
                if first_tree != second_tree:
                    raise FixtureError(
                        "stale recovery exact tree snapshot drifted"
                    )
                git_evidence = second_git
                tree_snapshot = second_tree
            except Exception:
                phase_store.unlink(
                    RECOVERY_CLAIM_TARGET,
                    expected=claim["snapshot"],
                )
                raise
    assert claim is not None

    if tombstone_name is None:
        tombstone_name = (
            f"bridge-{SUITE}-recovery-tombstone-"
            + secrets.token_urlsafe(24)
        )
    tombstone = parent / tombstone_name
    try:
        if before_quarantine is not None:
            before_quarantine(root)
        quarantine = quarantine_root_child_windows(
            parent,
            root.name,
            tombstone_name,
            expected_identity=root_identity,
            after_rename=after_handle_rename,
        )
    except WindowsRootQuarantinedError as error:
        raise _QuarantinedCleanupError(
            str(error),
            original=root,
            tombstone=error.tombstone,
            root_identity=error.root_identity,
            state="quarantined",
            partial_deletion=False,
        ) from error
    except Exception:
        _remove_exact_recovery_claim(
            root,
            expected_root_identity=root_identity,
            claim=claim,
        )
        raise

    deletion_evidence: Dict[str, Any] = {}
    try:
        quarantine.verify()
        if quarantine["root_identity"] != root_identity:
            raise FixtureError(
                "quarantined tombstone identity differs from source"
            )
        post_rename_tree = _snapshot_stale_tree(
            tombstone, recovery_claim=claim
        )
        if post_rename_tree != tree_snapshot:
            raise FixtureError(
                "quarantined tombstone bytes/identities drifted"
            )
        if os.path.lexists(root):
            raise FixtureError(
                "original fixture name was recreated after quarantine"
            )
        if after_quarantine is not None:
            after_quarantine(root, tombstone)
        remove = cleanup or _strict_remove_stale_tombstone
        deletion_evidence = remove(
            tombstone,
            expected_snapshot=tree_snapshot,
            expected_root_identity=root_identity,
            quarantine=quarantine,
            after_pin=after_pin,
            after_disposition=after_disposition,
        )
        if os.path.lexists(root):
            raise FixtureError(
                "original fixture name was recreated; preserved exactly"
            )
        if os.path.lexists(tombstone):
            raise FixtureError(
                "quarantine tombstone remains after deletion"
            )
    except WindowsPinnedTreePartialError as error:
        quarantine.close()
        raise _QuarantinedCleanupError(
            str(error),
            original=root,
            tombstone=tombstone,
            root_identity=root_identity,
            state="partial",
            partial_deletion=True,
            removed_entries=error.removed,
        ) from error
    except Exception as error:
        partial = bool(quarantine.disposed)
        quarantine.close()
        raise _QuarantinedCleanupError(
            str(error),
            original=root,
            tombstone=tombstone,
            root_identity=root_identity,
            state="partial" if partial else "quarantined",
            partial_deletion=partial,
        ) from error
    quarantine.close()

    return {
        "pass": True,
        "contract": STALE_RECOVERY_SPEC,
        "state": "closed",
        "scenario": scenario,
        "original_root": str(root),
        "tombstone": str(tombstone),
        "nonce": nonce,
        "marker_kind": marker_result["kind"],
        "marker_sha256": marker_result["raw_sha256"],
        "baseline_commit": git_evidence["baseline"],
        "head": git_evidence["head"],
        "git_object_format": git_evidence["object_format"],
        "tree_entries": len(tree_snapshot) - 1,
        "deletion_evidence": deletion_evidence,
        "original_root_identity": root_identity,
        "tombstone_root_identity": quarantine["root_identity"],
        "parent_identity": quarantine["parent_identity"],
        "caller_attestation": {
            "lost_lease_acknowledged": True,
            "no_active_external_operation_acknowledged": True,
            "external_operation_status": "operator-attested",
        },
        "trust_boundary": "operator-attested/fixture-cooperative",
        "quarantine_capability": capability,
        "original_absent": True,
        "tombstone_absent": True,
        "siblings_enumerated": False,
        "recoverable": False,
        "product_cleanup": False,
        "synthetic_fixture_data_only": True,
    }


def command_cleanup_stale(arguments: argparse.Namespace) -> int:
    try:
        result = _cleanup_stale_exact(
            scenario=arguments.scenario,
            raw_root=arguments.worktree,
            marker_sha256=arguments.marker_sha256,
            nonce=arguments.nonce,
            acknowledge_lost_lease=arguments.acknowledge_lost_lease,
            acknowledge_no_active_external_operation=(
                arguments.acknowledge_no_active_external_operation
            ),
        )
    except _QuarantinedCleanupError as error:
        _json_output(error.result)
        return 2
    _json_output(result)
    return 0


def command_cleanup(arguments: argparse.Namespace) -> int:
    _reject_recovery_claim(Path(arguments.worktree))
    _scenario(arguments.scenario)
    cleanup_leased_project(
        Path(arguments.worktree),
        suite=SUITE,
        scenario=arguments.scenario,
        lease=arguments.lease,
    )
    _json_output(
        {
            "removed": str(Path(arguments.worktree).resolve()),
            "recoverable": False,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and replay M3 entry/rule fixtures safely."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list")
    list_parser.set_defaults(handler=command_list)
    self_test_parser = subparsers.add_parser("self-test")
    self_test_parser.set_defaults(handler=command_self_test)
    materialize_parser = subparsers.add_parser("materialize")
    materialize_parser.add_argument("replay_input")
    materialize_parser.set_defaults(handler=command_materialize)
    replay_input_parser = subparsers.add_parser("replay-input")
    replay_input_parser.add_argument("replay_input")
    replay_input_parser.add_argument("worktree")
    replay_input_parser.add_argument("--lease", required=True)
    replay_input_parser.set_defaults(handler=command_replay_input)
    arm_fault_parser = subparsers.add_parser("arm-fault")
    arm_fault_parser.add_argument("replay_input")
    arm_fault_parser.add_argument("worktree")
    arm_fault_parser.add_argument("--lease", required=True)
    arm_fault_parser.add_argument("--plan", required=True)
    arm_fault_parser.add_argument("--operation-id", required=True)
    arm_fault_parser.set_defaults(handler=command_arm_fault)
    apply_fault_parser = subparsers.add_parser("apply-fault")
    apply_fault_parser.add_argument("replay_input")
    apply_fault_parser.add_argument("worktree")
    apply_fault_parser.add_argument("--lease", required=True)
    apply_fault_parser.add_argument("--operation-id", required=True)
    apply_fault_parser.set_defaults(handler=command_apply_fault)
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
    explain_plan_parser = subparsers.add_parser("explain-plan")
    explain_plan_parser.add_argument("replay_input")
    explain_plan_parser.add_argument("worktree")
    explain_plan_parser.add_argument("--lease", required=True)
    explain_plan_parser.add_argument("--plan", required=True)
    explain_plan_parser.add_argument(
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
    explain_plan_parser.set_defaults(handler=command_explain_plan)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("scenario")
    compare_parser.add_argument("worktree")
    compare_parser.add_argument("--lease", required=True)
    compare_parser.add_argument("--expectation", required=True)
    compare_parser.add_argument("--actual-plan", required=True)
    compare_parser.set_defaults(handler=command_compare)
    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("scenario")
    cleanup_parser.add_argument("worktree")
    cleanup_parser.add_argument("--lease", required=True)
    cleanup_parser.set_defaults(handler=command_cleanup)
    stale_cleanup_parser = subparsers.add_parser("cleanup-stale")
    stale_cleanup_parser.add_argument("scenario")
    stale_cleanup_parser.add_argument("worktree")
    stale_cleanup_parser.add_argument(
        "--marker-sha256", required=True
    )
    stale_cleanup_parser.add_argument("--nonce", required=True)
    stale_cleanup_parser.add_argument(
        "--acknowledge-lost-lease",
        action="store_true",
        required=True,
    )
    stale_cleanup_parser.add_argument(
        "--acknowledge-no-active-external-operation",
        action="store_true",
        required=True,
    )
    stale_cleanup_parser.set_defaults(
        handler=command_cleanup_stale
    )
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
