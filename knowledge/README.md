# knowledge/ — host fact base

This directory is the bridge's fact base about the two host tools, Claude
Code and Codex: what each host actually does with project-level agent
configuration, and how faithfully each semantic-unit class transfers between
the hosts. Sentinel reports and design decisions cite these files as
evidence.

## Scope boundary

Content here is limited to HOST FACTS and per-unit-class fidelity mappings.
The bridge's own normative prescriptions — marker grammar, rendering
templates, frontmatter schemas, the report format — live in the sentinel
skill's reference specs and are linked from here, never restated:

- [`../skills/bridge-sentinel/references/source-tree-spec.md`](../skills/bridge-sentinel/references/source-tree-spec.md)
  — source-tree entry conventions (spec version `source-tree/v2`)
- [`../skills/bridge-sentinel/references/report-spec.md`](../skills/bridge-sentinel/references/report-spec.md)
  — report states, tiers, lints, comparison rules (spec version `report/v2`)

## Files

| File | Unit class covered |
|---|---|
| [`entry-and-rules.md`](entry-and-rules.md) | Entry instructions and rule shards (`CLAUDE.md`, `.claude/rules/**`, root `AGENTS.md`) |
| [`skills.md`](skills.md) | Skills (`.claude/skills/` masters, `.agents/skills/` copies) |
| [`hooks.md`](hooks.md) | Hook intents and both hooks projection surfaces; ends with the per-hook-intent-class tier table stub, completed at M4 |
| [`execution-semantics.md`](execution-semantics.md) | Execution-semantics surfaces that are declared unsynced (approval policy, sandbox, execpolicy) |

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

- `status: watch` marks facts with open re-verification items. Watch items
  flagged "before M2 write work" gate the write-side milestone: re-check the
  official host docs before implementing against those facts.
- Every entry carries its collection date; entries are updated (with a new
  date) as hosts evolve.
