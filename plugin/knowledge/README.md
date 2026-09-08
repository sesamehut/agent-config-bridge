# knowledge/ — host fact base

This directory is the bridge's fact base about the two host tools, Claude
Code and Codex: what each host actually does with project-level agent
configuration, and how faithfully each semantic-unit class transfers between
the hosts. Sentinel reports and design decisions cite these files as
evidence.

## Scope boundary

Content here is limited to HOST FACTS and per-unit-class fidelity mappings.
The bridge's own normative prescriptions — covenant bytes, marker grammar,
rendering templates, control-comment and path schemas, report states, and
write decisions — live in the checked-in templates and skill reference specs.
Knowledge files summarize the host facts and point to those authorities; they
do not create a second contract.

Hooks follow the same boundary. The knowledge base records what each host
executes, delivers, trusts, and ignores, plus the resulting per-intent-class
tier mapping. The hook intent schema, the intent class and opt-in gates, the
JSON write protocol, the tier and reason registries, and every report state
belong to the specs. Hook facts also carry a safety consequence that the
knowledge base states rather than enforces: hooks committed to a repository
run for everyone who clones it, and Bridge classification is review metadata,
not a sandbox.

The single current writable contract tuple is:

```text
covenant/v3
source-tree/v5
report/v5
reconciliation/v3
sync-plan/v3
```

Its authorities are:

- [`../skills/bridge-sentinel/references/source-tree-spec.md`](../skills/bridge-sentinel/references/source-tree-spec.md)
  — source-tree entry conventions, onboarding, hook intent schema, and
  Git-tree identity (spec version `source-tree/v5`)
- [`../skills/bridge-sentinel/references/report-spec.md`](../skills/bridge-sentinel/references/report-spec.md)
  — read-only report states, tiers, lints, and comparison rules
  (spec version `report/v5`)
- [`../skills/bridge-sync/references/reconciliation-spec.md`](../skills/bridge-sync/references/reconciliation-spec.md)
  — write-side ownership, baseline, safety, and transaction contract
  (spec version `reconciliation/v3`)
- [`../skills/bridge-sync/references/sync-plan-spec.md`](../skills/bridge-sync/references/sync-plan-spec.md)
  — deterministic write-plan states, actions, outcomes, tiers, and warnings
  (spec version `sync-plan/v3`)
- [`../templates/covenant/README.md`](../templates/covenant/README.md)
  — exact current `covenant/v3` source and projection assets plus migration
  routing.

The exact former `covenant/v1` / `source-tree/v3` pair under
[`../templates/covenant/v1/`](../templates/covenant/v1/) and the exact former
`covenant/v2` / `source-tree/v4` pair under
[`../templates/covenant/v2/`](../templates/covenant/v2/) are archived migration
evidence only. Together they are the closed two-member archived-pair set. Each
is a single hop to the current tuple, neither is an alternate readable or
writable contract, and normal runtime has no dual-read compatibility.

## Files

| File | Unit class covered |
|---|---|
| [`entry-and-rules.md`](entry-and-rules.md) | Entry instructions and rule shards (`CLAUDE.md`, `.claude/rules/**`, root `AGENTS.md`) |
| [`skills.md`](skills.md) | Skills (`.claude/skills/` masters, `.agents/skills/` copies) |
| [`hooks.md`](hooks.md) | Hook intents, both native hook carriers, and the degradation surface; carries the completed per-intent-class tier table, the trust, delivery, shell and matcher facts, the refuted-fact list, and the dated live-verification record |
| [`execution-semantics.md`](execution-semantics.md) | Execution-semantics surfaces that are declared unsynced (approval policy, sandbox, execpolicy) plus the hook keys, carriers, and policies that stay unprojected |

Each file is organized per semantic-unit class in two layers: settled
enumeration tables first, long-tail prose after.

## Entry format

Every entry follows this template:

```markdown
## <topic>

- collected: YYYY-MM-DD
- source: <official doc URL or repo/commit>
- status: settled | watch

<enumeration table and/or prose>
```

- `status: watch` marks facts with open re-verification items. A watch item
  that gates a host surface must be rechecked against official host docs
  before write-side implementation relies on it.
- Every entry carries its collection date; entries are updated (with a new
  date) as hosts evolve.
