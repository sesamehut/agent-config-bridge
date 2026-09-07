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
| hooks | hooks/retired-guard | claude | drift | reconcile | native | - |
| hooks | hooks/retired-guard | codex | declared-unsynced | - | declared-unsynced | - |
| hooks | hooks/retired-note | claude | in-sync | - | native | - |
| hooks | hooks/retired-note | codex | declared-unsynced | - | declared-unsynced | - |
| skills | - | - | no-source-unit | - | - | - |

## Observations

- codex-effective-budget: AGENTS.md (project_doc_max_bytes=32768; source=resolved)
- hooks-globally-disabled: .claude/settings.json
- local-hooks-present: .claude/settings.local.json
