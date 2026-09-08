# Bridge source-tree specification

Spec version: source-tree/v5.

This file defines source units, onboarding, markers, rendering, intent
records, hook ownership, and skill portability. Its companion,
[`report-spec.md`](report-spec.md), defines inputs, findings, observations,
and report comparison. Rules consume the filtered tracked files called
**repo bytes** in that companion, except its exact untracked covenant-path
safety check. Codex activation checks consume the companion's separate
**live activation inputs**. Those inputs may explain whether a carrier can
load, but never establish Bridge ownership or a Git baseline.

## Contents

- [Unit model](#unit-model)
- [Onboarding anchor](#onboarding-anchor)
- [Marker grammar](#marker-grammar)
- [Applicability preamble and rendering pipeline](#applicability-preamble-and-rendering-pipeline)
- [Codex target eligibility](#codex-target-eligibility)
- [Manual-zone ownership](#manual-zone-ownership)
- [Normalization set N](#normalization-set-n-exact-closed)
- [Entry/rule control comments and paths](#entryrule-control-comments-and-paths)
- [Reverse-adoption origin map](#reverse-adoption-origin-map)
- [Skill intent supporting file](#skill-intent-supporting-file)
- [Hook intent document](#hook-intent-document)
- [Shared event registry](#shared-event-registry-shared-events2026-09-07)
- [Hook ownership](#declared-keys-and-ownership-derivation)
- [Hook degradation block](#hook-degradation-block)
- [Projected handler shape](#projected-handler-shape)
- [Byte-stable projection](#byte-stable-projection)
- [Array ordering discipline](#array-ordering-discipline)
- [Managed skill tree](#managed-skill-tree)
- [Skill compatibility layers](#skill-compatibility-layers)

## Unit model

A report row is keyed by `(surface, unit, host)`:

| Field | Values |
|---|---|
| `surface` | `agents-md`, `hooks`, `skills` |
| `unit` | a unit id; a repo-relative adoption path; `-` for `no-source-unit`; or `<unit-id>#<ordinal>` (`ordinal` ≥ 2) for duplicate managed blocks |
| `host` | `claude`, `codex`, or `-`; use `codex` for `agents-md` and `skills`, the declared host for `hooks`, the containing host for marked hook orphans, and `-` for `no-source-unit` |

The four `unit` token classes are disjoint; `#` is outside the unit-id
charset.

Enumerate units as follows:

- **agents-md**: the entry unit `entry` uses root `CLAUDE.md`, falling back to
  `.claude/CLAUDE.md`, and exists only when exactly one exists. If both exist,
  emit `dual-project-entry` and block the unit; neither file wins. Add one
  unit for each tracked `.claude/rules/**/*.md` except
  `.claude/rules/hooks.md` and the immutable
  `.claude/rules/bridge-covenant.md`; its id is
  `rules/<path below .claude/rules without .md>`. Pair units with root
  `AGENTS.md` managed blocks by `id`. The covenant is the separately
  validated onboarding unit `rules/bridge-covenant`.
- **hooks**: each schema-valid `.claude/rules/hooks.md` entry is
  `hooks/<entry-id>` and produces one row per declared target host. Pair a JSON
  carrier surface with its owned `(event, effective-matcher)` group in
  `.claude/settings.json` or `.codex/hooks.json`, and pair
  `targets.codex.surface: agents-md` with the root `AGENTS.md` managed block
  whose id is `hooks/<entry-id>`. Matcher absence matches only absence. Also
  enumerate handlers whose `statusMessage` begins `[bridge:` for orphan
  detection.
- **skills**: each immediate `.claude/skills/<name>/` directory containing a
  tracked regular-file `SKILL.md` is unit `<name>`. Its source is the complete
  regular-file Git tree rooted at that directory, including an explicitly
  authored `agents/openai.yaml` when present. Pair it with the same-name
  immediate directory under `.agents/skills/` when that directory also
  contains a tracked regular-file `SKILL.md`. Directories without `SKILL.md`
  are not units. Empty directories are not part of a Git tree.

A would-be source path outside the source-path grammar is not a unit; emit
`unrepresentable-source-path`. Each surface that otherwise has no rows emits
exactly `(surface, -, -, no-source-unit, -, -, -)`.

A plan hook unit id is the report hook unit id with that row's host appended:
`hooks/<entry-id>/<host>` with `<host>` in `source`, `claude`, `codex`. The
`source` host has no report row. The two specifications key hook rows
differently and neither derives the other.

## Onboarding anchor

Evaluate onboarding once per project. A persistent, versioned two-part
covenant anchor replaces inference from coincidental carrier equality:

1. source half: tracked `.claude/rules/bridge-covenant.md`, byte-equal to the
   current `covenant/v3` source template; and
2. projection half: a tracked, well-formed root `AGENTS.md` block whose id is
   `rules/bridge-covenant` and whose source attribute is
   `.claude/rules/bridge-covenant.md`, with body byte-equal after N to the
   current `covenant/v3` projection template.

Both templates declare `covenant/v3`, `source-tree/v5`, `report/v5`,
`reconciliation/v3`, and `sync-plan/v3`. Bootstrap installs both halves in
one confirmed write. The project is **onboarded** only while both halves are
present, schema-valid, version-equal, and template-valid. If neither exists,
it is **not-onboarded**. A partial, malformed, modified, untracked, or
version-mismatched anchor is **blocked**, not a degraded onboarding signal.
Contract upgrades use an explicit migration plan; they are never ordinary
content drift. The archived-pair recognizer is the closed two-member set
{`covenant/v1`, `covenant/v2`}: the exact former templates are retained under
`templates/covenant/v1/` and `templates/covenant/v2/` only as migration
evidence, each is a single hop to the current tuple, and there is no chaining
and no dual-read mode. Runtime scanning supports only the current tuple: an old
exact pair is read-only onboarding `blocked` and write-side
`contract-migration`, never an alternate readable contract. The write side must
carry every reachable archived-era proven managed unit through the closed-set
migration transition defined by `reconciliation/v3`, or record an explicit
per-unit release/repair decision. A hook unit never appears in that transition,
because `reconciliation/v2` forbade every hook write, so no reachable v2-era
commit can prove a hook baseline. Merely replacing the covenant bytes does not
establish current-tuple ownership.

The anchor declares the Bridge ownership model, not ownership of every
occupied path. A particular skill copy is proven managed only by a historical
identical baseline under an installed anchor or by an explicit current
annexation decision. The read-only sentinel never attempts that historical
proof. Before onboarding, missing projections are `not-projected` and
occupied projection locations are `adoption-candidate`. After onboarding,
carrier mismatches with a present canonical source are `drift`;
`bridge-sync` decides their direction. A copy-only skill remains
`adoption-candidate` under either onboarding state because the covenant alone
cannot prove that a missing source is a managed deletion. Only
`bridge-sync`, using reachable ownership history and a unique baseline, may
arbitrate that deletion. Removing the anchor from an onboarded history is
offboarding and requires an explicit write-side decision.

## Marker grammar

### The four marker lines

```
managed-start     = "<!-- bridge:managed:start id=" unit-id " source=" source-path " -->"
managed-end       = "<!-- bridge:managed:end -->"
claude-only-start = "<!-- bridge:claude-only:start -->"
claude-only-end   = "<!-- bridge:claude-only:end -->"
```

Exactly one U+0020 between every token shown; no tabs; no other attributes;
attribute order is `id`, then `source`. The bracketed `mode` form from v3 is
not part of v5; a legacy-looking start line containing `mode=` is a blocking
`legacy-managed-mode`, not a semantic escape hatch.

### Attribute charsets

```
unit-id     = seg *("/" seg)          ; seg = 1*[A-Za-z0-9._-]
source-path = seg *("/" seg)          ; same seg charset; repo-root-relative,
                                      ; "/" separators, no "./" prefix
```

The shared segment grammar admits ASCII letters, digits, dot, underscore, and
hyphen. It excludes whitespace, `=`, backticks, and `-->`. An
unrepresentable source path is not a unit and emits
`unrepresentable-source-path`.

### Line and placement rules

- A marker must occupy an entire line: after stripping the trailing EOL, the
   line must match the grammar from first byte to last. Anything else is
   ordinary content.
- Managed blocks appear only in root `AGENTS.md`. Claude-only pairs appear
   only in `CLAUDE.md` (or `.claude/CLAUDE.md`) and
   `.claude/rules/**/*.md`, and are recognized under the same rules.
- Scan top-to-bottom. A line with at most three leading spaces followed by
  three backticks or `~~~` toggles fence state. Recognize markers only while
  the fence is closed.
- Blocks do not nest. A start opens a block only when none is open; the next
  end closes it. An end without an open block is content.

### Malformation handling

Each condition emits one `marker-anomaly`:

| Condition | Interpretation |
|---|---|
| Start while a block is open | Body content |
| End without an open block | Content |
| Open block at EOF | Unrecognized block; its start is content |
| Block `source` differs from the path derived from `id` | Pair by authoritative `id` for reporting; block the full AGENTS region map |
| Duplicate `id` | Preserve file-order identities (`id`, then `<id>#<ordinal>`); block the full AGENTS region map |
| Claude-only start unclosed at EOF | Subtract nothing; retain the start and following content |

For a block whose id matches `^hooks/[a-z0-9][a-z0-9-]*$`, the derived source
path is the constant `.claude/rules/hooks.md`. Every other block derives its
source path from its id as before.

## Applicability preamble and rendering pipeline

### Preamble sentence template (versioned `pv2`)

For a rule shard with globs g1…gn in frontmatter order:

```
Applies only while reading or editing files that match at least one of these source globs: <G>. (bridge:pv2)
```

`<G>` is each glob wrapped in single backticks and joined by `, ` in
frontmatter order. The line, including `(bridge:pv2)`, admits no other
whitespace variation. A valid pattern cannot contain a backtick, so this
encoding is mechanically reversible.

### Applicability

Render the preamble only for a valid scoped rule as defined below. The entry
unit and a shard with no frontmatter are unscoped and render no preamble or
separator. A present but invalid, no-op, duplicate, or unrepresentable
`paths` value blocks the unit; it never degrades to unscoped content.

### Rendering pipeline

Throughout this specification, frontmatter is recognized only when the first
line is exactly `---` and a later full line is exactly `---`. An unclosed
block is content.

For an agents-md unit `u`, `render(u)`:

1. Take the source file's literal tracked bytes.
2. For a rule shard, strip its recognized YAML frontmatter, including both
   delimiter lines. Entry and covenant units have no frontmatter.
3. Strip the contiguous v5 control-comment header defined below.
4. Subtract claude-only segments: remove all lines from each recognized
   start through its end, inclusive.
5. Reject an active `@path` import in the remaining shared region. Active
   means outside fenced code and inline code spans; imports inside a
   claude-only segment were removed in step 4. Do not expand any import.
6. Strip leading blank lines.
7. Apply normalization N (defined below).
8. If applicable, prepend the exact `pv2` preamble and one empty line.

The projected block is:

```
<managed-start line for u>
<render(u)>
<managed-end line>
```

Compare `N(body between markers)` with `render(u)`. Any active shared import
blocks M3 projection because Codex does not expand Claude imports; this
includes `@AGENTS.md` and every other active `@path`. Code-span, code-fence,
and claude-only occurrences are inert and do not block. Projection-time
free-form rewriting is not a render mode: shared source prose must be
host-neutral, Claude-only prose uses the subtraction markers, and Codex-only
prose remains in the `AGENTS.md` manual zone.

### Codex target eligibility

Carrier equality does not prove that root `AGENTS.md` is the selected,
loadable Codex project document. Resolve activation from live inputs, not from
the ownership-byte filter:

- resolve the effective Codex values for root markers,
  `project_doc_fallback_filenames`, and `project_doc_max_bytes`;
- inspect the exact root override, root `AGENTS.md`, and configured
  same-directory fallback candidates even when they are untracked or ignored;
- read a candidate carrier only when it is a safe regular file at the expected
  root child path, with no symlink, reparse point, special type, or path
  escape; and
- retain only the resolved values, paths, type evidence, and byte counts as
  activation evidence. Never feed these bytes into ownership, source-unit,
  managed-region, or baseline decisions.

Before an M3 apply, block by default when:

- root `AGENTS.override.md` exists and shadows root `AGENTS.md`;
- the effective root-marker configuration cannot prove that the planned
  repository root is Codex's project root, including an empty marker list or
  exclusion of every marker present at that root;
- root `AGENTS.md` is absent and a configured same-directory fallback file is
  currently selected, because creating `AGENTS.md` would silently shadow it;
- effective `project_doc_max_bytes` is zero; or
- the exact planned root `AGENTS.md` UTF-8 byte count exceeds the effective
  positive project-document budget.

Also block when effective configuration, carrier selection, carrier safety, or
the byte budget cannot be determined. A documented host default may be used
only after configuration resolution proves the setting absent; inability to
resolve configuration is not evidence for a default.

Bridge reports these facts and asks the user to resolve discovery or adoption;
it does not edit Codex config, an override, a fallback file, or root markers.
At or above seven eighths of a positive budget is a warning requiring
confirmation, not a blocker by itself. Writes are followed by a fresh-session
activation hedge because the host builds its instruction chain per run.

### Manual-zone ownership

Parse root `AGENTS.md` into well-formed managed blocks and every intervening
byte span. Only a block with historical ownership evidence or an explicit
current annex decision is managed. Every other byte, including separators,
blank lines, comments, malformed marker-like text, unknown blocks, and
Codex-only prose, is manual-zone data.

An apply constructs one exact desired file image from selected block changes
plus unchanged protected spans. A conflict block may remain untouched while
an independent block changes, but both the untouched block and every manual
span participate in the complete planned preimage and postimage.

The write-side capability profile chooses a versioned protocol per path. An
attested `strict-replace/v1` binds the complete preimage to one replacement.
Otherwise an eligible existing regular UTF-8 text file may use
`guarded-patch/v1`: derive one non-empty contiguous region that covers every
change, extend it until its exact old value is unique in the complete
preimage, perform one exact-literal replacement, and surround it with
complete-file preflight and postverification. A missing file requires
`strict-create/v1`; ordinary create-after-check is not allowed.

Guarded preflight and postverification do not close the race inside the host
call. They prove planned complete bytes at observation points, not that a
concurrent manual-zone edit could not be overwritten. A guarded carrier must
therefore emit `manual-zone-guarded` and `guarded-patch-non-cas`, not
`manual-zone-preserved`. Marker malformation, duplicates, an unclosed block,
or inability to derive one eligible unique region blocks the whole file.

This protocol inherits the guarantee boundary of the selected host operation
and underlying filesystem. Bridge does not implement a lock, a multi-file
transaction, crash durability, or stronger atomicity than an attested strict
primitive actually supplies.

A leading UTF-8 BOM is content and prevents frontmatter or byte-zero control
header recognition, so it blocks an entry/rule unit. Only skill-lint
computation skips it, as defined in `report-spec.md`.

## Normalization set N (exact, closed)

Apply N only to both sides of agents-md body comparison and to report
comparison preprocessing. Skills use raw bytes; hooks use their field
normalization.

1. **EOL**: replace every CRLF (0x0D 0x0A) and every lone CR (0x0D) with LF
   (0x0A).
2. **Trailing whitespace**: strip runs of U+0020 and U+0009 at each line
   end.
3. **Final newline**: strip all trailing whitespace/newlines at end of
   content, then append exactly one LF; empty content stays empty.

Do not normalize BOM, Unicode forms, interior blank lines, interior
whitespace, or case.

## Entry/rule control comments and paths

### Intent-record format

Entry and rule intent records use one controlled HTML-comment grammar:

```text
<!-- bridge:intent <YYYY-MM-DD> <note> -->
```

The date is a valid calendar date. `<note>` is 1–120 Unicode scalar values,
is single-line, has no leading/trailing ASCII whitespace, and contains
neither `--` nor NUL. Records are oldest first. In an entry they form a
contiguous header from byte zero. In a scoped rule they form a contiguous
header immediately after the closing frontmatter delimiter; in an unscoped
rule they start at byte zero. The renderer strips this header.

Append one record for initial onboarding/annexation and whenever semantic
source intent changes. A mechanical reprojection appends nothing. Intent is
arbitration evidence, never ownership. Unknown `bridge:*` control comments,
misplaced records, or a `bridge` YAML frontmatter key block the unit. M3 does
not rely on undocumented tolerance of unknown YAML keys.

A source candidate may have no record before onboarding. From the first
confirmed create/annex onward, every managed entry/rule source requires at
least one valid record. Missing history does not change rendered carrier
equality, but write-side reconciliation reports `intent-missing` and repairs
the source before declaring the unit complete.

The immutable covenant source starts with the exact line:

```text
<!-- bridge:covenant covenant/v3 source-tree/v5 report/v5 reconciliation/v3 sync-plan/v3 -->
```

followed by its exact intent records. Changed, missing, reordered, or unknown
tuple fields are an anchor anomaly. An archived pair is recognized only by byte
equality to the archived migration evidence under `templates/covenant/v1/` or
`templates/covenant/v2/`.

### Rule-shard `paths` frontmatter

A v5 rule shard either has no frontmatter (unscoped) or has a YAML map whose
only key is `paths`. `paths` must be a non-empty list of unique strings.
Preserve list order; do not normalize or reorder globs. Bridge-specific
metadata never appears in YAML.

Every pattern must be non-empty after ASCII-whitespace inspection, valid
UTF-8, repo-relative, and use `/`. It may not contain NUL, CR, LF, a
backtick, a backslash, an empty/dot/dot-dot path segment, an unclosed bracket
expression, or a leading `/`. Exact patterns `**` and `**/*` are no-op
universal scopes and are invalid in v5; use an unscoped shard instead.
Duplicates are also no-op and block the unit.

Brace expansion is evaluated for the whole list under Claude's shared limit
of 1,000 expanded patterns and 4 MiB of expanded UTF-8 pattern bytes. If any
pattern is invalid, or the list cannot be proven to remain within both
limits, the unit is blocked. An over-budget pattern must not be rendered as
its literal unexpanded braces, because that would silently change the source
scope. Do not infer no-op from the current repository having no matching
file; v5's no-op set is the exact universal/duplicate set above.

The agent parses YAML and passes the validated ordered string list to any
mechanical renderer. A Python helper must not implement a partial general
YAML parser. Invalid, empty, no-op, duplicate, or over-budget `paths` never
fall back to an unscoped render.

### Active shared imports

After subtracting control comments and claude-only regions, scan shared
source for `@path` imports using Claude's active-import boundary: exclude
fenced code blocks under the marker fence rule. Outside fences, an inline
code span opens with a run of one or more backticks and closes at the next
run of exactly the same length; an unmatched run opens no excluded span.
Exclude those closed spans, then match
`(?<!\S)@[A-Za-z0-9_./~-]+`. Report the byte span of every match. Any
remaining active import blocks M3 projection. `@AGENTS.md` is the
self-referential high-risk case, but it is not the only blocker. Projection
cannot preserve Claude's import expansion semantics, and Bridge must not
inline another file implicitly.

### Reverse-adoption origin map

Rendering produces an origin map from every emitted shared line to its source
byte span, plus protected spans for frontmatter, control comments, and
claude-only regions. Projection-only adoption first removes an exact `pv2`
preamble, then maps changed body hunks through that origin map.

Body edits wholly inside mapped shared spans may update the corresponding
source spans. A preamble that still matches exact `pv2` grammar may update
`paths` after the same validity/budget gates. A hunk crossing a protected
span boundary, a free-form preamble, host-self wording that needs
neutralization, or any ambiguous mapping requires an explicit
`semantic-review-required` candidate: show both proposed source bytes and
their deterministic rerender before confirmation. Never discard or rewrite a
protected span implicitly.

### Skill intent supporting file

Every Bridge-managed skill master stores intent history at
`<skill-directory>/bridge-intent.yaml`:

```yaml
intent:
  - date: 2026-07-23
    note: One-line motivation
```

`intent` is the only defined top-level key. The file is required from the
first confirmed onboarding or annexation onward, copied byte-for-byte with the
rest of the skill tree, and read only as bridge evidence. Append a dated
motivation for a semantic change or projection-side adoption. Do not append
for a purely mechanical reprojection. Do not add Bridge-private keys to
`SKILL.md` frontmatter.

### Hook intent document

`.claude/rules/hooks.md` has no YAML frontmatter and loads unconditionally. It
is never a `rules/<id>` agents-md unit; the `hooks/<entry-id>` and `rules/<id>`
id namespaces are disjoint. Two file-level Bridge control comments are
recognized in v5: the `bridge:intent` header defined above, and the
shared-execution acknowledgement, byte-exact:

```text
<!-- bridge:hooks-shared-execution <YYYY-MM-DD> acknowledged: committed Claude hooks run for every clone without a trust prompt -->
```

Exactly one U+0020 between tokens, no other attributes, one whole line, placed
in the file-level control header before the first entry, with `<YYYY-MM-DD>` a
valid calendar date. It is a registered `bridge:*` control comment in v5, so it
never trips the unknown-control-comment blocker, and the renderer strips it with
the rest of the header. Hooks committed to a repository run for everyone who
clones it, and Bridge classification is review metadata, not a sandbox: this
record is a reviewable checkpoint in Git, never an enforcement boundary.

Each entry has a heading, five prose bullets, and one fenced `yaml` block:

```markdown
## hook: <id>

- Trigger: <prose>
- Purpose: <prose>
- Command: <prose>
- Environment: <prose>
- Failure policy: <prose>
```

Follow the prose with exactly one fenced code block whose info string is
`yaml`; it carries the machine fields below.

An entry starts at
`^## hook: (?<id>[a-z0-9][a-z0-9-]*)$` and ends before the next matching
heading or at EOF. The heading id is authoritative. Bullet labels are
exactly `Trigger`, `Purpose`, `Command`, `Environment`, and `Failure policy`.
Their prose never affects carrier consistency, but `Trigger`, `Purpose`, and
`Failure policy` are interpolated by the degradation render below, so all five
values belong to the source unit's compared value.

The file-level preamble before the first heading admits the control header and
prose only, so a fenced `yaml` block there belongs to no entry and is a
`yaml-block-count` violation. `inspect-hook-intents` scans that preamble and
emits the anomaly itself, with the line of the opening fence and no entry id,
so the scanner and the validating agent never disagree about a stray block.

Machine fields:

| Field | Type | Req | Meaning / constraints |
|---|---|---|---|
| `id` | string | required | equals the heading id; `[a-z0-9-]`, starting alphanumeric; unique |
| `event` | string | required | exact-case host event, validated against `shared-events/2026-09-07`; an unknown name stays valid and carries `event-unverified` |
| `class` | enum | required | `reminder`, `observation`, `gate`, or `side-effect`; author-declared, never inferred from a command string |
| `enabled` | boolean | required | `false` expects no handler on any target surface |
| `command` | string | required unless every target surface is `none` or a prose surface | must be valid in both bash and PowerShell unless a per-host override or `commandWindows` carries the divergent branch |
| `matcher` | string | optional | shared default; omission means no projected `matcher` key and matches only omission |
| `timeout` | integer | optional | seconds; projected iff declared; compared as an integer; range validated per host and event |
| `enabled-by` | list of `{date, note}` | required iff `class` is `gate` or `side-effect` and `enabled` is `true` | same record grammar as `intent` |
| `targets` | map | required | contains exactly `claude` and `codex` |
| `targets.claude.surface` | enum | required | `settings-json`, `intent-doc`, or `none` |
| `targets.codex.surface` | enum | required | `codex-hooks-json`, `agents-md`, or `none` |
| `targets.<host>.tier` | enum | required | `native`, `semantic`, or `declared-unsynced` |
| `targets.<host>.command` | string | optional | per-host override; wins over the shared value |
| `targets.<host>.matcher` | string | optional | per-host override; wins over the shared value |
| `targets.<host>.timeout` | integer | optional | per-host override; wins over the shared value |
| `targets.claude.shell` | enum | optional | Claude only; `bash` or `powershell`; projected verbatim |
| `targets.codex.commandWindows` | string | optional | Codex only; compared only on the Codex surface |
| `targets.<host>.override-reason` | enum | required iff that target declares at least one override key | `matcher-grammar`, `matcher-domain`, `platform-command`, `env-placeholder`, or `timeout-cap` |
| `intent` | list of `{date, note}` | optional | entry-local intent records, oldest first |

Both fenced-block record lists use one grammar. Each record is `- date:` with a
valid calendar date, records are oldest first, and each carries one `note:`
scalar that is non-empty, single-line, has no leading or trailing ASCII
whitespace, and contains no NUL. The 1-120 scalar cap and the `--` prohibition
of the `bridge:intent` comment are properties of the HTML-comment carrier and
do not apply inside the fenced block. A violation is `enabled-by-malformed`
for `enabled-by` and `field-invalid` for `intent`.

`commandWindows` is not a top-level key in v5, and `structural` is reserved and
invalid for hook rows. The fenced block must be valid YAML; quote scalars when
YAML requires it. Comparisons use parsed scalar values. The agent parses that
YAML and hands validated values to any mechanical helper; no Bridge helper
implements a partial general YAML parser.

A complete entry, every field shown:

```yaml
id: repo-guard
event: PreToolUse
class: gate
enabled: true
command: .bridge/hooks/guard.sh
matcher: "^(Bash)$"
timeout: 30
enabled-by:
  - date: 2026-09-07
    note: reviewed the exact command line and accepted repository-wide execution
targets:
  claude:
    surface: settings-json
    tier: native
    matcher: "Bash"
    shell: bash
    override-reason: matcher-grammar
  codex:
    surface: codex-hooks-json
    tier: native
    commandWindows: "pwsh -NoProfile -File .bridge/hooks/guard.ps1"
    override-reason: platform-command
intent:
  - date: 2026-09-07
    note: per-host matchers added; shared Bash was mode-ambiguous
```

Per-host surface, tier, and carrier are closed. The declared tier is validated,
never computed:

| host | surface | required tier | carrier | write |
|---|---|---|---|---|
| `claude` | `settings-json` | `native` | `.claude/settings.json` top-level `hooks` | `guarded-patch/v1` on owned spans |
| `claude` | `intent-doc` | `semantic` | `.claude/rules/hooks.md` itself | none; the source is the carrier |
| `claude` | `none` | `declared-unsynced` | none | none |
| `codex` | `codex-hooks-json` | `native` | `.codex/hooks.json` top-level `hooks` | `guarded-patch/v1` on owned spans |
| `codex` | `agents-md` | `semantic` | root `AGENTS.md` block `hooks/<id>` | through `closure/agents-md` |
| `codex` | `none` | `declared-unsynced` | none | none |

**Class and the explicit-enable gate.** `class` is author-declared and Bridge
never classifies a command string. A `gate` or `side-effect` entry with
`enabled: true` requires at least one covering `enabled-by` record. Without one
the entry stays schema-valid and still emits its rows; the write side serializes
a selected zero-write decision closure with action `opt-in-or-skip` and the
blocker warning `hook-opt-in-required`. Confirming the opt-in appends the
`enabled-by` record to the source, after which the entry projects normally.
`enabled: false` keeps its exact v4 meaning.

**Degradation eligibility (closed).** A prose surface, `intent-doc` on Claude or
`agents-md` on Codex, is admissible only when both hold: `class` is `reminder`
or `observation`; and the declared `event` is proven non-native on that host by
`shared-events/2026-09-07`. Otherwise the unsupported host must declare
`surface: none` with tier `declared-unsynced`. A degradation restates a
mechanism whose entire effect is delivering text to the model. A mechanism whose
effect is a runtime veto, a permission decision, or a filesystem or network side
effect is never degradable.

**Per-host overrides.** The override keys are exactly `command`, `matcher`, and
`timeout` on either target, plus `commandWindows` on `targets.codex` and `shell`
on `targets.claude`. The first three replace the shared scalar on that host
only. A target that declares one or more of the five requires exactly one
`targets.<host>.override-reason`; a target that declares none must omit it. The
`override-reason` registry and the `intent-doc-anomaly` reason registry are
separate closed sets that happen to share the token `matcher-domain`.
`targets.claude.shell` selects Claude's interpreter and never changes the
command text.
`targets.codex.commandWindows` selects Codex's command text on Windows and has
no interpreter meaning. They are not a mapping pair, and Bridge never derives
one from the other. A projected Claude `commandWindows` key and a projected
Codex `shell` key both remain undeclared.

A shared `command` must survive both Windows shells: on the same machine Claude
runs `command` under bash (Git Bash) while Codex runs `commandWindows` under
`pwsh -NoProfile -Command` (collected 2026-09-07). Project-scoped Codex hooks
receive no injected environment variables at all, while Claude exports
`${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, and `${CLAUDE_PLUGIN_DATA}`,
so a command referencing any path placeholder cannot be one shared string and
requires an override with `override-reason: env-placeholder`.

**Host keys outside the declared schema.** Three disjoint closed sets govern the
keys Bridge finds on an owned handler:

| Set | Keys | Handling |
|---|---|---|
| passthrough | Codex `additionalContextLimit`; Claude `if` | preserved byte-for-byte in place, never written, never removed, excluded from handler equality; the row carries `behavior-degraded` |
| semantics-changing | Claude `args`, `async`, `asyncRewake`, `once`; Codex `async` | never passthrough; presence on an owned handler is drift resolved only by `annex-or-keep` |
| never-project | handler types `http`, `mcp_tool`, `prompt`, `agent`, plus every key in the two sets above | Bridge never writes them |

Bridge writes only documented fields, so its own output can never break a host
loader. An owned Codex handler carrying any other key emits
`codex-handler-unknown-key` and keeps the key: Codex denies unknown fields only
at the top level of `.codex/hooks.json`, so an unknown key inside a matcher
group or a handler object is silently ignored by the host and its consequence
is a behavior claim Bridge cannot verify.

**Effective timeout ranges.** The effective timeout is the per-host override
when declared, else the shared `timeout`; an absent timeout is always in range.
A value outside the range is `timeout-out-of-range`:

| host | event | admissible range |
|---|---|---|
| `codex` | `SessionEnd`, `Interrupt` | 1 to 3 inclusive |
| `codex` | every other event | 1 to 600 inclusive |
| `claude` | `SessionEnd` | 1 to 60 inclusive |
| `claude` | every other event | any positive integer |

Codex normalizes an omitted timeout before dispatch, and only `SessionEnd` and
`Interrupt` are clamped: they default to 1 second and are silently rewritten
into 1 through 3 with a warning, so Bridge refuses to declare a value that host
would rewrite. Every other Codex event is `unwrap_or(600).max(1)`, a 600 second
default with a 1 second floor and no host-side ceiling. The upper bound `600` on
the `every other event` row above is therefore a Bridge-side conservative rule,
not a host cap: it keeps a declared timeout inside the range the host treats as
its own default, and a longer value is `timeout-out-of-range` even though the
host would accept it verbatim.

**Validation lints.** Each violation emits one `intent-doc-anomaly`, and an
invalid entry emits no unit row; the two non-invalidating reasons named after
the table are the only exceptions. The observation detail stays `(entry <id>)` or
`(line <n>)`; the reason token below names the lint in Evidence and notes and
never appears in the observation line. The reason registry is closed:

| Reason | Violation |
|---|---|
| `bullet-missing` | a required prose bullet is absent or carries one of the five labels in a form the closed grammar does not accept |
| `yaml-block-count` | zero or more than one fenced `yaml` block in the entry, or a fenced `yaml` block that belongs to no entry because it opens before the first `## hook:` heading; the stray-block case reports `(line <n>)` for the line of its opening fence and carries no entry id |
| `unrecognized-field` | a line inside the fenced block that the closed grammar does not recognize, including a construct no closed scanner can read and a YAML parse failure |
| `id-heading-mismatch` | `id` differs from the heading id |
| `field-missing` | a required machine field is absent |
| `field-invalid` | a machine field has the wrong type or an unusable value |
| `enum-invalid` | an enum field carries an unregistered or reserved token, including `structural` |
| `class-missing` | `class` is absent |
| `tier-surface-mismatch` | the declared tier is not the tier that host's surface requires |
| `surface-host-mismatch` | `surface: agents-md` on `targets.claude`, or `surface: intent-doc` on `targets.codex` |
| `tier-unsupported-event` | tier `native` declared for an event proven non-native on that host |
| `degradation-ineligible` | a prose surface with `class` `gate` or `side-effect`, or on an event not proven non-native on that host |
| `enabled-by-missing` | `class` `gate` or `side-effect` with `enabled: true` and no covering `enabled-by` record |
| `enabled-by-malformed` | an `enabled-by` record violates the `{date, note}` grammar |
| `override-without-reason` | an override key on a target that declares no `override-reason` |
| `reason-without-override` | `override-reason` on a target that declares no override key |
| `matcher-domain` | an effective matcher outside that host's closed per-event domain |
| `matcher-ignored` | a matcher declared for an event that host ignores |
| `timeout-out-of-range` | an effective timeout outside the host-and-event range above |
| `duplicate-id` | two entries share an `id` |
| `duplicate-ownership` | two entries share an `(event, effective-matcher, host)` triple |
| `shared-execution-unacknowledged` | a `settings-json` Claude surface with no file-level `bridge:hooks-shared-execution` comment |

Every entry sharing a duplicate id or a duplicate ownership declaration is
invalid. `enabled-by-missing` and `shared-execution-unacknowledged` are the two
non-invalidating members of this registry: each emits no `intent-doc-anomaly`,
leaves every unit row of its entry intact, and names only a condition the write
side reports as a closure-scoped blocker. `enabled-by-missing` is reported as
`hook-opt-in-required` on `closure/decision/hooks/<entry-id>`, and
`shared-execution-unacknowledged` as `hook-acknowledgement-missing` on
`closure/hooks/claude`. They are registered here so the reason set stays closed
and so a read-side report can name either condition in Evidence and notes.

Advisory and never a schema violation: the acknowledged
`matcher-grammar-divergent` and `platform-branch-divergence`, and the
informational `hook-output-not-delivered`, which applies to `class: reminder`
only because an `observation`'s effect does not depend on delivery.

### Shared event registry (`shared-events/2026-09-07`)

A dated closed registry, collected 2026-09-07 from both hosts' hook references.
A later collection is a new dated registry and a new spec version.

| Membership | Names |
|---|---|
| shared (11) | `SessionStart`, `SubagentStart`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop`, `SessionEnd` |
| Codex-only (1) | `Interrupt` |

Codex's event set is closed at exactly those 12 names on the registry date;
Claude's is open and remains a strict superset of the shared 11. Therefore:

- an event is **proven non-native on Claude** exactly when it is `Interrupt`;
- an event is **proven non-native on Codex** exactly when it is outside the 12;
- an event is **unknown** exactly when it is outside the 12. An unknown name
  stays valid, may be newer than the registry date, and makes every row of its
  entry carry the annotation `event-unverified`.

Matcher and delivery facts belong to the same dated registry:

- Codex ignores a declared matcher on `UserPromptSubmit`, `Stop`, and
  `Interrupt`; its other nine events honor one. A matcher declared for one of
  those three on the Codex target is `matcher-ignored`.
- Claude mode-switches on the character class `[A-Za-z0-9_ ,|-]`: a matcher
  built only from those characters is an exact string or a comma/pipe separated
  list, and any other character makes it an unanchored regular expression.
- Codex always compiles a matcher as an unanchored Rust regular expression, with
  no lookahead and no backreferences.
- `SessionStart` source domain: `startup`, `resume`, `clear`, and `compact` on
  both hosts, plus `fork` on Claude only.
- The `SessionEnd` reason domain on Codex is the single value `other`. The
  Claude `SessionEnd` reason domain is deliberately left open in v5 and never
  emits `matcher-domain`.
- `matcher-domain` is emitted only for a `(host, event)` pair whose domain this
  list closes. Every other pair has an open domain in v5.
- The shared stdout-delivering set is exactly `{SessionStart, UserPromptSubmit}`.
  A `class: reminder` entry declaring a `native` tier on any other event emits
  the informational `hook-output-not-delivered`.
- `matcher-grammar-divergent` has a closed predicate. It is emitted exactly
  when all three conditions hold: the entry's shared `matcher` is a string
  inside the Claude list class `^[A-Za-z0-9_ ,|-]*$` that contains `|` or `,`;
  both targets declare a host-executed JSON surface, that is `settings-json` on
  `targets.claude` and `codex-hooks-json` on `targets.codex`; and neither
  target overrides `matcher`. Claude then reads those bytes as one exact name
  or a `|` or `,` separated list of exact names while Codex compiles the same
  bytes as one unanchored regular expression, so the comma form never matches
  on Codex and the pipe form matches substrings. A bare literal such as `Bash`
  never emits it, because it is one exact name on Claude and an unanchored
  pattern that still selects that name on Codex. An entry that projects into
  only one JSON carrier never emits it either, because a single host cannot
  disagree with itself. The divergence is not a schema violation: it emits the
  acknowledged `matcher-grammar-divergent` so the author sees the divergence
  and may add per-host overrides, and adding either override silences it.

### Declared keys and ownership derivation

The intent document is the sole ownership declaration. For host `h`, owned
groups are exactly the `(event, effective-matcher(h))` pairs of valid entries
whose `targets.<h>.surface` is a JSON carrier, where `effective-matcher(h)` is
`targets.<h>.matcher` when declared, else the shared `matcher`, else absent.
Matcher absence matches only absence. `effective-command(h)` and
`effective-timeout(h)` resolve the same way. A duplicate
`(event, effective-matcher, host)` triple invalidates every involved entry.

For equality, strip leading and trailing ASCII whitespace from string fields,
then compare code points. Compare `timeout` as an integer and require `type` to
equal `command`. Passthrough keys are excluded from equality.
`statusMessage` is excluded from equality as well. It has no source field, so
the desired model takes its `statusMessage` from the existing handler on both
hosts; a `[bridge:<entry-id>]`-prefixed value present on one side only, or
carrying hand-added suffix text, is never a difference, an absent field, or an
extra key. A `statusMessage` whose value does not begin `[bridge:<entry-id>]`
stays undeclared and selects H-EXTRA-KEYS.

Allowed handler keys are `{type, command}`, plus:

- `commandWindows` on Codex only, iff `targets.codex.commandWindows` is declared;
- `shell` on Claude only, iff `targets.claude.shell` is declared;
- `timeout` iff the effective timeout is declared;
- optional `statusMessage` iff it begins `[bridge:<entry-id>]`;
- that host's passthrough key when the carrier already carries it.

`matcher` belongs to the group, not the handler. A projected Claude
`commandWindows` key and a projected Codex `shell` key both remain undeclared,
and any other handler key is undeclared.

The `[bridge:<entry-id>]` status prefix reinforces attribution but does not
establish ownership. Another `statusMessage` value is undeclared. A
`[bridge:<id>]` marker without a valid entry produces H-MARKED-ORPHAN.
Projection adds the marker on the Claude surface always, and on the Codex
surface only when creating the handler. Bridge never adds, changes, or removes a
Codex `statusMessage` on an otherwise converged handler, because Codex binds
per-hook trust to a normalized identity that includes it.

**Codex per-hook trust identity (collected 2026-09-07).** Codex hashes a
normalized handler identity built after timeout defaulting and clamping. In the
identity: the normalized `timeout`, `statusMessage`, the normalized
`additionalContextLimit`, `matcher`, `command`, and `async`. Not in the
identity: `commandWindows`. Replacing only a handler's `commandWindows`
therefore keeps the previously trusted hash valid, so changed Windows code runs
with no review prompt; the write side discloses that with the informational
`codex-trust-blind-change` and emits `codex-hook-retrust-required` only when an
identity field changes.

Codex persists per-hook trust in the user's `config.toml` as
`[hooks.state."<key>"]`, keyed
`<source>:<Event>:<groupIndex>:<handlerIndex>`. The key is positional, so moving
a group or a handler silently orphans an existing trust record and can
re-enable a hook the user deliberately disabled. Bridge therefore renders groups
and handlers in a stable order, appends only, and reports every index shift with
`codex-trust-reindex`. Bridge does not read `[hooks.state]`; resolved Codex
project trust is the only trust input, it is a live activation input, and it
never becomes repo ownership bytes.

### Hook degradation block

A `targets.codex.surface: agents-md` entry projects one ordinary managed block
into root `AGENTS.md`. Its marker id is `hooks/<entry-id>` and its marker source
is the constant `.claude/rules/hooks.md`. It is an ordinary root `AGENTS.md`
block for every other purpose: same marker grammar, membership in
`closure/agents-md`, and unchanged `project_doc_max_bytes`, `agents-md-size`,
and `agents-md-budget-exceeded` accounting.

The body is the closed template `hd1`. Let `bullet(e, L)` be entry `e`'s prose
for bullet label `L`: the text after `- <L>: `, with every LF and the run of
ASCII spaces and tabs following it replaced by one U+0020, then stripped of
leading and trailing ASCII space and tab. Folding is the caller's job; the
renderer rejects a bullet value that still spans lines. `render_hd1(e)` is
exactly these thirteen lines, with the line breaks shown:

```text
# Hook intent: <e.id>

Codex has no native hook carrier for the `<e.event>` event, so this `<e.class>`
intent is carried as a standing instruction instead of an executable hook.

- Trigger: <bullet(e, Trigger)>
- Purpose: <bullet(e, Purpose)>
- Command: <bullet(e, Command)>
- Environment: <bullet(e, Environment)>
- Failure policy: <bullet(e, Failure policy)>

Follow this instruction whenever the trigger condition holds. Bridge projects
no executable hook for this entry on Codex, so nothing runs automatically.
```

The template admits no whitespace variation and no re-wrapping: both prose
paragraphs break exactly where they break above. All five bullets are carried,
including `Command` and `Environment`, so a reader sees what the executable form
would have been without being told that anything runs. `render_hd1(e)` is then
normalized under N: LF line endings, no trailing whitespace, exactly one final
LF. Compare it with `N(body between markers)`.

The Claude half of degradation needs no write. `.claude/rules/hooks.md` is
itself loaded unconditionally, so a `targets.claude.surface: intent-doc` entry's
own prose already is the Claude standing instruction and Bridge writes nothing
for it.

### Projected handler shape

Both carriers place an array of groups under `hooks.<Event>`. Bridge writes a
group's keys in the order `matcher`, `hooks`, and a handler's keys in the order
`type`, `command`, `commandWindows`, `timeout`, `statusMessage`, then the
Claude-only `shell`, then any carried-forward passthrough key in its original
relative order. `commandWindows` never appears on Claude and `shell` never
appears on Codex, so one closed order serves both carriers.

```json
[
  {
    "matcher": "<effective matcher>",
    "hooks": [
      {
        "type": "command",
        "command": "<effective command>",
        "commandWindows": "<Codex only, when declared>",
        "timeout": 30,
        "statusMessage": "[bridge:<id>]"
      }
    ]
  }
]
```

Omit an optional key when it is undeclared. The handler carries no other key.
The two carriers differ only at their top level:

| Carrier | Top level | Bridge ownership |
|---|---|---|
| `.claude/settings.json` | the project's whole settings object | only the owned group spans inside `hooks` |
| `.codex/hooks.json` | exactly `description` and `hooks`; the host rejects any other top-level key | only the owned group spans inside `hooks` |

`.codex/hooks.json`'s `description` is the user's only metadata slot: Bridge
never writes it, never creates it, preserves an existing value byte-for-byte as
unowned bytes, and never repairs its absence. `.claude/settings.json`'s
`disableAllHooks` is read only for the `hooks-globally-disabled` observation and
is never written. `.claude/settings.local.json` is read only for
`local-hooks-present` and is never a write target.

### Byte-stable projection

A hooks carrier is edited in place and never reserialized.

**Eligibility.** The carrier must be an existing, safe, byte-round-trippable
regular UTF-8 text file that parses as a JSON object under a strict parser with
no duplicate object key anywhere, and whose `hooks` value stays inside the
closed shape: an object of event names, each value an array of group objects,
each group an optional string `matcher` plus a `hooks` array of handler objects.

A handler member whose value is not a string, integer, or boolean stays inside
the closed shape. The inspector reports that member with `scalar: false`, its
bytes are unowned and preserved verbatim, and Bridge never projects such a
member or reads it as a declared field. The motivating case is a Claude
`mcp_tool` handler carrying an `input` object: refusing every hook write in that
carrier would be a worse outcome than reporting the handler and leaving it
alone. A `never-project` handler type is reported, never rewritten, and never a
reason to block the carrier.

`unmodelled-shape` is therefore reserved for a carrier root that is not a JSON
object, a `hooks` value that is not an object, an event value that is not an
array, a group element that is not an object, a non-string `matcher`, a group
without a `hooks` array, a handler element that is not an object, a handler
without a string `type`, and the whole-carrier case of a span scan that
disagrees with the strict parser. A duplicate key or one of those violations
emits `hooks-carrier-unusable` and blocks the closure. Failing closed is
mandatory there: a bridge that guesses which duplicate it owns can silently drop
a user's hook.

**Idempotence law (normative).** `compose(preimage, desired) == preimage`
whenever every owned group already parses equal to its desired model, whatever
its formatting. Semantic handler equality decides the state; byte equality
decides only whether a write happens at all. A plan whose composed postimage
equals its preimage serializes `unchanged`/`unchanged` for that unit, emits no
write-capability row for that path, and emits the informational
`hook-format-preserved`.

**Existing spans.** A changed scalar replaces exactly that scalar token's value
span. An added key is inserted after the enclosing object's last existing
member, using that object's own separator and indent. A removed key removes its
member span plus exactly one separator. Group key order and an unchanged
`matcher` member are never rewritten. Sibling events, sibling groups in the same
event, unrelated top-level keys, the Codex `description`, key order,
indentation, and the file's trailing-newline presence are copied verbatim.

**New spans only.** A group or handler that does not exist yet is rendered
canonically with `style(F)` inferred from the enclosing file. `style(F)` is
closed: indent is 2 spaces, 4 spaces, or 1 tab, inferred from the first member
line of the `hooks` object and defaulting to 2 spaces; the key/value separator
is always `": "`; a handler uses one-line form only when the file already has at
least one one-line handler and no multi-line handler.

**Composition.** The postimage is the preimage with owned spans edited in place
and insertion points filled. Serializing the parsed document is forbidden. The
composed postimage must differ from the preimage only inside located spans, and
the write side re-derives the composition and requires byte equality with the
render operation's post value.

**Region derivation is unchanged.** The `(preimage, postimage)` pair goes to the
same `guarded-patch/v1` rule used for root `AGENTS.md`: one contiguous region
covering every change, extended at code-point boundaries with unchanged context
until its exact old value occurs once in the complete preimage. Hooks JSON is
repetitive, so the region may legitimately swallow adjacent unowned bytes whose
old and new values are identical, or may fail to become unique. Non-uniqueness
emits `guarded-patch-unavailable` and blocks. Context is never shortened to
force a match.

**An absent carrier is never created implicitly.** A missing
`.claude/settings.json` or `.codex/hooks.json` requires `strict-create/v1`,
which is unavailable on both hosts. The unit keeps action `create` with an
unavailable protocol and outcome `blocked`; Bridge neither writes the file with
an unconditional write nor invents a create-after-check, and it writes no Codex
`description` on a create.

### Array ordering discipline

Append-only. Bridge never reorders, sorts, or moves an existing array element,
owned or unowned, because Codex keys per-hook trust and the user's own `/hooks`
disable choice by group index and handler index.

- A newly owned group is appended at the closing bracket of `hooks.<Event>`,
  back-tracked over the trailing whitespace run: `,`, then LF, then the indent
  for that level, then the rendered group.
- A new `hooks.<Event>` member is appended at the closing brace of the `hooks`
  object. It is inserted in byte-wise ascending order among the existing event
  keys only when those keys are already ascending, and appended last otherwise;
  both branches are deterministic.
- A deletion removes the element span plus exactly one adjacent separator comma,
  the preceding one when the element is not first and the following one
  otherwise, together with the whitespace run on that side.
- Emptying an event removes the whole `"<Event>": [...]` member rather than
  leaving an empty array, because Codex trust keys are per event so no other
  event re-indexes.
- Emptying the `hooks` object leaves `"hooks": {}`; removing the key would
  change H-NOFILE semantics.
- Any deletion of a non-final element from an event that retains others emits
  the acknowledged `codex-trust-reindex`.

## Managed skill tree

The canonical unit is the complete Git tree rooted at the immediate directory
`.claude/skills/<name>/`. Its projection is the same relative file set and
bytes under `.agents/skills/<name>/`. This includes
`bridge-intent.yaml`, scripts, references, assets, and an explicitly authored
`agents/openai.yaml`. Bridge never derives a Codex sidecar and never writes
`skills.config`.

Only regular files and ordinary directories are representable. A Git symlink
(mode `120000`), gitlink, filesystem symlink, junction/reparse point, special
file, case-fold collision, or resolved path outside the unit root blocks the
unit. The sentinel reports the blocker; the write-side skill stops and asks.
Empty directories are absent from both the Git tree and byte comparison.
For a current manifest, the case-fold collision domain is the union of
current selected entry paths and tracked-deletion paths. Deduplicate an exact
same-path occurrence, but block distinct spellings such as deleted `Foo` plus
current `foo`; deletion does not release the path name inside this snapshot.

Git modes are part of the tree contract: identity compares relative path,
entry type, raw bytes, and mode. For tracked worktree entries, read the index
mode and the reachable `HEAD` tree mode, then use a POSIX executable-bit probe
when `core.filemode=true` to expose any unstaged mode-only change. When that
probe is unavailable, the index still proves the Git mode of an already
tracked entry, but it cannot prove a worktree-only executable-mode claim.
Historical entries take their mode directly from the selected Git tree.

For a relevant untracked file, no index or historical mode exists. Its mode is
the prospective Git-add mode rather than an existing tree fact. A reliable
POSIX executable-bit probe distinguishes `100644` from `100755`. When that
probe is unavailable on Windows, with `core.filemode=false`, or for another
host reason, an ordinary untracked regular file has the platform-provable
prospective default `100644`; that default is sufficient for create, ordinary
source additions, or an annex decision that explicitly adopts `100644`.

Do not infer executable intent from an unreliable filesystem bit. If a
tracked source, historical tree, or explicit user intent requires `100755`,
the target must already prove `100755` or expose a reliable way to set it.
Otherwise emit `mode-limited` for the proposed write. A direction-neutral
observation, including pending `annex-or-keep` or confirmed `keep`, does not
invent that requirement and is not blocked merely because the occupied file
is untracked. Mode `100755` is writable only when the evidence also proves
the target can preserve it.

## Skill compatibility layers

Byte identity and runtime behavior are separate. Evaluate these four axes
independently:

1. **Agent Skills format**: `SKILL.md` starts on byte one with parseable YAML
   frontmatter; `name` and `description` are non-empty strings; `name` equals
   the directory, is 1–64 characters, uses lowercase ASCII letters, digits,
   and hyphens, and has neither edge nor consecutive hyphens; `description`
   is at most 1024 characters. Standard optional keys are `license`,
   `compatibility`, `metadata`, and `allowed-tools`.
2. **Host runtime loadability**: identity, YAML, BOM, and known loader failures
   are blockers. Unknown live discovery or activation is not a byte state.
3. **Release validator profile**: the pinned Codex authoring validator may
   reject standard-valid `compatibility`, angle brackets in `description`, or
   host extensions. Record `codex-validator-rejection`; do not rewrite the
   source to satisfy a profile silently.
4. **Behavior portability**: `allowed-tools`, Claude-only frontmatter, and
   Claude-rendered dynamic content can remain loadable and are copied
   byte-for-byte, but receive `behavior-degraded`.

No file in a portable master begins with a UTF-8 BOM. The exact lint registry,
blocker mapping, and dynamic-content recognizers are in
[`report-spec.md`](report-spec.md). Lints never turn a changed carrier into a
directional adoption or conflict decision.
