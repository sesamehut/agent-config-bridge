# Bridge source-tree specification

Spec version: source-tree/v1.

This file is the durable normative home of the bridge's source-tree
conventions: the unit model and unit-id derivation, the onboarding
predicate, the managed-region marker grammar, the applicability preamble and
rendering pipeline, the normalization set N, the frontmatter schemas and the
intent-record format, the hook-intent entry format and ownership derivation,
and the skill portability requirements. Its companion,
[`report-spec.md`](report-spec.md), owns the report contract: the closed
state vocabulary and detection rules, the per-surface decision tables, the
diff shape, the observation vocabulary, the fidelity tier rules, the
portability lint list, the report document format, and the deterministic
expectation-comparison rule. Together these two files are complete: an
implementer or sentinel-executing agent needs nothing else.

Every rule in this file is a pure function of **repo bytes** — the tracked
files of the scan root, filtered by any scope excludes. The pinned input-set
definition (repo mode, fixture mode, untracked-file handling, and the
exclude glob dialect) lives in `report-spec.md`, as does the registry growth
rule binding every closed token set defined here.

## Unit model

A report row is keyed by `(surface, unit, host)`.

- `surface` ∈ { `agents-md`, `hooks`, `skills` } — the three fixed check
  surfaces.
- `unit` — a unit id (grammar under "Attribute charsets" below), or a
  repo-root-relative path (adoption candidates only), or `-` (no-source-unit
  rows only), or a synthetic ordinal-suffixed unit id `<unit-id>#<ordinal>`
  (ordinal ≥ 2; emitted only by the duplicate-block rule under "Malformation
  handling", on drift rows). Unit ids, paths, `-`, and synthetic ids are
  four distinct token classes; the registries never mix them. `#` is
  deliberately outside the unit-id charset, so a synthetic id can never
  collide with a real unit id.
- `host` ∈ { `claude`, `codex`, `-` }. Surface `agents-md` and `skills` rows
  always have host `codex` (Claude consumes the source natively; no
  Claude-side row exists for them). Surface `hooks` rows exist once per
  declared target host (plus marked-orphan rows on the host whose file holds
  the orphan). `-` only on no-source-unit rows.

Unit enumeration (pure function of repo bytes):

- `agents-md` source units: the **entry unit** (id `entry`, source = root
  `CLAUDE.md`; if root `CLAUDE.md` is absent and `.claude/CLAUDE.md` exists,
  source = `.claude/CLAUDE.md`; if both exist, source = root `CLAUDE.md` and
  the `dual-project-entry` observation is emitted) — the entry unit exists
  iff its source file exists; plus one **rule-shard unit** per tracked file
  matching `.claude/rules/**/*.md` EXCLUDING `.claude/rules/hooks.md` (owned
  by the hooks surface), with id `rules/<relative path under .claude/rules/
  minus the .md extension>` (e.g. `.claude/rules/docs.md` → `rules/docs`;
  `.claude/rules/API.md` → `rules/API`). Projection-side elements: the
  managed blocks parsed from the root `AGENTS.md` per the marker grammar
  below. Pairing key: block `id` attribute ↔ derived unit id.
- `hooks` source units: one per schema-valid entry of
  `.claude/rules/hooks.md` (schema under "Hook intent document" below), id
  `hooks/<entry id>`. Each entry produces one row per host in its `targets`
  map. Projection-side elements: the bridge-owned groups of
  `.claude/settings.json` (top-level `hooks` key) and `.codex/hooks.json` —
  a group is bridge-owned iff some schema-valid entry targeting that host
  (declared surface ≠ `none`) declares its `(event, matcher)` pair
  (matcher-absence counts as a value and matches only matcher-absence) —
  plus **marked handlers**: any handler object whose `statusMessage` value
  begins with `[bridge:` (the reinforcement marker defined below).
- `skills` source units: one per immediate subdirectory of `.claude/skills/`
  that contains a tracked `SKILL.md`; unit id = the directory name.
  Projection-side elements: immediate subdirectories of `.agents/skills/`
  containing a tracked `SKILL.md`. Pairing key: directory name. A
  subdirectory without `SKILL.md` on either side is not a unit (it is inert
  for both hosts); the sentinel checklist recommends a free-form note.
- A would-be source file whose repo-relative path contains any character
  outside the source-path charset below is NOT a unit; it emits the
  `unrepresentable-source-path` observation. Because the unit-id charset
  admits every character the source-path charset admits, every representable
  source path derives a valid unit id — no second failure mode exists.

**No-source-unit emission rule**: every surface emits at least one row. If a
surface would otherwise emit zero rows, it emits exactly one row
`(surface, -, -, no-source-unit, -, -, -)`.

## Onboarding predicate

> A project is **onboarded** if and only if at least one of the following
> holds over the tracked files of the scan root:
>
> (a) the root `AGENTS.md` contains at least one well-formed bridge managed
> block (a start marker and an end marker, matched as a pair per the marker
> grammar, outside code fences);
>
> (b) a bridge-declared hooks key exists: EITHER a hook intent document exists
> at `.claude/rules/hooks.md` and at least one of its schema-valid entries
> has, for some host with declared surface other than `none`, its owned
> `(event, matcher)` group present in that surface's file with at least one
> command handler (field values are irrelevant to the predicate); OR any
> handler object in `.claude/settings.json` or `.codex/hooks.json` carries a
> `statusMessage` value beginning with the characters `[bridge:`;
>
> (c) at least one directory `.agents/skills/<name>/` is a whole-directory
> raw-byte-identical copy of an existing master `.claude/skills/<name>/`
> (identical relative file sets; every file pair byte-identical);
>
> (d) the covenant rule shard exists at `.claude/rules/bridge-covenant.md`.
>
> Otherwise the project is **not-onboarded**. When not-onboarded, the report
> contains zero `drift` rows by construction: missing projections are
> `not-projected`, existing unmanaged content is `adoption-candidate`. When
> onboarded, every missing projection of a source unit is `drift` with
> suggested action `reproject-from-source`.

Notes pinned alongside (all facts normative):

- The predicate is project-level, never per-unit (a per-unit predicate would
  mislabel newly added source units forever and mask covenant omissions).
- Trigger (b) fires on group EXISTENCE, not field equality — a declared
  group whose command has drifted still evidences bridge management, and the
  field difference then reports as ordinary drift under the hooks decision
  table in `report-spec.md`. The marker clause makes bridge-written orphan
  keys (intent entry deleted or never landed) onboard the project so they
  can report as `drift`/`adopt-to-source` (有键无意图), never as silence.
- Trigger (c) deliberately requires whole-directory byte identity: a
  diverged same-name copy alone NEVER onboards a project — mere directory
  coexistence is not evidence of management (a hand-maintained parallel tree
  is the product's canonical pre-bridge user and exactly the Codex-start
  state M3 onboarding must recognize). Accepted boundary behavior, stated so
  fixture authors cannot encode another reading: in a project whose ONLY
  onboarding evidence is one byte-identical copy, a later one-byte
  divergence flips the project to not-onboarded and the pair reports as
  `not-projected` (master) plus `adoption-candidate` (copy). The covenant
  shard (d) is the robust anchor; trigger (c) is a fallback for
  covenant-less histories.
- Trigger (d) pins the covenant's installed filename,
  `.claude/rules/bridge-covenant.md`; the covenant asset shipped with the
  sentinel skill states this filename normatively.
- Intent records alone never make a project onboarded (evidence, not
  ownership).

## Marker grammar

### The four marker lines

```
managed-start     = "<!-- bridge:managed:start id=" unit-id " source=" source-path [" mode=" mode-token] " -->"
managed-end       = "<!-- bridge:managed:end -->"
claude-only-start = "<!-- bridge:claude-only:start -->"
claude-only-end   = "<!-- bridge:claude-only:end -->"
```

Exactly one U+0020 between every token shown; no tabs; no other attributes;
attribute order fixed (`id`, then `source`, then optional `mode`); no
quoting mechanism exists at M1 (a quoted-attribute grammar is RESERVED as a
future additive extension for paths containing whitespace).

### Attribute charsets

```
unit-id     = seg *("/" seg)          ; seg = 1*[A-Za-z0-9._-]
source-path = seg *("/" seg)          ; same seg charset; repo-root-relative,
                                      ; "/" separators, no "./" prefix
mode-token  = [a-z][a-z0-9-]{0,15}    ; absence of the attribute = verbatim mode
```

The unit-id and source-path charsets are deliberately identical per segment
(uppercase, digits, dot, underscore, hyphen), so every representable source
path derives a representable unit id — real-world file names like
`.claude/rules/API.md` or `team_style.md` are first-class source units.
Attribute values must not contain whitespace, `=`, backticks, or the byte
sequence `-->`; the seg charset enforces this. A file whose path cannot be
represented cannot be a source unit; the sentinel emits
`unrepresentable-source-path`. Within these charsets the marker parser stays
a single full-line regex; the reserved quoting extension (never a breaking
change) is the designated path to whitespace support.

### Line and placement rules

- A marker must occupy an entire line: after stripping the trailing EOL, the
  line must match the grammar from first byte to last. Anything else is
  ordinary content.
- Managed blocks appear only in root `AGENTS.md`. Claude-only pairs appear
  only in `CLAUDE.md` (or `.claude/CLAUDE.md`) and `.claude/rules/*.md`
  (Claude strips block-level HTML comments from this family before context
  injection — zero runtime cost Claude-side; Codex feeds markers to the
  model verbatim, counted against the 32 KiB budget).
- Code-fence rule (pinned, simplified from CommonMark, deterministic): scan
  lines top-to-bottom; a line whose first non-space characters (at most 3
  leading spaces) are three backticks or `~~~` toggles fence state; marker
  lines are recognized only while fence state is closed. This simplification
  is accepted and documented.
- Blocks never nest. Pairing algorithm: a full-line start match opens a
  block only when no block is open; every following line up to the next
  full-line end match is the block body; an end match with no open block is
  content.

### Malformation handling (deterministic, never fatal)

Every condition below additionally emits one `marker-anomaly` observation
(line format in `report-spec.md`); the states and agents-md cases named here
are defined in `report-spec.md`.

- Start marker while a block is open → the inner line is body content (it
  will byte-compare as drift).
- End marker with no open block → content.
- Block still open at EOF → the block is NOT recognized (its start line is
  content; the affected unit reports per case A3).
- A recognized block whose `source` attribute differs from the path derived
  from its `id` (unit-model derivation above) → the block still pairs by
  `id` (authoritative key).
- Duplicate blocks with the same `id` → the first (topmost) pairs; each
  later one reports per case A4 semantics as unattributable projection
  content (`drift`/`adopt-to-source`, unit = `<id>#<ordinal>` — the
  synthetic fourth unit token class of the unit model — ordinal 2, 3, … in
  file order).
- Claude-only: an unpaired start (no matching end before EOF, outside
  fences) → NOTHING is subtracted; rendering proceeds with the marker line
  included as literal content (the resulting drift is the honest signal).

### Marker byte cost

Per managed block, marker overhead on the Codex budget =
`41 + len(id) + len(source)` bytes for the start line (`+ 6 + len(mode)` when
a mode attribute is present) + `27` bytes for the end line + 2 EOL bytes
(LF). Example: the covenant block (`id=rules/bridge-covenant`, 21 bytes;
`source=.claude/rules/bridge-covenant.md`, 32 bytes) costs 41+21+32+27+2 =
123 bytes of the 32768-byte combined budget. The claude-only pair costs 33 +
31 bytes + 2 EOL where it appears (Claude-side files only — where stripping
makes runtime cost zero). Claude-side cost of all markers is zero (comments
stripped before context injection).

## Applicability preamble and rendering pipeline

### Preamble sentence template (versioned `pv1`)

For a rule shard whose frontmatter has a `paths` key with globs g1…gn (in
frontmatter list order):

```
Applies only when working on files matching: <G>. (bridge:pv1)
```

where `<G>` = the globs, each wrapped in single backticks, joined by the
two-byte string ", ". One line; no other whitespace variation permitted.
Example for `paths: ["docs/**/*"]`:

```
Applies only when working on files matching: `docs/**/*`. (bridge:pv1)
```

The trailing `(bridge:pv1)` token versions the template in-band (12 bytes
plus one leading space, 13 bytes total, per scoped block on the Codex
budget) — the only baseline-free way to know which template rendered a
block. A future template change bumps to `pv2`; blocks carrying an older
token than the current spec re-render as drift (deterministic, intended).

### Applicability

Rendered iff the shard's frontmatter `paths` list is present and non-empty.
The entry unit and unscoped shards render no preamble line (and no blank
separator line). Pinned edge: a `paths` key that is present but empty or not
a list of strings → no preamble; note the anomaly free-form.

### Rendering pipeline

`render(u)` for an agents-md unit u:

1. Take the source file's literal tracked bytes. For the entry unit this is
   the entry file itself — `@path` imports are NOT expanded; an imported file
   owns a projection only if it is itself a source unit. A leading UTF-8 BOM
   is NOT skipped anywhere in this pipeline (see the BOM note below).
2. Strip the YAML frontmatter block if the first line is exactly `---`
   (through the closing `---` line, inclusive).
3. Subtract claude-only segments: remove all lines from each recognized
   claude-only start-marker line through its end-marker line, inclusive
   (recognition per the marker grammar's line, placement, and malformation
   rules above).
4. Strip leading blank lines.
5. Apply normalization N (defined below).
6. If the applicability condition above holds, prepend the preamble line
   followed by exactly one empty line.

The projected block (what the covenant writes at M2+ and what the sentinel
re-renders for comparison) is:

```
<managed-start line for u>
<render(u)>
<managed-end line>
```

The sentinel compares N(body as found between the markers) against
render(u). "Entry-block comparison input = literal file bytes, no @import
expansion" is normative; an `@AGENTS.md` import is never expanded and
additionally trips the `self-referential-import` observation. LLM-rewritten
projections (host self-reference rewrites) are not a rendering mode:
source-side claude-only markers are the ONLY normative subtraction path; any
rewritten projection byte-compares as drift by construction (arbitration's
problem, M2+).

BOM note: a leading UTF-8 BOM is never skipped in this pipeline, nor by the
frontmatter recognition of the schemas below — a BOM'd file has no
recognizable frontmatter here, and in a rendered comparison a BOM is content
and produces honest drift. The single deliberate exception is lint
computation, which skips a leading BOM per the lint BOM-skip rule in
`report-spec.md` (lints diagnose what each host would see; rendering stays
byte-honest).

## Normalization set N (exact, closed)

Applied ONLY where a rule says so: agents-md body comparison (both sides)
and the report-comparison preprocessing in `report-spec.md`. Never applied
to the skills surface. Hooks fields use the field normalization under
"Declared-keys derivation" below instead.

1. **EOL**: replace every CRLF (0x0D 0x0A) and every lone CR (0x0D) with LF
   (0x0A).
2. **Trailing whitespace**: strip runs of U+0020 and U+0009 at each line
   end.
3. **Final newline**: strip all trailing whitespace/newlines at end of
   content, then append exactly one LF; empty content stays empty.

Nothing else. Explicitly NOT normalized: BOM (in a rendered comparison a BOM
is content and produces honest drift; on skills it is a lint), Unicode
normalization forms, interior blank lines, whitespace collapse, case. N is
deliberately the narrowest useful "empty diff" normalization; anything more
would smuggle semantic judgment into the deterministic layer.

## Frontmatter schemas and entry formats

### Rule-shard frontmatter (`.claude/rules/*.md`)

```yaml
---
paths:                # optional; YAML list of glob strings (host-native key)
  - "docs/**/*"
bridge:               # optional; the ONE bridge-namespaced key
  intent:             # required inside bridge:; list, newest entry appended last
    - date: 2026-07-08     # required; ISO 8601 calendar date, YYYY-MM-DD
      note: one-line motivation   # required; single-line string, recommended <= 120 chars
---
```

- `paths` is the only host-documented rules key; `bridge` is the single
  additional key the bridge ever adds to host-parsed frontmatter (minimal
  unknown-key surface). `bridge` is a map; M1 defines exactly one subkey,
  `intent`; other subkeys are reserved (ignored, never errors).
- Intent-record rule (the 含意图记录 convention): whenever a change lands in
  a source entry, the acting agent appends one `{date, note}` element to
  that entry's `bridge.intent` list in the same unit of work.
- Two intent-record forms are pinned, exactly one is in force at a time, and
  this spec states which. **In force: the frontmatter form above.** The
  fallback form — activated repo-wide only if the empirical check of
  Claude's tolerance for the extra `bridge` frontmatter key in rules files
  (officially unspecified; dated result recorded in this repo's
  `knowledge/entry-and-rules.md`) proves Claude intolerant — is a
  block-level HTML comment placed immediately after the frontmatter (or at
  the top of the file when no frontmatter exists), one per record, grammar
  `<!-- bridge:intent <YYYY-MM-DD> <single-line note> -->`, full-line,
  outside code fences.
- `CLAUDE.md` itself carries no frontmatter and no `bridge` key at M1 (entry
  intent records would use the comment fallback if ever needed).
- Skill masters may carry the same `bridge` key in `SKILL.md` frontmatter
  (Codex verifiably ignores unknown keys; `bridge` is exempt from the
  `claude-only-frontmatter` lint in `report-spec.md`).

### Intent-record format

One record = `{date: YYYY-MM-DD, note: single-line string}`. Records are
append-only in file order (oldest first), so git diffs of intent history
stay one-line additions. They are evidence for arbitration (M2+) and for the
report's evidence section; they never alter M1 state or suggested-action
determinations, and they never make a project onboarded.

### Hook intent document (`.claude/rules/hooks.md`)

File-level frontmatter: optional `bridge` key per the rule-shard schema
above (no `paths` — the intent document loads unconditionally). The document
body is a sequence of entries.

**Entry format** — heading, five-aspect prose bullets, then exactly ONE
fenced YAML block:

```markdown
## hook: <id>

- Trigger: <prose>
- Purpose: <prose>
- Command: <prose>
- Environment: <prose>
- Failure policy: <prose>
```

followed by one fenced code block with info string `yaml` carrying the
machine fields.

- Entry enumeration rule: an entry is a section opened by a level-2 heading
  matching the regex `^## hook: (?<id>[a-z0-9][a-z0-9-]*)$` and extending to
  the next such heading or EOF. The heading id is the authoritative entry
  id.
- The five bullet labels are pinned exactly: `Trigger`, `Purpose`,
  `Command`, `Environment`, `Failure policy`. Their prose never enters the
  consistency verdict.
- Exactly one fenced `yaml` block per entry carries the machine fields.

**Machine fields (names, types, required/optional):**

| Field | Type | Req | Meaning / constraints |
|---|---|---|---|
| `id` | string | required | must equal the heading id; charset `[a-z0-9-]`, starts alphanumeric; unique in the document |
| `event` | string | required | host event name, exact case (e.g. `Stop`, `SessionStart`, `PreToolUse`); unknown names are "newer than research date", never invalid |
| `matcher` | string | optional | omitted means "no matcher key in the projected group" (events like Stop take none); when present, compared code-point exact |
| `command` | string | required unless both targets are tier-4 | the command line |
| `commandWindows` | string | optional | Codex-only Windows branch; when declared, the codex handler must carry it; ignored on the claude surface at M1 (the mapping to Claude's handler `shell` field is deferred to M4) |
| `timeout` | integer | optional | seconds; when declared the handler must carry the same integer; when omitted the handler must omit it |
| `enabled` | boolean | required | `false` = declared but off: expected absence on all target surfaces (a present artifact is `drift`/`conflict` per case H-DISABLED-PRESENT in `report-spec.md`) |
| `targets` | map | required | MUST declare both `claude` and `codex` (complete projection) |
| `targets.claude.surface` | enum | required | `settings-json` \| `none` — abstract tokens, never file paths; the token→file mapping (`settings-json` → `.claude/settings.json` top-level `hooks` key) lives in this spec so a host layout change is a one-line spec edit, never a user-project migration |
| `targets.codex.surface` | enum | required | `codex-hooks-json` \| `none` — token→file: `codex-hooks-json` → `.codex/hooks.json` |
| `targets.<host>.tier` | enum | required | M1-valid set: `native` \| `declared-unsynced`, with `declared-unsynced` ⇔ `surface: none`. The values `structural` and `semantic` and the surface value `agents-md` (tier-3 standing-instruction carrier) are RESERVED for M4 and schema-invalid at M1 |
| `intent` | list of {date, note} | optional | per-entry intent log, same element schema as the intent-record format above (no `bridge:` wrapper needed — the fenced block is bridge-owned, no host parses it) |

**YAML quoting note (normative)**: the fenced block must parse as valid
YAML. A `command`, `commandWindows`, or `matcher` value containing `: `
(colon + space) — or any other construct YAML forbids in an unquoted plain
scalar — MUST be quoted (single quotes recommended). Comparison always uses
the parsed scalar value, so quoting never affects field equality.

**Schema violations**: any schema violation (missing required field,
duplicate id, unknown or reserved surface/tier value, tier/surface mismatch,
id/heading mismatch, zero or multiple `yaml` blocks in a section, an
unparseable `yaml` block per the quoting note above — counting as exactly
one violation for the section, never one per unextractable field — or
duplicate `(event, matcher, host)` declaration across entries, which makes
BOTH involved entries schema-invalid so ownership stays unambiguous per
group) → the entry (all involved entries, for the duplicate-pair case)
produces no unit rows and one mandatory `intent-doc-anomaly` observation per
violation (detail format in `report-spec.md` — the observation makes the
omission non-silent and fixture-comparable).

**Declared-keys derivation (ownership; PRIMARY rule)**: the intent document
IS the ownership declaration — no separate manifest exists or may be
introduced. For host h, the bridge-owned groups of h's file are exactly the
`(event, matcher)` pairs declared by schema-valid entries whose
`targets.<h>.surface` ≠ `none`. Field normalization for comparisons: string
fields are compared code-point exact after stripping leading/trailing ASCII
whitespace; `timeout` compares as integer; `type` must be exactly `command`;
matcher-absence in the intent matches only matcher-absence in the JSON
group.

**Reinforcement marker (SECONDARY, optional, never load-bearing)**: a
projected handler MAY carry `statusMessage` whose value begins with
`[bridge:<id>]` (the entry's id; any following text free-form). The marker's
roles: human readability in the JSON file, and orphan attribution — a marked
handler whose id has no schema-valid entry yields the H-MARKED-ORPHAN row of
the hooks decision table in `report-spec.md` instead of vanishing into the
undeclared channel. Comparison rule: a `statusMessage` matching
`[bridge:<entry-id>]…` on the entry's own handler is neither required nor an
undeclared key; any other `statusMessage` value IS an undeclared key. The
M2+ write path SHOULD add the marker on the Claude surface (`statusMessage`
is a Claude-documented handler field); whether it is written on the Codex
surface awaits live verification of Codex's tolerance for the field — the
marker is never required for ownership, which always derives from the intent
document.

**Allowed-key rule (for cases H-OK / H-EXTRA-KEYS)**: the handler's allowed
key set is `{type, command}` ∪ `{commandWindows}` if declared ∪ `{timeout}`
if declared ∪ `{statusMessage}` iff its value begins with
`[bridge:<entry-id>]`. Any other key present on the handler is an undeclared
key. The sibling `matcher` key on the GROUP object is governed by the
matcher field rule, not this set.

**Projected handler shape** (what the covenant writes at M2+, and what case
H-OK expects): inside `hooks.<event>` (settings.json) / `<event>`
(.codex/hooks.json), a group `{"matcher": <matcher>?, "hooks": [{"type":
"command", "command": <command>, "commandWindows": <commandWindows>?,
"timeout": <timeout>?, "statusMessage": "[bridge:<id>]"?}]}` with no other
keys on the handler. The `.codex/hooks.json` top-level shape (event-name
keys, no wrapper object — same family as Claude's hooks value) is PINNED but
UNVERIFIED: it must be live-verified before any M2 hooks write work (the
corresponding knowledge entry carries `status: watch`; the fixtures README
carries the caveat).

## Skill portability requirements

Normative MUSTs for every skill master `.claude/skills/<name>/`:

- `SKILL.md` has a YAML frontmatter block present from line 1;
- the frontmatter carries a non-empty `description`;
- the directory name is at most 64 characters, charset `[a-z0-9-]`;
- `name`, when present, equals the directory name;
- every file in the master directory is saved UTF-8 without BOM.

Schema surface: only `name` and `description` are host-portable; `bridge` is
Bridge-owned and inert on both hosts; every other frontmatter key is
Claude-only and lint-flagged. A violation of any MUST above is a portability
lint, never an error — the deterministic lint conditions and their pinned
report wordings are the closed lint list in `report-spec.md`, and lints
never affect the state column. Masters restricted to the portable subset
({`name`, `description`, `bridge`} frontmatter plus a static body) reach
`native` behaviorally; others reach `native` mechanically (the projection is
a byte copy) with degradation lints.
