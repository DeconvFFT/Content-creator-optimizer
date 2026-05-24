---
type: concept
project: agent-studio
status: active
updated: 2026-05-17
owners:
  - context-engineering-agent
  - interactive-note-taking-agent
  - artifact-librarian
confidence: high
source_notes:
  - [[../../raw/articles/2026-05-17-mitcham-ai-agent-operating-system]]
  - [[../../SCHEMA]]
---

# Three-Tier Agent Memory

## Definition

Three-tier agent memory separates evidence, synthesis, and deliverables:

1. Raw memory records what happened or what was sourced.
2. Wiki memory stores reusable understanding.
3. Output memory stores generated artifacts and views.

This prevents the system from treating every note, draft, screenshot, and source as equally authoritative.

## Tier Responsibilities

### Raw

Raw memory is append-only evidence.

Examples:

- User feedback.
- Web references.
- Run event exports.
- Research notes.
- Screenshot metadata.
- Provider test observations.

Raw memory answers: what did we see, hear, read, or receive?

### Wiki

Wiki memory is curated project knowledge.

Examples:

- Architecture decisions.
- System constraints.
- Agent policies.
- Memory routing rules.
- Retrieval and guardrail design.
- Runbooks.

Wiki memory answers: what does the project currently believe?

### Output

Output memory is derived presentation and delivery.

Examples:

- JSON architecture state.
- HTML viewers.
- Review packets.
- Reports.
- Drafts.
- Handoff summaries.

Output memory answers: what did we generate from the current memory?

## Authority Order

When notes conflict:

1. Raw evidence wins for source facts.
2. Decision log wins for explicit decisions.
3. Wiki wins for current synthesized design.
4. Output is regenerated if stale.

## Retrieval Policy

Agents should search in this order:

1. Relevant wiki index and current sprint.
2. Relevant wiki page.
3. Decision log for explicit constraints.
4. Raw notes for evidence.
5. Generated output only for review or display context.

## Maintenance Policy

The memory system should improve between user prompts.

Recurring checks should look for:

- Raw sources that have not been compiled into wiki knowledge.
- Wiki pages with stale `updated` dates or low confidence.
- Broken links, orphan pages, and pages missing frontmatter.
- Output artifacts that point at old wiki state.
- Retrieval ledgers with precision risks, recall gaps, or coverage gaps.

## Search Policy

Use hybrid retrieval when semantic search is available:

- Keyword search for exact decisions, IDs, URLs, file paths, and non-negotiables.
- Vector search for related concepts, repeated lessons, and synthesis.
- Reranking for final evidence selection before agents act.
- Graph traversal for connected claims, sources, memories, and artifacts.

## Context Savings

The point is not to store more text. The point is to store the right text at the right layer so agents can load small, high-signal notes instead of replaying the whole conversation.

## Agent Operating Pattern

For Agent Studio, the three tiers create a concrete loop:

1. Capture the source or user signal in `raw/`.
2. Compile stable policy or architecture into `wiki/`.
3. Generate JSON, HTML, reports, and content from `wiki/` into `output/`.

Codex should read [[../ops/active-codex-context]] first for compact state, then open only the subsystem note needed for the current slice. This is how the vault reduces token load without hiding important decisions.
