# Stack profile: Next.js, React, and Vercel

Read this when `package.json` has `next` or `react`, or the project deploys to
Vercel (`vercel.json`, a `.vercel/` directory, `@vercel/*` packages). It is
written against Next.js 16 (App Router, Turbopack builds) and React 19. Check
the installed versions before applying version-specific advice.

## Use Vercel's own skills for code-level rules

This file adds the stack's measurements and its usual culprits at the audit
level. It does not restate the framework vendors' rule sets:

- **`react-best-practices`** (Vercel plugin): 64 code-level rules in priority
  order: waterfalls, bundle size, server, client fetching, re-renders,
  rendering, JavaScript. When it is installed, cite rule IDs in findings and
  fixes (for example `async-parallel`, `bundle-barrel-imports`,
  `server-serialization`) and read the rule's file before recommending it.
- **`next-bundle-optimizer`** (`npx skills add vercel/next.js --skill next-bundle-optimizer`):
  bundle investigation from Turbopack's analyzer data.
- **`nextjs`, `next-cache-components`, `cdn-caching`, `vercel-functions`,
  `vercel-cli`** (Vercel plugin): framework and platform detail.

## Measure on this stack

- **Never measure `next dev`.** Development builds are unminified, compiled on
  demand, and carry dev-only tooling, so their numbers say nothing about
  production. Measure `next build && next start` (ask the user to run it) or a
  Vercel preview or production URL.
- **Bundles (Turbopack, Next.js 16.1+).** `npx next analyze --output` writes the
  analysis to `.next/diagnostics/analyze`. On 16.4+, take a snapshot before and
  after the change and compare the JSON Lines exports:
  `npx next analyze --output --snapshot before`, then
  `npx next analyze export --snapshot before > before.jsonl`.
  `@next/bundle-analyzer` is the webpack plugin; on a Turbopack build use
  `next analyze`, or build with `--webpack` to use the plugin.
- **CDN cache.** `curl -sI <url> | grep -i x-vercel-cache` returns `HIT`,
  `MISS`, `STALE`, `PRERENDER`, `REVALIDATED`, or `BYPASS`. For hit rate and
  where misses concentrate, `vercel metrics vercel.request.count --group-by cache_result`
  (needs a linked project and Observability Plus; the `cdn-caching` skill has
  the full procedure). The cache reason appears only in `vercel logs`, not in
  response headers.
- **Function latency by route.** Run `vercel metrics schema vercel.function_invocation`
  for the available aggregations, then query
  `vercel.function_invocation.request_duration_ms` grouped by `route` with the
  highest percentile it offers; an average hides the tail.
- **Field Core Web Vitals.** If `@vercel/speed-insights` is installed, look for
  its metrics in `vercel metrics schema --format=json` and query p75 by route
  when they are exposed; otherwise ask the user for the Speed Insights numbers.
  Label them `Field (Speed Insights)`. Never estimate.
- **Protected previews.** Lighthouse reaches a preview behind Vercel
  Authentication with `--extra-headers` carrying `x-vercel-protection-bypass`.
  Read the secret from the environment and never print it.

## Usual culprits

**Rendering and caching**

- **Accidentally dynamic routes.** `cookies()`, `headers()`, `searchParams`,
  `connection()`, or an uncached fetch in a layout makes every route under it
  dynamic: no static shell, no CDN `HIT`.
- **Nonce-based CSP.** Generating a nonce in `proxy.ts` forces every page it
  covers to render dynamically: static optimization and ISR are disabled, pages
  are not CDN-cached by default, and Partial Prerendering is incompatible.
  Confirm the trade-off is deliberate. Hash-based CSP through `experimental.sri`
  keeps static generation (experimental).
- **`proxy.ts` (formerly middleware) runs on every matched request.** Keep the
  matcher narrow (exclude `_next/static`, `_next/image`, and prefetch requests)
  and the work inside it light.
- **Cache Components.** With `cacheComponents: true`, a static shell plus
  `'use cache'` and Suspense around dynamic parts gives Partial Prerendering.
  `unstable_cache` is deprecated in 16 in favor of `'use cache'`.
- **Route handlers and ISR.** Cacheable responses need `Cache-Control` with
  `s-maxage` and `stale-while-revalidate`; `BYPASS` usually traces to cookies or
  `no-store`; very short `revalidate` intervals regenerate constantly.

**Server and data**

- Sequential `await`s in server components and route handlers: start
  independent work together, await late, and stream slow parts behind Suspense.
- Large props serialized across the server–client boundary.
- Work that does not need to block the response (logging, analytics) belongs in
  `after()`.
- A function region far from its database (`regions` in `vercel.json`,
  `preferredRegion`), or heavy server dependencies inflating cold starts.

**Client bundle**

- `'use client'` high in the tree pulls whole subtrees into the client bundle.
  Push it to the interactive leaves, and move pure data-to-markup work
  (markdown, syntax highlighting, static charts) into server components.
- Barrel imports from icon and utility libraries: `optimizePackageImports`
  (Next.js already optimizes some libraries automatically).
- Heavy, rarely used components: `next/dynamic` or `lazy`.
- Third-party scripts through `next/script` with an explicit `strategy`, or
  `@next/third-parties`, never a raw `<script>` in the head.

**Images and fonts**

- Content images through `next/image` with `width` and `height`, or `fill` with
  `sizes`. For the LCP image in Next.js 16, `priority` is deprecated: use
  `fetchPriority="high"` or `loading="eager"` (or `preload`). The default
  `qualities` is `[75]` since 16.
- Fonts through `next/font`, which self-hosts them and adjusts fallback metrics,
  not a `<link>` to a font CDN.

**React 19**

- If the React Compiler is enabled (`reactCompiler` in `next.config`, or
  `babel-plugin-react-compiler` installed), components are memoized
  automatically. Do not recommend manual `useMemo`, `useCallback`, or `memo`;
  look for components the compiler skipped instead.
- Expensive updates that block input: `useTransition` or `useDeferredValue`.

Sources: Next.js documentation (package bundling, Content Security Policy,
Image component, Cache Components) and Vercel's `cdn-caching` and `vercel-cli`
skills, checked against Next.js 16.4.
