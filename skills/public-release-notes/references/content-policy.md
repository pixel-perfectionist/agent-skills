# Public content policy

The Release Notes page is public on the internet. Everything below applies to
the entry text, the frontmatter, the alt text, the captions, the file names and
the pixels of every screenshot.

## What may become a note

Only changes a customer can see in the product UI and would want to hear about:
new capabilities, changed workflows or UX flows, and product updates that
change how customers work (SKILL.md step 4). Fixes and polish appear only as
items inside such a note. Customer administrators are customers, so
Configuration and Company settings work counts.

Exclude, recording exactly one category:

- `minor`: bug fixes, visual polish, copy and spacing tweaks and other small UI
  adjustments that do not change what a customer can do or how they work. Many
  of them together are still `minor`.
- `security`: security, access control, permissions, authentication, data
  access rules, vulnerabilities, hardening, rate limits. This holds even when
  the change shows up as a new screen or a "can no longer" behaviour.
- `infra`: infrastructure, migrations, performance, logging, dependencies, CI,
  tooling, refactors, tests, documentation, developer tooling.
- `vendor`: third-party providers and where customer data goes.
- `customer`: work for one customer, and any customer or tenant name.
- `unreleased`: prototypes, anything behind a feature flag or build toggle,
  platform-staff tools, devtools, mocks and fixtures.

Signals worth checking in a PR: a new build-time flag or flag module, a
platform-admin check, a `/prototypes/` path, mock data files, Risk or Security
sections that are not boilerplate, a security fix described as plain behaviour,
renames and removals filed as chores.

## Copy

- Formal register. Kinds: New feature, Enhancement. A fix never carries a note
  of its own.
- UI labels exactly as rendered, and terms from the product glossary.
- Short, direct, active sentences.
- No PR numbers, endpoints, tables, code names, hosts, customer, vendor or
  people names.
- A fix is described as the new behaviour, never as the flaw.
- Alt text and captions describe the UI element, never cell values.
- Follow `style.md`. In short: no em or en dashes, no "not X but Y", no
  announcement openers ("Introducing", "We're excited"), no exclamation marks
  or emoji, no bold-label list items, no Title Case headings, no sales or
  inflation words (seamless, powerful, robust, intuitive, leverage, unlock,
  crucial, pivotal), no claims of degree a PR does not measure, and no closing
  line that restates the point.
- Feature sentence shape: who can do what, by using which part of the UI.
  Present tense; "now" is implied.
- Length: title at most about 70 characters, summary one sentence of at most
  about 30 words, paragraphs at most 3 sentences, one to five "What has
  changed" items.

## Screenshots

- Every note with a UI change carries at least one screenshot.
- A new screen: one wide crop of that screen. A change to part of a screen: a
  crop of that part only.
- Several changed elements: a numbered collage, one crop per element; the
  numbers match the "What has changed" items.
- The changed element is outlined in the capture.
- Taken from the local copy of the app and its synthetic tenant only.
- Never the user menu, avatars, people or organization names, record
  identifiers, notifications or the Company switcher.
- Screens that render static data copied from a real customer stay on the
  denylist kept in the Decipher repo until that data is replaced.
