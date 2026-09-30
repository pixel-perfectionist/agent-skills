---
name: release-notes
description: >
  Use when the user says "/release-notes", "release notes for a period",
  "what changed since a date", "change digest", or asks to summarize the merged
  pull requests of a period (default: the last 7 days) for the business or
  product team. Collects every PR merged in the window, ranks the changes by
  impact, takes stage-data screenshots through the developer's own dev server,
  and produces one standalone HTML page that can be shared in Teams.
disable-model-invocation: true
---

# release-notes

Turns a date range of merged pull requests into one short, business-readable
page: biggest behaviour changes first, stage screenshots, where to try each
change, and a collapsed list of every PR. The output is a single `.html` file
with the screenshots embedded, so it can be attached in Teams and opened in any
browser.

**Domain language:** every product word on the page comes from
`VOCABULARY.md` at the decipher repo root. Grep it for a term; never read it
whole (it is large). Precedence: this skill is practice guidance (tier 4 in the
repo's `AGENTS.md` → Instruction precedence). The glossary decides meaning; the
user's instructions in the session win over both. Run the skill from a decipher
checkout. It is installed as a personal skill because the repo's `.gitignore`
hides `.claude/`.

Files in this skill:

| File | Use |
| --- | --- |
| `references/agent-prompt.md` | Prompt for the Explore agents that read PR bodies |
| `references/content-guide.md` | Page structure, ranking, copy rules, rollout checklist, Teams message |
| `assets/template.html` | The page (styles, components, zoom-on-click). Copy it, fill it |
| `scripts/run.mjs` | Playwright job runner for screenshots through the local dev server |
| `scripts/build.py` | `appendix` (every PR, grouped by area), `crop`, `bundle` (standalone HTML) |

Work in the session scratchpad (`$SCRATCH` below). Never write into the repo.

## 1. Resolve the period

Read the period from the request: "last week" = 7 days ending today, "last two
weeks" = 14, "since Sep 20", "Sep 14–28". No period given → the last 7 days.
State the resolved dates in one line (`2026-09-14 → 2026-09-28`) and continue;
ask only if the request names two different periods.

## 2. Collect every merged PR

```bash
git fetch -q origin main
gh pr list --repo DecipherIP/decipher --state merged --search "merged:<A>..<B>" --limit 300 --json number,title,mergedAt,author
gh pr list --repo DecipherIP/decipher --state open --search "updated:>=<A>" --limit 100 --json number,title,createdAt,author,isDraft
```

`main` squash-merges, so one commit is one PR; `git log origin/main
--since="<A> 00:00" --until="<B> 23:59:59" --format='%ad %s' --date=short` is
the fastest full list of titles. Open PRs feed the "In progress" section.

## 3. Read what each PR did

- Up to ~40 PRs: read the bodies yourself (`gh pr view <n> --json title,body`).
- More: launch up to 3 **Explore** agents in parallel, each on a slice of the
  window, with the prompt in `references/agent-prompt.md`. Split by date so each
  slice has a similar number of PRs.
- Check with the user whether there are themes they want highlighted (for
  example "the new signature flow"). Treat their list as a floor, not the whole
  story; the sweep finds the rest.

## 4. Verify the claims that matter

Before a sentence says something was **removed, deleted, turned off by default,
renamed, or sent to a third party**, grep the PR body for it:

```bash
gh pr view <n> --repo DecipherIP/decipher --json body --jq .body | grep -iE "deleted|not converted|default|removed|retired|openai|redirect"
```

Agents summarize well but occasionally overstate. A user-invisible internal log
is not a feature, so leave it out.

## 5. Screenshots (stage data through the local dev server)

The developer runs the dev server; you never start or restart it. Its frontend
calls the stage backend, so shots show stage data.

1. **Preconditions.** `lsof -nP -iTCP:3000 -sTCP:LISTEN` must answer. If it
   doesn't, ask the user to start it. Find the checkout it serves with
   `lsof -a -p <pid> -d cwd -Fn`, and compare that checkout's branch with
   `origin/main` (`git rev-list --left-right --count origin/main...HEAD`). Tell
   the user which merged PRs the dev build lacks; those get text only.
2. **Runner.** Run `scripts/run.mjs` from that checkout's `frontend/`, so
   `@playwright/test` resolves and the dev-login key is read by the process, never
   by you:

   ```bash
   cd <checkout>/frontend && set -a && . ./.env.local && set +a && \
     OUT_DIR="$SCRATCH/notes" JOB="$SCRATCH/notes/jobs/01.json" \
     node --input-type=module -e "$(cat <skill-dir>/scripts/run.mjs)"
   ```

   A job is a JSON array of steps (`login`, `goto`, `settle`, `click`, `hover`,
   `press`, `type`, `scroll`, `text`, `links`, `buttons`, `eval`, `shot`,
   `shotAround`; see the header of `run.mjs`). Start with `[{"op":"login"}]`.
   The browser profile persists in `$OUT_DIR/profile`, so later jobs reuse the
   session. Explore with `text`, `links` and `buttons` before shooting. Look at
   each shot once with Read.
3. **Company.** Shoot in the dev-login account's demo Company. Stay out of
   customer sandboxes. A page that needs another Active Company (for example
   Platform tools) needs the user's explicit OK for that switch. Switch back at
   the end of the same job and confirm `active_company` through `/api/auth/me`.
4. **Strictly read-only.** Never click Save, Send, Publish, Move, Pin, Delete or
   Create. Never flip a switch or toggle, even without saving; the auto-mode
   classifier refuses it and it would change shared stage state. Opening a
   dialog and closing it with Escape is fine. Don't resume Wizard drafts, because
   their steps autosave. If a feature has no example on stage (nothing
   configured yet), say so in the caption. The user can set one up.
5. **Crop** the left sidebar away, or crop to a dialog, with
   `python3 <skill-dir>/scripts/build.py crop <in> <out> <x> <y> <w> <h>`
   (pixel box).
6. **Clean up.** `rm -rf "$OUT_DIR/profile"` when done, since it holds live
   session cookies.

## 6. Write the page

Copy `assets/template.html` to `$SCRATCH/notes/page.src.html` and follow
`references/content-guide.md`. Images go in `$SCRATCH/notes/img/` and are
referenced as `src="img/<name>.jpg"`.

## 7. Build, check, deliver

```bash
python3 <skill-dir>/scripts/build.py appendix --since <A> --until <B> --out "$SCRATCH/notes/appendix.html"
python3 <skill-dir>/scripts/build.py bundle --src "$SCRATCH/notes/page.src.html" \
  --images "$SCRATCH/notes/img" --appendix "$SCRATCH/notes/appendix.html" \
  --out "$SCRATCH/notes/decipher-release-notes-<a>-<b>.html"
```

- `bundle` embeds every image as a data URI (resized to 1600 px, JPEG q78), so
  the file stands alone, usually 2–5 MB.
- Check it once with Playwright at 1440 px and 390 px. Every screenshot should
  decode, `#lightbox` should be hidden, and `scrollWidth` should equal the
  viewport width.
- Copy the file to `~/Downloads/` and send it with `SendUserFile`
  (`display: "attach"`).
- Reply with the paste-ready Teams message from the content guide. Also list
  what has no screenshot and why, and any state you changed (a Company switch)
  and restored.
- Publish a claude.ai Artifact only if the user asks for a link; the business
  team usually cannot open those.
