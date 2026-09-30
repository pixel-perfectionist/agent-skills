---
name: domain-language
description: Establish and maintain a shared domain language across business discussions, requirements, code, tests, APIs and UI copy. Use when creating or updating a domain glossary, clarifying conflicting business concepts, aligning a feature with agreed terminology, or auditing terminology drift.
---

# Domain Language

Keep each domain concept's meaning consistent from conversation to implementation. Use the project's accepted language and relevant context boundaries. The glossary evolves with agreed business understanding.

## Choose the scope

Infer the mode from the request; do not require the user to learn mode names.

| Mode | Work | Result |
| --- | --- | --- |
| Establish | Discover existing terminology and decisions, resolve consequential ambiguities, and establish or improve the authoritative glossary. | A concise glossary, explicit open questions, and links from the project's actual agent entry points. |
| Apply | Use the glossary during the requested feature or change; extend it when business meaning changes. | Consistent terminology and behavior in the touched scope, with compatibility mappings where needed. |
| Audit | Compare the requested code, documents, or diff with the accepted definitions. | Findings with locations, conflicting meanings, consequences, and proposed corrections. An audit alone does not edit files. |

Establishing a glossary does not authorize a repository-wide refactor. Apply changes within the user's requested scope. No architecture pattern, framework, event system, or database structure is required merely to use this skill.

## Discover the language before naming

1. Read the project's instructions and locate its accepted glossary, domain decisions, and relevant requirements. Common locations include `VOCABULARY.md`, `GLOSSARY.md`, and domain documentation. Reuse the existing authority and layout; do not create a competing glossary. If several sources disagree, follow the project's authority rules or surface the unresolved conflict.
2. Identify the context and map the user's wording to existing concepts. Search the affected implementation and contracts for competing names: models, variables, routes, serializers, schemas, events, tests, fixtures, UI text, examples, and documentation as applicable. Existing code demonstrates implemented behavior; it does not by itself establish intended business meaning.
3. Distinguish a spelling variant, a permitted translation, a legacy alias, and a genuinely different concept. Within one context, a canonical term should have one clear meaning. Across bounded contexts, document different meanings and their translation instead of forcing one global definition.
4. Ask a focused question when competing interpretations change identity, ownership, permissions, relationships, lifecycle, or externally observable behavior. Show the concrete alternatives and their consequences. Continue independent work while that question is pending; do not invent the missing business rule or disguise it behind a new synonym.

Separate **accepted meaning**, **implemented behavior**, and **proposed or unknown meaning**. A requirement in the glossary is not proof that code enforces it. Keep inferred definitions visibly provisional until supported by the user's instructions or accepted domain sources; explicit new business requirements can change earlier definitions.

## Define and maintain concepts

Read [the glossary and adoption guide](references/glossary-and-adoption.md) when creating entries, recording a compatibility boundary, or wiring project instructions.

For relevant concepts, record a concise definition, its context, distinctions from neighboring concepts, important rules, business and code spellings, and the source of the agreed meaning. Add examples or counterexamples when they clarify a real ambiguity. Link to detailed design decisions instead of embedding their full history in the glossary.

Business language and code need a consistent mapping, not identical typography. Respect language conventions such as `Subscription`, `subscription_id`, and localized UI labels without changing the underlying concept. Do not add every technical helper or local variable to the domain glossary.

Apply the language to the conversation as well as the implementation. When a user uses an ambiguous alias, state the canonical concept you are using; ask only if the intended meaning remains consequentially uncertain.

## Change meaning and implementation together

- Update accepted definitions and affected code, tests, UI copy, and documentation in the same change where practical. Include the behavior or business rule behind the name; a cosmetic rename cannot fix a semantic mismatch.
- Separate an internal rename from a persisted or public contract change. For database values, API fields, events, URLs, and external providers, retain the existing boundary spelling through an explicit mapping unless the requested work includes a compatible migration. Record the reason and the condition for retiring that mapping, when known.
- Keep historical migrations, vendor contracts, compatibility tests, and intentional counterexamples intact. A search hit for a retired term is a candidate to inspect, not an instruction to replace it everywhere.
- Record discrepancies outside the requested scope with their consequences and next step. Do not quietly reinterpret the glossary to make existing code appear consistent, and do not expand a naming task into an unrelated migration.

## Make the practice survive the session

When establishing or adopting the workflow, add a short read-first link to the accepted glossary in the project entry points actually used, such as `AGENTS.md` and `CLAUDE.md`. Preserve existing instructions and their precedence. Refer to the definitions instead of copying them into every file; do not create instruction files for tools the project does not use.

For large glossaries, provide an index and load the shared rules plus the relevant context sections. Give isolated reviewers and subagents the definitions and constraints their task needs; do not assume they inherited the parent conversation. Use the project's existing mechanism to register new instruction surfaces when one exists.

Ordinary Apply and Audit requests do not silently add hooks, CI checks, or project-wide policies. Establishing this skill's workflow can add the small instruction links above; automated enforcement is a separate implementation choice. Skill installation alone does not guarantee that every future session loads the glossary.

## Verify and report

Review the changed scope against the glossary's meanings and rules. Search for newly introduced aliases and inspect each remaining legacy spelling in context. When behavior or a public boundary changed, run the relevant checks; do not describe a text search as semantic validation.

Report the glossary used, the meaningful changes or audit findings, unresolved questions, and any compatibility mappings retained. For findings, identify the file or contract and explain the concrete difference in meaning. State limitations where only part of the domain was inspected. In Apply mode, keep this concise and integrated with the feature's normal completion report.
