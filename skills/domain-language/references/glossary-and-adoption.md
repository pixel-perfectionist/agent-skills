# Glossary and adoption guide

Use these shapes selectively and preserve the project's existing conventions. A small domain can use one file; larger domains can use an index with context-specific sections or files. Avoid duplicate authorities for the same concept.

## Concept entry

```markdown
### Canonical term

- Context: The bounded context in which this definition applies.
- Meaning: One clear definition in business language.
- Distinguish from: Nearby concepts and the precise difference.
- Business rules: Accepted invariants or lifecycle rules relevant to this concept.
- Business and code forms: Singular/plural terms, localized labels when needed,
  and the corresponding type, field, or operation names.
- Example / counterexample: Include only if it resolves a likely ambiguity.
- Basis: The user decision, requirement, or domain source establishing the meaning.
- Status or gap: Note proposed meaning, an unanswered question, or a known
  implementation gap when applicable; do not present it as an enforced rule.
- Compatibility: Link any retained external or persisted spelling and its mapping.
```

This is a writing aid, not a required schema. Omit irrelevant fields. Existing accepted entries do not need a new approval ceremony merely because they are reformatted.

For example, an accepted Subscription concept might use `Subscription` as a type and `subscription_id` as its identifier. That naming convention alone says nothing about cancellation, renewal, or billing behavior; those rules must come from the domain. A translated label can denote the same concept without becoming a different entity.

## Compatibility mapping

Use a small entry near the affected concept or link an existing migration decision:

| Field | Record |
| --- | --- |
| Accepted concept | The canonical term and context. |
| Boundary spelling | Exact API key, event field, database value, URL, or vendor label. |
| Mapping | Where and how the external representation becomes the domain concept. State if it is only a partial mapping. |
| Reason retained | The consumer, stored data, or integration requiring compatibility. |
| Change condition | The agreed migration, deprecation, or removal condition, if known. Do not invent a deadline. |
| Verification | The contract or behavior check needed when that boundary changes. |

If one field conflates multiple meanings, record the conflict rather than claiming a one-to-one mapping. Follow the project's existing migration practice and treat external consumers as part of the change's scope.

## Project instruction links

During Establish mode, inspect the actual agent entry points before editing. Add a short section or update an existing one, preserving unrelated instructions. Adapt this example to the real glossary path and the project's precedence rules; resolve relative links from each entry point's directory.

```markdown
## Domain language

Before planning, editing, or reviewing domain work, read
[the domain glossary](VOCABULARY.md), including the shared rules and relevant
context sections. Use its accepted definitions in discussion, code, tests,
APIs, and UI copy. Clarify consequential ambiguity before choosing a meaning.
Update the glossary when agreed business meaning changes, and preserve
persisted or public contracts through explicit compatibility mappings.
```

Do not leave the example link pointing at a nonexistent file. A repo with an existing `docs/domain/glossary.md` should link there; an entry point in a child directory needs a path relative to that directory. When the project has no glossary, choose its location using existing documentation conventions, with `VOCABULARY.md` as a simple fallback.

Keep a context index when needed, linking each entry to its scope. Independently invoked agents need a way to find that authority; delegated agents need the relevant excerpts or readable links in their handoff. Preserve the project's precedence rather than inserting a universal instruction hierarchy.

## DDD foundations

This skill applies ubiquitous language and explicit context boundaries. It does not prescribe the full set of DDD tactical patterns. The sources below explain the concepts; they do not evaluate this AI skill's effectiveness.

- Eric Evans, [Domain-Driven Design Reference: Definitions and Pattern Summaries](https://www.domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf), 2015. Connects a shared language to the domain model within an explicit bounded context.
- Martin Fowler, [Ubiquitous Language](https://martinfowler.com/bliki/UbiquitousLanguage.html), 2006. Describes language used and refined in collaboration between developers and domain experts.
- Martin Fowler, [Bounded Context](https://martinfowler.com/bliki/BoundedContext.html), 2014. Explains why larger systems may need different models and explicit mappings across contexts.
