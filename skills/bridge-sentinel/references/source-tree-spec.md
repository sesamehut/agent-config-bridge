# Bridge source-tree specification

Spec version: source-tree/v4.

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
- [Hook ownership](#declared-keys-and-ownership-derivation)
- [Projected handler shape](#projected-handler-shape)
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
  `hooks/<entry-id>` and produces one row per declared target host. Pair it
  with its owned `(event, matcher)` group in `.claude/settings.json` or
  `.codex/hooks.json`. Matcher absence matches only absence. Also enumerate
  handlers whose `statusMessage` begins `[bridge:` for orphan detection.
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

## Onboarding anchor

Evaluate onboarding once per project. A persistent, versioned two-part
covenant anchor replaces inference from coincidental carrier equality:

1. source half: tracked `.claude/rules/bridge-covenant.md`, byte-equal to the
   current `covenant/v2` source template; and
2. projection half: a tracked, well-formed root `AGENTS.md` block whose id is
   `rules/bridge-covenant` and whose source attribute is
   `.claude/rules/bridge-covenant.md`, with body byte-equal after N to the
   current `covenant/v2` projection template.

Both templates declare `covenant/v2`, `source-tree/v4`, `report/v4`,
`reconciliation/v2`, and `sync-plan/v2`. Bootstrap installs both halves in
one confirmed write. The project is **onboarded** only while both halves are
present, schema-valid, version-equal, and template-valid. If neither exists,
it is **not-onboarded**. A partial, malformed, modified, untracked, or
version-mismatched anchor is **blocked**, not a degraded onboarding signal.
Contract upgrades use an explicit migration plan; they are never ordinary
content drift. The exact former `covenant/v1` templates are retained under
`templates/covenant/v1/` only as migration evidence. Runtime scanning supports
only the current tuple: an old exact pair is read-only onboarding `blocked`
and write-side `contract-migration`, never an alternate readable contract.
The write side must carry every reachable-v1 proven managed unit through the
closed-set migration transition defined by `reconciliation/v2`, or record an
explicit per-unit release/repair decision. Merely replacing the covenant
bytes does not establish current-tuple ownership.

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
not part of v4; a legacy-looking start line containing `mode=` is a blocking
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
3. Strip the contiguous v4 control-comment header defined below.
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
<!-- bridge:covenant covenant/v2 source-tree/v4 report/v4 reconciliation/v2 sync-plan/v2 -->
```

followed by its exact intent record. Changed, missing, reordered, or unknown
tuple fields are an anchor anomaly. The former v1 YAML template is recognized
only by byte equality to the archived migration evidence.

### Rule-shard `paths` frontmatter

A v4 rule shard either has no frontmatter (unscoped) or has a YAML map whose
only key is `paths`. `paths` must be a non-empty list of unique strings.
Preserve list order; do not normalize or reorder globs. Bridge-specific
metadata never appears in YAML.

Every pattern must be non-empty after ASCII-whitespace inspection, valid
UTF-8, repo-relative, and use `/`. It may not contain NUL, CR, LF, a
backtick, a backslash, an empty/dot/dot-dot path segment, an unclosed bracket
expression, or a leading `/`. Exact patterns `**` and `**/*` are no-op
universal scopes and are invalid in v4; use an unscoped shard instead.
Duplicates are also no-op and block the unit.

Brace expansion is evaluated for the whole list under Claude's shared limit
of 1,000 expanded patterns and 4 MiB of expanded UTF-8 pattern bytes. If any
pattern is invalid, or the list cannot be proven to remain within both
limits, the unit is blocked. An over-budget pattern must not be rendered as
its literal unexpanded braces, because that would silently change the source
scope. Do not infer no-op from the current repository having no matching
file; v4's no-op set is the exact universal/duplicate set above.

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

`.claude/rules/hooks.md` has no YAML frontmatter; future file-level Bridge
intent uses the same controlled HTML comments. It loads unconditionally.
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
exactly `Trigger`, `Purpose`, `Command`, `Environment`, and `Failure policy`;
their prose does not affect consistency.

Machine fields:

| Field | Type | Req | Meaning / constraints |
|---|---|---|---|
| `id` | string | required | equals the heading id; `[a-z0-9-]`, starting alphanumeric; unique |
| `event` | string | required | exact-case host event; unknown names remain valid |
| `matcher` | string | optional | omission means no projected `matcher` key and matches only omission; otherwise use the string normalization below |
| `command` | string | required unless both targets are tier-4 | the command line |
| `commandWindows` | string | optional | Codex-only Windows branch; compare only on the Codex surface |
| `timeout` | integer | optional | seconds; projected iff declared and equal as an integer |
| `enabled` | boolean | required | `false` expects no handler on any target surface |
| `targets` | map | required | contains exactly `claude` and `codex` |
| `targets.claude.surface` | enum | required | `settings-json` → `.claude/settings.json` top-level `hooks`; or `none` |
| `targets.codex.surface` | enum | required | `codex-hooks-json` → `.codex/hooks.json` top-level `hooks`; or `none` |
| `targets.<host>.tier` | enum | required | `native` or `declared-unsynced`; `declared-unsynced` iff surface is `none` |
| `intent` | list of {date, note} | optional | entry-local intent records |

`structural`, `semantic`, and surface `agents-md` are reserved and invalid in
v4. The fenced block must be valid YAML; quote scalars when YAML requires it.
Comparisons use parsed scalar values.

Schema violations include a missing or mislabeled prose bullet, a missing or
invalid machine field, heading/id mismatch, zero or multiple `yaml` blocks,
unknown or reserved enum values, tier/surface mismatch, duplicate ids, and duplicate
`(event, matcher, host)` declarations. YAML parse failure counts as one
violation for its section. Every entry sharing a duplicate id or ownership
declaration is invalid. An invalid entry emits no unit row and emits one
`intent-doc-anomaly` per violation.

### Declared keys and ownership derivation

The intent document is the sole ownership declaration. For host `h`, owned
groups are exactly the `(event, matcher)` pairs from valid entries whose
`targets.<h>.surface` is not `none`.

For equality, strip leading and trailing ASCII whitespace from string fields,
then compare code points. Compare `timeout` as an integer and require `type`
to equal `command`. Matcher absence matches only absence.

Allowed handler keys are `{type, command}`, plus:

- `commandWindows` on Codex only, iff declared;
- `timeout` iff declared;
- optional `statusMessage` iff it begins `[bridge:<entry-id>]`.

Claude ignores the source `commandWindows` field; a projected Claude
`commandWindows` key remains undeclared. `matcher` belongs to the group, not
the handler. Any other handler key is undeclared.

The optional `[bridge:<entry-id>]` status prefix reinforces attribution but
does not establish ownership. Another `statusMessage` value is undeclared. A
`[bridge:<id>]` marker without a valid entry produces H-MARKED-ORPHAN.
Projection SHOULD add the marker on both hosts; ownership remains
intent-derived.

### Projected handler shape

Both projection files place an array of groups under `hooks.<event>`:

```json
[
  {
    "matcher": "<matcher>",
    "hooks": [
      {
        "type": "command",
        "command": "<command>",
        "commandWindows": "<Codex-only, when declared>",
        "timeout": 30,
        "statusMessage": "[bridge:<id>]"
      }
    ]
  }
]
```

Omit optional keys when undeclared. The handler contains no other keys.
`.codex/hooks.json` may also contain a top-level `description` string, which
the sentinel ignores.

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
