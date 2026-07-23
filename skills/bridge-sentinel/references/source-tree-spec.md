# Bridge source-tree specification

Spec version: source-tree/v3.

This file defines source units, onboarding, markers, rendering, intent
records, hook ownership, and skill portability. Its companion,
[`report-spec.md`](report-spec.md), defines inputs, findings, observations,
and report comparison. Rules consume the filtered tracked files called
**repo bytes** in that companion, except its exact untracked covenant-path
safety check.

## Contents

- [Unit model](#unit-model)
- [Onboarding anchor](#onboarding-anchor)
- [Marker grammar](#marker-grammar)
- [Applicability preamble and rendering pipeline](#applicability-preamble-and-rendering-pipeline)
- [Normalization set N](#normalization-set-n-exact-closed)
- [Frontmatter schemas and entry formats](#frontmatter-schemas-and-entry-formats)
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
  `.claude/CLAUDE.md`, and exists only when one of them exists. If both exist,
  root wins and emit
  `dual-project-entry`. Add one unit for each tracked
  `.claude/rules/**/*.md` except `.claude/rules/hooks.md`; its id is
  `rules/<path below .claude/rules without .md>`. Pair units with root
  `AGENTS.md` managed blocks by `id`.
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

Evaluate onboarding once per project. M2 replaces inference from coincidental
carrier equality with a persistent, versioned two-part covenant anchor:

1. source half: tracked `.claude/rules/bridge-covenant.md`, byte-equal to the
   `covenant/v1` source template; and
2. projection half: a tracked, well-formed root `AGENTS.md` block whose id is
   `rules/bridge-covenant` and whose source attribute is
   `.claude/rules/bridge-covenant.md`, with body byte-equal after N to the
   `covenant/v1` projection template.

Both templates declare `covenant/v1`, `source-tree/v3`, `report/v3`,
`reconciliation/v1`, and `sync-plan/v1`. Bootstrap installs both halves in
one confirmed write. The project is **onboarded** only while both halves are
present, schema-valid, version-equal, and template-valid. If neither exists,
it is **not-onboarded**. A partial, malformed, modified, untracked, or
version-mismatched anchor is **blocked**, not a degraded onboarding signal.
Contract upgrades use an explicit migration plan; they are never ordinary
content drift.

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
managed-start     = "<!-- bridge:managed:start id=" unit-id " source=" source-path [" mode=" mode-token] " -->"
managed-end       = "<!-- bridge:managed:end -->"
claude-only-start = "<!-- bridge:claude-only:start -->"
claude-only-end   = "<!-- bridge:claude-only:end -->"
```

Exactly one U+0020 between every token shown; no tabs; no other attributes;
attribute order is `id`, `source`, then optional `mode`. Absent `mode` means
verbatim mode.

### Attribute charsets

```
unit-id     = seg *("/" seg)          ; seg = 1*[A-Za-z0-9._-]
source-path = seg *("/" seg)          ; same seg charset; repo-root-relative,
                                      ; "/" separators, no "./" prefix
mode-token  = [a-z][a-z0-9-]{0,15}    ; absence of the attribute = verbatim mode
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
   only in `CLAUDE.md` (or `.claude/CLAUDE.md`) and `.claude/rules/*.md`
   and are recognized under the same rules.
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
| Block `source` differs from the path derived from `id` | Pair by authoritative `id` |
| Duplicate `id` | Pair the first; report later blocks as A4 with unit `<id>#<ordinal>` in file order |
| Claude-only start unclosed at EOF | Subtract nothing; retain the start and following content |

## Applicability preamble and rendering pipeline

### Preamble sentence template (versioned `pv1`)

For a rule shard with globs g1…gn in frontmatter order:

```
Applies only when working on files matching: <G>. (bridge:pv1)
```

`<G>` is each glob wrapped in single backticks and joined by `, `. The line,
including `(bridge:pv1)`, admits no other whitespace variation.

### Applicability

Render the preamble only when `paths` is a non-empty list of strings. The
entry unit, unscoped shards, and invalid or empty `paths` values render no
preamble or separator; note an empty or invalid value free-form.

### Rendering pipeline

Throughout this specification, frontmatter is recognized only when the first
line is exactly `---` and a later full line is exactly `---`. An unclosed
block is content.

For an agents-md unit `u`, `render(u)`:

1. Take the source file's literal tracked bytes. For the entry unit this is
   the entry file itself; do not expand `@path` imports.
2. Strip recognized YAML frontmatter, including both delimiter lines.
3. Subtract claude-only segments: remove all lines from each recognized
   start through its end, inclusive.
4. Strip leading blank lines.
5. Apply normalization N (defined below).
6. If applicable, prepend the preamble and exactly one empty line.

The projected block is:

```
<managed-start line for u>
<render(u)>
<managed-end line>
```

Compare `N(body between markers)` with `render(u)`. An `@AGENTS.md` import
remains literal and also emits `self-referential-import`. Claude-only segments
are the sole subtraction mechanism; rewritten projection text compares as
drift.

A leading UTF-8 BOM is content and prevents frontmatter recognition. Only
skill-lint computation skips it, as defined in `report-spec.md`.

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

## Frontmatter schemas and entry formats

### Intent-record format

One record is `{date: valid YYYY-MM-DD calendar date, note: single-line
string}`. Keep records oldest first. Append a record for initial onboarding or
annexation and whenever a semantic source intent changes. A byte-for-byte
mechanical reprojection does not append a record. Records are arbitration and
report evidence only; they follow normal byte comparison when part of a
compared unit and never override decision-table state, action, or onboarding.

A root entry record, when needed, is a full line at the file top:
`<!-- bridge:intent <YYYY-MM-DD> <single-line note> -->`. The same grammar is
reserved as a rule-shard fallback but is not active for rule shards in v3.

### Rule-shard frontmatter (`.claude/rules/*.md`)

```yaml
---
paths:                # optional list of glob strings
  - "docs/**/*"
bridge:               # optional map
  intent:             # required when bridge is present
    - date: 2026-07-08
      note: one-line motivation
---
```

`paths` is the host-native rules key. In v3, `bridge` frontmatter is the
rule-shard intent carrier and the sole bridge-added key;
its `intent` value is a list of intent records, with notes recommended at no
more than 120 characters. Ignore reserved unknown `bridge` subkeys.
The entry file (`CLAUDE.md` or `.claude/CLAUDE.md`) has no frontmatter.

The single covenant shard `.claude/rules/bridge-covenant.md` additionally
requires this exact map inside `bridge`:

```yaml
covenant:
  version: covenant/v1
  source_tree: source-tree/v3
  report: report/v3
  reconciliation: reconciliation/v1
  sync_plan: sync-plan/v1
```

The covenant is immutable infrastructure. Unknown, missing, or changed
covenant fields are an anchor anomaly and require migration or repair, not a
normal rule-shard intent update.

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

`.claude/rules/hooks.md` may use `bridge` frontmatter but not `paths`; it loads
unconditionally. Each entry has a heading, five prose bullets, and one fenced
`yaml` block:

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
v3. The fenced block must be valid YAML; quote scalars when YAML requires it.
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
`agents/openai.yaml`. M2 never derives a Codex sidecar and never writes
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
