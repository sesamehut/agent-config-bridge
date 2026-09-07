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
| hooks | hooks/foreign-mcp | claude | drift | reconcile | native | - |
| hooks | hooks/foreign-mcp | codex | in-sync | - | native | awaiting-host-trust |
| hooks | hooks/prompt-note | claude | in-sync | - | native | behavior-degraded |
| hooks | hooks/prompt-note | codex | drift | reconcile | native | behavior-degraded |
| hooks | hooks/semantics-async | claude | drift | reconcile | native | - |
| hooks | hooks/semantics-async | codex | in-sync | - | native | awaiting-host-trust; behavior-degraded |
| hooks | hooks/session-note | claude | in-sync | - | native | - |
| hooks | hooks/session-note | codex | declared-unsynced | - | declared-unsynced | - |
| skills | - | - | no-source-unit | - | - | - |

## Observations

- codex-effective-budget: AGENTS.md (project_doc_max_bytes=32768; source=resolved)
- codex-handler-unknown-key: .codex/hooks.json (UserPromptSubmit group=0 handler=0 key=onFailure)
