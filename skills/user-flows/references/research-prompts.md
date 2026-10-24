# Research prompts

Starting prompts for parallel, read-only research threads. Fill in the angle
brackets. Each thread gets the whole context it needs, because a subagent does
not inherit the conversation. Ask for file and line citations so claims can be
checked, and treat every report as leads to verify.

## Shared preamble

```text
Repository root: <absolute path>. Product: <name> (<former names, if any>),
deployed at <URL, if any>. Goal: produce a USER FLOW inventory so we can draw
user-flow diagrams and plan regression tests. A user flow is: where a person
starts, every action they take, what opens, and the outcome. Read-only; do not
modify files. Return structured markdown with file:line citations.
```

## Website routes and dialogs

```text
<preamble>
Scope: <website directories, router, layout, shared components, config with
strings and routes>. Do not cover <the embedded viewer> in depth; note where the
site links into it.
Report:
1. Route table: every URL path (client and server), the component rendered,
   whether sign-in is required, what an unauthenticated visitor gets.
2. Global navigation: header, account menu, footer; each item and destination.
3. Per page: what is shown, every interactive element, what each click does
   (navigation, dialog, API call with method and path), and the resulting state,
   including empty, loading and error states.
4. Dialogs and deep-link query parameters that open them; each dialog's steps,
   fields, buttons and outcome.
5. Any role- or capability-dependent UI.
```

## Embedded or framed viewer

```text
<preamble>
Scope: <viewer/stage/toolbar directories, SDK, integrations, how the server
serves published content>.
Report:
1. URL shapes for the viewer, a specific version, and the raw content; how the
   server frames and isolates it.
2. Every toolbar control in each mode (viewing vs authoring): what it does,
   which API it calls, the outcome, and who may see it.
3. Settings or details panels: fields, save behavior, permissions.
4. Any publish or export flow from inside the viewer: steps, progress,
   success, cancel, and each error status with what it means in the handler.
5. Error states: not found, no access, unpublished, bad version, slow or failed
   load.
```

## Authoring tools

```text
<preamble>
Scope: <CLI, IDE extension, chat participants, environment lifecycle scripts
(e.g. codespace or devcontainer hooks), the module that saves and publishes,
templates>.
Report:
1. Entry points into authoring and what each link or command carries.
2. Environment boot as the user perceives it: what they wait for, what opens
   automatically, sign-in prompts, failure messages and recovery.
3. Every IDE command, status-bar item, chat command, and CLI command with its
   outcome.
4. Save and publish end to end, including permission checks and offline
   behavior.
5. Decisions made on the user's behalf (resume or copy, new or existing) and
   what the user sees for each.
6. Templates or starters, and which can actually be started.
```

## API, access and existing tests

```text
<preamble>
Part A, API and access. Scope: <API router, auth, permission model, storage>.
Report every endpoint (method, path, auth, required role or capability, what it
does, which surface calls it), identity sources, roles and capabilities, health
endpoints.
Part B, test coverage. Scope: every test file outside dependencies, test runner
configuration, CI and deploy workflows. For each test file, one line on what
behavior its assertions cover, grouped by area. State explicitly: is there any
real-browser test, any test against a deployed environment, and what the deploy
verifies after rollout.
```
