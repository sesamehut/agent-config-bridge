- expectation: report/v1
- scan root: .
- scope excludes: (none)
- onboarding: onboarded

## Findings

| surface | unit | host | state | suggested action | tier | annotations |
|---|---|---|---|---|---|---|
| agents-md | entry | codex | in-sync | - | structural | - |
| agents-md | rules/legacy | codex | drift | adopt-to-source | - | - |
| agents-md | rules/style | codex | in-sync | - | semantic | - |
| hooks | hooks/fixture-orphan | codex | drift | adopt-to-source | - | - |
| hooks | hooks/fmt-on-save | claude | drift | reproject-from-source | native | - |
| hooks | hooks/fmt-on-save | codex | drift | reproject-from-source | native | - |
| hooks | hooks/sandbox-guard | claude | in-sync | - | native | - |
| hooks | hooks/sandbox-guard | codex | declared-unsynced | - | declared-unsynced | - |
| hooks | hooks/sentinel-stop | claude | in-sync | - | native | - |
| hooks | hooks/sentinel-stop | codex | in-sync | - | native | awaiting-host-trust |
| skills | .agents/skills/fixture-codex-only | codex | adoption-candidate | annex-or-keep | - | - |
| skills | fixture-bom-with-a-very-long-directory-name-exceeding-codexs-limit | codex | in-sync | - | native | awaiting-host-trust; lint:claude-only-frontmatter; lint:name-length; lint:utf8-bom |
| skills | fixture-claude-flavored | codex | in-sync | - | native | awaiting-host-trust; lint:claude-only-frontmatter; lint:dynamic-content |
| skills | fixture-drifted | codex | drift | conflict | native | lint:claude-only-frontmatter |
| skills | fixture-portable | codex | in-sync | - | native | awaiting-host-trust; lint:claude-only-frontmatter |
| skills | fixture-undiscoverable | codex | in-sync | - | native | awaiting-host-trust; lint:claude-only-frontmatter; lint:missing-description |

## Observations

- nested-agents-md: sub/AGENTS.md
- undeclared-hooks-key: .claude/settings.json (SessionStart matcher=startup)
