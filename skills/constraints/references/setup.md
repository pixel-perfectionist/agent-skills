# Setup reference

Material for Steps 3 and 4 of the skill: the CONSTRAINTS.md template, the
default thresholds with their reasons, and the de facto tool for each
dimension.

## CONSTRAINTS.md template

Keep the four sections. Drop rows for dimensions the user did not pick, and give
every number its reason (see the defaults below).

```markdown
# Constraints

Last reviewed: YYYY-MM-DD by @owner

## Floor (always enforced, no setup required)

- No new suppression comments: `@ts-ignore`, `eslint-disable`, `# noqa`, `# type: ignore`
- No unimplemented stubs: `throw new Error("Not implemented")`, empty `catch {}`
- No skipped or deleted tests without a reason in the commit message
- No secrets in source
- This file does not get weakened to make a change pass

## Enforced with numbers

| Dimension | Rule | Checked by | Runs at |
|-----------|------|-----------|---------|
| Types | Zero type errors | `tsc --noEmit` | every edit |
| Lint | Zero errors from our config | `biome check` | every edit |
| Secrets | No secrets in source | `gitleaks detect --redact` | task end, CI |
| Coverage | Changed lines ≥ 80% covered | `vitest run --coverage` + git diff | task end, CI |
| Security: code | No high findings | `semgrep scan --config p/default` | CI |
| Security: deps | Nothing at high or above | `osv-scanner scan source -r .` | CI |
| Accessibility | Zero critical or serious | `axe $PREVIEW_URL --tags wcag2a,wcag2aa,wcag21aa` | preview deploy |
| Performance | LCP ≤ 2500 ms, CLS ≤ 0.1 | `lighthouse $PREVIEW_URL --output=json` | preview deploy |

A dimension with a number and no command in "Checked by" is an aspiration, not
a constraint.

## Measured, not yet enforced

| Metric | Today | Direction |
|--------|-------|-----------|
| Project coverage | 62.4% | must not fall |
| Bundle size (main) | 184 kB | must not grow |

## Exceptions

| ID | Rule | Path | Reason | Owner | Expires |
|----|------|------|--------|-------|---------|
| W1 | `no-explicit-any` | `src/legacy/**` | Rewrite tracked in an issue | @owner | YYYY-MM-DD |
```

The floor guard reads this file: floor bullets are keyed by the text before
their first colon, table rows by their first cell, and threshold direction by
the words around each number (`≥`, `at least`, `must not fall`, `≤`, `under`,
`must not grow`). Keep those words next to the numbers so a loosened threshold
is recognized.

## Sane defaults

When the user has no opinion, use these. Most codebases meet them on day one.

| Constraint | Default | Why this number |
|---|---|---|
| Coverage of changed lines | ≥ 80% | High enough to force a test, low enough to allow a config line |
| Project coverage | today's value, must not fall | No argument needed to adopt |
| Mutation score, if used | ≥ 60% to start | Typical for a suite never mutated; 80% is mature |
| Dependency vulnerabilities | nothing at high or above | Below that is mostly noise |
| LCP | ≤ 2500 ms | Core Web Vitals "good" threshold |
| CLS | ≤ 0.1 | Same |
| Accessibility | zero critical or serious axe violations | Moderate and minor are often debatable |
| Exception lifetime | 90 days | Long enough to plan the fix, short enough to remember |
| Ratchet tolerance | 0.5% | Absorbs drift when an unrelated file moves the number |

A threshold without a stated reason gets deleted by the next person it blocks.

## Tools by dimension

These are listed because their rule formats and thresholds are what the rest of
the ecosystem targets, so the team's existing configuration keeps working.

| Dimension | Tool | Install | Run | Gate on |
|---|---|---|---|---|
| Types (TS) | tsc | already there | `tsc --noEmit` | any error |
| Types (Python) | mypy | `pip install mypy` | `mypy .` | any error |
| Lint | existing config | already there | `eslint .` / `biome check` / `ruff check` | any error |
| Coverage (JS) | the test runner | already there | `vitest run --coverage` or `jest --coverage` | changed-line coverage |
| Coverage (Python) | pytest-cov | `pip install pytest-cov` | `pytest --cov --cov-report=lcov` | same |
| Security: code | Semgrep | `pipx install semgrep` | `semgrep scan --config p/default --config p/owasp-top-ten` | any high finding |
| Security: secrets | gitleaks | `brew install gitleaks` | `gitleaks detect --redact --no-banner` | any finding |
| Security: deps | osv-scanner | `brew install osv-scanner` | `osv-scanner scan source -r .` | high or above |
| Performance: page | Lighthouse | `npm i -D lighthouse` | `lighthouse $URL --output=json --quiet` | LCP, CLS, score |
| Performance: bundle | size-limit | `npm i -D size-limit` | `size-limit --json` | per-entry budget |
| Accessibility | axe-core | `npm i -D @axe-core/cli` | `axe $URL --tags wcag2a,wcag2aa,wcag21aa` | zero critical or serious |
| Architecture | dependency-cruiser | `npm i -D dependency-cruiser` | `depcruise --validate src` | any violation |
| Assertion quality | Stryker | `npm i -D @stryker-mutator/core` | `stryker run --mutate <changed files>` | mutation score |

Semgrep's registry rules are free to run; check their license before
redistributing them. `opengrep` is a drop-in fork with the same rule format and
JSON output.

## Project scripts

Mirror the commands so they run without an agent, in CI and by hand:

```json
{
  "scripts": {
    "check:fast": "tsc --noEmit && eslint .",
    "check:task": "npm run check:fast && vitest run --coverage && gitleaks detect --redact --no-banner",
    "check:full": "npm run check:task && semgrep scan --config p/default && osv-scanner scan source -r ."
  }
}
```

`check:fast` runs after each edit, `check:task` when the work is done,
`check:full` in CI. For other ecosystems use the equivalent `make` targets or
task-runner entries.
