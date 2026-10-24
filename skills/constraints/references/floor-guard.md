# Floor guard

Every numbered dimension in CONSTRAINTS.md maps to a de facto tool. The floor
does not: it is a diff-scoped check for the five moves in Step 6. Without a
shipped implementation, every agent writes its own, and two runs (or a Python
repository and a Go one) end up with two different guards. The script in
[`../scripts/floor-guard.mjs`](../scripts/floor-guard.mjs) is that
implementation. Copy it into the project and adapt its patterns; keep the
contract.

## Usage

```sh
node scripts/floor-guard.mjs                    # diff against origin/HEAD, else origin/main
node scripts/floor-guard.mjs --base origin/dev  # explicit base
node scripts/floor-guard.mjs --hook             # Claude Code Stop hook
```

Requires Node.js 18 or later and git. It installs nothing.

## Contract

- **Input:** the diff between the merge base and the working tree, with added
  and removed lines, plus untracked files. A guard that reads only `git diff`
  misses new files.
- **Detects:** a weakened, changed, or removed threshold in CONSTRAINTS.md; a
  test made easier (`.skip`, a deleted test file, an assertion removed from a
  test that stayed); a new suppression comment; unfinished work (a stub, an
  empty `catch`, a `TODO`); a new Exceptions row.
- **Tightening is silent, loosening is loud:** a raised threshold or a removed
  exception is not reported.
- **Never prints a matched secret value.** Findings show the rule, the file, and
  at most 120 characters of the line.
- **Exempt from the pattern checks:** Markdown and other prose files, which can
  name a suppression without applying one (CONSTRAINTS.md lists them all), and
  the guard's own source. CONSTRAINTS.md is still checked for weakened rules and
  new exceptions.

## Exit codes

| Result | Default (CI, terminal) | `--hook` (Claude Code) |
|---|---|---|
| Clean | 0 | 0, silent |
| Violation | 1 | 2: findings go to Claude, which keeps working |
| Violation again after a retry (`stop_hook_active`) | — | 1: shown to the user, no loop |
| Cannot run (not a repository, no merge base) | 2 | 1: shown to the user, does not block |

"Cannot run" never reads as clean. In hook mode it does not block, because a
broken git setup should reach the person, not trap the agent.

## Adapting it

- **Patterns are the only stack-specific part.** Add your language's
  suppression, stub, and skip forms to the `SUPPRESSIONS`, `STUBS`, and `SKIPS`
  expressions. The diff plumbing, the CONSTRAINTS.md checks, and the exit codes
  stay as they are.
- **Exempt a path deliberately.** If a generated or vendored path trips the
  patterns, extend `isExempt` or add a `.constraintsignore` (one glob per line)
  and check each file against it, so the exception is a tracked file, not a
  loosened rule.
- **Renames read as removals.** Rename a rule in one commit and change its
  thresholds in another, or the guard reports the old rule as removed.
- **It is regex-shallow on purpose.** It catches the cheap road to green that
  agents actually take, not a determined person hiding a change. That is the
  right trade for a check that runs on every turn. When it is outgrown, move to a
  dedicated runner.
- **Tests:** `node --test skills/constraints/scripts/floor-guard.test.mjs` in
  this repository covers each detection, the docs exemption, and both exit-code
  modes.
