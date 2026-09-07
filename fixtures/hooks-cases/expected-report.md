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
| hooks | hooks/extra-keys | claude | drift | reconcile | native | - |
| hooks | hooks/extra-keys | codex | declared-unsynced | - | declared-unsynced | - |
| hooks | hooks/field-absent | claude | drift | reconcile | native | - |
| hooks | hooks/field-absent | codex | declared-unsynced | - | declared-unsynced | - |
| hooks | hooks/field-diff | claude | drift | reconcile | native | - |
| hooks | hooks/field-diff | codex | declared-unsynced | - | declared-unsynced | - |
| hooks | hooks/multi-handler | claude | drift | reconcile | native | - |
| hooks | hooks/multi-handler | codex | declared-unsynced | - | declared-unsynced | - |
| hooks | hooks/ok-both | claude | in-sync | - | native | - |
| hooks | hooks/ok-both | codex | in-sync | - | native | awaiting-host-trust |
| hooks | hooks/t4-present | claude | in-sync | - | native | - |
| hooks | hooks/t4-present | codex | drift | reconcile | declared-unsynced | - |
| skills | - | - | no-source-unit | - | - | - |

## Observations

- codex-effective-budget: AGENTS.md (project_doc_max_bytes=32768; source=resolved)
- codex-hooks-feature-disabled: .
- codex-project-untrusted: .
- undeclared-hooks-key: .codex/hooks.json (Stop matcher=omitted)
