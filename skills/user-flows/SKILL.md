---
name: user-flows
description: Map what people actually do in a product, end to end, as user flows (user journeys) with Mermaid diagrams, then set each journey against the existing tests to find the critical user journeys a pre-release regression suite must protect. Use when the user asks for user flows, user journeys, use cases, critical user journeys (CUJ), a USER-FLOWS.md, "what does a person do from the home page to the result", or "what must we cover with tests before we ship". Produces a document and findings; it does not write the tests.
---

# User flows

Turn a product into a map of journeys: where a person starts, what they press,
what opens, and what they end up with. Then show which of those journeys are
protected today and which must be before the next release. The result is a
`USER-FLOWS.md` (or the location the user chooses) that a team can review and
plan tests from.

## Vocabulary to give the user

People often ask for this without the words for it. Offer them once, briefly,
and use them consistently afterwards.

| Term | Meaning |
| --- | --- |
| **User flow / user journey** | One path: start point, actions, screens that open, outcome. |
| **Critical user journey (CUJ)** | A journey that, if broken, breaks the product's promise. The release gate. |
| **Use-case map** | Actors and what each can do, without steps. An overview, not a flow. |
| **Smoke / regression suite** | Automated checks that walk the critical journeys before or right after a deploy. |

A UML use-case diagram is not what they want when they describe "page → action
→ what opens → next choice"; that is a user-flow diagram.

## Settle scope first

Ask only what changes the work, one question at a time, with a recommended
option first:

1. **Surfaces.** Everything a person touches (web app, embedded viewer, IDE
   extension, CLI, chat, admin), or only the browser-testable part.
2. **Output.** A repository document beside the existing top-level docs, in the
   language those docs use, delivered as a pull request; or a session artifact
   only. Follow the repository's naming and documentation conventions.

Writing the tests, fixing what is found, and adding screenshots to the
repository are out of scope unless the user asks.

## Gather evidence

Read the project's own authority before anything else: README, specification,
architecture notes, agent instructions, the route table, the API endpoint
declarations, the permission model, the test files, and the CI and deploy
workflows. These name the vocabulary to reuse and the invariants a journey must
respect.

Then inventory the surfaces. When isolated subagents are available, run one per
independent research thread in parallel, using the prompts in
[research prompts](references/research-prompts.md): website routes and dialogs,
the embedded or framed viewer, authoring tools (CLI, IDE, chat), and API,
access and existing tests. Give each the repository path, the product name, the
scope boundary, and the exact report shape. Without subagents, do the same
threads in sequence.

Subagent reports are leads, not facts. Every claim that ends up in a diagram is
checked against the code or the running UI.

## Walk the real UI

Code shows what can happen; the running UI shows what a person sees. Run the
product locally and walk it.

1. Start the development server the project documents. Prefer a mode that signs
   the local user in. Seed realistic data through the product's own API or
   upload path rather than writing into storage directly. Note every file and
   directory created so it can be removed afterwards.
2. Drive it with [`scripts/walk_ui.mjs`](scripts/walk_ui.mjs), which lists the
   visible links, buttons, inputs, headings and dialog contents after each step
   and saves screenshots. It uses the project's own Playwright or Puppeteer; see
   [the script reference](references/scripts.md). A host browser panel works
   too when it responds.
3. Follow each journey to its outcome: dialogs step by step, deep-link query
   parameters (`?dialog=`, `?project=`, `?template=`), the exact external URLs
   produced (sign-in, codespace, download), empty and error states, and every
   role-dependent control. Use development harness pages when the project has
   them, for states that are hard to reach.
4. Record the labels exactly as shown. When the UI and the code disagree, the
   UI is what users experience; record the disagreement as an open question.

A deployed site behind single sign-on is not scraped or bypassed. Say which
parts were walked and which were read from code.

## Write the document

Use the structure and conventions in
[the document template](references/document-template.md):

- **Vocabulary**, linking to the project's own glossary where one exists.
- **Actors**, defined by what they may do (capabilities), not job titles.
- **The map**: a use-case flowchart (actor → journey) and a site map of routes
  and dialog deep links.
- **Journeys**, numbered `J1…Jn`, each with who, where it starts, where it ends,
  a Mermaid flow, branches for permissions, empty and failure states, the API
  calls it makes, and links to the code (paths and symbols, not line numbers).
- **Coverage**: each journey against the tests that protect it today, what is
  not covered, a priority, and a suggested test layer.
- **Open questions**: inconsistencies found, recorded rather than fixed.

Rules that make the map useful:

- **Name a journey the way the user would say it.** "Open a published project",
  not "View the stage". A reader scanning for "opening a project" must find it
  by its name.
- **Start every journey diagram from all of its entry points.** A card, a shared
  link, a version link, the link a previous journey produced. A flow that starts
  at a URL hides how people get there.
- **One diagram per journey, readable on its own.** Link to neighbouring
  journeys by id (`J3`) instead of redrawing them. Keep a diagram to roughly
  twenty nodes; split a journey that needs more.
- **Show the decision points** a test would branch on: signed in or not, which
  capability, empty or failed, first time or repeat.
- **Never guess what a status code or message means.** Read the handler. A
  `409` that means "already running" is not a permission refusal.

### Priorities

- **P0**: breaking it breaks the product's core promise. Checked against every
  deployment.
- **P1**: used daily. Checked in CI.
- **P2**: worth a check, not a gate.

Derive P0 from the project's own statement of what it guarantees, and say which
statement each P0 traces to.

### Coverage

Map tests to journeys by reading test names and assertions, not file names.
State explicitly whether anything runs in a real browser, whether anything runs
against a deployed environment, and what the deploy itself verifies. The usual
finding is that every check is green in CI while nothing confirms a person can
still complete a P0 journey on the deployed site; say so plainly when it is
true.

Suggest layers (post-deploy smoke, local browser E2E, existing unit tests) and
assign journeys to each. Name the decision that must come before any deployed
test, such as an identity that can pass single sign-on without a person.

## Verify

1. Render every diagram with [`scripts/check_mermaid.mjs`](scripts/check_mermaid.mjs).
   Parsing alone is not enough; render, and look at the largest diagrams as
   images.
2. Run the project's formatter on the document.
3. Re-check each claim you were least sure of against the code: endpoint and
   method, status-code meaning, which role sees which control, which feed lists
   what.
4. Remove the data you seeded and stop the servers you started.

## Deliver

Link the document from the README or the docs index the project uses. Follow
the repository's commit, branch, and pull request conventions. The pull
request description lists the journeys, the main coverage gaps, the open
questions, and exactly how the journeys were verified, including what was only
read from code.

When the user later finds a journey hard to locate, treat it as a naming or
entry-point problem in the document first: rename it in their words and add
the missing entry points, then update the description.

Report to the user in their language: what the document contains, the P0
journeys, the main gaps, the open questions, and what was not verified.
