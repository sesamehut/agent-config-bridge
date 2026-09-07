- expectation: report/v5
- scan root: .
- scope excludes: (none)
- activation profile: activation-profile.json
- onboarding: onboarded

## Findings

| surface | unit | host | state | suggested action | tier | annotations |
|---|---|---|---|---|---|---|
| agents-md | entry | codex | in-sync | - | structural | - |
| agents-md | rules/bridge-covenant | codex | in-sync | - | structural | - |
| agents-md | rules/legacy | codex | drift | reconcile | - | - |
| agents-md | rules/style | codex | in-sync | - | semantic | - |
| agents-md | rules/tone | codex | in-sync | - | semantic | - |
| hooks | hooks/fixture-orphan | codex | drift | reconcile | - | - |
| hooks | hooks/fmt-on-save | claude | drift | reconcile | native | - |
| hooks | hooks/fmt-on-save | codex | drift | reconcile | native | - |
| hooks | hooks/sandbox-guard | claude | in-sync | - | native | - |
| hooks | hooks/sandbox-guard | codex | declared-unsynced | - | declared-unsynced | - |
| hooks | hooks/sentinel-stop | claude | in-sync | - | native | - |
| hooks | hooks/sentinel-stop | codex | in-sync | - | native | awaiting-host-trust |
| skills | .agents/skills/fixture-codex-only | codex | adoption-candidate | annex-or-keep | - | live-activation-unknown |
| skills | fixture-bom-with-a-very-long-directory-name-exceeding-codexs-limit | codex | blocked | resolve-blocker | native | lint:codex-validator-rejection; lint:invalid-name; lint:utf8-bom; live-activation-unknown |
| skills | fixture-claude-flavored | codex | in-sync | - | native | behavior-degraded; lint:codex-validator-rejection; lint:dynamic-content; lint:implementation-specific-frontmatter; live-activation-unknown |
| skills | fixture-drifted | codex | drift | reconcile | native | live-activation-unknown |
| skills | fixture-portable | codex | in-sync | - | native | live-activation-unknown |
| skills | fixture-undiscoverable | codex | blocked | resolve-blocker | native | lint:invalid-frontmatter; live-activation-unknown |

## Observations

- codex-effective-budget: AGENTS.md (project_doc_max_bytes=32768; source=resolved)
- nested-agents-md: sub/AGENTS.md
- undeclared-hooks-key: .claude/settings.json (SessionStart matcher=startup)
