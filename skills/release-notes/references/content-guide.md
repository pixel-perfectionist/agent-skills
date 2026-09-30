# Content guide

The reader is the business and product team. They were not in the PRs, and they
will test on stage tomorrow. Every item answers three questions: what changed,
what will I notice, and where do I try it.

## Page structure (in this order)

1. **Header.** Eyebrow "Decipher · Product update for the business team", then
   the title "What changed in Decipher, <Mon D–D>". The lead gives the PR count
   and says the page covers what users and admins notice, biggest first, with
   screenshots from stage (name the Company). The meta row carries the date
   prepared, the stage link, and "click any screenshot to enlarge it".
2. **At a glance.** 5–7 bullets, each a bold one-line claim plus one plain
   sentence. A reader who stops here knows the headline changes.
3. **Legend + section chips** (from the template).
4. **Changes how you work** (`tag change`). Anything that alters an existing
   screen, rule, default or data: removed tabs, retired concepts, new blockers
   on publishing, data that was deleted or migrated, access that got narrower.
   Rank by how many people notice it, then by how surprising it is.
5. **New capabilities** (`tag new`). Things to try that take nothing away.
   Finish with a "Smaller additions" list card.
6. **Access & security** (`tag access` wording in the list). Mostly invisible,
   but it decides what limited-access people see.
7. **Faster and sturdier.** One paragraph for all performance, logging and
   clean-up PRs, with a PR range.
8. **In progress this week.** Dashed cards from open PRs and anything the user
   says the team is working on. Not on stage yet, or only as a prototype.
9. **Before this reaches customers** (`list-card rollout`). Decisions and checks
   for beta and production (see below).
10. **All N pull requests.** A collapsed appendix built by
    `scripts/build.py appendix`.

## One change item

```html
<article class="change" id="<slug>">
  <div class="change-head">
    <span class="tag change">Changes how you work</span>   <!-- or: new, access -->
    <h3>Title that states the outcome</h3>
  </div>
  <p class="summary">2–3 sentences: what it is and why it matters.</p>
  <span class="notice-label">What you'll notice</span>
  <ul><li>2–5 concrete, observable facts</li></ul>
  <p class="heads-up"><strong>Heads-up:</strong> the one thing that will confuse people.</p>
  <div class="shots two|pair">…figures…</div>
  <div class="foot">
    <a class="try" href="https://stage.decipherip.ai/…">Try it on stage → where › what to click</a>
    <span class="prs">#1234 #1240</span>
  </div>
</article>
```

- **Titles state the outcome.** Write "Personas and Organizations are linked through
  form fields", not "Reference Fields refactor".
- **Group PRs into one item per feature.** A feature built across 15 PRs is one
  item listing all 15 numbers.
- **Use a heads-up** for one surprise per item at most. Examples: emptier panels
  after a migration, a default that changed, data that was not carried over.
- **Figures.** Use `shots` for one wide image, `shots two` for wide plus narrow,
  and `shots pair` for two equal images. A caption names the record ("NDA-26-0032")
  and says what to look at. If an example isn't configured on stage, say so and
  tell the reader how to set one up.
- **"Try it" links** point at a real stage record. A link that only works in
  another Company says which one.

## Copy rules

- Write from the user's side of the screen, with the labels they will see in
  the UI ("Freezes the record", "Send for signature"). Use glossary terms for
  concepts (Asset, Asset Configuration, Persona, Organization, Status,
  Transition, Record Lock, Group, Data Silo).
- Use short, direct sentences in the active voice. Leave out em-dash asides,
  "not X but Y" framing, and stock phrases.
- Leave out code names, table names, migrations and endpoints. PR numbers go
  only in `.prs`.
- Describe the product as it is today. If PR #1 added something and PR #9
  changed it, describe what #9 left.
- Every sentence that says something was deleted, removed, defaulted or sent to
  a third party must be verified against a PR body (SKILL.md step 4).

## "Before this reaches customers": what belongs there

Look through the reports' "surprises" sections and PR bodies for:

- **Data** that migrations delete or do not carry over. Name what, and give the
  action ("export first").
- **Third-party processing** of customer content, such as embeddings or LLM
  calls. Say which provider, and that data-processing terms need confirming.
- **Infrastructure** a release needs, such as a database extension, an env key,
  a manual command, or a backfill.
- **Defaults that changed per Company**, such as Modules now opt-in, or
  Configurations needing a republish.
- **Stage caveats**: the backend is deployed by hand, and the screenshot build
  may lack some merged PRs.

## Paste-ready Teams message

Keep it under 12 lines:

```text
Hi team — attached is a summary of everything we shipped <period>, sorted by
impact, with screenshots from stage. Download it and open it in any browser.

The biggest changes to know before <meeting>:
• <at-a-glance bullet 1, one line>
• <bullet 2>
• <bullet 3>
• <bullet 4>
• <bullet 5>

Please skim it before the meeting and note your questions. The last section lists
decisions we need before this reaches customers.
```
