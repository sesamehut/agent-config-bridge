# Agent Config Bridge

`agent-config-bridge` is the single-repo home for Agent Config Bridge: a Claude
Code / Codex bridge designed to let a project maintain one canonical source
for agent skills, hooks, and rules, then project that source into host-native
layouts.

The development tree has completed M1 and M2. Its current capability is the
project-skill surface:

- [`bridge-sentinel`](skills/bridge-sentinel/SKILL.md) observes repository
  carriers without writing, using `source-tree/v3` and `report/v3`.
- [`bridge-sync`](skills/bridge-sync/SKILL.md) plans, confirms, projects,
  adopts, and verifies complete skill trees using Git-proven per-unit
  baselines, `reconciliation/v1`, and `sync-plan/v1`.
- [`covenant/v1`](templates/covenant/README.md) provides the exact two-part
  onboarding anchor.
- The [M2 fixture matrix](fixtures/m2-sync/README.md) defines 13 isolated
  scenarios and 22 lightweight safeguards. Twelve scenarios have real agent
  workflow replay evidence; `write-verify-failure` is deliberately
  declarative-only because it requires fault injection between write and
  verification.

Reproduce the stable repository-local mechanical checks with:

```text
python -B skills/bridge-sentinel/scripts/sentinel_mechanics.py self-test
python -B fixtures/m2-sync/fixture_harness.py self-test
git diff --check
```

The fixture harness command validates scenario contracts, expected plans,
post-state trees, and safeguards; it is not a substitute for agent workflow
replay. The completed replay evidence covers 6/6 transition scenarios with
7/7 plan-plus-tree comparisons, 7/7 guard branches, and the independent
baseline-DAG ambiguity case.

M3 entry/rule projection is next and has not been implemented. There is no
CLI, npm package, plugin manifest or payload, CI release gate, or claimed
Claude Code/Codex live-host activation smoke yet. Packaging remains gated
until M5, and CI remains M6 work. Product artifacts land milestone by
milestone; the [roadmap](docs/phases/roadmap.md) owns that boundary.

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
