# Canonical sync-plan cases

This reference contains minimal normative `sync-plan/v3` fragments for
replay and formal-validator implementations. A real document still includes
every section required by
[`sync-plan-spec.md`](sync-plan-spec.md). Values such as the all-`a` baseline
below are grammar examples, not ownership evidence.

## Unattested strict operation

Generic file I/O does not create a strict capability. When no versioned
adapter attestation exists, an otherwise desired create serializes:

```markdown
## Capability profiles

- (none)

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/agents-md | AGENTS.md | create | unavailable | - | unavailable | - |

## Warnings

- conditional-write-unavailable: AGENTS.md
```

PowerShell/.NET, Claude Code `Edit`/`Write`, Codex `apply_patch`, Python I/O,
or a successful post-read cannot change either `unavailable` token.

## Fixture capability admission

A `write-capability-fixture/v1` profile is accepted only when the formal
validation context proves this complete chain:

```text
caller lease
  -> lease hash in the safe materialization marker
  -> marker suite + scenario + root + baseline + HEAD
  -> capability-document SHA-256 bound by the marker
  -> capability document repeats the marker identity and binds the exact
     replay-input branch + operations + protocols + profile fields used by
     the plan
```

Breaking any arrow rejects the profile. The same profile is invalid in a
non-fixture repository or another materialization.

## Pending onboarding decision

```markdown
## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| onboarding/agents-md | closure/decision/onboarding/agents-md | not-selected | - | no-baseline | annex-or-keep | user-decision | not-applicable | not-selected | - | decision-required |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/onboarding/agents-md | onboarding/agents-md | - | not-selected | not-applicable | not-selected |
```

This fragment is `phase: pre-write` and header authorization
`not-applicable`. It has no capability rows and no restart or live-activation
annotation. Before the user confirms a source destination, there is no source
intent target to diagnose, so this row never invents `intent-required`.

## Confirmed shared entry

Once the exact shared-entry disposition, destination, source bytes, initial
intent, and rerender are confirmed, the pending row is replaced:

```markdown
## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| entry | closure/agents-md | selected | - | no-baseline | annex | projection-to-source | confirmed | planned | structural | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/agents-md | entry | - | selected | confirmed | planned |

## Adoption decisions

| segment | lines | disposition | destination | decision |
|---|---|---|---|---|
| segment/1 | 1-3 | shared-entry | entry | confirmed |
```

The obsolete onboarding decision row and decision closure are absent.
Satisfied `decision-required`, `semantic-review-required`, and
`intent-required` annotations are absent.

## Conflict and semantic source candidate

A two-sided conflict is a selected zero-write decision, not an omitted batch
member:

```markdown
| entry | closure/decision/entry | selected | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | both-changed | conflict | user-decision | required | deferred | structural | decision-required |
```

A projection-only semantic-review candidate that already names exact proposed
source bytes is also selected. It remains a physical closure with
`required` / `planned`, and carries both `intent-required` and
`semantic-review-required` until confirmation:

```markdown
| entry | closure/agents-md | selected | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | projection-only | adopt | projection-to-source | required | planned | structural | intent-required; semantic-review-required |
```

Neither row is the pending Codex-onboarding segmentation shape above.

## Authenticated tier mapping

A multi-unit plan can apply one structural entry while retaining a different
unscoped rule as a selected, required, deferred conflict:

```markdown
| entry | closure/agents-md | selected | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | source-only | update | source-to-projection | confirmed | applied | structural | live-activation-unknown; restart-may-be-required |
| rules/beta | closure/decision/rules/beta | selected | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | both-changed | conflict | user-decision | required | deferred | structural | decision-required |
```

The formal validator derives both tiers from the authenticated public replay
documents. It rejects a `semantic` beta row, a row whose rule id has no
corresponding public source mapping, and duplicate Units mappings.

A valid path-scoped `rules/docs` row is `semantic` in both directions:
Claude-source-to-Codex projection and Codex-projection-to-Claude reverse
adoption. When an exact confirmed source update adds or removes scope,
the rendered/proposed source tier wins over the input tier. A managed or
resolved skill row is `native`; an unresolved `annex-or-keep` / `keep`
skill row, onboarding row, or other no-source row uses `-`. An entry row is
always `structural`. A deleted rule with no result source falls back to its
authenticated input source or exact managed-block `pv2` preamble; no evidence
is a rejection, not a guessed tier.

## Empty bootstrap capability blocker

An empty-project create blocker contains only the affected covenant unit.
`onboarding/agents-md` appears only when exact existing `AGENTS.md` segments
are present in Adoption decisions; a generic authorization record or an
unavailable `AGENTS.md` create does not create that unit:

```markdown
| onboarding/covenant | closure/agents-md | selected | - | no-baseline | create | source-to-projection | confirmed | blocked | - | - |
```

## Empty bootstrap temporal boundary

These two accepted shapes describe different validation contexts, not two
interpretations of one snapshot.

For the verified or closed operation that started with both covenant carriers
absent and applied the two bound strict creates, retain the original bootstrap
classification:

```markdown
- phase: post-write
- onboarding: bootstrap-required
- authorization: confirmed

| onboarding/covenant | closure/agents-md | selected | - | no-baseline | create | source-to-projection | confirmed | applied | - | live-activation-unknown; restart-may-be-required |

| closure/agents-md | onboarding/covenant | - | selected | confirmed | applied |
```

Its warnings include `untracked-files-included` for both newly created
carriers while they remain untracked. They do not include
`covenant-anchor-anomaly`: this result is still scoped to the live operation
that created and verified them.

After the journal is closed, an independent scan with the same two exact
carriers still untracked is a new prepared lifecycle and accepts only this
zero-write blocker:

```markdown
- phase: pre-write
- onboarding: blocked
- authorization: not-applicable

| onboarding/covenant | closure/decision/onboarding/covenant | selected | - | blocked | resolve-blocker | user-decision | not-applicable | blocked | - | - |

| closure/decision/onboarding/covenant | onboarding/covenant | - | selected | not-applicable | blocked |
```

Both capability sections are `- (none)`. The warning set contains these four
carrier lines:

```text
- covenant-anchor-anomaly: .claude/rules/bridge-covenant.md (untracked)
- covenant-anchor-anomaly: AGENTS.md (untracked)
- untracked-files-included: .claude/rules/bridge-covenant.md
- untracked-files-included: AGENTS.md
```

## Phase and carrier annotations

| Operation context | phase | Carrier annotations |
|---|---|---|
| execution never entered, including blocker or journal `prepared` | `pre-write` | none |
| lifecycle entered `executing`; carrier call was never reached | `post-write` | none |
| carrier call verified exact preimage after failure | `post-write` | none |
| carrier was written or a partial result means it may have been written | `post-write` | `live-activation-unknown; restart-may-be-required` |

Attach the annotations only to the unit rows backed by that Codex skill
carrier or root `AGENTS.md` carrier.

## Guarded final-preflight mismatch

A deterministic manual-tail change injected after exact plan confirmation but
before the final full-file preflight yields a post-write result even though
Bridge wrote nothing:

```markdown
| entry | closure/agents-md | selected | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | source-only | update | source-to-projection | confirmed | failed | structural | - |

| closure/agents-md | entry | - | selected | confirmed | failed |
```

The complete live tree must equal the confirmed input tree plus only the
independently bound injected change. The affected closure is exactly
`failed`, no unit is `applied`, and neither `restart-may-be-required` nor
`live-activation-unknown` is present. A fixture replay additionally requires
its exact armed, single-consumption claim, and injected receipts plus the
confirmed-plan snapshot; a caller-supplied phase label is not evidence.

## Native two-host hook projection

An advisory `SessionStart` reminder projected to both native carriers. The
source entry is unchanged and unwritten, so no `/source` row is serialized:

```markdown
## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| hooks/reminder-start/claude | closure/hooks/claude | selected | - | no-baseline | create | source-to-projection | confirmed | applied | native | - |
| hooks/reminder-start/codex | closure/hooks/codex | selected | - | no-baseline | create | source-to-projection | confirmed | applied | native | awaiting-host-trust |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/claude | hooks/reminder-start/claude | - | selected | confirmed | applied |
| closure/hooks/codex | hooks/reminder-start/codex | - | selected | confirmed | applied |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/claude | .claude/settings.json | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 2 | closure/hooks/codex | .codex/hooks.json | replace | guarded-patch/v1 | capability/1 | unavailable | - |

## Warnings

- claude-hooks-shared-execution: .claude/settings.json
- guarded-patch-non-cas: .claude/settings.json
- guarded-patch-non-cas: .codex/hooks.json
- strict-compensation-unavailable: .claude/settings.json
- strict-compensation-unavailable: .codex/hooks.json

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/reminder-start/claude | reminder | settings-json | native | shared-event-command |
| hooks/reminder-start/codex | reminder | codex-hooks-json | native | shared-event-command |
```

The action is `create` because the projection member is missing, while the
operation is `replace` because the carrier file already exists. That split is
the same one a new block inside an existing `AGENTS.md` already uses.
`awaiting-host-trust` appears only in a post-write result and only on the
Codex row.

## Degraded Codex hook in root AGENTS.md

A Claude-only event with `class: reminder`, first projection, pre-write and
confirmed. The event is outside the 12 names of `shared-events/2026-09-07`,
so every row of the entry carries `event-unverified`. Units and Closures
rows:

```markdown
| hooks/context-note/claude | closure/hooks/claude | selected | - | no-baseline | create | source-to-projection | confirmed | planned | native | event-unverified |
| hooks/context-note/codex | closure/agents-md | selected | - | no-baseline | create | source-to-projection | confirmed | planned | semantic | behavior-degraded; event-unverified |

| closure/agents-md | hooks/context-note/codex | - | selected | confirmed | planned |
| closure/hooks/claude | hooks/context-note/claude | - | selected | confirmed | planned |

| 1 | closure/agents-md | AGENTS.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 2 | closure/hooks/claude | .claude/settings.json | replace | guarded-patch/v1 | capability/1 | unavailable | - |
```

Its warning section is exactly:

```text
- claude-hooks-shared-execution: .claude/settings.json
- guarded-patch-non-cas: .claude/settings.json
- guarded-patch-non-cas: AGENTS.md
- hook-output-not-delivered: .claude/rules/hooks.md (entry context-note)
- manual-zone-guarded: AGENTS.md
- strict-compensation-unavailable: .claude/settings.json
- strict-compensation-unavailable: AGENTS.md
```

Its Hook tiers rows are:

```markdown
| hooks/context-note/claude | reminder | settings-json | native | claude-only-event |
| hooks/context-note/codex | reminder | agents-md | semantic | degraded-standing-instruction |
```

The degraded row joins the existing `closure/agents-md`; no new closure id is
invented. The two closures do not depend on each other, and step order alone
places the explanation before the executable hook. Post-write the Codex row
additionally carries `live-activation-unknown; restart-may-be-required`,
because the `AGENTS.md` carrier-touch predicate in `sync-plan/v3` names a
degraded `hooks/<entry-id>/codex` row whose block was written; its complete
annotation cell is then
`behavior-degraded; event-unverified; live-activation-unknown; restart-may-be-required`.

## Declared-unsynced hook decision closure

A `class: gate` entry whose Codex target declares `surface: none`, with the
Claude side already converged:

```markdown
| hooks/sandbox-guard/claude | closure/decision/hooks/sandbox-guard | selected | 4e77a1b3c5d7e9f1a3b5c7d9e1f3a5b7c9d1e3f5 | unchanged | unchanged | - | not-applicable | unchanged | native | - |
| hooks/sandbox-guard/codex | closure/decision/hooks/sandbox-guard | selected | - | declared-unsynced | unchanged | - | not-applicable | unchanged | declared-unsynced | - |

| closure/decision/hooks/sandbox-guard | hooks/sandbox-guard/claude; hooks/sandbox-guard/codex | - | selected | not-applicable | unchanged |

| hooks/sandbox-guard/claude | gate | settings-json | native | shared-event-command |
| hooks/sandbox-guard/codex | gate | none | declared-unsynced | decision-not-portable |
```

`Capability profiles` and `Write capabilities` are both `- (none)` and the
header is `- authorization: not-applicable`. `declared-unsynced` appears as
both a plan state and a plan tier: the state says this host has no
counterpart, the tier repeats the entry's own declaration, and the reason
names the exact obstacle.

## Hook opt-in pending

`class: side-effect` with `enabled: true` and no covering `enabled-by`
record:

```markdown
| hooks/deploy-on-stop/claude | closure/decision/hooks/deploy-on-stop | selected | - | no-baseline | opt-in-or-skip | user-decision | required | deferred | native | decision-required; opt-in-required |
| hooks/deploy-on-stop/codex | closure/decision/hooks/deploy-on-stop | selected | - | no-baseline | opt-in-or-skip | user-decision | required | deferred | native | decision-required; opt-in-required |

| closure/decision/hooks/deploy-on-stop | hooks/deploy-on-stop/claude; hooks/deploy-on-stop/codex | - | selected | required | deferred |

| hooks/deploy-on-stop/claude | side-effect | settings-json | native | opt-in-pending |
| hooks/deploy-on-stop/codex | side-effect | codex-hooks-json | native | opt-in-pending |
```

Its warning section is exactly one line:

```text
- hook-opt-in-required: .claude/rules/hooks.md (entry deploy-on-stop)
```

Both capability sections are `- (none)`. The header is
`- authorization: not-applicable` and there is no `authorization-incomplete`
line: the header derives from selected mutating closures, and a zero-write
decision closure cannot mutate. Evidence must carry the exact command line
plus the pinned sentence that the opt-in record is a review checkpoint in Git
and not an enforcement boundary. Confirming the opt-in produces a
`hooks/deploy-on-stop/source` row in `closure/hooks/source` that appends the
dated `enabled-by` record, plus the two carrier rows that depend on it.

## Absent Codex hook carrier

`.codex/hooks.json` does not exist and `strict-create/v1` is unavailable, so
the Claude closure proceeds while the Codex closure is scoped-blocked:

```markdown
| hooks/reminder-start/claude | closure/hooks/claude | selected | - | no-baseline | create | source-to-projection | confirmed | planned | native | - |
| hooks/reminder-start/codex | closure/hooks/codex | selected | - | no-baseline | create | source-to-projection | not-applicable | blocked | native | - |

| closure/hooks/claude | hooks/reminder-start/claude | - | selected | confirmed | planned |
| closure/hooks/codex | hooks/reminder-start/codex | - | selected | not-applicable | blocked |

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

| 1 | closure/hooks/claude | .claude/settings.json | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 2 | closure/hooks/codex | .codex/hooks.json | create | unavailable | - | unavailable | - |
```

Its warning section is exactly:

```text
- claude-hooks-shared-execution: .claude/settings.json
- conditional-write-unavailable: .codex/hooks.json
- guarded-patch-non-cas: .claude/settings.json
- hook-carrier-absent: .codex/hooks.json
- hook-projection-asymmetric: .codex/hooks.json (hooks/reminder-start/codex)
- strict-compensation-unavailable: .claude/settings.json
```

The blocked Codex closure keeps `selected` with authorization
`not-applicable`: a scoped `write capability` or `hook carrier` failure is
never relabelled `not-selected`. Evidence prints the exact bytes to paste to
create the carrier and states that Bridge provides no cross-carrier
atomicity, so the Claude hook is active while the Codex hook is absent. Had
`class` been `gate`, the blocked Codex closure would keep `selected` /
`not-applicable` / `blocked` and the Claude carrier closure would instead be
forced to `not-selected` with zero writes.

## Hook adoption decisions

Two hand-written Codex handlers, one proposed for adoption into the existing
entry `reminder-start` and one `[bridge:legacy-guard]`-marked orphan in an
unrelated `PreToolUse` group already confirmed as unowned occupancy:

```markdown
## Hook adoption decisions

| handler | location | disposition | destination | decision |
|---|---|---|---|---|
| handler/1 | .codex/hooks.json#SessionStart[0][0] | adopt | hooks/reminder-start | pending |
| handler/2 | .codex/hooks.json#PreToolUse[1][0] | keep | - | confirmed |
```

The pending row uses the pending hook occupancy shape:
`closure/decision/hooks/reminder-start` with `not-selected` /
`not-applicable` / `not-selected` and `decision-required`. The confirmed
`keep` row uses handler/2's own marked-orphan closure
`closure/decision/hooks/legacy-guard` with `selected` / `not-applicable` /
`deferred` and no annotation. Each entry id owns exactly one hook decision
closure, so an unrelated `PreToolUse` handler never joins the occupancy
decision of entry `reminder-start`. A `discard` disposition is destructive
and needs its own explicit confirmation.

## Warning grammar

Accepted examples:

```text
- agents-md-near-budget: AGENTS.md (28672 bytes of 32768)
- codex-hook-retrust-required: .codex/hooks.json (PreToolUse group=0 handler=1)
- codex-inline-hooks-conflict: .codex/config.toml (pointer-key)
- codex-root-unresolved: . (root-marker-excluded)
- hook-opt-in-required: .claude/rules/hooks.md (entry deploy-on-stop)
- hook-projection-asymmetric: .codex/hooks.json (hooks/reminder-start/codex)
- hooks-carrier-unusable: .codex/hooks.json (duplicate-key)
- marker-anomaly: AGENTS.md (line 7)
- undeclared-hooks-key: .claude/settings.json (Stop matcher=omitted)
- untracked-files-included: .claude/rules/style.md
```

Rejected examples include `28672/32768`, an unknown unresolved reason,
`(line seven)`, an absolute path, a unit id in the path field, a directory
path, `.` for `untracked-files-included`, `(group 0 handler 1)` without the
`=` separators, an uppercase or underscored entry id in `(entry <id>)`, a
`hooks/<id>/<host>` unit id in the path field of a hook warning, and a
`hook-projection-asymmetric` detail naming a path instead of a unit id.

## Per-unit migration candidates

```markdown
## Migration decisions

| unit | legacy baseline | current relation | disposition | decision |
|---|---|---|---|---|
| entry | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | converged | carry-forward | derived |
| rules/style | - | ambiguous | block | pending |

## Migration candidates

| unit | legacy candidate |
|---|---|
| entry | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |
| rules/style | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb |
| rules/style | cccccccccccccccccccccccccccccccccccccccc |
```

`onboarding/covenant` is absent from both tables. The covenant pair remains a
member of `closure/migration`.

When any payload unit is ambiguous, every member of `closure/migration` is
selected and blocked with `contract-migration` / `resolve-blocker`,
`user-decision`, authorization `not-applicable`, outcome `blocked`, and Units
baseline `-`. The ambiguous payload row carries only `decision-required`;
the covenant and unambiguously carried payload rows carry
`migration-transition-required`. Candidate oids remain only in the two
migration tables.

After migration bytes are applied, a released unit has Units baseline `-` and
no migration transition annotation. Carried and repaired units retain their
unique legacy baseline and `migration-transition-required` until the closed
transition commit is reachable.

For the canonical confirmed multi-path migration, all three forward
replacements use `guarded-patch/v1`, all three inverse protocols are
`unavailable`, and root `AGENTS.md` is manual-zone guarded. The verified
post-write warning section is exactly this byte-wise whole-line order:

```text
- guarded-patch-non-cas: .agents/skills/fixture-legacy-repair/SKILL.md
- guarded-patch-non-cas: .claude/rules/bridge-covenant.md
- guarded-patch-non-cas: AGENTS.md
- manual-zone-guarded: AGENTS.md
- migration-transition-uncommitted: .
- strict-compensation-unavailable: .agents/skills/fixture-legacy-repair/SKILL.md
- strict-compensation-unavailable: .claude/rules/bridge-covenant.md
- strict-compensation-unavailable: AGENTS.md
```

The confirmed prepared pre-write fragment omits only
`migration-transition-uncommitted`; it is not yet a verified live render.
Each guarded or unavailable-inverse operation contributes one line for its
exact path. One token-level acknowledgement cannot stand in for three path
facts, and a duplicate line cannot satisfy cardinality.

## Formal-validator cases

The formal validator accepts the fragments above only inside a complete
document with matching scan/operation context. It must reject at least:

- a post-write phase before lifecycle `executing`;
- an applied empty-bootstrap operation result that changes
  `bootstrap-required` / `no-baseline` / `create` / `applied` or adds a
  `covenant-anchor-anomaly`;
- an independent exact-pair untracked scan that omits either carrier's
  covenant anomaly or untracked warning, invents a baseline or annotation,
  uses a write closure/capability, or is labeled `bootstrap-required`;
- either empty-bootstrap temporal shape when supplied under the other
  lifecycle context;
- a bound guarded-preflight fault whose affected closure is not exactly
  `failed`, whose full tree differs beyond the declared injected target, or
  whose plan/arm/claim/injected evidence is absent or swapped;
- a pre-write blocker carrying restart or live-activation annotations;
- a pending onboarding row using `deferred` or a selected closure;
- a pending onboarding row carrying `intent-required`;
- `onboarding/agents-md` without pending exact Adoption decisions;
- a `both-changed` row that is not selected / required / deferred;
- a semantic-review adoption candidate that is not selected / required /
  planned or omits `intent-required`;
- a unit tier that differs from its authenticated public input/render source,
  including an unscoped rule labeled `semantic`, a scoped rule labeled
  `structural`, a skill not labeled `native`, or a missing/duplicate mapping;
- a confirmed entry that remains in
  `closure/decision/onboarding/agents-md`;
- a strict protocol backed only by a generic I/O tool name;
- a fixture profile with any lease, marker, hash, branch, root, or `HEAD`
  mismatch;
- a relevant untracked file without its warning;
- an incomplete legacy-mode / orphan-marker warning set;
- a fallback blocker that names units outside the covenant blocker scope;
- an ambiguous migration member with a current Units baseline, or a released
  post-migration member that retains a baseline/transition annotation;
- a rename destination with a baseline or a state other than `no-baseline`;
- a warning with a non-canonical path or detail;
- `onboarding/covenant` or any `hooks/*` unit in either migration table;
- a hook unit id without a `source`, `claude`, or `codex` host segment, or any
  hook row that widens the eleven-column Units header;
- a `hooks/<id>/source` row serialized when `.claude/rules/hooks.md` is
  neither written by the plan nor itself blocked;
- a hook Units row with no `## Hook tiers` row, a duplicated or extra Hook
  tiers row, or a Hook tiers `tier` that disagrees with its Units row;
- a hook row using tier `structural`, a Claude row declaring surface
  `agents-md`, or a Codex row declaring surface `intent-doc`;
- a hook `both-changed` conflict or opt-in decision bound to
  `closure/decision/<unit>` instead of `closure/decision/hooks/<entry-id>`,
  or an entry whose two host rows split across two decision closures;
- an opt-in-pending plan whose header authorization is `required` or that
  emits `authorization-incomplete` for a zero-write decision closure;
- a scoped-blocked hook carrier closure relabelled `not-selected`, or a
  `class: gate` entry that applies one carrier while the sibling carrier is
  blocked or unavailable;
- `awaiting-host-trust` in a pre-write plan, or attached to any row other
  than a `hooks/<id>/codex` row whose carrier was or may have been written;
- a hooks-carrier postimage produced by reserializing the parsed document, or
  one that differs anywhere outside the located owned spans and insertion
  points;
- a `## Hook adoption decisions` table with gapped `handler/<n>` numbering, a
  location outside the `<file>#<Event>[<i>][<j>]` grammar, an `adopt` row
  whose destination is `-`, or a `keep`/`discard` row whose destination is
  not `-`; or
- expectation comparison offered as proof that the plan grammar is valid.
