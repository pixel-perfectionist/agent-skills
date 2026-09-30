---
name: crossfire
description: Stress-test a decision, idea, proposal or plan with a Strategist, Advocate, Critic and Observer, then synthesize an evidence-based recommendation. Use when explicitly invoked as $crossfire in Codex, /crossfire in Claude Code, or a requested Crossfire review.
disable-model-invocation: true
argument-hint: "<decision, idea, proposal or plan>"
---

# Crossfire

> **The purpose of the Council is not to make a decision sound intelligent. Its purpose is to expose what must be true for the decision to be good.**

A pros-and-cons list is not a Council. The Council:

1. finds out which decision is actually being made;
2. builds the strongest case for it;
3. tries to find why it will fail;
4. judges the quality of those arguments independently;
5. names the missing data;
6. proposes the next step that most cheaply reduces uncertainty.

```
                 ┌──────────┐
                 │  Critic  │  what kills the idea
                 └────▲─────┘
┌──────────┐          │          ┌────────────┐
│ Observer │ ◄──  COUNCIL  ◄──── │ Strategist │  what decision is this
└──────────┘          │          └────────────┘
  judges all     ┌────▼─────┐
                 │ Advocate │  hidden upsides
                 └──────────┘

Strategist → (Advocate ∥ Critic) → one cross-examination → Observer → Synthesis
```

Four standing roles. **Synthesis is not a fifth character** — it is the Council itself weighing what the roles produced.

## Non-negotiables

- **No artificial consensus.** A material disagreement that survives cross-examination survives into the output, stated as a disagreement.
- **No voting.** "Advocate yes, Critic no, Observer yes → 2:1" is forbidden. Arguments are weighed by evidence and consequence, not counted.
- **Label every load-bearing claim** — see Evidence below.
- **No false precision.** Confidence is High / Medium / Low with a reason, never a percentage.
- **Proportionality.** A trivial question gets a short answer (Quick mode). A question that hinges on an unknown gets a way to find it out, not more reasoning (Blocked mode).
- **Honesty over rhetoric.** The Advocate never hides a known flaw; the Critic never inflates a risk to win.
- **Roles stay pure.** The Strategist neither defends nor attacks. The Observer adds no third list of pros and cons.

## Evidence

Every claim a conclusion rests on carries one label:

| Label | Meaning |
|---|---|
| **Known** | Confirmed by the context — the user's words, a file read, a tool result — or a reliable source. Say which. |
| **Inferred** | Follows logically from Known claims. Show the step. |
| **Assumed** | Taken as true without enough evidence. |
| **Unknown** | No data. |

When the decision materially depends on an Unknown, never paper over it with a confident conclusion. Write: **"Decision depends on X."**

## Procedure

### Step 0 — Take the input

The idea comes from the argument and the conversation. If there is none, ask for it and stop.

If the decision concerns something inspectable — a codebase, a document, data, a system — read what the decision turns on *before* the debate, so the roles argue over facts from the source rather than from memory. Read only what the decision needs.

### Step 1 — Strategist (main context)

**Question: what decision are we actually making?**

The Strategist runs in the main context because it needs the conversation; the other roles do not see it. It neither defends nor criticizes. It produces the **Brief** — the shared factual input for every role, alongside that role's instructions and the handoffs specified below. The Brief must be self-contained:

```
BRIEF
Original idea:      <as the user put it>
Problem it solves:  <...>
Decision question:  <the normalized question — see Reframing>
Goal:               <...>
Success criteria:   <observable, so "did it work?" has an answer>
Constraints:        <budget, time, team, tech, policy...>
Facts:              - <claim> [Known: source]
Assumptions:        - <claim> [Assumed]
Unknowns:           - <what is missing, and why it matters>
Alternatives:       - <obvious ones; always include "do nothing / keep the status quo">
Context:            <everything a role needs that lives only in the conversation or in files read>
Specialists:        <none | up to 3, each with the reason its expertise changes the decision>
Mode:               Full | Quick | Blocked — <why>
```

**Reframing.** A vague question gets normalized before anyone argues about it, so every role argues about the same thing:

- *Should we use PostgreSQL?*
- → *Should project metadata currently stored in Azure Blob Storage be migrated to PostgreSQL, while binary assets stay in Blob Storage?*

If the normalization hinges on something only the user knows **and** the possible answers send the Council in different directions, ask **one** question and wait. Otherwise state the reframing as an Assumption and proceed.

**Specialists.** Add one only when its expertise could change the decision, never "for completeness". Menu:

- *Software architecture:* Security, Performance, Infrastructure
- *Product:* UX, Customer, Market
- *Business:* Finance, Sales, Legal

**Mode.**

- **Quick** — the decision is trivial, cheap to reverse or low-stakes, with no real alternative worth debating. Go to *Quick output*.
- **Blocked** — the Brief already shows an Unknown the decision turns on that reasoning cannot resolve. Go to *Blocked output*.
- **Full** — everything else.

### Step 2 — Advocate ∥ Critic (independent, in parallel)

Both receive their role instructions and the same Brief. Neither receives the parent conversation or another role's work before Step 3. Specialists, if any, use the same isolation. Run independent reviews in parallel when capacity allows; separate contexts preserve independence even when capacity requires successive batches.

**Advocate — what is the strongest possible case for this idea?**
A steelman, not a sales pitch. It covers the main advantages, the hidden advantages, long-term options the idea opens, why it beats the alternatives, what problems it removes, which objections can be softened, and the conditions under which it works best. It must write the two sentences *"The strongest argument for this idea is …"* and *"This idea works especially well if …"*. It must list the known weaknesses it could not argue away.

**Critic — what could kill this idea?**
It assumes the idea may be wrong and tries to show it. It hunts for fatal flaws, wrong assumptions, hidden complexity and cost, security, scalability and operational risk, maintenance burden, UX harm, organizational dependencies, second-order effects, opportunity cost and edge cases. It must run a **premortem**: *"We implemented this. Six months later we consider it a mistake. What most likely happened?"*. It classifies every serious objection:

| Class | Meaning |
|---|---|
| **Fatal** | The idea must not proceed until this is solved. |
| **Major** | Significant, but it can be mitigated. |
| **Minor** | A real drawback that does not change the decision. |
| **Unknown** | Cannot be rated without more data. |

**Specialist** — answers the Decision question strictly through its own lens. It lists the findings that bear on the decision, with evidence labels, and gives no overall verdict.

### Step 3 — Cross-examination (one round)

1. The **Advocate** receives the Brief, its initial report, the Critic's report and all specialist findings. It answers **only the strongest objections**: every Fatal and each specialist finding that could block the proposal, then the Majors most likely to change the decision. Normally cover at most five; never omit a blocker to meet that limit. Preserve each finding's source. Each answer is a rebuttal, a mitigation or a concession checked against the Brief's constraints. No new arguments in favour.
2. The **Critic** receives the Brief, its initial report, all specialist findings and the Advocate's answers. It classifies any serious specialist objection using Fatal / Major / Minor / Unknown, then rules on the objections addressed: **Resolved**, **Partially resolved**, **Unresolved**, or **Requires evidence** (saying what evidence). It explicitly carries forward unanswered serious objections. It may add objections only from specialist findings or risks introduced by an answer. A proposed mitigation does not establish resolution until the evidence supports it and it meets the Brief's constraints.

Use the complete continuation templates below for both resumed and replacement agents. One round is enough. Whatever remains unresolved goes to the Observer as it is. Do not start a second round.

### Step 4 — Observer

**Question: what is actually happening in this debate?**

The Observer receives the full record: the Brief, both reports, any specialist findings and the cross-examination. It judges the **reasoning**, not the idea. It does not produce another list of pros and cons. It checks:

- where facts are used, and where assumptions are passed off as facts;
- unsupported claims;
- where the Advocate is too optimistic, and where the Critic overstates a risk;
- where the two sides argue from different assumptions;
- which arguments would actually change the decision, and which are noise;
- which single piece of data would settle each live disagreement.

The most valuable finding is a **hidden disagreement**. For example, the Advocate says *"PostgreSQL simplifies querying"* and the Critic says *"PostgreSQL adds needless infrastructure"*. The Observer notices that the dispute is not about PostgreSQL at all: the two sides assume different future query complexity. The disagreement then becomes the fact that settles it: expected query complexity.

### Step 5 — Synthesis (the Council, main context)

Weigh evidence and consequence, never headcount. A recommendation may be conditional ("A if X, otherwise B"). Where the decision depends on an Unknown, say so.

This completes the Council stage. When it produces a concrete plan, offer the separate next stage: **“Type AI ping pong to have Claude Opus 5.5 and Codex GPT-6 Astra review and refine this plan until both approve.”** That stage is the `ai-ping-pong` skill. Do not start it merely because the Council finished; the user must request it. Council conclusions are not approval by both external models.

## Output

Write in the user's language. Keep the section order below.

### Full output

- **Decision question** — the normalized question.
- **Recommendation** — the best-supported direction right now. It may be conditional.
- **Why** — the 2–4 reasons that carry the most weight.
- **Strongest case for** — the Advocate's best argument, as it survived cross-examination.
- **Strongest case against** — the Critic's best argument, as it survived cross-examination.
- **Critical assumptions** — what must turn out to be true for the recommendation to be good.
- **Unresolved risks** — whatever the debate did not close, with its Critic class.
- **Unknowns** — the missing information, and which part of the decision each one blocks.
- **What would change the recommendation** — concrete triggers, such as *"changes if expected traffic exceeds X"* or *"changes if the API cannot support Y"*. This section is required.
- **Next step** — the cheapest action that reduces the biggest uncertainty: a prototype, benchmark, user test, experiment, research, architecture spike, a question to a stakeholder, or a look at production data. Say what result would mean what.
- **Confidence** — High, Medium or Low, plus the reason. For example: *"Medium: the architecture is understood, but production query volume and migration cost are unknown."*
- **Preserved disagreement** — include only when one survived: each position, and the evidence that would decide between them.

Then add a short **Council record**, one or two lines per role, with the point each role contributed that mattered most. Give the full role reports only when asked.

### Quick output

Use this when the Strategist chose Quick. Give the **Decision question**, **Recommendation**, **Why**, **Main risk**, **What would change it**, **Next step** and **Confidence**. Open with one line saying why a full Council was not needed.

### Blocked output

Use this when a decision-critical Unknown makes further reasoning pointless. It can come from the Strategist or at any later step. Give:

- **Decision question**
- ***"We cannot resolve X from reasoning alone."*** — and why X decides the matter.
- **How to get X** — the cheapest way to obtain it.
- **Conditional recommendation** — *"If X …, then A; if X …, then B."*
- **Already clear** — whatever the Council did establish.

Do not produce more debate to fill the gap.

## Running it

Choose the execution path from the available tools and their context controls. Codex and Claude Code can both provide subagents; the product name alone does not determine which path applies.

### With isolated subagents

- The **Strategist** and the **Synthesis** run in the main context.
- The **Advocate**, **Critic** and any **specialists** are separate agents with fresh contexts. Disable parent conversation inheritance where configurable (for example, `fork_turns="none"` when that option exists). Each initial prompt contains only its role template and the Brief, pasted verbatim. Keep shared project instructions in force. The agents are read-only: they may read relevant files and search, and they never edit anything.
- Launch independent reviews before waiting where the harness allows it. Respect its concurrency limit; use isolated batches if needed, without passing earlier reports into later initial reviews. Wait for all initial reports and specialist findings before cross-examination.
- **Cross-examination:** use a continuation operation that actually starts a new turn on the same agent when supported. Otherwise start a fresh agent with the full corresponding continuation template below. Each template restates the role's task and includes the original Brief, its initial report and all incoming review material; an earlier report alone is insufficient. Finish the Advocate's answers before starting the Critic's continuation.
- The **Observer** is a fresh agent with no inherited conversation. Pass its template with the Brief, both initial reports, all specialist findings and both cross-examination responses.
- Report progress in one line per stage, e.g. "Brief ready → Advocate/Critic running → cross-exam → Observer → synthesis".
- **Cost:** Full mode uses 2 agents + specialists + 1 Observer + 2 cross-examination turns; replacement agents add startups. Quick and Blocked chosen before the debate use no agents. If a required report fails to arrive, identify the missing contribution and limit the recommendation accordingly; do not invent it.

### Without isolated subagents

Use this path only when subagents are unavailable or their contexts cannot be isolated. Run the roles one after another in the same context, using the same templates and complete handoffs. Base each initial role on the Brief, and never quote or answer another role before Step 3. Do the Critic before the Advocate. Independence here is simulated, so anchoring is possible: mention that once in the Council record.

## Role prompts

Replace each placeholder with its full content. Paste the same Brief wherever it says `{BRIEF}`. For `{SPECIALIST FINDINGS}`, supply all specialist reports, or `None` when no specialists were used. Never infer that a missing report means no findings.

**Advocate**
```
You are the Advocate on a decision council. Build the strongest honest case FOR the decision
below: a steelman, not a sales pitch. You have not seen any criticism, and must not guess it.
Cover the main advantages, the hidden advantages, long-term options it opens, why it beats the
listed alternatives, the problems it removes, how the likely objections can be softened, and
the conditions under which it works best.
Write the two sentences "The strongest argument for this idea is …" and "This idea works
especially well if …".
List the known weaknesses you could not argue away. Hiding them is failure.
Label every load-bearing claim [Known: source] / [Inferred: step] / [Assumed] / [Unknown].
Read files or search if the Brief points at them. Never edit anything. Under 500 words.

{BRIEF}
```

**Critic**
```
You are the Critic on a decision council. Assume the decision below may be wrong and try to show
it. You have not seen the case for it.
First run a premortem: "We implemented this. Six months later we consider it a mistake. What
most likely happened?"
Then list the serious objections. Look for fatal flaws, wrong assumptions, hidden complexity and
cost, security, scalability, operations, maintenance burden, UX harm, organizational dependencies,
second-order effects, opportunity cost and edge cases.
Give each objection one class: Fatal (must not proceed until solved) / Major (mitigable) /
Minor (doesn't change the decision) / Unknown (can't rate without data).
For each one, give the evidence label and what would resolve it. Do not inflate risks to win;
an unclassified laundry list is failure.
Label every load-bearing claim [Known: source] / [Inferred: step] / [Assumed] / [Unknown].
Read files or search if the Brief points at them. Never edit anything. Under 500 words.

{BRIEF}
```

**Specialist** (`{LENS}` = e.g. Security)
```
You are the {LENS} specialist on a decision council. Answer the decision question below
strictly through the {LENS} lens. List only the findings that could change the decision, each
with an evidence label and its consequence. Give no overall verdict. Never edit anything.
Under 300 words.

{BRIEF}
```

**Cross-examination: Advocate**
```
You are the Advocate continuing a decision council. This is cross-examination, not a repeat
of your initial report. Defend the proposal honestly against the strongest objections from
the Critic and specialists. Cover every Fatal and each specialist finding that could block
the proposal, then the most decision-relevant Majors. Normally cover at most five; never
omit a blocker to meet that limit. Preserve each finding's source. For each, give a rebuttal,
mitigation or concession checked against the Brief's constraints and success criteria.
Add no new arguments in favour. Label load-bearing claims [Known: source] / [Inferred: step] /
[Assumed] / [Unknown]. Never edit anything.

Original Brief:
{BRIEF}

Your initial report:
{ADVOCATE REPORT}

Critic's initial report:
{CRITIC REPORT}

Specialist findings:
{SPECIALIST FINDINGS}
```

**Cross-examination: Critic**
```
You are the Critic continuing a decision council. This is cross-examination, not a repeat
of your initial report. Classify any serious specialist objections: Fatal (must not proceed
until solved) / Major (mitigable) / Minor (doesn't change the decision) / Unknown (needs data).
For the objections addressed, rule Resolved / Partially resolved / Unresolved / Requires
evidence (say what evidence), with a reason checked against the original Brief. Explicitly
carry forward unanswered serious objections. Preserve each finding's source. A proposed
mitigation establishes resolution only when supported by evidence and consistent with the
Brief's constraints. Add objections only from specialist findings or risks introduced by an
answer. Label load-bearing claims [Known: source] / [Inferred: step] / [Assumed] / [Unknown].
Never edit anything.

Original Brief:
{BRIEF}

Your initial report:
{CRITIC REPORT}

Specialist findings:
{SPECIALIST FINDINGS}

Advocate's cross-examination answers:
{ADVOCATE ANSWERS}
```

**Observer**
```
You are the Observer on a decision council. Judge the REASONING in the record below, not the
idea. Do not add your own pros and cons.
Report:
(1) claims presented as fact that are really assumptions, and claims with no support;
(2) where the Advocate is too optimistic, and where the Critic overstates a risk;
(3) hidden disagreements, where the two sides rest on different assumptions: name the
    assumption and the fact that would settle it;
(4) which arguments would actually change the decision, and which are noise;
(5) the single most decision-relevant piece of missing evidence.
Under 400 words.

{BRIEF}
{ADVOCATE REPORT}
{CRITIC REPORT}
{SPECIALIST FINDINGS}
{CROSS-EXAMINATION}
```

## Anti-patterns

- A pros-and-cons list presented as a Council.
- Counting votes, or averaging the roles.
- Confidence given as a percentage.
- A Strategist that argues a side, or an Observer that acts as a third debater.
- A full Council on a trivial question, or more reasoning thrown at a decision-critical Unknown.
- Specialists added by default.
- An Advocate that hides known flaws, or a Critic that lists every conceivable risk without classifying it.
- A consensus manufactured in the synthesis that the debate never reached.
- A recommendation without **What would change the recommendation**.
