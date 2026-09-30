# Explore agent prompt: one slice of the window

Launch up to three of these in one message (`subagent_type: Explore`,
`run_in_background: true`), one per date slice. Fill in `<A>`, `<B>`, the
checkout path, and the "Known context" line when you already know some PRs.
The last slice also takes the open PRs.

```text
Read-only research. Repo DecipherIP/decipher; local checkout at <checkout> (run
commands from there). Do NOT modify files, branches, or any GitHub state. Use
the `gh` CLI. If a Bash call fails with a transient "classifier gave no verdict"
error, retry it.

GOAL: raw material for a concise English change digest for the company's
NON-technical business/product team. They must understand what changed for
users, what may surprise them, and where to look on stage
(https://stage.decipherip.ai; the frontend auto-deploys from main, the backend
is deployed by hand).

YOUR WINDOW: PRs merged <A> through <B> inclusive.
[Last slice only: PLUS open PRs updated since <window start> (in-progress work).]

Steps:
1. gh pr list --repo DecipherIP/decipher --state merged --search "merged:<A>..<B>" --limit 200 --json number,title,mergedAt,author
2. For EVERY PR: gh pr view <n> --repo DecipherIP/decipher --json title,body,author,mergedAt,labels
   and read the body (summary, decisions, test plan). For big or vague ones also
   gh pr diff <n> --repo DecipherIP/decipher --name-only | head -60
3. For each user-visible change, find the page where a user sees it: map it to
   route folders under frontend/app/(app)/** using the actual Experience
   prefixes verified in this checkout, and to the PR's test plan. Give a concrete stage path and what to click.
4. Use the repo's domain names. VOCABULARY.md is large (400+ KB): grep it for
   a term, never read it whole.

Known context (verify against the PR bodies, don't repeat blindly): <optional>

REPORT (markdown, no code):
A. Table, one row per PR: PR# | merged | author | title | visibility
   (user-visible / admin-only / platform-only / internal) | area | 1–2
   plain-English sentences of effect for a business reader | behaviour change
   for EXISTING users (what they will notice) | stage path to see it | needs
   backend deploy or migration? (name migrations)
B. [Last slice] Table of OPEN PRs: PR# | title | author | draft? | what it will
   do, in one plain sentence | status.
C. Group related PRs into features; give each feature a plain name and a
   one-paragraph business summary.
D. Say explicitly whether the window touches each theme in this list, with PR
   numbers and one line each: <themes the user named, plus: access / Data
   Silos, Persona Roles and Groups, search, performance>.
E. Things likely to SURPRISE existing users: removed or moved tabs and
   screens, renamed concepts, data migrations that change what is displayed or
   delete data, features now off by default, retired features.
Be complete: every merged PR in the window must appear in table A.
```

## Using the reports

- Agents' tables are raw material, never page copy. Rewrite everything in the
  voice of `content-guide.md`.
- Section E of each report feeds "Changes how you work" and "Before this
  reaches customers".
- When two slices disagree about the same feature, the later PR wins. Say what
  the page looks like **today**, not what an intermediate PR did.
