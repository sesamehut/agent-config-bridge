#!/usr/bin/env python3
"""Breaking-v2 command and state-machine tests for journal_validator.py."""

from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

import fixture_harness as harness
import journal_validator as validator


HERE = Path(__file__).resolve().parent
REPLAY_INPUT = "codex-first-confirmed"
SCENARIO = "codex-first-mixed"
EXPECTED_CASES = 66
CONCURRENT_WORKERS = 2
CONCURRENT_DEADLINE_SECONDS = 180.0
CONCURRENT_REAP_RESERVE_SECONDS = 15.0
CONCURRENT_REAP_STEP_SECONDS = 2.0
WORKER_DIAGNOSTIC_EXCERPT_BYTES = 4096
WORKER_MATRIX_SPEC = "bridge-journal-worker-lifecycle-tests/v1"
PLAN_TEXT = """# Bridge Sync Plan

- project: codex-first-mixed
- scan root: .
- date: 2026-07-24
- spec: sync-plan/v3
- contracts: covenant/v3, source-tree/v5, report/v5, reconciliation/v3
- phase: pre-write
- onboarding: onboarded
- authorization: confirmed

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| entry | closure/agents-md | selected | - | no-baseline | annex | projection-to-source | confirmed | planned | structural | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/agents-md | entry | - | selected | confirmed | planned |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-create-v1 | python-exclusive-create/v1 | other | exclusive-create/v1; safe-parent/v1 |
| capability/2 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/agents-md | CLAUDE.md | create | strict-create/v1 | capability/1 | unavailable | - |
| 2 | closure/agents-md | AGENTS.md | replace | guarded-patch/v1 | capability/2 | unavailable | - |

## Warnings

- guarded-patch-non-cas: AGENTS.md
- manual-zone-guarded: AGENTS.md
- strict-compensation-unavailable: AGENTS.md
- strict-compensation-unavailable: CLAUDE.md

## Hook tiers

- (none)

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

| segment | lines | disposition | destination | decision |
|---|---|---|---|---|
| segment/1 | 49-51 | shared-entry | entry | confirmed |
| segment/2 | 53-55 | manual | - | confirmed |

## Hook adoption decisions

- (none)
"""
FORMAL_SCRATCH_PATTERNS = (
    "bridge-journal-formal-attestation-*",
    "bridge-journal-formal-context-*",
    "bridge-journal-formal-plan-*",
)
WORKER_GROUP_TIMEOUT_SECONDS = 180.0
WORKER_REAP_TIMEOUT_SECONDS = 5.0


class TestFailure(RuntimeError):
    pass


@contextmanager
def _session_temp_root() -> Iterator[Path]:
    parent = harness.os_temp_root()
    previous_tempdir = tempfile.tempdir
    previous_environment = {
        name: os.environ.get(name)
        for name in (
            "TMPDIR",
            "TEMP",
            "TMP",
            "BRIDGE_JOURNAL_TEST_SESSION",
        )
    }
    session_root = Path(
        tempfile.mkdtemp(
            prefix="bridge-journal-v2-session-",
            dir=parent,
        )
    )
    try:
        if (
            Path(os.path.abspath(session_root)).parent != parent
            or not session_root.name.startswith(
                "bridge-journal-v2-session-"
            )
        ):
            raise TestFailure("journal test session root escaped its parent")
        os.chmod(session_root, 0o700)
        tempfile.tempdir = str(session_root)
        for name in previous_environment:
            os.environ[name] = str(session_root)
        if harness.os_temp_root() != session_root:
            raise TestFailure("journal test session temp authority did not bind")
        yield session_root
    finally:
        tempfile.tempdir = previous_tempdir
        for name, value in previous_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        harness.strict_remove_tree(session_root)


def _formal_scratch_entries(session_root: Path) -> set[str]:
    return {
        path.relative_to(session_root).as_posix()
        for pattern in FORMAL_SCRATCH_PATTERNS
        for path in session_root.glob(pattern)
    }


def _run(command: Sequence[str], *, expected_exit: int) -> Mapping[str, Any]:
    process = subprocess.run(
        list(command),
        cwd=HERE.parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != expected_exit:
        raise TestFailure(
            f"exit {process.returncode}, wanted {expected_exit}: "
            f"stdout={process.stdout.decode('utf-8', errors='replace')} "
            f"stderr={process.stderr.decode('utf-8', errors='replace')}"
        )
    try:
        value = json.loads(process.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TestFailure("command did not emit one JSON object") from error
    if not isinstance(value, dict):
        raise TestFailure("command JSON root is not an object")
    return value


def _command(
    *,
    root: Path,
    lease: str,
    plan_path: Path,
    journal_path: Path,
    cleanup: bool = False,
) -> List[str]:
    command = [
        sys.executable,
        "-B",
        str(HERE / "journal_validator.py"),
        "validate-journal",
        REPLAY_INPUT,
        str(root),
        f"--lease={lease}",
        f"--plan={plan_path}",
        f"--journal={journal_path}",
    ]
    if cleanup:
        command.append("--request-cleanup-receipt")
    return command


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    path.write_bytes(validator.canonical_json_bytes(value))


def _assert_failure(
    results: List[Dict[str, Any]],
    label: str,
    command: Sequence[str],
    failure_id: str,
) -> Mapping[str, Any]:
    result = _run(command, expected_exit=1)
    failures = result.get("failures", [])
    if result.get("pass") is not False or failure_id not in failures:
        raise TestFailure(
            f"{label}: expected {failure_id}, got {failures}"
        )
    results.append({"case": label, "failures": failures})
    return result


def _event(
    events: List[Dict[str, Any]],
    *,
    anchor: str,
    event: str,
    state: str,
    step: Optional[str] = None,
    observation: Optional[Mapping[str, Any]] = None,
    snapshot: Optional[Sequence[Mapping[str, Any]]] = None,
    result: Optional[str] = None,
    reason: Optional[str] = None,
) -> None:
    events.append(
        validator.make_event(
            anchor_sha256=anchor,
            ordinal=len(events) + 1,
            event=event,
            state=state,
            step=step,
            observation=observation,
            snapshot=snapshot,
            result=result,
            reason=reason,
            previous_sha256=(
                anchor if not events else events[-1]["event-sha256"]
            ),
        )
    )


def _lifecycle(
    journal: Mapping[str, Any],
    *,
    result: str,
) -> Dict[str, Any]:
    operations = journal["path-operations"]
    pre = {
        operation["step"]: operation["pre-value"]
        for operation in operations
    }
    current = copy.deepcopy(pre)
    anchor = validator._lifecycle_anchor(journal)
    events: List[Dict[str, Any]] = []
    _event(
        events,
        anchor=anchor,
        event="prepared",
        state="prepared",
        snapshot=validator._value_snapshot(operations, current),
    )
    _event(
        events,
        anchor=anchor,
        event="execution-started",
        state="executing",
    )
    if result == "applied":
        for operation in operations:
            step = operation["step"]
            _event(
                events,
                anchor=anchor,
                event="forward-attempted",
                state="executing",
                step=step,
            )
            current[step] = operation["intended-post-value"]
            _event(
                events,
                anchor=anchor,
                event="forward-observed",
                state="executing",
                step=step,
                observation=current[step],
            )
    elif result == "failed":
        operation = operations[0]
        _event(
            events,
            anchor=anchor,
            event="forward-attempted",
            state="executing",
            step=operation["step"],
        )
        _event(
            events,
            anchor=anchor,
            event="forward-observed",
            state="failed",
            step=operation["step"],
            observation=operation["pre-value"],
        )
    elif result == "partial":
        operation = operations[0]
        _event(
            events,
            anchor=anchor,
            event="forward-attempted",
            state="executing",
            step=operation["step"],
        )
        current[operation["step"]] = operation["intended-post-value"]
        _event(
            events,
            anchor=anchor,
            event="forward-observed",
            state="executing",
            step=operation["step"],
            observation=current[operation["step"]],
            reason="unprovable",
        )
    else:
        raise TestFailure(f"unsupported lifecycle result: {result}")
    _event(
        events,
        anchor=anchor,
        event="terminal",
        state=result,
        snapshot=validator._value_snapshot(operations, current),
        result=result,
    )
    if result != "partial":
        _event(
            events,
            anchor=anchor,
            event="closed",
            state="closed",
            snapshot=validator._value_snapshot(operations, current),
            result=result,
        )
    return {
        "algorithm": validator.CHAIN_SPEC,
        "anchor-sha256": anchor,
        "events": events,
        "head-sha256": events[-1]["event-sha256"],
        "state": events[-1]["state"],
    }


def _apply_values(
    root: Path,
    operations: Sequence[Mapping[str, Any]],
    values: Mapping[str, Mapping[str, Any]],
) -> None:
    for operation in operations:
        path = root.joinpath(*operation["path"].split("/"))
        value = values[operation["step"]]
        if value["kind"] == "missing":
            if os.path.lexists(path):
                path.unlink()
            continue
        data = base64.b64decode(value["base64"], validate=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if os.name != "nt":
            os.chmod(path, 0o755 if value["mode"] == "100755" else 0o644)


def _terminal_values(journal: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    terminal = next(
        event
        for event in reversed(journal["lifecycle"]["events"])
        if event["event"] in {"terminal", "closed"}
    )
    return {
        item["step"]: item["value"] for item in terminal["snapshot"]
    }


def _build_journal(
    *,
    root: Path,
    lease: str,
    plan_path: Path,
    journal_path: Path,
    operation_id: str,
    result: str = "applied",
) -> Dict[str, Any]:
    tree = validator.RetainedTree(root)
    plan_directory: Optional[validator.RetainedDirectory] = None
    plan_file: Optional[validator.RetainedFile] = None
    lease_directory: Optional[validator.RetainedDirectory] = None
    try:
        head = validator._head_from_tree(tree)
        envelope, payload, _, fixture_binding = validator._bundle_snapshot(
            tree,
            replay_input=REPLAY_INPUT,
            lease=lease,
            head=head,
        )
        plan_directory = validator.RetainedDirectory(plan_path.parent)
        plan_file = validator.RetainedFile(
            plan_path,
            label="test plan",
            parent=plan_directory,
            leaf_name=plan_path.name,
        )
        plan = validator._parse_plan_memory(plan_file.data)
        operations = validator._expected_operations(plan, payload)
        lease_directory = validator.RetainedDirectory(journal_path.parent)
        prefix = harness._journal_lease_prefix(operation_id)
        nonce = journal_path.parent.name[len(prefix) :]
        journal: Dict[str, Any] = {
            "canonicalization": validator.CANONICALIZATION,
            "closures": validator._expected_closures(plan),
            "fixture-binding": fixture_binding,
            "lifecycle": {},
            "operation": {
                "allocation": {
                    "contract": validator.ALLOCATION_SPEC,
                    "lease": {
                        "directory": str(journal_path.parent),
                        "identity": copy.deepcopy(lease_directory.identity),
                    },
                    "lease-name": journal_path.parent.name,
                    "nonce": nonce,
                },
                "id": operation_id,
            },
            "path-operations": operations,
            "plan": {},
            "repository": {
                "git-directory": {
                    "identity": copy.deepcopy(
                        tree.directories[".git"].identity
                    ),
                    "path": ".git",
                },
                "head": head,
                "identity": copy.deepcopy(tree.identity),
                "resolved-root": str(tree.root),
            },
            "spec": validator.JOURNAL_SPEC,
        }
        plan_sha = hashlib.sha256(plan_file.data).hexdigest()
        context, validation_result = validator._formal_plan_attestation(
            plan_bytes=plan_file.data,
            replay_input=REPLAY_INPUT,
            root=tree.root,
            lease=lease,
            envelope=envelope,
            diagnostic_case=f"journal-build:{operation_id}",
        )
        journal["plan"] = {
                "identity": copy.deepcopy(plan_file.identity),
                "sha256": plan_sha,
                "validation-context": context,
                "validation-context-sha256": hashlib.sha256(
                    validator.canonical_json_bytes(context)
                ).hexdigest(),
                "validation-result": validation_result,
                "validation-result-sha256": hashlib.sha256(
                    validator.canonical_json_bytes(validation_result)
                ).hexdigest(),
        }
        journal["lifecycle"] = _lifecycle(journal, result=result)
        return journal
    finally:
        if lease_directory is not None:
            lease_directory.close()
        if plan_file is not None:
            plan_file.close()
        if plan_directory is not None:
            plan_directory.close()
        tree.close()


def _rehash_events(journal: Dict[str, Any]) -> None:
    lifecycle = journal["lifecycle"]
    anchor = validator._lifecycle_anchor(journal)
    lifecycle["anchor-sha256"] = anchor
    previous = anchor
    for ordinal, event in enumerate(lifecycle["events"], start=1):
        event["ordinal"] = str(ordinal)
        event["previous-sha256"] = previous
        event["event-sha256"] = validator._event_hash(
            event, anchor_sha256=anchor
        )
        previous = event["event-sha256"]
    lifecycle["head-sha256"] = previous
    lifecycle["state"] = lifecycle["events"][-1]["state"]


def _noncanonical_base64(value: str) -> Optional[str]:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    if value.endswith("=="):
        index = alphabet.index(value[-3])
        return value[:-3] + alphabet[index | 1] + "=="
    if value.endswith("="):
        index = alphabet.index(value[-2])
        return value[:-2] + alphabet[index | 1] + "="
    return None


def _exercise_pure_lifecycle(
    results: List[Dict[str, Any]],
    base: Mapping[str, Any],
) -> None:
    operations = copy.deepcopy(base["path-operations"])
    for operation in operations:
        operation["inverse-protocol"] = operation["protocol"]
        operation["inverse-binding"] = operation["binding"]
    static = copy.deepcopy(base)
    static["path-operations"] = operations
    static["lifecycle"] = {}
    pre = {
        operation["step"]: operation["pre-value"]
        for operation in operations
    }
    current = copy.deepcopy(pre)
    anchor = validator._lifecycle_anchor(static)
    events: List[Dict[str, Any]] = []
    _event(
        events,
        anchor=anchor,
        event="prepared",
        state="prepared",
        snapshot=validator._value_snapshot(operations, current),
    )
    _event(
        events,
        anchor=anchor,
        event="execution-started",
        state="executing",
    )
    for operation in operations:
        step = operation["step"]
        _event(
            events,
            anchor=anchor,
            event="forward-attempted",
            state="executing",
            step=step,
        )
        if step == "1":
            current[step] = operation["intended-post-value"]
            _event(
                events,
                anchor=anchor,
                event="forward-observed",
                state="executing",
                step=step,
                observation=current[step],
            )
        else:
            _event(
                events,
                anchor=anchor,
                event="forward-observed",
                state="executing",
                step=step,
                observation=operation["pre-value"],
            )
            break
    _event(
        events,
        anchor=anchor,
        event="compensation-started",
        state="compensating",
    )
    operation = operations[0]
    _event(
        events,
        anchor=anchor,
        event="inverse-attempted",
        state="compensating",
        step="1",
    )
    current["1"] = operation["pre-value"]
    _event(
        events,
        anchor=anchor,
        event="inverse-observed",
        state="compensating",
        step="1",
        observation=current["1"],
    )
    snapshot = validator._value_snapshot(operations, current)
    _event(
        events,
        anchor=anchor,
        event="terminal",
        state="compensated",
        snapshot=snapshot,
        result="compensated",
    )
    _event(
        events,
        anchor=anchor,
        event="closed",
        state="closed",
        snapshot=snapshot,
        result="compensated",
    )
    lifecycle = {
        "algorithm": validator.CHAIN_SPEC,
        "anchor-sha256": anchor,
        "events": events,
        "head-sha256": events[-1]["event-sha256"],
        "state": "closed",
    }
    static["lifecycle"] = lifecycle
    outcome = validator._validate_lifecycle(lifecycle, operations, static)
    if outcome["result"] != "compensated" or outcome["state"] != "closed":
        raise TestFailure("valid compensated chain was rejected")
    results.append({"case": "compensated-reverse-positive", "failures": []})

    wrong = copy.deepcopy(static)
    inverse_attempt = next(
        event
        for event in wrong["lifecycle"]["events"]
        if event["event"] == "inverse-attempted"
    )
    inverse_attempt["step"] = "2"
    _rehash_events(wrong)
    try:
        validator._validate_lifecycle(
            wrong["lifecycle"], operations, wrong
        )
    except validator.ValidationError as error:
        if error.failure_id != "lifecycle-semantics":
            raise
    else:
        raise TestFailure("forward-order compensation was accepted")
    results.append(
        {"case": "compensation-wrong-order", "failures": ["lifecycle-semantics"]}
    )


def _exercise_formal_validator(
    results: List[Dict[str, Any]],
    *,
    root: Path,
    lease: str,
    plan_path: Path,
    valid: Mapping[str, Any],
    session_root: Path,
) -> None:
    before = _formal_scratch_entries(session_root)
    plan_bytes = plan_path.read_bytes()
    envelope = harness._validate_blind_installed_replay_input(
        root,
        lease=lease,
        replay_id=REPLAY_INPUT,
        require_input_tree=False,
    )
    try:
        validator._formal_plan_result(
            plan_bytes=b"not a bridge sync plan\n",
            replay_input=REPLAY_INPUT,
            root=root,
            lease=lease,
        )
    except validator.ValidationError as error:
        if error.failure_id != "formal-plan-validation":
            raise
    else:
        raise TestFailure("the real formal validator failure was ignored")
    if _formal_scratch_entries(session_root) != before:
        raise TestFailure("failed formal validation leaked its scratch copy")
    results.append(
        {
            "case": "real-formal-validator-failure",
            "failures": ["formal-plan-validation"],
        }
    )

    original_run = validator.subprocess.run

    def reject_validator_child(
        command: Sequence[str], *args: Any, **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        if (
            isinstance(command, (list, tuple))
            and "validate-plan" in command
        ):
            raise TestFailure(
                "formal attestation spawned the CLI validator"
            )
        return original_run(command, *args, **kwargs)

    validator.subprocess.run = reject_validator_child
    try:
        in_process = validator._formal_plan_result(
            plan_bytes=plan_bytes,
            replay_input=REPLAY_INPUT,
            root=root,
            lease=lease,
        )
    finally:
        validator.subprocess.run = original_run
    if (
        in_process != valid["plan"]["validation-result"]
        or in_process.get("pass") is not True
    ):
        raise TestFailure("in-process formal validation result diverged")
    if _formal_scratch_entries(session_root) != before:
        raise TestFailure("in-process formal validation leaked scratch")
    results.append(
        {
            "case": "formal-in-process-core-positive",
            "failures": [],
        }
    )

    parity_directory = Path(
        tempfile.mkdtemp(
            prefix="bridge-journal-formal-parity-",
            dir=session_root,
        )
    )
    try:
        formal_environment, context = validator._prepared_formal_context(
            replay_input=REPLAY_INPUT,
            root=root,
            envelope=envelope,
            scratch_index=parity_directory / "prepared-index",
        )
        direct_positive, _ = harness._validate_plan_bytes_core(
            replay_input=REPLAY_INPUT,
            root=root,
            lease=lease,
            plan_bytes=plan_bytes,
            lifecycle="prepared",
            envelope=envelope,
            actual_untracked=context["live_untracked"],
        )
        cli_positive = validator._formal_plan_cli_snapshot(
            replay_input=REPLAY_INPUT,
            root=root,
            lease=lease,
            plan_path=plan_path,
            formal_environment=formal_environment,
            diagnostic_case="formal-core-cli-positive",
        )
        if (
            direct_positive != cli_positive
            or direct_positive.get("pass") is not True
        ):
            raise TestFailure("positive formal core/CLI parity diverged")
        results.append(
            {
                "case": "formal-core-cli-parity-positive",
                "failures": [],
            }
        )

        invalid_plan_path = parity_directory / "invalid-plan.md"
        invalid_plan_bytes = b"not a bridge sync plan\n"
        invalid_plan_path.write_bytes(invalid_plan_bytes)
        direct_negative, _ = harness._validate_plan_bytes_core(
            replay_input=REPLAY_INPUT,
            root=root,
            lease=lease,
            plan_bytes=invalid_plan_bytes,
            lifecycle="prepared",
            envelope=envelope,
            actual_untracked=context["live_untracked"],
        )
        cli_negative = validator._formal_plan_cli_snapshot(
            replay_input=REPLAY_INPUT,
            root=root,
            lease=lease,
            plan_path=invalid_plan_path,
            formal_environment=formal_environment,
            diagnostic_case="formal-core-cli-negative",
        )
        if (
            direct_negative != cli_negative
            or direct_negative.get("pass") is not False
            or not direct_negative.get("failures")
        ):
            raise TestFailure("negative formal core/CLI parity diverged")
        results.append(
            {
                "case": "formal-core-cli-parity-negative",
                "failures": list(direct_negative["failures"]),
            }
        )

        leading_hyphen = validator._formal_plan_cli_snapshot(
            replay_input=REPLAY_INPUT,
            root=root,
            lease="-forced-leading-hyphen",
            plan_path=plan_path,
            formal_environment=formal_environment,
            diagnostic_case="formal-cli-leading-hyphen",
        )
        if (
            leading_hyphen.get("pass") is not False
            or not leading_hyphen.get("failures")
        ):
            raise TestFailure(
                "leading-hyphen lease did not reach formal CLI validation"
            )
        command_probe = _command(
            root=root,
            lease="-forced-leading-hyphen",
            plan_path=plan_path,
            journal_path=parity_directory / "journal.json",
        )
        if (
            "--lease=-forced-leading-hyphen" not in command_probe
            or "--lease" in command_probe
        ):
            raise TestFailure(
                "journal CLI command retained ambiguous lease arguments"
            )
        results.append(
            {
                "case": "formal-cli-leading-hyphen-lease",
                "failures": list(leading_hyphen["failures"]),
            }
        )
    finally:
        harness.strict_remove_tree(parity_directory)

    index_path = root / ".git" / "index"
    index_before = (
        os.path.lexists(index_path),
        index_path.read_bytes() if os.path.lexists(index_path) else b"",
    )
    prepared_indexes: List[Path] = []
    original_sanitizer = validator._sanitized_formal_environment
    hostile_names = (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CEILING_DIRECTORIES",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_WORK_TREE",
    )
    previous_git_environment = {
        name: os.environ.get(name) for name in hostile_names
    }

    def capturing_sanitizer(*, prepared_index: Path) -> Dict[str, str]:
        prepared_indexes.append(prepared_index)
        environment = original_sanitizer(prepared_index=prepared_index)
        if (
            environment.get("GIT_INDEX_FILE") != str(prepared_index)
            or environment.get("GIT_OPTIONAL_LOCKS") != "0"
            or any(
                name in environment
                for name in hostile_names
                if name != "GIT_INDEX_FILE"
            )
        ):
            raise TestFailure("formal Git environment was not sanitized")
        return environment

    for name in hostile_names:
        os.environ[name] = str(session_root / f"hostile-{name.lower()}")
    validator._sanitized_formal_environment = capturing_sanitizer
    try:
        for index in range(2):
            _, isolated = validator._formal_plan_attestation(
                plan_bytes=plan_bytes,
                replay_input=REPLAY_INPUT,
                root=root,
                lease=lease,
                envelope=envelope,
                diagnostic_case=f"formal-index-isolation-{index + 1}",
            )
            if isolated.get("pass") is not True:
                raise TestFailure(
                    "sanitized formal attestation did not pass"
                )
    finally:
        validator._sanitized_formal_environment = original_sanitizer
        for name, value in previous_git_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    index_after = (
        os.path.lexists(index_path),
        index_path.read_bytes() if os.path.lexists(index_path) else b"",
    )
    if (
        len(prepared_indexes) != 2
        or prepared_indexes[0] == prepared_indexes[1]
        or any(os.path.lexists(path) for path in prepared_indexes)
        or index_after != index_before
    ):
        raise TestFailure(
            "formal prepared index isolation or real index preservation failed"
        )
    results.append(
        {
            "case": "formal-git-environment-index-isolation",
            "failures": [],
        }
    )

    diagnostic_plan = session_root / "formal-diagnostic-plan.md"
    diagnostic_plan.write_bytes(plan_bytes)
    original_run = validator.subprocess.run

    def invalid_child(
        command: Sequence[str], *args: Any, **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            command,
            2,
            b"",
            b"argument --lease: expected one argument",
        )

    validator.subprocess.run = invalid_child
    try:
        try:
            validator._formal_plan_cli_snapshot(
                replay_input=REPLAY_INPUT,
                root=root,
                lease=lease,
                plan_path=diagnostic_plan,
                formal_environment={},
                diagnostic_case="formal-cli-diagnostic-probe",
            )
        except validator.ValidationError as error:
            diagnostic_message = str(error)
            if (
                error.failure_id != "formal-plan-validation"
                or '"case":"formal-cli-diagnostic-probe"'
                not in diagnostic_message
                or '"child_returncode":2' not in diagnostic_message
                or "expected one argument" not in diagnostic_message
                or '"session":' not in diagnostic_message
            ):
                raise TestFailure(
                    "formal CLI child diagnostic lost bound evidence"
                ) from error
        else:
            raise TestFailure("invalid formal CLI child output was accepted")
    finally:
        validator.subprocess.run = original_run
        diagnostic_plan.unlink()
    results.append(
        {
            "case": "formal-cli-child-diagnostic-contract",
            "failures": ["formal-plan-validation"],
        }
    )

    leaked_scratch: List[Path] = []
    original_core = harness._validate_plan_bytes_core
    original_cleanup = harness.strict_remove_tree

    def fail_core(**_: Any) -> Tuple[Dict[str, Any], Optional[Any]]:
        raise RuntimeError("primary formal core failure")

    def fail_attestation_cleanup(path: Path) -> None:
        if path.name.startswith("bridge-journal-formal-attestation-"):
            leaked_scratch.append(path)
            raise harness.FixtureError("injected formal cleanup failure")
        original_cleanup(path)

    harness._validate_plan_bytes_core = fail_core
    harness.strict_remove_tree = fail_attestation_cleanup
    try:
        try:
            validator._formal_plan_attestation(
                plan_bytes=plan_bytes,
                replay_input=REPLAY_INPUT,
                root=root,
                lease=lease,
                envelope=envelope,
                diagnostic_case="formal-primary-cleanup-failure",
            )
        except RuntimeError as error:
            notes = getattr(error, "__notes__", [])
            if (
                str(error) != "primary formal core failure"
                or not any(
                    "formal attestation cleanup also failed" in note
                    for note in notes
                )
            ):
                raise TestFailure(
                    "formal cleanup did not preserve the primary failure"
                ) from error
        else:
            raise TestFailure("injected formal core failure was ignored")
    finally:
        harness._validate_plan_bytes_core = original_core
        harness.strict_remove_tree = original_cleanup
        for path in leaked_scratch:
            if path.exists():
                original_cleanup(path)
    results.append(
        {
            "case": "formal-cleanup-preserves-primary-failure",
            "failures": ["formal-plan-validation"],
        }
    )
    if _formal_scratch_entries(session_root) != before:
        raise TestFailure("formal validator matrix leaked scratch")


def _exercise_unborn(
    results: List[Dict[str, Any]],
    *,
    root: Path,
    lease: str,
    plan_path: Path,
    journal_path: Path,
) -> None:
    generic_root = Path(
        tempfile.mkdtemp(prefix="bridge-journal-unborn-")
    )
    try:
        (generic_root / ".git").mkdir()
        (generic_root / ".git" / "HEAD").write_bytes(
            b"ref: refs/heads/main\n"
        )
        tree = validator.RetainedTree(generic_root)
        try:
            head = validator._head_from_tree(tree)
            tree.verify()
        finally:
            tree.close()
        if head != {"oid": None, "ref": "refs/heads/main", "state": "unborn"}:
            raise TestFailure(f"unborn HEAD misclassified: {head}")
        results.append(
            {
                "case": "production-unbound-head-probe-unborn-positive",
                "failures": [],
            }
        )
    finally:
        harness.strict_remove_tree(generic_root)

    fixture_root = Path(os.path.abspath(root))
    head_text = (fixture_root / ".git" / "HEAD").read_text(
        encoding="ascii"
    ).strip()
    if not head_text.startswith("ref: "):
        raise TestFailure("fixture profile lacks an attached HEAD")
    ref_path = fixture_root / ".git" / Path(head_text[5:])
    if not ref_path.is_file():
        raise TestFailure("fixture profile HEAD is not a loose ref")
    ref_bytes = ref_path.read_bytes()
    ref_path.unlink()
    try:
        _assert_failure(
            results,
            "fixture-profile-unborn-refused",
            _command(
                root=fixture_root,
                lease=lease,
                plan_path=plan_path,
                journal_path=journal_path,
            ),
            "head-binding",
        )
    finally:
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_bytes(ref_bytes)


def _exercise_posix_retained_drift(
    results: List[Dict[str, Any]],
) -> None:
    if os.name == "nt":
        results.extend(
            [
                {
                    "case": "posix-same-inode-drift-capability-gated",
                    "failures": ["platform-capability"],
                },
                {
                    "case": "posix-parent-drift-capability-gated",
                    "failures": ["platform-capability"],
                },
            ]
        )
        return

    scratch = Path(tempfile.mkdtemp(prefix="bridge-journal-posix-drift-"))
    parent: Optional[validator.RetainedDirectory] = None
    retained: Optional[validator.RetainedFile] = None
    try:
        path = scratch / "same-inode.txt"
        path.write_bytes(b"original")
        parent = validator.RetainedDirectory(scratch)
        retained = validator.RetainedFile(
            path,
            label="same-inode regression",
            parent=parent,
            leaf_name=path.name,
        )
        inode = os.stat(path).st_ino
        with path.open("r+b") as stream:
            stream.seek(0)
            stream.write(b"tampered")
            stream.flush()
            os.fsync(stream.fileno())
        if os.stat(path).st_ino != inode:
            raise TestFailure("same-inode regression replaced the inode")
        try:
            retained.verify()
        except validator.ValidationError as error:
            if error.failure_id != "authority-identity":
                raise
        else:
            raise TestFailure("same-inode retained-byte drift was accepted")
        results.append(
            {
                "case": "posix-same-inode-drift-refused",
                "failures": ["authority-identity"],
            }
        )
    finally:
        if retained is not None:
            retained.close()
        if parent is not None:
            parent.close()
        harness.strict_remove_tree(scratch)

    scratch = Path(tempfile.mkdtemp(prefix="bridge-journal-posix-parent-"))
    outer: Optional[validator.RetainedDirectory] = None
    parent = None
    retained = None
    try:
        lease_directory = scratch / "lease"
        lease_directory.mkdir()
        path = lease_directory / "journal.json"
        path.write_bytes(b"original")
        outer = validator.RetainedDirectory(scratch)
        parent = validator.RetainedDirectory(
            lease_directory,
            parent=outer,
            leaf_name=lease_directory.name,
        )
        retained = validator.RetainedFile(
            path,
            label="parent-drift regression",
            parent=parent,
            leaf_name=path.name,
        )
        moved = scratch / "moved-lease"
        os.rename(lease_directory, moved)
        lease_directory.mkdir()
        (lease_directory / "journal.json").write_bytes(b"original")
        try:
            retained.verify()
        except validator.ValidationError as error:
            if error.failure_id != "authority-identity":
                raise
        else:
            raise TestFailure("retained parent replacement was accepted")
        results.append(
            {
                "case": "posix-parent-drift-refused",
                "failures": ["authority-identity"],
            }
        )
    finally:
        if retained is not None:
            retained.close()
        if parent is not None:
            parent.close()
        if outer is not None:
            outer.close()
        harness.strict_remove_tree(scratch)


def _exercise_cross_contexts(
    results: List[Dict[str, Any]],
    *,
    session_root: Path,
) -> None:
    scratch = Path(
        tempfile.mkdtemp(
            prefix="bridge-journal-context-tests-",
            dir=session_root,
        )
    )

    def materialize(replay_input: str) -> Tuple[Mapping[str, Any], Path, str]:
        value = _run(
            [
                sys.executable,
                "-B",
                str(HERE / "fixture_harness.py"),
                "materialize",
                replay_input,
            ],
            expected_exit=0,
        )
        return value, Path(value["worktree"]), str(value["lease"])

    def bound_plan(
        name: str,
        *,
        root: Path,
        replay_input: str,
        lease: str,
    ) -> Path:
        source = HERE / "plans" / name
        data = source.read_bytes()
        marker = harness.validate_marker(
            root,
            suite=harness.SUITE,
            scenario=str(
                harness._validate_blind_installed_replay_input(
                    root,
                    lease=lease,
                    replay_id=replay_input,
                    require_input_tree=False,
                )["payload"]["binding"]["scenario"]
            ),
            lease=lease,
        )
        data = data.replace(
            harness.ZERO_BASELINE.encode("ascii"),
            marker["baseline_commit"].encode("ascii"),
        )
        target = scratch / f"{replay_input}-plan.md"
        target.write_bytes(data)
        return target

    def context_and_formal(
        *,
        replay_input: str,
        root: Path,
        lease: str,
        plan_path: Path,
    ) -> Tuple[Dict[str, Any], Mapping[str, Any]]:
        envelope = harness._validate_blind_installed_replay_input(
            root,
            lease=lease,
            replay_id=replay_input,
            require_input_tree=False,
        )
        context, formal = validator._formal_plan_attestation(
            plan_bytes=plan_path.read_bytes(),
            replay_input=replay_input,
            root=root,
            lease=lease,
            envelope=envelope,
        )
        context_sha = hashlib.sha256(
            validator.canonical_json_bytes(context)
        ).hexdigest()
        if (
            set(context)
            != {
                "binding",
                "lifecycle",
                "live_untracked",
                "replay_input",
                "resolved_root",
                "temporal_context",
            }
            or formal.get("context_sha256") != context_sha
            or formal.get("pass") is not True
            or formal.get("failures") != []
        ):
            raise TestFailure(
                f"{replay_input}: prepared context/formal result diverged"
            )
        return context, formal

    current_lease = ""
    formal_scratch_before = _formal_scratch_entries(session_root)
    try:
        materialized, root, current_lease = materialize(
            "migration-v1-v3"
        )
        try:
            plan_path = bound_plan(
                "migration-v1-v3-confirmed.md",
                root=root,
                replay_input="migration-v1-v3",
                lease=current_lease,
            )
            context, formal = context_and_formal(
                replay_input="migration-v1-v3",
                root=root,
                lease=current_lease,
                plan_path=plan_path,
            )
            direct = harness._validate_plan_result(
                replay_input="migration-v1-v3",
                root=root,
                lease=current_lease,
                plan_path=plan_path,
                lifecycle="prepared",
            )
            if (
                context["temporal_context"]
                != harness.GENERAL_PLAN_CONTEXT
                or context["live_untracked"]
                or direct != formal
            ):
                raise TestFailure(
                    "migration prepared direct/journal context mismatch"
                )
            results.append(
                {
                    "case": "migration-prepared-context-positive",
                    "failures": [],
                }
            )
        finally:
            harness.cleanup_leased_project(
                root,
                suite=harness.SUITE,
                scenario=str(materialized["scenario"]),
                lease=current_lease,
            )

        materialized, root, current_lease = materialize("empty-create")
        try:
            envelope = harness._validate_blind_installed_replay_input(
                root,
                lease=current_lease,
                replay_id="empty-create",
                require_input_tree=False,
            )
            payload = envelope["payload"]
            rendered_tree = harness._rendered_tree_from_envelope(
                harness._facts_tree(payload["input"]["files"]),
                payload["render"]["operations"],
            )
            harness.materialize_tree(root, rendered_tree)
            plan_path = bound_plan(
                "empty-create-confirmed.md",
                root=root,
                replay_input="empty-create",
                lease=current_lease,
            )
            context, _ = context_and_formal(
                replay_input="empty-create",
                root=root,
                lease=current_lease,
                plan_path=plan_path,
            )
            if (
                context["temporal_context"]
                != harness.GENERAL_PLAN_CONTEXT
                or context["live_untracked"]
            ):
                raise TestFailure(
                    "empty post prepared context did not hide live creates"
                )
            live_result = harness._validate_plan_result(
                replay_input="empty-create",
                root=root,
                lease=current_lease,
                plan_path=plan_path,
                lifecycle="prepared",
            )
            if (
                live_result["pass"]
                or live_result["failures"] != ["warning-grammar"]
                or live_result["context_sha256"]
                == hashlib.sha256(
                    validator.canonical_json_bytes(context)
                ).hexdigest()
            ):
                raise TestFailure(
                    "empty post live-index negative did not diverge"
                )
            results.extend(
                [
                    {
                        "case": "empty-post-prepared-context-positive",
                        "failures": [],
                    },
                    {
                        "case": "empty-post-live-index-negative",
                        "failures": ["formal-plan-validation"],
                    },
                ]
            )
        finally:
            harness.cleanup_leased_project(
                root,
                suite=harness.SUITE,
                scenario=str(materialized["scenario"]),
                lease=current_lease,
            )

        materialized, root, current_lease = materialize(
            "empty-untracked-rescan"
        )
        try:
            plan_path = bound_plan(
                "empty-untracked-rescan-prepared.md",
                root=root,
                replay_input="empty-untracked-rescan",
                lease=current_lease,
            )
            context, formal = context_and_formal(
                replay_input="empty-untracked-rescan",
                root=root,
                lease=current_lease,
                plan_path=plan_path,
            )
            direct = harness._validate_plan_result(
                replay_input="empty-untracked-rescan",
                root=root,
                lease=current_lease,
                plan_path=plan_path,
                lifecycle="prepared",
            )
            if (
                context["temporal_context"]
                != harness.EMPTY_UNTRACKED_SCAN_CONTEXT
                or context["live_untracked"]
                != sorted(harness.COVENANT_CARRIERS)
                or direct != formal
            ):
                raise TestFailure(
                    "empty fresh direct/journal context mismatch"
                )
            results.append(
                {
                    "case": "empty-fresh-context-positive",
                    "failures": [],
                }
            )
        finally:
            harness.cleanup_leased_project(
                root,
                suite=harness.SUITE,
                scenario=str(materialized["scenario"]),
                lease=current_lease,
            )

        try:
            validator._formal_plan_result(
                plan_bytes=b"irrelevant",
                replay_input="not-used",
                root=Path("."),
                lease="not-used",
                context={},
            )
        except TypeError:
            pass
        else:
            raise TestFailure(
                "formal plan result still accepts caller context"
            )
        results.append(
            {
                "case": "formal-context-caller-argument-rejected",
                "failures": ["formal-plan-validation"],
            }
        )
    finally:
        if scratch.exists():
            harness.strict_remove_tree(scratch)
    formal_scratch_after = _formal_scratch_entries(session_root)
    if formal_scratch_after != formal_scratch_before:
        raise TestFailure("cross-context formal attestation leaked scratch")
    results.append(
        {
            "case": "cross-context-formal-scratch-cleanup",
            "failures": [],
        }
    )


def run_tests(*, session_root: Path) -> Mapping[str, Any]:
    materialized = _run(
        [
            sys.executable,
            "-B",
            str(HERE / "fixture_harness.py"),
            "materialize",
            REPLAY_INPUT,
        ],
        expected_exit=0,
    )
    root = Path(materialized["worktree"])
    lease = materialized["lease"]
    scratch = Path(
        tempfile.mkdtemp(
            prefix="bridge-journal-v2-tests-",
            dir=session_root,
        )
    )
    operation_id = "journal-v2-command-tests"
    journal_path: Optional[Path] = None
    results: List[Dict[str, Any]] = []
    try:
        plan_path = scratch / "plan.md"
        plan_path.write_text(PLAN_TEXT, encoding="utf-8", newline="\n")
        journal_path = harness._allocate_journal_path(root, operation_id)
        valid = _build_journal(
            root=root,
            lease=lease,
            plan_path=plan_path,
            journal_path=journal_path,
            operation_id=operation_id,
            result="applied",
        )
        _apply_values(
            root,
            valid["path-operations"],
            _terminal_values(valid),
        )
        _write_canonical(journal_path, valid)
        base_command = _command(
            root=root,
            lease=lease,
            plan_path=plan_path,
            journal_path=journal_path,
        )
        positive = _run(base_command, expected_exit=0)
        if (
            positive.get("pass") is not True
            or positive.get("failures") != []
            or positive.get("lifecycle", {}).get("result") != "applied"
        ):
            raise TestFailure(f"valid v2 journal rejected: {positive}")
        results.append({"case": "applied-closed-positive", "failures": []})
        _exercise_formal_validator(
            results,
            root=root,
            lease=lease,
            plan_path=plan_path,
            valid=valid,
            session_root=session_root,
        )
        _exercise_cross_contexts(
            results,
            session_root=session_root,
        )

        raw = validator.canonical_json_bytes(valid)
        canonical_cases = [
            ("canonical-bom", b"\xef\xbb\xbf" + raw),
            ("canonical-trailing-newline", raw + b"\n"),
            (
                "canonical-whitespace",
                raw.replace(b'":', b'": ', 1),
            ),
            (
                "canonical-duplicate-key",
                b'{"canonicalization":"canonical-json/v1",'
                + raw[1:],
            ),
            ("canonical-nan", b'{"extra":NaN,' + raw[1:]),
        ]
        for label, data in canonical_cases:
            journal_path.write_bytes(data)
            _assert_failure(
                results, label, base_command, "canonical-document"
            )

        mutations: List[Tuple[str, str, Any]] = [
            (
                "schema-missing-field",
                "journal-schema",
                lambda item: item.pop("repository"),
            ),
            (
                "wrong-journal-version",
                "journal-version",
                lambda item: item.__setitem__(
                    "spec", "bridge-live-operation-journal/v1"
                ),
            ),
            (
                "operation-nonce",
                "operation-binding",
                lambda item: item["operation"]["allocation"].__setitem__(
                    "nonce", "wrong"
                ),
            ),
            (
                "operation-lease-identity",
                "operation-binding",
                lambda item: item["operation"]["allocation"]["lease"][
                    "identity"
                ].__setitem__("inode", "0"),
            ),
            (
                "repository-identity",
                "repository-binding",
                lambda item: item["repository"]["identity"].__setitem__(
                    "inode", "0"
                ),
            ),
            (
                "repository-head",
                "head-binding",
                lambda item: item["repository"]["head"].__setitem__(
                    "oid", "0" * 40
                ),
            ),
            (
                "plan-digest",
                "plan-digest",
                lambda item: item["plan"].__setitem__("sha256", "0" * 64),
            ),
            (
                "formal-context",
                "formal-plan-validation",
                lambda item: item["plan"]["validation-result"].__setitem__(
                    "context_sha256", "0" * 64
                ),
            ),
            (
                "fixture-envelope-hash",
                "fixture-binding",
                lambda item: item["fixture-binding"]["documents"][
                    "envelope"
                ].__setitem__("raw-sha256", "0" * 64),
            ),
            (
                "closure-members",
                "closure-binding",
                lambda item: item["closures"][0].__setitem__(
                    "members", ["rules/fake.md"]
                ),
            ),
            (
                "reordered-write-steps",
                "write-step-binding",
                lambda item: item["path-operations"].reverse(),
            ),
            (
                "missing-write-step",
                "write-step-binding",
                lambda item: item.__setitem__(
                    "path-operations", item["path-operations"][:-1]
                ),
            ),
        ]
        for label, failure_id, mutate in mutations:
            candidate = copy.deepcopy(valid)
            mutate(candidate)
            _write_canonical(journal_path, candidate)
            _assert_failure(results, label, base_command, failure_id)

        candidate = copy.deepcopy(valid)
        forged_context = candidate["plan"]["validation-context"]
        forged_context["live_untracked"] = ["forged-context.md"]
        forged_context["temporal_context"] = (
            harness.EMPTY_UNTRACKED_SCAN_CONTEXT
        )
        forged_context_sha = hashlib.sha256(
            validator.canonical_json_bytes(forged_context)
        ).hexdigest()
        candidate["plan"]["validation-context-sha256"] = (
            forged_context_sha
        )
        candidate["plan"]["validation-result"]["context_sha256"] = (
            forged_context_sha
        )
        candidate["plan"]["validation-result-sha256"] = hashlib.sha256(
            validator.canonical_json_bytes(
                candidate["plan"]["validation-result"]
            )
        ).hexdigest()
        _write_canonical(journal_path, candidate)
        _assert_failure(
            results,
            "self-consistent-forged-formal-context",
            base_command,
            "formal-plan-validation",
        )

        for unsafe in (
            "../escape",
            r"bad\path",
            "/absolute",
            "double//separator",
            "C:stream",
            "AGENTS.md:stream",
            "CON.txt",
            "trailing. ",
            "e\u0301.md",
        ):
            candidate = copy.deepcopy(valid)
            candidate["path-operations"][0]["path"] = unsafe
            _write_canonical(journal_path, candidate)
            _assert_failure(
                results,
                f"unsafe-path-{len(results)}",
                base_command,
                "path-binding",
            )

        candidate = copy.deepcopy(valid)
        candidate["path-operations"][1]["path"] = candidate[
            "path-operations"
        ][0]["path"].swapcase()
        _write_canonical(journal_path, candidate)
        _assert_failure(
            results,
            "casefold-path-collision",
            base_command,
            "path-binding",
        )

        candidate = copy.deepcopy(valid)
        encoded = candidate["path-operations"][0][
            "intended-post-value"
        ]["base64"]
        noncanonical = _noncanonical_base64(encoded)
        if noncanonical is None:
            raise TestFailure("test operation lacks padded base64")
        if base64.b64decode(noncanonical) != base64.b64decode(encoded):
            raise TestFailure("base64 pad-bit mutation changed decoded bytes")
        candidate["path-operations"][0]["intended-post-value"][
            "base64"
        ] = noncanonical
        _write_canonical(journal_path, candidate)
        _assert_failure(
            results,
            "noncanonical-base64",
            base_command,
            "value-binding",
        )

        candidate = copy.deepcopy(valid)
        guarded = next(
            operation
            for operation in candidate["path-operations"]
            if "guarded-region" in operation
        )
        guarded["guarded-region"]["byte-offset"] = str(
            int(guarded["guarded-region"]["byte-offset"]) + 1
        )
        _write_canonical(journal_path, candidate)
        _assert_failure(
            results,
            "guarded-region-offset",
            base_command,
            "guarded-region",
        )

        candidate = copy.deepcopy(valid)
        candidate["lifecycle"]["events"][1]["event-sha256"] = "0" * 64
        _write_canonical(journal_path, candidate)
        _assert_failure(
            results, "event-hash-tamper", base_command, "lifecycle-chain"
        )

        candidate = copy.deepcopy(valid)
        forward_attempts = [
            event
            for event in candidate["lifecycle"]["events"]
            if event["event"] == "forward-attempted"
        ]
        forward_attempts[0]["step"] = "2"
        _rehash_events(candidate)
        _write_canonical(journal_path, candidate)
        _assert_failure(
            results,
            "forward-step-skip",
            base_command,
            "lifecycle-semantics",
        )

        candidate = copy.deepcopy(valid)
        candidate["lifecycle"]["events"] = [
            event
            for event in candidate["lifecycle"]["events"]
            if not (
                event["event"] == "forward-attempted"
                and event["step"] == "1"
            )
        ]
        _rehash_events(candidate)
        _write_canonical(journal_path, candidate)
        _assert_failure(
            results,
            "observation-without-attempt",
            base_command,
            "lifecycle-semantics",
        )

        candidate = copy.deepcopy(valid)
        candidate["lifecycle"]["anchor-sha256"] = "0" * 64
        _write_canonical(journal_path, candidate)
        _assert_failure(
            results, "static-anchor-tamper", base_command, "lifecycle-chain"
        )

        invalid_plan = scratch / "invalid-plan.md"
        invalid_plan.write_bytes(b"not a bridge plan\n")
        _write_canonical(journal_path, valid)
        _assert_failure(
            results,
            "invalid-plan-document",
            _command(
                root=root,
                lease=lease,
                plan_path=invalid_plan,
                journal_path=journal_path,
            ),
            "plan-document",
        )

        _apply_values(
            root,
            valid["path-operations"],
            _terminal_values(valid),
        )
        _write_canonical(journal_path, valid)
        drift_path = root / "AGENTS.md"
        original_drift_bytes = drift_path.read_bytes()
        drift_path.write_bytes(original_drift_bytes + b"drift\n")
        try:
            _assert_failure(
                results,
                "terminal-worktree-drift",
                base_command,
                "worktree-binding",
            )
        finally:
            drift_path.write_bytes(original_drift_bytes)

        partial = _build_journal(
            root=root,
            lease=lease,
            plan_path=plan_path,
            journal_path=journal_path,
            operation_id=operation_id,
            result="partial",
        )
        _apply_values(
            root,
            partial["path-operations"],
            _terminal_values(partial),
        )
        _write_canonical(journal_path, partial)
        partial_result = _run(base_command, expected_exit=0)
        if (
            partial_result.get("lifecycle", {}).get("result") != "partial"
            or partial_result.get("pass") is not True
        ):
            raise TestFailure("valid retained partial journal was rejected")
        results.append({"case": "partial-positive", "failures": []})
        _assert_failure(
            results,
            "partial-cleanup-refused",
            _command(
                root=root,
                lease=lease,
                plan_path=plan_path,
                journal_path=journal_path,
                cleanup=True,
            ),
            "cleanup-eligibility",
        )

        failed = _build_journal(
            root=root,
            lease=lease,
            plan_path=plan_path,
            journal_path=journal_path,
            operation_id=operation_id,
            result="failed",
        )
        _apply_values(
            root,
            failed["path-operations"],
            _terminal_values(failed),
        )
        _write_canonical(journal_path, failed)
        failed_result = _run(base_command, expected_exit=0)
        if (
            failed_result.get("lifecycle", {}).get("result") != "failed"
            or failed_result.get("pass") is not True
        ):
            raise TestFailure("exact-preimage failed journal was rejected")
        results.append({"case": "failed-closed-positive", "failures": []})

        cleanup_command = _command(
            root=root,
            lease=lease,
            plan_path=plan_path,
            journal_path=journal_path,
            cleanup=True,
        )
        if os.name == "nt":
            cleanup_result = _assert_failure(
                results,
                "windows-cleanup-capability-block",
                cleanup_command,
                "platform-capability",
            )
            if cleanup_result.get("cleanup-receipt") is not None:
                raise TestFailure("Windows emitted an unproven cleanup receipt")
        else:
            cleanup_result = _run(cleanup_command, expected_exit=0)
            if set(cleanup_result.get("cleanup-receipt") or {}) != {
                "journal-sha",
                "file-id",
                "lease-id",
            }:
                raise TestFailure("POSIX cleanup receipt fields are invalid")
            results.append({"case": "cleanup-receipt-positive", "failures": []})

        _exercise_pure_lifecycle(results, valid)
        _exercise_unborn(
            results,
            root=root,
            lease=lease,
            plan_path=plan_path,
            journal_path=journal_path,
        )
        _exercise_posix_retained_drift(results)

        cleanup_first = {
            "journal-file-identity": {"id": "file-a"},
            "journal-sha256": "a" * 64,
            "lease-identity": {"id": "lease-a"},
            "lifecycle": {"result": "failed", "state": "closed"},
            "plan-sha256": "b" * 64,
        }
        cleanup_second = copy.deepcopy(cleanup_first)
        cleanup_second["journal-sha256"] = "c" * 64
        try:
            validator.cleanup_receipt(cleanup_first, cleanup_second)
        except validator.ValidationError as error:
            if error.failure_id != "cleanup-drift":
                raise
        else:
            raise TestFailure("cleanup receipt accepted a drifting snapshot")
        results.append(
            {"case": "cleanup-snapshot-drift", "failures": ["cleanup-drift"]}
        )

        _write_canonical(journal_path, failed)
        hardlink = scratch / "plan-hardlink.md"
        os.link(plan_path, hardlink)
        try:
            _assert_failure(
                results, "plan-hardlink", base_command, "authority-identity"
            )
        finally:
            hardlink.unlink()

        journal_hardlink = scratch / "journal-hardlink.json"
        os.link(journal_path, journal_hardlink)
        try:
            _assert_failure(
                results,
                "journal-hardlink",
                base_command,
                "authority-identity",
            )
        finally:
            journal_hardlink.unlink()

        envelope_path = root / validator.DOCUMENT_PATHS["envelope"]
        envelope_bytes = envelope_path.read_bytes()
        envelope = json.loads(envelope_bytes.decode("utf-8"))
        envelope["commitment_sha256"] = "0" * 64
        envelope_path.write_bytes(validator.canonical_json_bytes(envelope))
        try:
            _assert_failure(
                results,
                "outer-envelope-commitment-tamper",
                base_command,
                "fixture-binding",
            )
        finally:
            envelope_path.write_bytes(envelope_bytes)

        capability_path = root / validator.DOCUMENT_PATHS["write-capability"]
        capability_bytes = capability_path.read_bytes()
        replacement = capability_path.with_name("capability-replacement.tmp")
        replacement.write_bytes(capability_bytes)
        os.replace(replacement, capability_path)
        _assert_failure(
            results,
            "same-bytes-capability-swap",
            base_command,
            "fixture-binding",
        )

        covered = {
            failure
            for result in results
            for failure in result["failures"]
        }
        required = {
            "canonical-document",
            "journal-schema",
            "journal-version",
            "authority-identity",
            "operation-binding",
            "repository-binding",
            "head-binding",
            "plan-digest",
            "formal-plan-validation",
            "fixture-binding",
            "closure-binding",
            "path-binding",
            "write-step-binding",
            "value-binding",
            "guarded-region",
            "lifecycle-chain",
            "lifecycle-semantics",
            "worktree-binding",
            "cleanup-eligibility",
            "cleanup-drift",
        }
        if required - covered:
            raise TestFailure(
                f"required failure coverage missing: {sorted(required - covered)}"
            )
        return {
            "cases": len(results),
            "contract": validator.VALIDATOR_SPEC,
            "failure_ids": list(validator.FAILURE_ORDER),
            "journal_spec": validator.JOURNAL_SPEC,
            "pass": True,
            "platform_capability": validator._platform_capability(),
        }
    finally:
        if journal_path is not None and journal_path.parent.exists():
            harness.strict_remove_tree(journal_path.parent)
        if root.exists():
            harness.cleanup_leased_project(
                root,
                suite=harness.SUITE,
                scenario=SCENARIO,
                lease=lease,
            )
        if scratch.exists():
            harness.strict_remove_tree(scratch)


def _single_result() -> Dict[str, Any]:
    session_id = ""
    with _session_temp_root() as session_root:
        session_id = session_root.name
        result = dict(run_tests(session_root=session_root))
    if session_root.exists():
        raise TestFailure("journal test session root survived cleanup")
    if (
        result.get("pass") is not True
        or result.get("cases") != EXPECTED_CASES
        or result.get("contract") != validator.VALIDATOR_SPEC
        or result.get("journal_spec") != validator.JOURNAL_SPEC
    ):
        raise TestFailure("journal single-suite result contract drifted")
    result.update(
        {
            "mode": "single",
            "session_cleanup": True,
            "session_id": session_id,
        }
    )
    return result


def _worker_timeout(
    deadline: float,
    *,
    reserve_seconds: float = 0.0,
    maximum_seconds: Optional[float] = None,
    monotonic: Any = time.monotonic,
) -> float:
    remaining = max(
        0.0,
        deadline - monotonic() - reserve_seconds,
    )
    if maximum_seconds is not None:
        remaining = min(remaining, maximum_seconds)
    return remaining


def _worker_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def _new_worker_record(index: int) -> Dict[str, Any]:
    return {
        "case": f"concurrent-worker-{index}",
        "cleanup_errors": [],
        "collection_error": None,
        "communicated": False,
        "killed": False,
        "launch_error": None,
        "pid": None,
        "reaped": False,
        "returncode": None,
        "session": None,
        "started": False,
        "stderr": b"",
        "stdout": b"",
        "terminated": False,
        "waited": False,
    }


def _capture_worker_output(
    record: Dict[str, Any],
    stdout: Any,
    stderr: Any,
) -> None:
    if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
        raise TestFailure("concurrent worker pipes did not return bytes")
    record["stdout"] = stdout
    record["stderr"] = stderr
    record["communicated"] = True


def _safe_worker_poll(
    process: Any,
    record: Dict[str, Any],
) -> Optional[int]:
    try:
        value = process.poll()
    except Exception as error:
        record["cleanup_errors"].append(
            "poll: " + _worker_error(error)
        )
        return None
    if value is not None and not isinstance(value, int):
        record["cleanup_errors"].append(
            f"poll: non-integer return code {value!r}"
        )
        return None
    return value


def _collect_concurrent_workers(
    *,
    command: Sequence[str],
    environment: Mapping[str, str],
    worker_count: int = CONCURRENT_WORKERS,
    deadline_seconds: float = CONCURRENT_DEADLINE_SECONDS,
    popen_factory: Any = subprocess.Popen,
    monotonic: Any = time.monotonic,
) -> List[Dict[str, Any]]:
    if (
        worker_count <= 0
        or deadline_seconds <= CONCURRENT_REAP_RESERVE_SECONDS
    ):
        raise TestFailure("concurrent worker deadline configuration is invalid")
    deadline = monotonic() + deadline_seconds
    records: List[Dict[str, Any]] = []
    started: List[Tuple[Dict[str, Any], Any]] = []
    launch_failed = False
    try:
        for index in range(1, worker_count + 1):
            record = _new_worker_record(index)
            records.append(record)
            if launch_failed:
                record["launch_error"] = (
                    "not started after an earlier launch failure"
                )
                continue
            if (
                _worker_timeout(
                    deadline,
                    reserve_seconds=CONCURRENT_REAP_RESERVE_SECONDS,
                    monotonic=monotonic,
                )
                <= 0
            ):
                record["launch_error"] = (
                    "single monotonic worker deadline expired before launch"
                )
                launch_failed = True
                continue
            try:
                process = popen_factory(
                    list(command),
                    cwd=HERE.parent.parent,
                    env=dict(environment),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except Exception as error:
                record["launch_error"] = _worker_error(error)
                launch_failed = True
                continue
            record["started"] = True
            record["pid"] = getattr(process, "pid", None)
            started.append((record, process))
            if (
                _worker_timeout(
                    deadline,
                    reserve_seconds=CONCURRENT_REAP_RESERVE_SECONDS,
                    monotonic=monotonic,
                )
                <= 0
            ):
                record["collection_error"] = (
                    "single monotonic worker deadline expired during launch"
                )
                launch_failed = True

        if not launch_failed:
            for record, process in started:
                timeout = _worker_timeout(
                    deadline,
                    reserve_seconds=CONCURRENT_REAP_RESERVE_SECONDS,
                    monotonic=monotonic,
                )
                if timeout <= 0:
                    record["collection_error"] = (
                        "single monotonic worker deadline expired "
                        "before communicate"
                    )
                    continue
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                    _capture_worker_output(record, stdout, stderr)
                except subprocess.TimeoutExpired as error:
                    record["collection_error"] = _worker_error(error)
                except Exception as error:
                    record["collection_error"] = _worker_error(error)
    finally:
        for record, process in started:
            if _safe_worker_poll(process, record) is None:
                try:
                    process.terminate()
                    record["terminated"] = True
                except Exception as error:
                    record["cleanup_errors"].append(
                        "terminate: " + _worker_error(error)
                    )

        for record, process in started:
            if record["communicated"]:
                continue
            try:
                stdout, stderr = process.communicate(
                    timeout=_worker_timeout(
                        deadline,
                        maximum_seconds=CONCURRENT_REAP_STEP_SECONDS,
                        monotonic=monotonic,
                    )
                )
                _capture_worker_output(record, stdout, stderr)
            except subprocess.TimeoutExpired as error:
                record["cleanup_errors"].append(
                    "communicate-after-terminate: "
                    + _worker_error(error)
                )
            except Exception as error:
                record["cleanup_errors"].append(
                    "communicate-after-terminate: "
                    + _worker_error(error)
                )

        for record, process in started:
            if _safe_worker_poll(process, record) is None:
                try:
                    process.kill()
                    record["killed"] = True
                except Exception as error:
                    record["cleanup_errors"].append(
                        "kill: " + _worker_error(error)
                    )

        for record, process in started:
            if record["communicated"]:
                continue
            try:
                stdout, stderr = process.communicate(
                    timeout=_worker_timeout(
                        deadline,
                        maximum_seconds=CONCURRENT_REAP_STEP_SECONDS,
                        monotonic=monotonic,
                    )
                )
                _capture_worker_output(record, stdout, stderr)
            except subprocess.TimeoutExpired as error:
                record["cleanup_errors"].append(
                    "communicate-after-kill: " + _worker_error(error)
                )
            except Exception as error:
                record["cleanup_errors"].append(
                    "communicate-after-kill: " + _worker_error(error)
                )

        for record, process in started:
            try:
                process.wait(
                    timeout=_worker_timeout(
                        deadline,
                        maximum_seconds=CONCURRENT_REAP_STEP_SECONDS,
                        monotonic=monotonic,
                    )
                )
                record["waited"] = True
            except subprocess.TimeoutExpired as error:
                record["cleanup_errors"].append(
                    "wait: " + _worker_error(error)
                )
            except Exception as error:
                record["cleanup_errors"].append(
                    "wait: " + _worker_error(error)
                )
            returncode = _safe_worker_poll(process, record)
            record["returncode"] = returncode
            record["reaped"] = record["waited"] and returncode is not None

    for record in records:
        try:
            candidate = json.loads(record["stdout"].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(candidate, dict) and isinstance(
            candidate.get("session_id"), str
        ):
            record["session"] = candidate["session_id"]
    return records


def _worker_diagnostic(records: Sequence[Mapping[str, Any]]) -> str:
    def stream_evidence(data: Any) -> Dict[str, Any]:
        if not isinstance(data, bytes):
            raise TestFailure("worker diagnostic stream is not bytes")
        excerpt = data[:WORKER_DIAGNOSTIC_EXCERPT_BYTES]
        return {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "truncated": len(data) > len(excerpt),
            "utf8_excerpt": excerpt.decode(
                "utf-8", errors="backslashreplace"
            ),
        }

    diagnostic = []
    for record in records:
        diagnostic.append(
            {
                "case": record["case"],
                "cleanup_errors": list(record["cleanup_errors"]),
                "collection_error": record["collection_error"],
                "communicated": record["communicated"],
                "killed": record["killed"],
                "launch_error": record["launch_error"],
                "pid": record["pid"],
                "reaped": record["reaped"],
                "returncode": record["returncode"],
                "session": record["session"],
                "started": record["started"],
                "stderr": stream_evidence(record["stderr"]),
                "stdout": stream_evidence(record["stdout"]),
                "terminated": record["terminated"],
                "waited": record["waited"],
            }
        )
    return json.dumps(
        diagnostic,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _validate_concurrent_workers(
    records: Sequence[Mapping[str, Any]],
    *,
    expected_workers: int = CONCURRENT_WORKERS,
    validation_hook: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    if validation_hook is not None:
        validation_hook(records)
    errors: List[str] = []
    parsed: List[Optional[Dict[str, Any]]] = []
    if len(records) != expected_workers:
        errors.append(
            f"worker cardinality {len(records)}, wanted {expected_workers}"
        )
    for record in records:
        result: Optional[Dict[str, Any]] = None
        if record["launch_error"] is not None:
            errors.append(
                f"{record['case']}: launch failed: "
                f"{record['launch_error']}"
            )
        if record["started"] and (
            not isinstance(record["pid"], int)
            or record["pid"] <= 0
        ):
            errors.append(f"{record['case']}: process PID is invalid")
        if record["started"] and not record["reaped"]:
            errors.append(f"{record['case']}: process was not reaped")
        if record["cleanup_errors"]:
            errors.append(
                f"{record['case']}: cleanup failed: "
                + "; ".join(record["cleanup_errors"])
            )
        if record["collection_error"] is not None:
            errors.append(
                f"{record['case']}: collection failed: "
                f"{record['collection_error']}"
            )
        try:
            candidate = json.loads(record["stdout"].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            errors.append(
                f"{record['case']}: stdout is not one JSON object: "
                f"{_worker_error(error)}"
            )
        else:
            if isinstance(candidate, dict):
                result = candidate
            else:
                errors.append(
                    f"{record['case']}: worker JSON root is not an object"
                )
        if (
            result is not None
            and (
                record["returncode"] != 0
                or result.get("pass") is not True
                or result.get("mode") != "single"
                or result.get("cases") != EXPECTED_CASES
                or result.get("contract") != validator.VALIDATOR_SPEC
                or result.get("journal_spec") != validator.JOURNAL_SPEC
                or result.get("session_cleanup") is not True
                or result.get("session_id") != record["session"]
            )
        ):
            errors.append(
                f"{record['case']}: worker result contract drifted"
            )
        parsed.append(result)
    session_ids = {
        str(result["session_id"])
        for result in parsed
        if isinstance(result, dict)
        and isinstance(result.get("session_id"), str)
    }
    if len(session_ids) != expected_workers:
        errors.append(
            "concurrent journal workers did not use unique session roots"
        )
    if errors:
        raise TestFailure(
            "concurrent journal worker group failed: "
            + "; ".join(errors)
            + "; evidence="
            + _worker_diagnostic(records)
        )
    return [
        result
        for result in parsed
        if isinstance(result, dict)
    ]


def _concurrent_summary(workers: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "cases_per_worker": EXPECTED_CASES,
        "contract": validator.VALIDATOR_SPEC,
        "journal_spec": validator.JOURNAL_SPEC,
        "mode": "concurrent",
        "pass": True,
        "passed": len(workers),
        "session_cleanup_passed": sum(
            result.get("session_cleanup") is True for result in workers
        ),
        "total_cases": len(workers) * EXPECTED_CASES,
        "unique_session_roots": len(
            {str(result["session_id"]) for result in workers}
        ),
        "workers": len(workers),
    }


def _concurrent_command() -> Tuple[List[str], Dict[str, str]]:
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--mode",
        "single",
    ]
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"
    return command, environment


def _concurrent_result() -> Dict[str, Any]:
    command, environment = _concurrent_command()
    records = _collect_concurrent_workers(
        command=command,
        environment=environment,
    )
    workers = _validate_concurrent_workers(records)
    return _concurrent_summary(workers)


def _fake_worker_payload(session_id: str) -> bytes:
    return json.dumps(
        {
            "cases": EXPECTED_CASES,
            "contract": validator.VALIDATOR_SPEC,
            "journal_spec": validator.JOURNAL_SPEC,
            "mode": "single",
            "pass": True,
            "session_cleanup": True,
            "session_id": session_id,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class _FakeWorkerProcess:
    def __init__(
        self,
        *,
        pid: int,
        behavior: str,
        stdout: bytes,
        stderr: bytes = b"",
        events: Optional[List[Tuple[Any, ...]]] = None,
    ) -> None:
        self.pid = pid
        self.behavior = behavior
        self._stdout = stdout
        self._stderr = stderr
        self.returncode: Optional[int] = None
        self.communicate_calls = 0
        self.kill_calls = 0
        self.terminate_calls = 0
        self.wait_calls = 0
        self.events = events

    def poll(self) -> Optional[int]:
        return self.returncode

    def communicate(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> Tuple[bytes, bytes]:
        self.communicate_calls += 1
        if self.events is not None:
            self.events.append(("communicate", self.pid, timeout))
        if self.behavior == "timeout" and self.kill_calls == 0:
            raise subprocess.TimeoutExpired(
                cmd=["fake-journal-worker"],
                timeout=timeout,
                output=self._stdout,
                stderr=self._stderr,
            )
        if self.returncode is None:
            self.returncode = -9 if self.kill_calls else 0
        return self._stdout, self._stderr

    def terminate(self) -> None:
        self.terminate_calls += 1
        if self.events is not None:
            self.events.append(("terminate", self.pid))

    def kill(self) -> None:
        self.kill_calls += 1
        if self.events is not None:
            self.events.append(("kill", self.pid))
        self.returncode = -9

    def wait(self, *, timeout: Optional[float] = None) -> int:
        self.wait_calls += 1
        if self.events is not None:
            self.events.append(("wait", self.pid, timeout))
        if self.returncode is None:
            raise subprocess.TimeoutExpired(
                cmd=["fake-journal-worker"],
                timeout=timeout,
            )
        return self.returncode


class _FakePopenFactory:
    def __init__(
        self,
        behaviors: Sequence[str],
        *,
        fail_launch: Optional[int] = None,
        events: Optional[List[Tuple[Any, ...]]] = None,
    ) -> None:
        self.behaviors = list(behaviors)
        self.fail_launch = fail_launch
        self.calls = 0
        self.processes: List[_FakeWorkerProcess] = []
        self.events = events

    def __call__(self, *_: Any, **__: Any) -> _FakeWorkerProcess:
        self.calls += 1
        if self.events is not None:
            self.events.append(("launch", self.calls))
        if self.calls == self.fail_launch:
            raise OSError(f"injected launch failure {self.calls}")
        behavior = self.behaviors[self.calls - 1]
        if behavior == "bad-json":
            stdout = b"{broken-json"
            stderr = b""
        elif behavior == "oversize":
            stdout = b"{" + b"x" * (
                2 * WORKER_DIAGNOSTIC_EXCERPT_BYTES
            )
            stderr = b"e" * (
                2 * WORKER_DIAGNOSTIC_EXCERPT_BYTES + 1
            )
        elif behavior == "invalid-utf8":
            stdout = b"\xff\xfe{broken-json"
            stderr = b"\x80invalid-stderr"
        else:
            stdout = _fake_worker_payload(
                f"fake-session-{self.calls}"
            )
            stderr = b""
        process = _FakeWorkerProcess(
            pid=50000 + self.calls,
            behavior=behavior,
            stdout=stdout,
            stderr=stderr,
            events=self.events,
        )
        self.processes.append(process)
        return process


class _FakeMonotonic:
    def __init__(
        self,
        events: List[Tuple[Any, ...]],
        *,
        start: float = 1000.0,
        step: float = 0.25,
    ) -> None:
        self.events = events
        self.current = start
        self.step = step

    def __call__(self) -> float:
        value = self.current
        self.current += self.step
        self.events.append(("monotonic", value))
        return value


def _expect_worker_failure(
    records: Sequence[Mapping[str, Any]],
    *,
    required: str,
    validation_hook: Optional[Any] = None,
) -> str:
    try:
        _validate_concurrent_workers(
            records,
            validation_hook=validation_hook,
        )
    except TestFailure as error:
        message = str(error)
        if required not in message:
            raise TestFailure(
                f"worker failure lacked {required!r}: {message}"
            ) from error
        return message
    raise TestFailure("injected worker lifecycle failure was accepted")


def _worker_failure_evidence(message: str) -> List[Dict[str, Any]]:
    marker = "; evidence="
    if marker not in message:
        raise TestFailure("worker failure omitted structured evidence")
    try:
        value = json.loads(message.split(marker, 1)[1])
    except json.JSONDecodeError as error:
        raise TestFailure(
            "worker failure evidence is not JSON"
        ) from error
    if (
        not isinstance(value, list)
        or any(not isinstance(item, dict) for item in value)
    ):
        raise TestFailure("worker failure evidence shape is invalid")
    return value


def _worker_fault_matrix() -> Dict[str, Any]:
    command = ["fake-journal-worker"]
    environment: Dict[str, str] = {}
    cases: List[str] = []

    success_events: List[Tuple[Any, ...]] = []
    success_clock = _FakeMonotonic(success_events)
    success = _FakePopenFactory(
        ["success", "success"],
        events=success_events,
    )
    success_records = _collect_concurrent_workers(
        command=command,
        environment=environment,
        popen_factory=success,
        monotonic=success_clock,
    )
    success_workers = _validate_concurrent_workers(success_records)
    if (
        _concurrent_summary(success_workers)["total_cases"]
        != 2 * EXPECTED_CASES
        or any(
            process.wait_calls != 1
            or process.terminate_calls
            or process.kill_calls
            for process in success.processes
        )
    ):
        raise TestFailure("fake dual-success worker lifecycle drifted")
    cases.append("dual-success")
    launch_indexes = [
        index
        for index, event in enumerate(success_events)
        if event[0] == "launch"
    ]
    communicate_indexes = [
        index
        for index, event in enumerate(success_events)
        if event[0] == "communicate"
    ]
    if (
        len(launch_indexes) != CONCURRENT_WORKERS
        or not communicate_indexes
        or max(launch_indexes) >= min(communicate_indexes)
    ):
        raise TestFailure(
            "concurrent workers were serialized before all launches"
        )
    cases.append("all-workers-launched-before-collect")
    reconstructed_deadlines: List[float] = []
    seen_communicate_pids = set()
    for index in communicate_indexes:
        event = success_events[index]
        pid = event[1]
        if pid in seen_communicate_pids:
            continue
        seen_communicate_pids.add(pid)
        previous = success_events[index - 1]
        if (
            previous[0] != "monotonic"
            or not isinstance(event[2], float)
        ):
            raise TestFailure(
                "worker communicate timeout lacks monotonic evidence"
            )
        reconstructed_deadlines.append(
            previous[1]
            + event[2]
            + CONCURRENT_REAP_RESERVE_SECONDS
        )
    expected_deadline = 1000.0 + CONCURRENT_DEADLINE_SECONDS
    if (
        len(reconstructed_deadlines) != CONCURRENT_WORKERS
        or any(
            deadline != expected_deadline
            for deadline in reconstructed_deadlines
        )
    ):
        raise TestFailure(
            "concurrent workers did not share one absolute deadline"
        )
    cases.append("shared-monotonic-deadline")

    launch_failure = _FakePopenFactory(
        ["success", "success"],
        fail_launch=2,
    )
    launch_records = _collect_concurrent_workers(
        command=command,
        environment=environment,
        popen_factory=launch_failure,
    )
    _expect_worker_failure(
        launch_records,
        required="injected launch failure 2",
    )
    if (
        len(launch_failure.processes) != 1
        or launch_failure.processes[0].terminate_calls != 1
        or launch_failure.processes[0].wait_calls != 1
        or not launch_records[0]["reaped"]
    ):
        raise TestFailure(
            "partial worker launch did not reap its started process"
        )
    cases.append("second-launch-failure-reaped")

    timeout_events: List[Tuple[Any, ...]] = []
    timeout_factory = _FakePopenFactory(
        ["timeout", "success"],
        events=timeout_events,
    )
    timeout_records = _collect_concurrent_workers(
        command=command,
        environment=environment,
        popen_factory=timeout_factory,
    )
    _expect_worker_failure(timeout_records, required="TimeoutExpired")
    timed_out = timeout_factory.processes[0]
    if (
        timed_out.terminate_calls != 1
        or timed_out.kill_calls != 1
        or timed_out.wait_calls != 1
        or not timeout_records[0]["reaped"]
        or any(
            process.wait_calls != 1
            for process in timeout_factory.processes
        )
    ):
        raise TestFailure(
            "timed-out worker did not complete terminate/kill/wait"
        )
    timeout_actions = [
        event[0]
        for event in timeout_events
        if event[0]
        in {"communicate", "terminate", "kill", "wait"}
        and event[1] == timed_out.pid
    ]
    if timeout_actions != [
        "communicate",
        "terminate",
        "communicate",
        "kill",
        "communicate",
        "wait",
    ]:
        raise TestFailure(
            "timed-out worker lifecycle order drifted: "
            + repr(timeout_actions)
        )
    cases.append("communicate-timeout-killed-reaped")
    cases.append("timeout-reap-order")

    bad_events: List[Tuple[Any, ...]] = []
    bad_json = _FakePopenFactory(
        ["bad-json", "success"],
        events=bad_events,
    )
    bad_records = _collect_concurrent_workers(
        command=command,
        environment=environment,
        popen_factory=bad_json,
    )
    if not all(
        record["reaped"] and process.wait_calls == 1
        for record, process in zip(bad_records, bad_json.processes)
    ):
        raise TestFailure(
            "bad-JSON worker was validated before all workers were reaped"
        )
    def validation_after_reap(
        records: Sequence[Mapping[str, Any]],
    ) -> None:
        bad_events.append(("validate",))
        if not all(
            record["reaped"] and process.wait_calls == 1
            for record, process in zip(records, bad_json.processes)
        ):
            raise TestFailure(
                "worker validation began before complete reaping"
            )

    bad_message = _expect_worker_failure(
        bad_records,
        required="stdout is not one JSON object",
        validation_hook=validation_after_reap,
    )
    validation_index = next(
        index
        for index, event in enumerate(bad_events)
        if event[0] == "validate"
    )
    wait_indexes = [
        index
        for index, event in enumerate(bad_events)
        if event[0] == "wait"
    ]
    if (
        len(wait_indexes) != CONCURRENT_WORKERS
        or max(wait_indexes) >= validation_index
    ):
        raise TestFailure(
            "worker parse/validation ran before all wait events"
        )
    cases.append("bad-json-after-full-reap")
    cases.append("validation-after-full-reap")
    bad_evidence = _worker_failure_evidence(bad_message)
    if len(bad_evidence) != len(bad_records):
        raise TestFailure("bad-JSON diagnostic omitted peer worker evidence")
    for evidence, record in zip(bad_evidence, bad_records):
        if (
            evidence.get("case") != record["case"]
            or evidence.get("pid") != record["pid"]
            or evidence.get("session") != record["session"]
            or evidence.get("returncode") != record["returncode"]
        ):
            raise TestFailure(
                "peer worker identity/result diagnostic is incomplete"
            )
        for stream_name in ("stdout", "stderr"):
            original = record[stream_name]
            stream = evidence.get(stream_name, {})
            if (
                stream.get("bytes") != len(original)
                or stream.get("sha256")
                != hashlib.sha256(original).hexdigest()
                or stream.get("truncated") is not False
                or stream.get("utf8_excerpt")
                != original.decode("utf-8")
            ):
                raise TestFailure(
                    f"peer worker {stream_name} diagnostic is incomplete"
                )
    cases.append("peer-diagnostic-complete")

    oversize = _FakePopenFactory(["oversize", "success"])
    oversize_records = _collect_concurrent_workers(
        command=command,
        environment=environment,
        popen_factory=oversize,
    )
    oversize_message = _expect_worker_failure(
        oversize_records,
        required="stdout is not one JSON object",
    )
    oversize_evidence = _worker_failure_evidence(oversize_message)[0]
    for stream_name, original in (
        ("stdout", oversize_records[0]["stdout"]),
        ("stderr", oversize_records[0]["stderr"]),
    ):
        stream = oversize_evidence[stream_name]
        if (
            stream.get("bytes") != len(original)
            or stream.get("sha256")
            != hashlib.sha256(original).hexdigest()
            or stream.get("truncated") is not True
            or len(
                stream.get("utf8_excerpt", "").encode("utf-8")
            )
            != WORKER_DIAGNOSTIC_EXCERPT_BYTES
        ):
            raise TestFailure(
                f"oversize worker {stream_name} evidence is unbounded"
            )
    if (
        len(oversize_message)
        >= len(oversize_records[0]["stdout"])
        + len(oversize_records[0]["stderr"])
    ):
        raise TestFailure("oversize worker diagnostic retained full streams")
    cases.append("oversize-streams-bounded")

    invalid_utf8 = _FakePopenFactory(["invalid-utf8", "success"])
    invalid_records = _collect_concurrent_workers(
        command=command,
        environment=environment,
        popen_factory=invalid_utf8,
    )
    invalid_message = _expect_worker_failure(
        invalid_records,
        required="stdout is not one JSON object",
    )
    invalid_evidence = _worker_failure_evidence(invalid_message)[0]
    for stream_name, escape in (
        ("stdout", "\\xff"),
        ("stderr", "\\x80"),
    ):
        original = invalid_records[0][stream_name]
        stream = invalid_evidence[stream_name]
        if (
            stream.get("bytes") != len(original)
            or stream.get("sha256")
            != hashlib.sha256(original).hexdigest()
            or stream.get("truncated") is not False
            or escape not in stream.get("utf8_excerpt", "")
        ):
            raise TestFailure(
                f"invalid UTF-8 worker {stream_name} evidence is unsafe"
            )
    cases.append("invalid-utf8-streams-safe")

    return {
        "cases": cases,
        "contract": WORKER_MATRIX_SPEC,
        "pass": True,
        "passed": len(cases),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exercise the breaking-v2 live journal validator."
    )
    parser.add_argument(
        "--mode",
        choices=("single", "concurrent", "worker-matrix"),
        default="single",
    )
    arguments = parser.parse_args()
    try:
        if arguments.mode == "single":
            result = _single_result()
        elif arguments.mode == "concurrent":
            result = _concurrent_result()
        else:
            result = _worker_fault_matrix()
    except (
        harness.FixtureError,
        OSError,
        TestFailure,
        validator.ValidationError,
        ValueError,
    ) as error:
        print(
            json.dumps(
                {"error": str(error), "pass": False},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
