# Voice

Review comments in this style are short, plain and friendly. They read like a
colleague who checked the work, not like a report. Replace the examples below
with your own comments to match how you write.

## Patterns

- Lead with the point. If something was checked, say how in a few words.
- One reason, one ask. "Could we ...?" for requests, "Question:" or "What do
  you think about ...?" for open questions, "Small thing:" or "Nit:" for
  optional items, "not a blocker" when it is not.
- Simple words and short sentences, easy to read for non-native speakers.
- "we" for shared work ("Could we rebase this onto main?").
- Numbers instead of adjectives when they exist ("32px vs 12px", "11 files
  instead of 4").
- No em dashes. Use a period or a comma.

## Examples

A PR comment that is first in the batch, so it carries the only greeting:

````md
Thanks, Sam! I checked it in the browser and the fields don't jump anymore.

The Test check is failing though. `hides the hint once the title is long enough` (`src/SaveDialog.test.tsx`, line 88) still expects the hint text to be gone, but now it's only hidden. Could we check the class instead?

```ts
expect(container.querySelector("#title-hint")?.classList).toContain(
	"hint-satisfied",
);
```

With this the dialog tests pass for me.
````

A PR comment later in the same batch, so no greeting:

```md
This reads much better. I checked it in the side panel and in the details dialog. The arrow only shows when a note is cut off, and rows without it still line up.

One request: could we rebase this onto main? The branch also carries #41 and #43, so the diff shows 11 files instead of 4. This change doesn't depend on them. I applied just this commit on main: no conflicts, and tests and typecheck pass. Then it can merge without waiting for #41.
```

A PR comment that collects items with no line in the diff:

```md
The new fields look good, and the API already saves `description` when a project is created (I tried it locally).

A few things:
- This branch is built on #41, so the diff also shows #41's commits. Could we set the base to `feature/sync` for now? Then the diff only shows this change.
- It conflicts with #45 in the title hint, so whichever lands second needs a small rebase.
```

Inline, a real problem with a fix:

```md
If a saved project ends up with a title under 4 characters (for example after `cli init --title ui`), Save is enabled but fails right away, because `saveProject` still checks the title. And the form has no title field to fix it. Could we also show the title field when the current title is too short? Something like `isNew || !isValidTitle(title)`.
```

Inline, an optional design question:

```md
Small design question, not a blocker. When the title is already fine (the usual case, since it's prefilled), the hint's space stays empty under the field: about 32px, while other fields have 12px. What do you think about always showing the hint as small helper text? Then nothing jumps and there's no empty gap.
```

Inline, a nit:

```md
Nit: when there's only one textarea, `summary` and `notes` point to the same element here. Selecting by id would be clearer: `#summary` and `#notes`.
```

A short list of asks before merging:

```md
Thanks, Sam! Could we cover these three things before merging?
- The CLI command still skips this step. Could we include it too?
- New local branches fail to push without an upstream. Could we handle and test that case?
- Could we show a warning when the push fails, even if the upload succeeds?
```

Explaining your own code to reviewers:

```md
- Defines which address can reach the database.
- Only a single IPv4 address is allowed, not a range.
- Unsafe addresses like 0.0.0.0 are blocked.
```

## Rewrites

Bad:

> Great work on this PR! 🎉 I noticed that the test on line 88 seems to be failing — it might be worth considering updating the assertion to ensure it robustly checks the new behavior. Let me know if you have any questions!

Good:

> The Test check is failing. This test still expects the hint text to be gone, but now it's only hidden. Could we check the class instead?

Bad:

> **🟡 Risk:** The `isReady` logic bypasses validation for subsequent saves, which could potentially lead to a degraded user experience in edge cases.

Good:

> If a saved project ends up with a title under 4 characters, Save is enabled but fails right away, and the form has no title field to fix it. Could we also show the title field when the title is too short?

Bad: three comments in one batch, each starting with "Thanks, Sam!".

Good: the greeting once, in the first comment posted.

## Before showing the list

- One point per comment, the reason in one sentence, a concrete ask.
- True and verified, and it says how when that matters.
- At most one greeting in the whole batch.
- No em dashes, emoji, headings, bold, severity labels, filler or AI mentions.
- Inline comments sit on lines that are in the diff.
