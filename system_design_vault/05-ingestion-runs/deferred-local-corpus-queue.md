---
type: deferred-local-corpus-queue
project: agent-studio-system-design
status: active
updated: 2026-05-18
manifest: deferred-local-corpus-queue.json
---

# Deferred Local Corpus Queue

## Purpose

`deferred-local-corpus-queue.json` tracks local files that are present and legally usable as user-provided local material, but should not be promoted into Agent Studio architecture canon by default.

This queue prevents two failure modes:

- forgetting deferred files entirely;
- summarizing low-value, private, or backlog-only material just to create ingestion activity.

## Deferred Categories

| Category | Count | Policy |
|---|---:|---|
| `defer` | 5 | Use only for glossary, onboarding, beginner explanation, or prerequisite gaps not covered by canon-ready sources. |
| `defer_private_notes` | 2 | Do not use as source canon unless the user explicitly asks for the private material in a narrow task. |
| `question_backlog_ready` | 1 | Use as question/eval coverage backlog only, not factual source evidence. |
| `support_ready` | 1 | Small onboarding/prerequisite slice promoted from a deferred local source without making the source architecture canon. |

## Promotion Rules

- Promote only the smallest relevant slice.
- Log the concrete Agent Studio gap before writing notes.
- Preserve rights/provenance status from the local source manifest.
- Do not store raw text, copied tables, exercises, or long excerpts.
- Cross-check against canon-ready local books or official/open sources before any architecture implication is accepted.

## Promoted Support Slices

| Source | Gap filled | Note | Status |
|---|---|---|---|
| `Machine Learning for Humans` | Beginner ML/AI vocabulary and prerequisite concept map for downstream agents before they enter dense release-gate notes. | `02-books/machine-learning-for-humans/onboarding-prerequisite-map.md` | `support_ready`; not architecture canon |

## Agent Studio Implication

Deferred sources are backlog and support material, not hidden canon. The production design should prefer existing canon sources first, then use deferred material only to improve explanations, check question coverage, or fill a specific prerequisite gap.
