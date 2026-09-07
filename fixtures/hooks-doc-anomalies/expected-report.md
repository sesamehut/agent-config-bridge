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
| hooks | hooks/opt-in-pending | claude | drift | reconcile | native | opt-in-required |
| hooks | hooks/opt-in-pending | codex | drift | reconcile | native | opt-in-required |
| skills | - | - | no-source-unit | - | - | - |

## Observations

- codex-effective-budget: AGENTS.md (project_doc_max_bytes=32768; source=resolved)
- intent-doc-anomaly: .claude/rules/hooks.md (entry dup-own-a)
- intent-doc-anomaly: .claude/rules/hooks.md (entry dup-own-b)
- intent-doc-anomaly: .claude/rules/hooks.md (entry duplicate-id)
- intent-doc-anomaly: .claude/rules/hooks.md (entry duplicate-id)
- intent-doc-anomaly: .claude/rules/hooks.md (entry interrupt-native)
- intent-doc-anomaly: .claude/rules/hooks.md (entry missing-bullet)
- intent-doc-anomaly: .claude/rules/hooks.md (entry override-no-reason)
- intent-doc-anomaly: .claude/rules/hooks.md (entry two-yaml-blocks)
- intent-doc-anomaly: .claude/rules/hooks.md (line 27)
- matcher-grammar-divergent: .claude/rules/hooks.md (entry opt-in-pending)
