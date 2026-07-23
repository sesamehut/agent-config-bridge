---
name: fixture-dynamic-content
description: Inert fixture covering Claude dynamic content; do not invoke.
arguments:
  - name: target
    description: Inert fixture argument
---

This skill is an inert bridge mutation fixture. Every command-like form below
is inert fixture text and must never be executed.

Arguments: $0, $ARGUMENTS[12], and $target.

Inline fixture command: !`printf 'inert inline fixture'`

    !`printf 'inert indented fixture'`

```!
printf '%s\n' 'inert fenced fixture'
```
