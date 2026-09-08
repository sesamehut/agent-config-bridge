---
paths:
  - "docs/**/*"
---

# docs/ - Agent Config Bridge Design Documents

Split by document role / audience, not by implementation subsystem:
`product/` · `architecture/` · `implementation/` · `research/` · `phases/`.

## Directory Structure

This file is the docs entry point and inventory.

- `product/` - Product scope and boundaries
  - `scope.md` - Product positioning, scope, and non-goals
- `architecture/` - System design and design decisions
  - `overview.md` - System architecture and the design decisions behind it
  - `tech-stack.md` - Technology selection and dependency boundaries
  - `write-protocol.md` - Write protocol decision and capability boundaries
- `implementation/` - Technical implementation notes / strategy
  - `sync-model.md` - The synchronization model between the canonical source
    and host-native layouts
  - `distribution-model.md` - Repository layout and plugin packaging
- `research/` - Supporting research; externally sourced, non-decisional, each
  entry carries its collection date
  - `ecosystem.md` - Research on existing Claude/Codex config sync tools
  - `host-context-loading.md` - Verified host behavior for entry files and
    project context loading
  - `codex-capability-surface.md` - Verified Codex-side mechanisms: hooks,
    skills, rules, and the project-level config surface
  - `write-primitives.md` - Verified host and filesystem write primitives
  - `plugin-distribution-surface.md` - Verified Claude Code / Codex plugin
    manifest, skill-runtime, and marketplace mechanics behind the packaging
    design
- `phases/` - Phase planning and milestone tracking
  - `roadmap.md` - Milestone roadmap and phase planning
  - `closure/` - Per-milestone closure records: the evidence and check
    procedure frozen when a milestone closes; the newest record owns the
    standing procedure
    - `m1.md` - M1 closure record
    - `m2.md` - M2 closure record
    - `m3.md` - M3 closure record
    - `m4.md` - M4 closure record
    - `m5.md` - M5 closure record

## Rules

- **Structural source of truth** - this file owns the directory listing above.
  Whenever a file under `docs/` is added, renamed, or removed, update this
  inventory and nearby cross-document links in the same change.
- **Inventory describes purpose, not content** - each entry states what a doc is
  for / which topic it owns, never a summary of its claims or conclusions. Read
  the file itself for content. This keeps the inventory stable as docs evolve and
  avoids the description drifting out of sync with the document.
- **Docs taxonomy** - put new docs in the directory matching their role:
  positioning / scope -> `product/`; system design and design decisions ->
  `architecture/`; technical implementation notes -> `implementation/`;
  supporting research -> `research/`; phase plans and roadmap -> `phases/`.
- **Docs depth** - docs should focus on problem analysis, goals, design logic,
  module responsibilities, architecture, and implementation strategy -
  conclusions, not payloads. Exact product texts (skill bodies, covenant text
  templates, report schemas, mapping-knowledge entries) live in the product
  directories (`skills/`, `knowledge/`, `fixtures/`); design docs link to them
  instead of inlining them. Mechanism enumerations and host-behavior specifics
  live in `research/` entries; design docs state the conclusion and link.
- **Roadmap is plan only** - `phases/roadmap.md` holds each milestone's goal,
  work items, completion criteria, and deferrals, nothing else. Milestone
  status, delivered lists, check commands, evidence counts, and evidence
  boundaries belong to the per-milestone `phases/closure/<m>.md` record linked
  from the roadmap; each new record repeats every still-valid runnable command
  and links the standing prose checklists, so the newest record plus what it
  links is the complete procedure. Edit the roadmap only when the plan itself
  changes or new scope is added, never to record status or evidence.
- **Generated artifacts** - `plugin/` and the root
  `.claude-plugin/marketplace.json` are the only generated artifacts:
  `python -B scripts/package_plugin.py build` assembles them from the allowlist
  and `verify` must pass before they are committed. Never hand-edit them, and
  do not introduce other manifests, bundled CLIs, package files, or lockfiles.
- **Research freshness** - Claude Code and Codex plugin / skill behavior is
  time-sensitive. Preserve collection dates in research notes and re-check
  official host docs before turning stale research into implementation.
- **Language** - all `docs/` content is written in Chinese; technical terms,
  commands, paths, file names, protocol names, and host names stay in English.
  This rule file lives outside `docs/`, so it is in English.
- **Cross-references** - use markdown links with relative paths from the
  current file; never absolute paths from the repo root.
