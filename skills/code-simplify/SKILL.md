---
name: code-simplify
description: Simplify recently changed code for clarity while proving its behavior did not change. Checks why code exists before removing it, treats any test that must change as a behavior change, and stays conservative where no test covers the code. Use only when the user invokes code-simplify or explicitly asks for a behavior-preserving simplification pass. Complements Claude Code's built-in /simplify rather than replacing it.
disable-model-invocation: true
argument-hint: "[path, glob, or git range; defaults to the current changes]"
license: MIT. See LICENSE.
---

# Code Simplify

> Adapted from `code-simplification` in [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT), which was itself inspired by Anthropic's [code-simplifier](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/code-simplifier) agent. Rewritten for Claude Code. See [LICENSE](LICENSE).

Make code faster to read, change, and debug without changing what it does.
Fewer lines is not the goal. A reader understanding the code sooner is.

Claude Code's built-in `/simplify` looks for reuse, simplification, and
efficiency cleanups in a diff. This skill is narrower: it is the contract that
makes a simplification safe to accept. Where the two overlap, follow the
behavior and verification rules here.

## Scope

Requested scope: $ARGUMENTS

If no scope is given above, work on the code changed on this branch: the diff
against the merge base with the default branch, plus uncommitted and untracked
files. (In hosts that do not substitute arguments, take the scope from the
user's request.) Do not widen the scope on your own. A drive-by refactor of
untouched code is diff noise and risk nobody asked for; list worthwhile
candidates outside the scope at the end instead.

## The contract: behavior stays identical

Same result for every input, same errors and error types, same side effects in
the same order, same public names, types, and exports. If you cannot convince
yourself a change preserves all of that, do not make it.

These look like simplifications and are not:

- `x || fallback` in place of an explicit `null`/`undefined` check (or `??`):
  `0`, `''`, and `false` now take the fallback.
- Dropping `return await` inside `try`: rejections are no longer caught there.
- A different result shape: an object becomes a `Map`, an array becomes an
  iterator, a `null` becomes `undefined`.
- An async `forEach` turned into `for...of`, or the reverse: concurrency changes.
- Reordering conditions or calls that have side effects or short-circuit.
- Inlining a function that tests mock or spy on, or that another package
  imports.
- Removing "dead" code that is reached through dynamic imports, string-based
  dispatch, reflection, configuration, or a public export.

## Before removing anything, find out why it exists

Odd code often encodes a bug fix, a platform quirk, or a performance
constraint. For anything you are about to delete or restructure:

1. Find every caller, including dynamic and string references and exports used
   outside the package.
2. Read the history of those lines (`git log -L <start>,<end>:<file>` or
   `git blame`) and the commit or pull request that introduced them.
3. If the history explains the code, keep it, and add the missing "why" comment
   if that is the real problem. If nothing explains it and no test covers it,
   leave it and name it in the report.

## Know what proves behavior before you edit

Find the tests that exercise the target code and run them once for a green
baseline.

- **Covered code.** The tests are your evidence. A simplification that needs a
  test edited to pass has changed behavior: revert the simplification, do not
  edit the test. If the test itself is wrong, stop and raise it with the user.
- **Uncovered code.** "Tests pass" proves nothing here. Either add a small
  characterization test that pins the current behavior first, and call it out
  in the report as the evidence, or limit yourself to transformations a tool can
  verify: renames through the language server, removing bindings the compiler
  or linter reports as unused, guard-clause inversions the type checker still
  accepts. Say in the report that the code was uncovered.

## What is worth changing

Good targets: nesting that guard clauses flatten, a function doing several jobs,
nested ternaries, boolean flag parameters, the same block repeated several
times, wrappers that add nothing, names that misstate what the code does,
comments that restate the code (keep the ones that explain why), confirmed dead
code.

Leave alone, or revert if you already did it:

- Inlining a helper whose name carried meaning.
- Merging two simple functions into one complex one.
- Removing an abstraction that exists for testability or a real second
  implementation.
- Compressing readable code into dense one-liners.
- Replacing the project's conventions (CLAUDE.md, neighboring code) with your
  preferences.
- Removing or weakening error handling.

## Working loop

- Order changes by risk. Mechanical, tool-checked changes can go together.
  Anything that touches control flow, error paths, or data shapes goes one at a
  time.
- After each risky change, run the narrowest tests that cover it and the type
  checker. Run the relevant suite, lint, and build once at the end.
- If a check fails after a change, revert that change rather than patching
  around it.
- For more than a few hundred mechanical edits, use the language server,
  `ast-grep`, or a codemod, not hand edits or regex replacement.
- Keep simplification out of feature and fix commits. If the user asks you to
  commit, commit it separately. Do not create branches or pull requests for it
  unless asked.

## Report

End with:

- What changed, grouped by kind.
- The evidence for each group: which tests, type check, or tool verified it.
- What you deliberately left alone and why: unexplained code, uncovered code,
  changes that did not read better on a second look.
- Candidates outside the requested scope.
