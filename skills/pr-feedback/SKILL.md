---
name: pr-feedback
description: Review someone else's GitHub pull request with the pragmatic-engineering skill, verify the findings, draft short, friendly review comments in the user's own voice, show every comment for approval, and only then post them from the user's GitHub account one at a time with random 3-7 minute delays. Use when the user asks to review one or more pull requests and leave or post comments, for example "review #42 and comment" or "review my teammate's PRs and post feedback". Never posts without explicit approval of the exact text.
---

# PR feedback

Review a pull request properly, turn the findings into a few comments that
sound like the user wrote them, show them, and post them only after the user
says so.

Always in this order:

1. Review with `pragmatic-engineering` and verify the findings.
2. Draft comments in the user's voice.
3. Show every comment and get explicit approval.
4. Post with random delays, then verify.

Requirements: `gh` signed in as the account that should post, `git`, and
Python 3.9 or later (the helper uses only the standard library).

Keep everything this skill creates (worktrees, plan, log) in one scratch
folder outside every repository: the host's session folder when it has one,
otherwise `$TMPDIR/pr-feedback/`. Below it is called `<scratch>`. This skill's
own folder is `<skill>`.

## 1. Review

Read `pragmatic-engineering` before reading the diff. Load it with the host's
skill tool, or read `../pragmatic-engineering/SKILL.md` next to this skill
when the host lets only the user invoke it (Claude Code
`disable-model-invocation`, Codex explicit-only metadata). Invoking this skill
is the explicit request for it. Use it as the review lens together with the
repository's own instructions (`AGENTS.md`, `CLAUDE.md`,
`.github/copilot-instructions.md`, `.github/instructions/*.md`,
`CONTRIBUTING.md`). The repository wins when they disagree.

Gather context with `gh`:

- `gh pr view <n> --json title,body,author,headRefName,headRefOid,baseRefName,commits,files,statusCheckRollup,reviewDecision`
- Failing checks: `gh pr checks <n>`, then
  `gh run view <run> --job <job> --log-failed` for the failing job.
- Existing feedback: `repos/<owner>/<repo>/pulls/<n>/reviews`,
  `.../pulls/<n>/comments` and `.../issues/<n>/comments`. Do not repeat what
  someone already said. If an earlier ask was not addressed, say so.
- Stacking: compare the PR's commits with other open PRs. When a PR carries
  another PR's commits, review only its own commits
  (`git diff <parent head> <pr head>`) and mention the stacking.

Verify before claiming anything:

- Fetch heads into throwaway refs:
  `git fetch origin pull/<n>/head:refs/review/pr<n>`.
- Work in a temporary worktree under `<scratch>` and install dependencies the
  way the repository documents. Never switch the branch of the user's
  checkout.
- Run the smallest test, lint and typecheck commands that cover the change.
  Reproduce failing CI locally. Try a fix before suggesting it, then revert it.
- Check conflicts between related PRs with `git merge-tree --write-tree <a> <b>`.
  It needs no commit. Never create commits with another identity or with
  `--no-verify`, not even throwaway ones.
- For UI changes, look at the running UI when the host has a browser (dev
  server or the repository's dev pages), and measure instead of guessing.
- Clean up at the end: the worktree, the `refs/review/*` refs, any servers and
  scratch files.

Write the findings first as a private list for the user. Terse is fine here.
Separate correctness problems from preferences. Drop anything you could not
verify, or turn it into a question.

## 2. Draft comments in the user's voice

Read [references/voice.md](references/voice.md) before writing. In short:

- Plain, short sentences. One point per comment, with the reason in one
  sentence and a concrete ask.
- Ask with "Could we ...?". Start questions with "Question:" or "What do you
  think about ...?". Mark optional items "Small thing:" or "Nit:".
- "Thanks, <first name>!" at most once per batch, in the first comment posted.
  No other thank-yous or praise openers. One specific, true positive per PR is
  fine ("I checked it in the browser and the fields don't jump anymore.").
- Say what you verified ("I tried it locally", "With this the tests pass for
  me"). Never mention AI, agents or tools.
- No em dashes, emoji, headings, bold, severity labels or filler ("I noticed",
  "It seems", "Great job", "Let me know", "ensure", "robust").
- Backticks only for code names and paths. A code block only for a short fix
  you have tested.
- Write in the PR's language, usually English, even when the user talks to you
  in another language.

If another review skill loads automatically (for example `caveman-review`),
use its format only for the private findings list, never for comments that
get posted.

Placement:

- One PR comment (conversation comment) per PR for the overall message and for
  anything that has no line in the diff.
- Inline comments only on right-side lines inside the PR diff, at the reviewed
  head commit. Anchor each one on the line the reader needs to look at.
- Order: PRs in the order the user gave. Within a PR, the PR comment first,
  then inline comments from most to least important.

## 3. Show and get approval

Never post anything before the user approves the exact text.

Write the plan to `<scratch>/plan.json` (format below), never into a
repository, then run:

```bash
python3 <skill>/scripts/post_review_comments.py validate --plan <scratch>/plan.json
```

It checks that each inline line is in the diff at the current head, that the
user has no pending review on the PR, that no comment is already on GitHub,
and it flags voice problems (em dashes, a second thank-you, filler, AI
mentions). Fix every error. Fix warnings unless the wording is deliberate.

Then show the user, in chat:

- One line per PR with the suggested outcome (for example "request changes:
  CI is red") and the merge order when it matters.
- Every comment in posting order: number, PR, location (`path:line` or "PR
  comment"), and the exact body in a ````md fence so it can be copied.
- The account that will post (from `validate`), the order, the random 3-7
  minute delay, and the rough total time. When `gh` has several accounts,
  confirm the active one is the right one.

Ask with the host's question tool when it has one, with the choices "Post all
as shown", "Edit first" and "Don't post"; otherwise ask in chat and wait.
After any edit, update the plan, validate again, show it again and ask again.
Approval covers only the text that was shown.

## 4. Post and verify

Start the poster detached from the session (a detached background shell, or
`nohup ... &`), so a closed session does not stop it halfway:

```bash
python3 -u <skill>/scripts/post_review_comments.py post --plan <scratch>/plan.json >> <scratch>/post.log 2>&1
```

- It runs the same checks as `validate` first and posts nothing if any fail.
- The first comment goes out at once. Before each next one it waits a random
  3-7 minutes (`--min-delay 180 --max-delay 420`).
- Before each inline comment it checks the PR head. If the author pushed, it
  stops, so you can re-check the anchors and ask the user again.
- It records progress in `posted.json` next to the plan, so a rerun skips what
  is already posted.
- It posts plain comments only. Never approve, request changes, resolve
  threads or edit other people's comments unless the user asks.
- Separate comments with delays are deliberate for reviewing other people's
  pull requests. The `pragmatic-engineering` rule to submit replies together
  as one review covers answering feedback on your own pull request.

Check the log every few minutes (`sleep 540; tail <scratch>/post.log`) until
it says `done` or `STOP`. After `STOP` (the author pushed), re-check the
remaining anchors against the new head, show the changes and ask again before
rerunning. Then run `status --plan <scratch>/plan.json` to confirm every
comment exists on GitHub, give the user the links, and delete `<scratch>`.

`post --dry-run --min-delay 1 --max-delay 2` runs the whole flow without
posting, which is useful after changing the script.

## Plan format

```json
{
  "repo": "owner/name",
  "comments": [
    { "key": "42-pr", "pr": 42, "kind": "pr", "body": "Thanks, Sam! ..." },
    {
      "key": "42-hint-gap",
      "pr": 42,
      "kind": "inline",
      "path": "src/components/SaveDialog.css",
      "line": 48,
      "commit_id": "<full head sha that was reviewed>",
      "body": "Small design question, not a blocker. ..."
    }
  ]
}
```

`kind` is `pr` for a conversation comment or `inline` for a diff comment.
Inline comments may add `start_line` for a range. Each `key` must be unique;
reruns use it to skip comments that are already posted.
