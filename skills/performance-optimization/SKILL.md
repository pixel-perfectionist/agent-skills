---
name: performance-optimization
description: Measure-first performance work across frontend, backend, and database code. Finds the real bottleneck, changes one thing, re-measures against run-to-run noise, keeps only what beats the baseline, and guards the metric. Use when there is a performance requirement or budget, a reported or suspected slowdown or regression, Core Web Vitals or load times to improve, N+1 or slow queries, cache or connection-pool problems, or a profile that shows a bottleneck. Not for speculative optimization without evidence of a problem.
license: MIT. See LICENSE.
---

# Performance Optimization

> Adapted from `performance-optimization` in [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT). Rewritten for Claude Code: measurements the agent runs itself, one statement per rule, no commits implied. See [LICENSE](LICENSE).

An optimization is a hypothesis until a measurement says otherwise. Measure,
find the actual bottleneck, change one thing, measure again the same way, and
keep the change only if it beat the noise. Without evidence of a problem, do
not optimize: unmeasured "improvements" add complexity that never pays for
itself. If the user asks to "make it faster" without a symptom, start by
measuring to find out what is slow.

## Step 1: Measure the baseline yourself

You have a shell. Produce numbers with a command instead of asking the user
to click through a profiler. Pick by surface:

| Surface | Command | Read |
|---|---|---|
| CLI, script, build step, function behind a script | `hyperfine --warmup 3 --runs 10 '<cmd>'` | Mean ± σ. Compare two versions in one call: `hyperfine '<baseline>' '<candidate>'` |
| HTTP endpoint | `npx autocannon -c 10 -d 20 <url>` | High latency percentiles and throughput, not the average |
| Page load (lab) | `npx lighthouse <url> --output=json --output-path=<file> --quiet --chrome-flags="--headless=new"`, 3–5 runs; or `npx @lhci/cli collect --url=<url> --numberOfRuns=5` | Median of the runs, per metric |
| Interactions, LCP and layout-shift attribution | Chrome DevTools MCP (`performance_start_trace`, `performance_stop_trace`, `performance_analyze_insight`) when the harness has it; otherwise any browser automation tool plus `PerformanceObserver` for `largest-contentful-paint`, `layout-shift`, and `event` entries | Long tasks and the elements responsible |
| SQL | `EXPLAIN (ANALYZE, BUFFERS) <query>` through the project's database client, on realistic data volume | Plan nodes, actual vs estimated rows, buffers |
| Bundle | The bundler's stats or visualizer; `npx size-limit` where configured | Bytes per entry, what dominates |
| Real users (field) | The project's RUM (`web-vitals`), CrUX or PageSpeed Insights API when a key is available | p75 over the reporting window |

Constraints that keep this safe and honest:

- `EXPLAIN ANALYZE` executes the statement. Wrap writes in a transaction you
  roll back, and never run it against production without the user's say-so.
- Lighthouse and browser traces need a running URL. If nothing answers, ask
  the user to start the app or give you a preview URL; starting long-running
  servers is their call unless the project's instructions say otherwise.
- Lab and field data are different things. A single synthetic run is not what
  users experienced; never present one as the other.

**Stack profile.** For a Next.js, React, or Vercel project, also read
[references/nextjs-vercel.md](references/nextjs-vercel.md). It adds that stack's
measurements (Turbopack bundle snapshots, CDN cache results, Vercel metrics,
Speed Insights), its usual culprits, and when to defer to Vercel's own skills for
code-level rules.

Record the baseline exactly: the command, the conditions (cold or warm cache,
throttling, data volume, machine), and the numbers with their spread.
Core Web Vitals thresholds are in
[references/performance-checklist.md](references/performance-checklist.md#core-web-vitals-targets).

## Step 2: Find the bottleneck

Let the symptom choose what to look at, then confirm it in the measurement
before touching code:

```
First page load slow
├── Large bundle → bundle stats, code splitting
├── Slow server response → TTFB in the network waterfall
│   ├── DNS / TCP / TLS long → preconnect, HTTP/2, edge, keep-alive
│   └── Waiting long → profile the backend, queries, caching
└── Render-blocking CSS/JS → waterfall
Interaction sluggish
├── Freeze on click → long tasks (> 50 ms) on the main thread
├── Input lag → re-renders, controlled-input overhead
└── Animation jank → layout thrashing, forced reflow
After navigation
├── Data → API timings, request waterfalls
└── Rendering → component render time, N+1 fetches
Backend / API
├── One endpoint slow → its queries and indexes
├── Every endpoint slow at once → connection pool, memory, CPU
└── Intermittent → lock contention, GC pauses, external dependencies
Memory grows → heap snapshots: leaked references, unbounded caches
CPU spikes → CPU profile: synchronous heavy work, regex backtracking
```

## Step 3: Change one thing

Fix the bottleneck Step 2 identified, nothing else. These are the usual
suspects. Each states the rule and the signature; the worked fix is in
[references/optimization-patterns.md](references/optimization-patterns.md).
Open the section you need when you reach that code.

**Backend**

- **N+1 queries.** One query per row. Fetch the relation in the same query
  (join or include) instead of in the loop.
  [Pattern](references/optimization-patterns.md#n1-queries-backend).
- **Unbounded fetching.** Every list endpoint paginates with a limit and a
  stable order. [Pattern](references/optimization-patterns.md#unbounded-data-fetching).
- **A query that ignores its index.** "Add an index" is the guess; the plan is
  the measurement. A `Seq Scan` where you expected an index, a `rows=` estimate
  off by an order of magnitude, and a `Sort` above the scan each call for a
  different fix. A bad estimate means stale statistics: run `ANALYZE` before
  adding anything. Index the shape of the query (equality columns first, then
  the range or sort column). A plain index will not help the dominant value of
  a low-selectivity column (a partial index serves the rare value), a leading
  wildcard (needs trigram or full-text), or a function on the column (index the
  expression). Every index taxes every write; one that did not change the plan
  is a revert.
  [Pattern](references/optimization-patterns.md#queries-that-ignore-their-index).
- **Connection pool exhaustion.** Signature: every endpoint slows at once, time
  goes to waiting for a connection, and the database shows mostly idle
  sessions. Find what holds connections (long transactions, a missing `await`,
  leaked clients) before resizing. One pool per process, with
  `instances × max` under the database's connection ceiling. A bigger pool
  moves the queue into the database, where it is harder to see; with unbounded
  instances, multiplex through a proxy (pgbouncer, RDS Proxy).
  [Pattern](references/optimization-patterns.md#connection-pool-exhaustion).
- **Missing caching.** Cache what is expensive to produce and read far more
  often than it changes; caching a fast call adds a hop and a staleness bug for
  nothing. Every input that changes the response belongs in the key (tenant,
  viewer, locale, permissions, feature flags): a key that omits the viewer
  serves one user's data to another. Choose one invalidation strategy and write
  down the acceptable staleness. Protect hot keys from the stampede (serve stale
  while one request recomputes, or coalesce misses). Never cache what must be
  fresh: balances, permissions, inventory at checkout.
  [Pattern](references/optimization-patterns.md#missing-caching-backend);
  coalescing, write strategies, and negative caching are in the
  [checklist](references/performance-checklist.md#caching-strategies).

**Frontend**

- **Images.** Every image declares `width` and `height`. The LCP image gets
  `fetchpriority="high"`, modern formats through `<picture>`, and
  `srcset`/`sizes`, and is never lazy. Below-the-fold images get
  `loading="lazy"` and `decoding="async"`.
  [Pattern](references/optimization-patterns.md#missing-image-optimization-frontend).
- **Re-renders.** An object or function created during render is a new
  reference every time. Hoist constants; use `React.memo` and `useMemo` only
  where the profile shows expensive work, since blanket memoization is its own
  cost. [Pattern](references/optimization-patterns.md#unnecessary-re-renders-react).
- **Bundle size.** Modern bundlers tree-shake ESM named imports already; the
  gains are route-level splitting and lazy-loading heavy, rarely used features.
  [Pattern](references/optimization-patterns.md#large-bundle-size).

## Step 4: Re-measure, then keep or revert

Re-run the baseline command under the same conditions with the same budget. A
cold-cache baseline against a warm-cache result measures the cache, not the
change. Measure changes one at a time; three changes in one number cannot be
attributed.

Compare the difference with the run-to-run spread (hyperfine's σ, the range of
the Lighthouse runs), not just the means. A 3% gain inside ±5% variance is a
different sample, not a gain.

| Result against baseline | Decision |
|---|---|
| Beyond the noise, tests green | Keep |
| Within the noise | Revert |
| Worse | Revert |
| Better, but a test went red or had to change | Revert: the win came from dropping work the product needs |

Neutral is a revert. The change already being written is not a reason to keep
it; kept code is maintained forever, so it has to have bought something.

Put the before and after numbers in your report, and in the commit message if
the user asks you to commit. Log every attempt, including reverted ones, in
the pull request description or a `PERF.md`, and read that log before
proposing an experiment, so a dead idea is not tried again:

| Idea | Baseline → Result | Verdict | Why |
|---|---|---|---|
| Memoize the row component | INP 240 ms → 235 ms | reverted | Inside noise (±15 ms); rows were not the bottleneck |
| Virtualize the list | INP 240 ms → 90 ms | kept | Long tasks gone from the trace |

## Step 5: Guard the metric

Guard the metric that justified the work (LCP, INP, p95 latency), not every
available number.

- **Synthetic gate in CI.** A performance budget checked before merge, using
  repeated runs or a median so normal variance does not make it flaky
  (`npx @lhci/cli autorun` with assertions, `npx size-limit`).
- **Field monitoring.** Alert on a meaningful p75 movement in RUM data; use
  attributed `web-vitals` data to locate the cause. Treat CrUX's rolling window
  as confirmation, not an alert.

Starting budgets when the project has none (tune to the product):

```
Initial JavaScript   < 200 KB gzipped
CSS                  < 50 KB gzipped
Above-the-fold image < 200 KB each
Fonts                < 100 KB total
API p95              < 200 ms
Lighthouse Performance ≥ 90
LCP ≤ 2.5 s · INP ≤ 200 ms · CLS ≤ 0.1 (p75)
```

When a guard fires, return to Step 1 and take a fresh baseline before proposing
a fix.

## Before you report

- [ ] Before and after numbers exist, measured the same way, with their spread
- [ ] The kept change beats the noise; neutral or worse changes were reverted
- [ ] Tests pass without being changed, skipped, or deleted
- [ ] Attempts are logged, reverted ones included
- [ ] Any new index has a plan before and after and a considered write cost
- [ ] Any new cache states its key inputs and its staleness window
- [ ] Lab and field numbers are labeled as such
- [ ] The guarded metric has a budget or a monitor that would catch a regression
