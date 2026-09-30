---
name: pragmatic-engineering
description: Apply pragmatic engineering practices to TypeScript and JavaScript projects only when the user explicitly invokes pragmatic-engineering or asks to apply this style. Use clear contracts, observable failures, minimal necessary complexity, and the project's existing conventions. Do not activate for generic coding or review requests alone.
disable-model-invocation: true
---

# Pragmatic Engineering

Solve the actual problem with the smallest design that remains correct,
understandable, and verifiable. Make important decisions explicit, not every
implementation elaborate.

## Activation and scope

Use this skill only when the user names `pragmatic-engineering` or explicitly
asks for this engineering style. A generic request to write, debug, review,
refactor, or commit code is not an activation trigger.

Example requests:

- "Use pragmatic-engineering to implement this change."
- "Review this code using the pragmatic-engineering style."
- "Apply this pragmatic engineering approach to the refactor."

This is guidance for TypeScript and JavaScript, not a mandatory framework.
Explicit task requirements and the current project's applicable instructions,
contracts, and runtime constraints take precedence. Raise a conflict instead
of silently overriding them.

Do not use this skill as permission to migrate a JavaScript project to
TypeScript, replace its architecture, or perform unrelated cleanup. Honor
explicit prototype boundaries without hiding errors or taking unsafe actions.

## Start with the project

Before changing code:

1. Read the applicable project instructions and the relevant implementation.
2. Identify the runtime: browser, server, worker, command-line tool, or a
   combination. Check module format and supported language/runtime versions.
3. Find existing utilities, validation, logging, configuration, and test
   patterns. Check the declared package manager, lockfiles, and task commands.
4. Define the required behavior, failure behavior, and smallest meaningful
   verification. Ask about consequential ambiguity rather than guessing.

Use the repository's commands and directory conventions. Do not introduce a
runner, package manager, library, lifecycle hook, or compatibility layer just
to satisfy this skill.

## Core principles

### 1. Keep the change focused and complete

Fix the underlying problem across the surfaces it actually affects. Preserve
unrelated behavior and user changes. Remove code made obsolete by this change,
not everything that could be improved nearby.

Start with a direct implementation. Extract a helper when it expresses a useful
domain operation, removes meaningful duplication, or protects an invariant.
Do not build for hypothetical future consumers.

### 2. Make names explain intent

Use the project's vocabulary and naming conventions. Include scope when it
resolves real ambiguity; do not repeat context already clear from a module or
type. Rename an identifier when its meaning changes.

Distinguish observation from mutation in the API. If a name promises
idempotency, such as `ensure`, make the behavior genuinely idempotent. Names
alone do not establish purity or idempotency.

### 3. Validate at trust boundaries

Treat external input as untrusted until its relevant structure and constraints
have been checked. Reuse the project's schemas, parsers, or type guards. Keep
validated values typed inside the system rather than repeatedly casting them.

In TypeScript, `as` and non-null assertions are not runtime validation. A
narrow, justified assertion may encode an invariant already established by a
check; it must not conceal an unchecked assumption.

In JavaScript, use the same runtime checks and the project's existing JSDoc or
type-checking practices. Do not require a language migration.

Normalize data only when the contract defines that meaning. Do not turn a
failed parse into an empty result, `false`, or another success-shaped default.

### 4. Make failure behavior explicit

Use the project's error and logging conventions. Preserve error causes and
useful diagnostic context without logging credentials, tokens, or unnecessary
personal data.

Catch an error to handle a known outcome, add useful context, clean up, or
translate it at a boundary. Do not silently catch and continue. Model expected
absence explicitly when it is part of the contract; do not treat every missing
value as either a fatal error or an automatic success.

Report failures at the layer that can act on them. Avoid duplicate logging at
every layer. A warning is appropriate for a recoverable condition, not a
replacement for reporting that the requested operation failed.

### 5. Respect runtime and module boundaries

Reuse helpers only where their dependencies and side effects are appropriate.
Do not import server-only modules into browser or worker code. Avoid hidden
work at module import time.

Keep environment-specific configuration at explicit boundaries, validate it,
and pass the necessary values inward. Centralize shared configuration when
there is a genuine single source of truth; do not create a global registry for
unrelated values.

Keep production, development, and optional dependencies aligned with their
actual use. Preserve the project's dependency-management workflow.

### 6. Choose clear control flow and state ownership

Use ordinary conditions, exhaustive `switch` statements, typed lookup tables,
or an existing matching helper according to the problem and local style.
Do not add a matching library to avoid a readable `switch`.

Use functions for straightforward transformations and operations. Use classes
or objects when they clearly own state, behavior, or a lifecycle. Do not
convert one form to another solely as a style preference.

Pass context explicitly when it clarifies dependencies or capabilities.
Avoid giant context objects that expose everything to every caller.

### 7. Make effects inspectable when the risk warrants it

Keep observation and mutation distinguishable. For migrations, reconciliation,
or other consequential multi-step operations, consider a non-mutating plan
followed by an explicit apply step.

A simple, well-tested `dryRun` branch can be sufficient for a small tool. Test
that preview mode performs no writes; do not infer that from a flag or type.
Do not introduce capability types or deferred operations without a concrete
benefit.

Prefer structured APIs over shell command strings. When invoking a process,
use a trusted executable and separate arguments with shell interpretation
disabled where possible. Check option semantics and exit status.

For paths derived from external input, enforce the intended filesystem
boundary with runtime-appropriate checks, including the symlink policy.
A string prefix test alone is not a complete containment guarantee.

### 8. Verify the actual requirement

Use the existing test runner, linter, type checker, and build commands. Begin
with the smallest checks covering the change, then expand when the affected
boundaries require it.

Test observable behavior, relevant limits, and failure paths. For intentional
behavior changes, state the new contract and cover it explicitly.

Do not claim a check passed unless it ran successfully. Distinguish automated
tests, manual inspection, and checks that could not run. Do not add a new test
framework solely to follow this skill.

### 9. Leave useful explanations, not clutter

Document what a user or maintainer needs: usage, contracts, constraints, and
non-obvious decisions. Keep comments near the code they explain. Avoid
duplicating details likely to drift, but do not delete useful documentation
merely because it is long or describes structure.

In review, identify the location, concrete problem, and actionable fix.
Separate correctness issues from optional preferences. Use an exact
replacement suggestion when it makes the correction clearer.

Keep changes independently reviewable. When commits are requested, follow the
repository's commit conventions and explain non-obvious rationale. This skill
does not authorize staging, committing, rewriting history, pushing, deploying,
or publishing.

## Optional architectural guidance

Read the relevant section of [Architecture patterns](references/architecture.md)
only when the task needs it. Advanced patterns are options with costs, not
requirements to retrofit into every project.

## Final self-check

- Does the change solve the requested problem without unrelated work?
- Does it fit the project's runtime, public contracts, and conventions?
- Are invalid input, expected absence, and unexpected failure distinguishable?
- Is each added abstraction or dependency earning its cost?
- Were the relevant behavior and failure paths actually verified?
- Are any remaining risks or unverified checks stated accurately?
