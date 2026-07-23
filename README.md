# Agent Config Bridge

`agent-config-bridge` is the single-repo home for Agent Config Bridge: a Claude
Code / Codex bridge that will let a project maintain one canonical source for
agent skills, hooks, and rules, then project that source into host-native
layouts.

The repository is in the implementation phase: the roadmap has opened M1
(source-tree declaration and a read-only sentinel). Product artifacts land
milestone by milestone; the [roadmap](docs/phases/roadmap.md) says what each
milestone introduces.

Start with:

- [Product scope](docs/product/scope.md)
- [Architecture overview](docs/architecture/overview.md)
- [Sync model](docs/implementation/sync-model.md)
- [Distribution model](docs/implementation/distribution-model.md)
- [Tooling landscape](docs/research/ecosystem.md)
- [Roadmap](docs/phases/roadmap.md)

## Repository role

This is a single repository, modeled on `appstore-connect-skill` and
`sesamehut-auth`: it is the upstream design/development home and will carry the
installable plugin payload once the packaging milestone opens. The layout
layers by role:

- `skills/` — agent-facing skill sources: `SKILL.md`, references, metadata,
  and narrowly scoped read-only mechanics (tracked).
- `templates/` — install-time project templates such as the bridge covenant;
  these are not loaded as skill instructions (tracked).
- `knowledge/` — the host-mapping knowledge base, with collection dates
  (tracked).
- `fixtures/` — fixture projects with known states and expected reports, used
  to validate the skills (tracked).
- `src/` — TypeScript sources for the thin wrapper script (tracked; arrives
  with the packaging milestone).
- `dist/` — build/bundle intermediates for the wrapper (gitignored; arrives
  with the packaging milestone).
- `plugin/` — the installable payload, assembled at the packaging milestone
  and committed as a checked-in boundary artifact: plugin manifest,
  agent-facing skills, the host-mapping knowledge base, a thin wrapper, and
  README. It is assembled from audited upstream
  sources and keeps its generated-output nature — edit upstream and regenerate,
  never hand-edit `plugin/`.

The repository is named by domain plus product noun (`agent-config-bridge`),
with no `-plugin` distribution-form suffix; the plugin form is carried by the
inner `plugin/` directory.
