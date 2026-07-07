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
- `implementation/` - Technical implementation notes / strategy
  - `sync-model.md` - The synchronization model between the canonical source
    and host-native layouts
  - `distribution-model.md` - Repository layout and plugin packaging
- `research/` - Supporting research; externally sourced, non-decisional, each
  entry carries its collection date
  - `ecosystem.md` - Research on existing Claude/Codex config sync tools
  - `host-context-loading.md` - Verified host behavior for entry files and
    project context loading
- `phases/` - Phase planning and milestone tracking
  - `roadmap.md` - Milestone roadmap and phase planning

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
  module responsibilities, architecture, and implementation strategy. Do not
  include runnable code, exact generated payloads, full type definitions, or
  low-level configuration dumps while the repo is in the design/bootstrap phase.
- **Generated artifacts** - plugin manifests, bundled CLIs, generated skills,
  package lockfiles, and distribution payloads should not be introduced until
  the roadmap explicitly opens implementation or packaging work.
- **Research freshness** - Claude Code and Codex plugin / skill behavior is
  time-sensitive. Preserve collection dates in research notes and re-check
  official host docs before turning stale research into implementation.
- **Language** - all `docs/` content is written in Chinese; technical terms,
  commands, paths, file names, protocol names, and host names stay in English.
  This rule file lives outside `docs/`, so it is in English.
- **Cross-references** - use markdown links with relative paths from the
  current file; never absolute paths from the repo root.
