---
name: webperf
description: Run a read-only web performance audit of a web app, route, component, or live URL. Returns a Core Web Vitals scorecard filled only from real measurements, plus ranked findings with fixes for the detected stack. Use when the user invokes webperf or asks for a web performance or Core Web Vitals audit. Not for libraries, CLIs, or server-only code with no browser-facing output.
argument-hint: "[url | path | route] [lighthouse.json | psi.json | trace.json]"
context: fork
agent: web-performance-auditor
license: MIT. See LICENSE.
---

# Web performance audit

<!-- Adapted from the /webperf command in https://github.com/addyosmani/agent-skills (MIT). See LICENSE. -->

Audit target and inputs: $ARGUMENTS

If no target is given above, audit the web application in the current working
directory. When this branch has changes (`git diff` against the merge base with
the default branch, plus uncommitted files), focus on the browser-facing code
they touch and say so in the report.

If this is not a web application (a library, CLI, or server-only code with no
browser-facing output), stop and say that a web performance audit does not
apply.

1. Detect the framework, rendering model (SSR, CSR, static), bundler, and
   hosting from the manifest and config files. Treat `vercel.json`, a `.vercel/`
   directory, or `@vercel/*` packages as a Vercel deployment.
2. Choose the mode. Deep mode applies when the inputs include a Lighthouse,
   PageSpeed Insights, or CrUX JSON file or a trace, or name a URL that answers
   (a local production server, or a Vercel preview or production URL). Otherwise
   use Quick mode. Never start the app yourself; if a named URL does not answer,
   say that Deep mode needs it running and continue in Quick mode.
3. Run the audit and return the complete report in the output format of your
   instructions as your final message.

If your instructions do not already contain the web performance auditor's
rules (for example, this skill is running without the `web-performance-auditor`
agent, or in a host without subagents), read
`agents/web-performance-auditor.md` in this skill's directory
(${CLAUDE_SKILL_DIR}) and follow it, ignoring its frontmatter. Do not edit
project files during the audit.
