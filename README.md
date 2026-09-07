# Agent Config Bridge

`agent-config-bridge` is the single-repo home for Agent Config Bridge: a Claude
Code / Codex bridge designed to let a project maintain one canonical source
for agent skills, hooks, and rules, then project that source into host-native
layouts.

The development tree has completed M1 through M3. M4 hook-intent modeling and
dual-host hook projection are in progress.

- [`bridge-sentinel`](skills/bridge-sentinel/SKILL.md) observes repository
  carriers without writing, using `source-tree/v5` and `report/v5`.
- [`bridge-sync`](skills/bridge-sync/SKILL.md) plans, confirms, projects,
  adopts, and verifies complete skill trees, entry/rule managed blocks, and
  hook intents using Git-proven per-unit baselines, deterministic rendering,
  serialized closure selection/authorization, and explicit strict or non-CAS
  guarded write protocols under `reconciliation/v3` and `sync-plan/v3`.
- Hook intents live in `.claude/rules/hooks.md` and project into two native
  carriers, `.claude/settings.json` for Claude and `.codex/hooks.json` for
  Codex, editing only the spans each intent owns and never rewriting the rest
  of either document. A `reminder` or `observation` intent whose event has no
  native carrier on one host degrades to a standing instruction there; a `gate`
  or `side-effect` intent is not projected at all until a dated `enabled-by`
  record covers it. Hooks committed to a repository run for everyone who clones
  it: Bridge classification is review metadata, not a sandbox.
- [`covenant/v3`](templates/covenant/README.md) provides the exact two-part
  onboarding anchor; the archived v1 and v2 bytes form a closed two-member set
  identifying a single-hop migration whose ownership transition still requires
  reachable Git evidence, not a supported legacy runtime contract.
- The [M2 fixture matrix](fixtures/m2-sync/README.md) defines 13 isolated
  scenarios and 22 lightweight safeguards. Twelve scenarios have real agent
  workflow replay evidence; `write-verify-failure` is deliberately
  declarative-only because it requires fault injection between write and
  verification.
- The [M3 fixture matrix](fixtures/m3-rules/README.md) defines 41 scenarios,
  42 expectations, and 42 replay inputs. All 39 agent-replayable scenarios
  (40 inputs) have accepted real workflow replay evidence;
  `guarded-postverify-race` and `verify-failure-no-compensation` remain
  explicitly declarative-only.

Reproduce the stable repository-local mechanical checks with:

```text
python -B skills/bridge-sentinel/scripts/sentinel_mechanics.py self-test
python -B fixtures/m2-sync/fixture_harness.py self-test
python -B fixtures/m3-rules/fixture_harness.py self-test
python -B fixtures/m3-rules/journal_validator_tests.py --mode worker-matrix
python -B fixtures/m3-rules/journal_validator_tests.py --mode single
python -B fixtures/m3-rules/journal_validator_tests.py --mode concurrent
git diff --check
```

Fixture harnesses validate declarations, expected plans, exact post-state
trees, and safeguards; they are not substitutes for agent workflow replay.
At M1 closure the sentinel self-test closed 36 checks. M2 closes 13
definitions, 12 replayable scenarios, one declarative-only scenario, and 22
safeguards. At M3 closure the M3 main harness closed 809 checks: 28 adapter
checks, one journal-suite gate, 737 other contract checks, and 43
stale-recovery checks. Its independent journal evidence closes an 11/11 worker
matrix and a 66/66 single suite; the concurrent gate closes two workers, 132
cases, two unique session roots, and two successful cleanups. Three final
independent concurrent runs passed on their first attempt without retry. The
two closure counts above are milestone evidence, not the current totals: M4 is
adding the `sync-plan/v3` plan grammar to the M3 harness and seven hooks
subcommands to the sentinel mechanics, so both self-tests now report more
checks, and the M4 numbers are recorded at M4 closure. <!-- m4-counts-pending -->

These results prove repository contracts, isolated fixture behavior, and the
recorded agent workflows; repository bytes do not prove Claude Code or Codex
live-host discovery or activation, and they never prove that a projected hook
is trusted or will run. M4 is in progress: the contract tuple is raised and the
hook design is settled, but the hook specs, mechanics, and fixture suite are
still landing, so the command list above stays at its M3 shape until the M4
harness exists. There is no CLI, npm package, plugin manifest or payload, or CI
release gate: packaging remains gated until M5, and CI remains M6 work. Product
artifacts land milestone by milestone; the [roadmap](docs/phases/roadmap.md)
owns that boundary.

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
- `templates/` — install-time project templates such as the bridge covenant,
  plus the hook intent example document, which nothing installs; these are not
  loaded as skill instructions (tracked).
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
