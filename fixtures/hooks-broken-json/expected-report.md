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
| hooks | hooks/guard-tools | claude | drift | reconcile | native | - |
| hooks | hooks/guard-tools | codex | drift | reconcile | native | - |
| hooks | hooks/wrap-up | claude | drift | reconcile | native | - |
| hooks | hooks/wrap-up | codex | drift | reconcile | native | - |
| skills | - | - | no-source-unit | - | - | - |

## Observations

- codex-effective-budget: AGENTS.md (project_doc_max_bytes=32768; source=resolved)
- hooks-carrier-unmodelled: .claude/settings.json (duplicate-key)
- json-parse-error: .codex/hooks.json
