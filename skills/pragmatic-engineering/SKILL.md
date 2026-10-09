---
name: pragmatic-engineering
description: Apply pragmatic engineering practices to TypeScript and JavaScript projects only when the user explicitly invokes pragmatic-engineering or asks to apply this style. Use clear contracts, observable failures, minimal necessary complexity, small changes that can be verified end to end, and the project's existing conventions and delivery path. Do not activate for generic coding or review requests alone.
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

1. Read the applicable project instructions and the relevant implementation,
   including the documentation nearest the changed code and the utilities it
   calls. Treat documented decisions and lessons from past incidents as
   constraints.
2. Identify the runtime: browser, server, worker, command-line tool, or a
   combination. Check module format and supported language/runtime versions.
3. Find existing utilities, validation, logging, configuration, and test
   patterns. Check the declared package manager, lockfiles, and task commands.
   Find the documented delivery path: how changes are built, provisioned,
   migrated, and deployed.
4. When review history is available, check recent maintainer feedback on
   similar changes. Reconcile it with current docs and code, then apply what
   still holds before review rather than after.
5. Define the required behavior, failure behavior, and smallest meaningful
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

Deliver the smallest slice a reviewer can verify end to end. Include only the
setup needed to exercise it, such as the configuration that creates a new
schema locally; a layer too thin to run is unverifiable, not smaller. Agree on
foundational contracts and data models before building infrastructure on
them. Follow the project's stacking policy, and do not present dependent work
as ready before its prerequisite is accepted.

### 2. Make names explain intent

Use the project's vocabulary and naming conventions. Judge names where they
are read, such as imports, logs, search results, and test reports, not only
where they are declared. Qualify a generic noun such as schema, config, or
session when it is ambiguous there; avoid redundant qualifiers otherwise.
Rename an identifier when its meaning changes.

Name events and quantities precisely: `lastSignedInAt` rather than
`lastSeenAt`, `maxWaitMs` rather than `timeout`. If readers have to ask what a
name means, rename it; documenting an unclear name does not fix it.

Do not leave magic numbers or opaque codes in code or tests. When a literal's
meaning is not obvious, as with a limit, duration, size, count, port, or exit
or error code, give it a named constant, preferably one the library or
project already defines, and keep its unit visible:
`const maxWaitMs = 60_000; // 1 minute`. Define each such value once. Values
whose meaning is plain in context, such as 0, 1, or an empty string, need no
name.

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

Scale safeguards to the trust boundary, impact, and privileges involved, not
to habit. Skip ceremony around trusted local fixtures; apply real checks
wherever code handles untrusted input, files, processes, credentials, or
shared resources.

### 4. Make failure behavior explicit

Use the project's error and logging conventions. Preserve error causes and
useful diagnostic context without logging credentials, tokens, or unnecessary
personal data. Unless the project's logger contract says otherwise, keep log
messages static and put dynamic values in structured fields.

Catch an error to handle a known outcome, add useful context, clean up, or
translate it at a boundary. Do not silently catch and continue. Model expected
absence explicitly when it is part of the contract; do not treat every missing
value as either a fatal error or an automatic success.

Report failures at the layer that can act on them. Avoid duplicate logging at
every layer. A warning is appropriate for a recoverable condition, not a
replacement for reporting that the requested operation failed.

When the contract marks a capability optional and continuing leaves a valid
state, report the degradation clearly and continue; do not add a pre-emptive
check that fails the whole operation. Otherwise keep the operation's required
failure or atomicity semantics.

### 5. Respect runtime and module boundaries

Reuse helpers only where their dependencies and side effects are appropriate.
Do not import server-only modules into browser or worker code. Avoid hidden
work at module import time.

Keep environment-specific configuration at explicit boundaries, validate it,
and pass the necessary values inward.

Keep one authoritative definition for enumerations, allowed values,
user-facing strings, and shared configuration. Import it when the dependency
direction and runtime allow; otherwise extract a dependency-neutral module or
generate the copy. Do not duplicate on an assumed constraint; check it first,
and pair any unavoidable copy with an automated drift check. Do not create a
global registry for unrelated values.

Keep production, development, and optional dependencies aligned with their
actual use. Preserve the project's dependency-management workflow. Justify
each dependency override, patch, or unusual pin: what breaks without it, a
link to the advisory or upstream issue, and when it can be removed.

### 6. Choose clear control flow and state ownership

Use ordinary conditions, exhaustive `switch` statements, typed lookup tables,
or an existing matching helper according to the problem and local style.
Do not add a matching library to avoid a readable `switch`.

Use functions for straightforward transformations and operations. Use classes
or objects when they clearly own state, behavior, or a lifecycle. Do not
convert one form to another solely as a style preference.

Pass context explicitly when it clarifies dependencies or capabilities.
Avoid giant context objects that expose everything to every caller.

Each branch that changes behavior needs a reason a reader can see: name the
condition after that reason or add a one-line comment, and remove the branch
if no requirement justifies it. Make the worst case of a wait or retry
visible, and use a deadline when elapsed time is the contract.

### 7. Make effects inspectable when the risk warrants it

Keep observation and mutation distinguishable. For migrations, reconciliation,
or other consequential multi-step operations, consider a non-mutating plan
followed by an explicit apply step. Keep that preview within the project's
delivery path; see principle 8.

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

### 8. Ship through the existing delivery path

Follow the project's documented delivery and approval path. When that path
owns provisioning, migration, or deployment, extend it instead of adding a
parallel script, manual step, or separate bootstrap mode, and make it
initialize what it owns from the project's documented baseline, often an empty
environment. Treat merging as approval to apply only when the project defines
it that way, and preserve any required human-approval boundary. If a manual
step is unavoidable, explain why and agree on it with the maintainers before
building around it.

### 9. Verify the actual requirement

Use the existing test runner, linter, type checker, and build commands. Begin
with the smallest checks covering the change, then expand when the affected
boundaries require it.

Test observable behavior, relevant limits, and failure paths. For intentional
behavior changes, state the new contract and cover it explicitly.

Focus tests on the behavior and uncertainty the change introduces. Do not
transcribe a declaration, such as a schema, constant table, or type, into
assertions field by field. Do not re-prove what a trusted framework or
database already enforces for a declaration, such as a column type,
`NOT NULL`, uniqueness, a default, or a foreign key. One smoke test that the
project's configuration or migrations create what was declared is enough;
test custom constraints, migrations, queries, and failure paths instead. Do
not assert that removed code or UI is gone unless its absence is itself a
requirement. Keep the suite proportional to the risk, and hold test code to
the repository's static-analysis rules.

Make each test readable on its own. Its full title, including enclosing
groups, names the subject and the expected behavior, such as
`parseRetryOptions rejects a negative retryLimit`. Assert the specific outcome
in domain terms, such as the name of the violated rule, rather than a status
or error code that many different failures share.

Do not claim a check passed unless it ran successfully. Distinguish automated
tests, manual inspection, and checks that could not run. Do not add a new test
framework solely to follow this skill.

### 10. Leave useful explanations, not clutter

Document what a user or maintainer needs: usage, contracts, constraints, and
non-obvious decisions. Explain a decision where the reader meets it, not only
in the pull request description: in a comment beside the code or, for formats
without comments such as JSON, in the nearest documentation. Avoid
duplicating details likely to drift, but do not delete useful documentation
merely because it is long or describes structure.

User-facing text is behavior. It must describe what the product actually
does, such as who needs approval or whether deletion is permanent, and it
belongs in the project's string catalog, in the catalog's existing shape.

In review, identify the location, concrete problem, and actionable fix.
Separate correctness issues from optional preferences. Use an exact
replacement suggestion when it makes the correction clearer.

Keep changes independently reviewable. When commits are requested, follow the
repository's commit conventions and explain non-obvious rationale. This skill
does not authorize staging, committing, rewriting history, pushing, deploying,
or publishing.

## Addressing review feedback

- Apply the principle behind each comment across the current change and
  dependent work in scope; a repeated comment means it was applied too
  narrowly. Flag similar cases outside that scope instead of editing them.
- Do what was asked at the scope asked. When a test should be removed, do not
  substitute a heavier one.
- Answer every question, and prefer a change that makes the answer visible in
  the code over an answer that exists only in the thread.
- Prepare a reply for every thread in the reviewer's own register: short,
  plain, first person. "Done" or "Renamed to `lastSignedInAt`" is enough for
  a requested change; answer a question in a sentence or two. Do not restate
  the comment, invent labels for kinds of changes, count tests, narrate CI
  runs, or link to lines on a branch that will move. Do not post replies
  unless authorized; when posting, submit them together as one review.

## Optional architectural guidance

Read the relevant section of [Architecture patterns](references/architecture.md)
only when the task needs it. It covers boundary parsing, finite states, typed
invariants, plan and apply, state ownership, runtime effects, and persisted
data models. Advanced patterns are options with costs, not requirements to
retrofit into every project.

## Final self-check

- Does the change solve the requested problem without unrelated work, as the
  smallest slice that can be verified end to end?
- Does it fit the project's runtime, public contracts, conventions, and
  delivery path?
- Are invalid input, expected absence, and unexpected failure distinguishable,
  with severity that matches the contract?
- Is each added abstraction, guard, copy, or dependency earning its cost?
- Would a reader have to ask what a name, literal, or code means, or why a
  branch, override, or test exists?
- Do the tests cover logic the change owns, and were the relevant behavior
  and failure paths actually verified?
- Does every review thread have a resolution, with its principle applied in
  scope?
- Are any remaining risks or unverified checks stated accurately?
