# Bridge source-tree specification

Spec version: source-tree/v2.

This file defines source units, onboarding, markers, rendering, intent
records, hook ownership, and skill portability. Its companion,
[`report-spec.md`](report-spec.md), defines inputs, findings, observations,
and report comparison. All rules consume the filtered tracked files called
**repo bytes** in that companion.

## Contents

- [Unit model](#unit-model)
- [Onboarding predicate](#onboarding-predicate)
- [Marker grammar](#marker-grammar)
- [Applicability preamble and rendering pipeline](#applicability-preamble-and-rendering-pipeline)
- [Normalization set N](#normalization-set-n-exact-closed)
- [Frontmatter schemas and entry formats](#frontmatter-schemas-and-entry-formats)
- [Skill intent supporting file](#skill-intent-supporting-file)
- [Hook intent document](#hook-intent-document)
- [Hook ownership](#declared-keys-and-ownership-derivation)
- [Projected handler shape](#projected-handler-shape)
- [Skill portability requirements](#skill-portability-requirements)

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
  tracked `SKILL.md` is unit `<name>`. Pair it with the same-name immediate
  directory under `.agents/skills/` when that directory also contains a
  tracked `SKILL.md`. Directories without `SKILL.md` are not units.

A would-be source path outside the source-path grammar is not a unit; emit
`unrepresentable-source-path`. Each surface that otherwise has no rows emits
exactly `(surface, -, -, no-source-unit, -, -, -)`.

## Onboarding predicate

Evaluate onboarding once per project. The project is **onboarded** when any
trigger holds over repo bytes:

| Trigger | Evidence |
|---|---|
| a | Root `AGENTS.md` contains a well-formed managed block outside code fences. |
| b | A schema-valid hook entry targeting a non-`none` surface has an owned `(event, matcher)` group with a command handler, regardless of field equality; or either hooks file contains a handler whose `statusMessage` begins `[bridge:`. |
| c | A `.agents/skills/<name>/` copy and its `.claude/skills/<name>/` master have identical relative file sets and raw bytes. |
| d | `.claude/rules/bridge-covenant.md` exists. |

Otherwise the project is **not-onboarded**: missing projections are
`not-projected`, existing unmanaged content is `adoption-candidate`, and no
row is `drift`. In an onboarded project, a missing source projection is
`drift`/`reproject-from-source`.

The predicate is project-level. Intent records do not trigger it. A diverged
same-name skill pair does not satisfy trigger c; if c was the only trigger,
divergence changes the project to not-onboarded and yields a master
`not-projected` row plus a copy `adoption-candidate` row.

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
string}`. Keep records oldest first and append one in the same change whenever
a source entry changes. They are arbitration and report evidence only; they
follow normal byte comparison when part of a compared unit and never override
decision-table state, action, or onboarding.

A root entry record, when needed, is a full line at the file top:
`<!-- bridge:intent <YYYY-MM-DD> <single-line note> -->`. The same grammar is
reserved as a rule-shard fallback but is not active for rule shards in v2.

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

`paths` is the host-native rules key. In v2, `bridge` frontmatter is the
rule-shard intent carrier and the sole bridge-added key;
its `intent` value is a list of intent records, with notes recommended at no
more than 120 characters. Ignore reserved unknown `bridge` subkeys.
The entry file (`CLAUDE.md` or `.claude/CLAUDE.md`) has no frontmatter.

### Skill intent supporting file

A skill master that carries intent history stores it at
`<skill-directory>/bridge-intent.yaml`:

```yaml
intent:
  - date: 2026-07-23
    note: One-line motivation
```

`intent` is the only defined top-level key. The file is copied byte-for-byte
with the skill and read only as bridge evidence. Do not add `bridge` to
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
v2. The fenced block must be valid YAML; quote scalars when YAML requires it.
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

## Skill portability requirements

Every skill master `.claude/skills/<name>/` must satisfy:

- `SKILL.md` has a YAML frontmatter block present from line 1;
- the frontmatter carries `name` and `description` as non-empty strings;
- `name` equals the directory name, is 1–64 characters, uses only
  lowercase ASCII letters, digits, and hyphens, does not begin or end with a
  hyphen, does not contain consecutive hyphens, and does not contain the
  reserved words `anthropic` or `claude`;
- `description` is at most 1024 characters and contains neither `<` nor `>`;
- the frontmatter uses only the cross-host keys `name`, `description`,
  `license`, `metadata`, and `allowed-tools`;
- no file in the master directory begins with a UTF-8 BOM.

The Agent Skills `compatibility` key receives `codex-validator-gap` because
the v2 Codex validator profile rejects it. Other keys outside the five-key
set, including Claude-specific keys, receive
`implementation-specific-frontmatter`. Dynamic body features and violations
above produce the lints defined in `report-spec.md`; lints do not change
projection state.
