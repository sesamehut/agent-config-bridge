- expectation: report/v5
- scan root: .
- scope excludes: (none)
- activation profile: activation-profile.json
- onboarding: onboarded

## Findings

| surface | unit | host | state | suggested action | tier | annotations |
|---|---|---|---|---|---|---|
| agents-md | entry | codex | in-sync | - | structural | - |
| agents-md | hooks/retired-note | codex | drift | reconcile | - | - |
| agents-md | rules/bridge-covenant | codex | in-sync | - | structural | - |
| hooks | hooks/degraded-diff | claude | declared-unsynced | - | declared-unsynced | event-unverified |
| hooks | hooks/degraded-diff | codex | drift | reconcile | semantic | event-unverified |
| hooks | hooks/degraded-missing | claude | declared-unsynced | - | declared-unsynced | event-unverified |
| hooks | hooks/degraded-missing | codex | drift | reconcile | semantic | event-unverified |
| hooks | hooks/degraded-native-present | claude | declared-unsynced | - | declared-unsynced | event-unverified |
| hooks | hooks/degraded-native-present | codex | drift | reconcile | semantic | event-unverified |
| hooks | hooks/degraded-ok | claude | declared-unsynced | - | declared-unsynced | event-unverified |
| hooks | hooks/degraded-ok | codex | in-sync | - | semantic | event-unverified |
| hooks | hooks/doc-interrupt | claude | in-sync | - | semantic | - |
| hooks | hooks/doc-interrupt | codex | declared-unsynced | - | declared-unsynced | - |
| skills | - | - | no-source-unit | - | - | - |

## Observations

- codex-effective-budget: AGENTS.md (project_doc_max_bytes=32768; source=resolved)
- undeclared-hooks-key: .codex/hooks.json (Setup matcher=omitted)
