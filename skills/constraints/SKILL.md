---
name: constraints
description: Write a project's quality bar down as CONSTRAINTS.md and enforce it while the agent works, so it is not quietly lowered. Interviews the user on which dimensions matter, supplies sane default thresholds when they have no number in mind, installs the de facto tool for each dimension, wires checks into Claude Code hooks, and watches the diff for a weakened bar such as new @ts-ignore or eslint-disable suppressions, skipped or deleted tests, removed assertions, unimplemented stubs, or thresholds edited down. Use when no quality bar is written down, when the user says "set up constraints" or "define our standards", when accessibility, web performance, or coverage should become enforced constraints, when an agent keeps silencing checks or skipping tests to get to green, or when a coverage or performance threshold is needed and nobody knows what number to pick.
argument-hint: "[check | guard | ratchet]"
allowed-tools:
  - Bash(node ${CLAUDE_SKILL_DIR}/scripts/floor-guard.mjs *)
  - Bash(node scripts/floor-guard.mjs *)
license: MIT. See LICENSE.
---

# Constraints

> Adapted from `constraint-driven-development` in [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT). Rewritten for Claude Code: checks run in hooks, the bar is protected by a permission rule, and the floor guard ships as a tested script. Sections marked **Claude Code** use harness features; other agents use the written file, the scripts, and CI. See [LICENSE](LICENSE).

An agent writes more in an afternoon than anyone reads in a week, so judgment
has to move out of the reviewer's head into checks. Those checks need numbers
the team actually chose, and they need to fire close enough to the work that
the agent fixes its own output. Instructions an agent reads are the weakest
form of that; a hook that blocks is the strongest. This skill produces both: a
written record of this project's bar, with numbers, and the wiring that
enforces it.

## What was requested

Arguments: $ARGUMENTS

- **No argument:** set up constraints for this repository (Steps 1–7).
- **`check`:** run every command in CONSTRAINTS.md against the current branch,
  scoped to the diff where the tool allows, and report each row as pass or fail
  with the relevant output.
- **`guard`:** run the floor guard (`node scripts/floor-guard.mjs` if the
  project has a copy, otherwise `node ${CLAUDE_SKILL_DIR}/scripts/floor-guard.mjs`)
  and explain each finding and how to resolve it without lowering the bar.
- **`ratchet`:** measure every metric in "Measured, not yet enforced" and raise
  recorded values that improved. Never lower a recorded value; report a drop as
  a finding.

## When not to use

- CONSTRAINTS.md exists and the user is not changing it: follow it.
- One-off scripts, spikes, throwaway prototypes.
- Non-interactive runs (CI, `claude -p`, loops, autonomous agents): do not
  interview. Apply the Floor, say that you did, and leave the rest to a person.

## Step 1: Detect before asking

Never ask for what you can read. Gather first:

| What | Where |
|---|---|
| Language and stack | `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml` |
| Test runner | dev dependencies, the `test` script, existing test files |
| Linters | `eslint.config.*`, `biome.json`, `.ruff.toml` |
| Coverage today | existing coverage output, or one run of the suite |
| CI | `.github/workflows/`, `.gitlab-ci.yml` |
| Agent setup | `CLAUDE.md`, `.claude/settings.json`, `AGENTS.md`, `.codex/` |

Report what you found in two lines, then ask only what is left.

## Step 2: Four questions, each with a default

Every question has a guess and a default, so "I don't know" is a complete answer
that still produces a working config. Ask them together, in whatever question
format the host or the user's instructions prefer. Stop at four.

1. **Which dimensions beyond the floor?** Coverage of new code, security
   scanning, performance budgets, accessibility, architecture boundaries.
   Default: coverage and security. Say what each costs: performance and
   accessibility need a running URL; architecture needs a rules file.
2. **Block or warn when a check fails mid-task?** Default: block on the floor,
   warn on the rest for the first two weeks.
3. **Target numbers, or measure today and hold the line?** Default: measure and
   hold (see Step 7). An invented number gets ignored.
4. **Slowest check tolerated before work is handed back?** Default: about 90
   seconds at task end, unlimited in CI.

## Step 3: Write CONSTRAINTS.md

One file at the repository root, from the
[template](references/setup.md#constraintsmd-template): a Floor, rules enforced
with numbers and the command that checks each, metrics measured but not yet
enforced with today's value and a direction, and exceptions with an owner and an
expiry. Every agent can read it, and a change to it shows up in review. Give
every number its reason; the [defaults](references/setup.md#sane-defaults) come
with theirs.

Then point agents at the file:

- **Claude Code:** add `@CONSTRAINTS.md` on its own line in the project's
  CLAUDE.md, followed by "Do not weaken CONSTRAINTS.md to make a change pass."
  The import loads the file into every session; a "please read it" line relies
  on the agent remembering to.
- **Other agents:** the same sentence, with an instruction to read the file, in
  AGENTS.md.

## Step 4: Install what each dimension needs

Picking a dimension means installing its tool; a number with no command behind
it is an aspiration. Use the de facto tool from the
[tools table](references/setup.md#tools-by-dimension) so the team's existing rule
formats and thresholds keep working, and do not write your own checker when one
exists. Record each command in the "Checked by" column and mirror it in the
project's [`check:fast`, `check:task`, and `check:full`](references/setup.md#project-scripts)
scripts. CONSTRAINTS.md is the source of truth; if the scripts drift, the file
wins.

Things that bite if skipped:

1. **Always pass `--redact` to gitleaks.** Without it the secret lands in the
   agent's transcript and from there in logs, summaries, or commit messages.
   Report the rule and location, never the value.
2. **Lighthouse and axe need a URL.** They belong at preview deploy or against a
   server the user runs. If the project has no URL (a CLI, a library), say so
   and drop the dimension rather than inventing a check that cannot run.
3. **Scope expensive tools to the diff.** Stryker and Semgrep take a path list;
   on changed files they take seconds instead of hours.
4. **Coverage needs no second test run.** Intersect the lcov the suite already
   writes with `git diff`.

## Step 5: Wire checks into the loop

A check that stalls the agent gets switched off, and a switched-off gate is worse
than none because the bar still looks like it exists. Place each check by cost
and scope it to the diff:

| Stage | What runs | Budget |
|---|---|---|
| Every edit | types, lint (`check:fast`) | a few seconds |
| End of the agent's turn | the floor guard | seconds |
| Task end | related tests, changed-line coverage, secrets (`check:task`) | under ~90 s |
| CI and review | everything (`check:full`), the guard against the base branch | minutes |

**Claude Code.** Copy the guard into the project so CI and people run the same
check without this skill:

```sh
mkdir -p scripts && cp "${CLAUDE_SKILL_DIR}/scripts/floor-guard.mjs" scripts/floor-guard.mjs
```

Then add to the project's `.claude/settings.json` (merge with what is there):

```json
{
  "permissions": {
    "ask": ["Edit(/CONSTRAINTS.md)"]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "cd \"$CLAUDE_PROJECT_DIR\" && npm run --silent check:fast 1>&2 || exit 2" }]
      }
    ],
    "Stop": [
      {
        "hooks": [{ "type": "command", "command": "cd \"$CLAUDE_PROJECT_DIR\" && node scripts/floor-guard.mjs --hook" }]
      }
    ]
  }
}
```

What each piece does:

- **`ask` on `Edit(/CONSTRAINTS.md)`:** every edit Claude makes to the bar needs
  the user's approval, so loosening it is loud by construction. The leading `/`
  anchors the path at the project root. The rule covers Claude's file-editing
  tools, not shell writes; the floor guard catches a weakened file at the end of
  the turn either way.
- **`PostToolUse` → `check:fast`:** exit 2 sends the error output to Claude,
  which fixes it in the same turn. Keep `check:fast` to a few seconds; if
  whole-project type checking is slower, move it to task end or scope the hook
  to the edited file (its path arrives on stdin as `tool_input.file_path`).
- **`Stop` → floor guard with `--hook`:** a violation exits 2, which keeps
  Claude working with the findings as feedback. If the same violation is still
  there on the next stop (`stop_hook_active`), it exits 1, so the user sees a
  notice and the session does not loop. Without `--hook` the guard uses CI exit
  codes, where 1 means violation; Claude Code treats exit 1 as a non-blocking
  notice Claude never sees, so never wire the CI mode into a hook.
- **`check:task`** stays out of the Stop hook because Stop fires after every
  turn, including ones that change nothing. Add it there only if the suite runs
  in seconds; otherwise run it when the task is done, as CLAUDE.md instructs.

**CI, for every agent and every person:** run `npm run check:full` and
`node scripts/floor-guard.mjs --base origin/<base-branch>` on pull requests.

## Step 6: Guard the bar itself

If the agent writes both the code and the checks, the checks prove less. Agents
rarely craft loopholes; they take the cheapest road to green. The floor guard
looks for five moves in the diff:

1. **A threshold moved:** a budget lowered, a severity dropped, a check removed
   from a stage.
2. **A test got easier:** `.skip` added, a test file deleted, assertions pulled
   from tests that stayed.
3. **A checker was silenced:** new `@ts-ignore` or `eslint-disable`. Watch four
   in particular, because they switch off a check you rely on: `istanbul ignore`
   drops code from coverage, `Stryker disable` hides a surviving mutant,
   `nosemgrep` and `gitleaks:allow` hide security findings.
4. **Work is unfinished:** a stub that throws, an empty `catch`, a `TODO` where
   the implementation should be.
5. **An exception appeared:** a new row in the Exceptions table.

Tightening is silent; loosening is loud. The guard's contract, exit codes, and
how to adapt its patterns are in [references/floor-guard.md](references/floor-guard.md).
Adapt the shipped script rather than writing another, so every run and every
stack uses the same mechanism.

Rank checks by one question: can the agent pass it by writing code that does not
work?

- **External:** axe encodes WCAG, osv-scanner reads a vulnerability database,
  Lighthouse measures a real browser. The agent cannot argue with these.
- **Project:** lint rules and layer boundaries a person owns.
- **Suite:** the project's own tests, the most useful and the only circular kind.

Make sure at least one external constraint is present.

## Step 7: Ratchets, when there is no number

Setting 80% coverage on a codebase at 62% produces a permanently red build and a
team that learns to ignore red builds. Instead, record today's value with a
direction in "Measured, not yet enforced" and refuse to get worse. Checks compare
against the recorded value. When a number improves, `/constraints ratchet`
raises it; when it drops, that is the finding.

## How much enforcement

1. **Written:** CONSTRAINTS.md exists and agents read it. Relies on compliance.
2. **Scripted and hooked:** `check:*` scripts, the floor guard, the Claude Code
   hooks and permission rule above, and CI. Deterministic, no new service.
3. **Tool-backed:** a dedicated runner for diff scoping, budgets, and ratchets,
   once the shell scripts pass about thirty lines.

Most projects should stop at 2. A first run can be floor-only: the guard needs no
installs, so the floor can be enforced on day one and numbered dimensions added
as each tool goes in. Machine-wide security tools can run in CI only; say so in
the "Runs at" column.

## Stop and reconsider if

- A budget was set that the codebase fails today, with no plan to reach it.
- Every constraint is judged by the project's own tests.
- CONSTRAINTS.md changed in the same commit as the feature that was failing.
- You are about to propose relaxing a threshold instead of fixing the code.
- Slow checks landed in the edit loop and someone reached for `--no-verify`.

## Done when

- [ ] CONSTRAINTS.md exists and every number has a stated reason
- [ ] The floor guard passes on the current branch
- [ ] Every picked dimension has an installed tool and a command that runs today
- [ ] Each constraint states where it runs, and the edit-loop stage takes seconds
- [ ] At least one constraint is external
- [ ] Measured-only metrics record today's value and a direction
- [ ] Exceptions have an owner and an expiry
- [ ] CLAUDE.md imports `@CONSTRAINTS.md` (or AGENTS.md points at it)
- [ ] **Claude Code:** the hooks and the `ask` rule are in `.claude/settings.json`
- [ ] A trial run on the current branch produces no failure the user disagrees with
