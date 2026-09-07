- expectation: report/v5
- scan root: ../..
- scope excludes: fixtures/**
- activation profile: activation-profile.json
- onboarding: not-onboarded

## Findings

| surface | unit | host | state | suggested action | tier | annotations |
|---|---|---|---|---|---|---|
| agents-md | AGENTS.md | codex | adoption-candidate | annex-or-keep | - | - |
| agents-md | entry | codex | not-projected | onboard | structural | - |
| agents-md | rules/docs | codex | not-projected | onboard | semantic | - |
| agents-md | rules/fixtures | codex | not-projected | onboard | semantic | - |
| hooks | - | - | no-source-unit | - | - | - |
| skills | - | - | no-source-unit | - | - | - |

## Observations

- codex-effective-budget: AGENTS.md (project_doc_max_bytes=32768; source=resolved)
