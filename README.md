# Agent Config Bridge

`agent-config-bridge` is the single-repo home for Agent Config Bridge: a Claude
Code / Codex bridge that will let a project maintain one canonical source for
agent skills, hooks, and rules, then project that source into host-native
layouts.

The repository is currently in the design phase. It should contain project
guidance and design documents only until the roadmap explicitly opens an
implementation phase.

Start with:

- [Product scope](docs/product/scope.md)
- [Architecture overview](docs/architecture/overview.md)
- [Sync model](docs/implementation/sync-model.md)
- [Distribution model](docs/implementation/distribution-model.md)
- [Tooling landscape](docs/research/ecosystem.md)
- [Roadmap](docs/phases/roadmap.md)

## Repository role

This is a single repository, modeled on `appstore-connect-skill` and
`sesamehut-auth`: it is the upstream design/development home **and** carries the
installable plugin payload. Once implementation opens, the layout layers by role:

- `src/` — TypeScript sources for the thin wrapper script (tracked).
- `dist/` — build/bundle intermediates for the wrapper (gitignored).
- `plugin/` — the installable payload committed as a checked-in boundary
  artifact: plugin manifest, agent-facing skills, the host-mapping knowledge
  base, a thin wrapper, and README. It is assembled from audited upstream
  sources and keeps its generated-output nature — edit upstream and regenerate,
  never hand-edit `plugin/`.

The repository is named by domain plus product noun (`agent-config-bridge`),
with no `-plugin` distribution-form suffix; the plugin form is carried by the
inner `plugin/` directory.
