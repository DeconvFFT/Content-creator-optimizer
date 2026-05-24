---
name: agent-studio-research-grounding
description: "Ground generated social content in real sources. Use when researching a topic, creating source ledgers, checking freshness, extracting claims, mapping claims to evidence, marking unsupported claims, or preparing source-backed briefs for reels, posts, and Substack articles."
---

# Agent Studio Research Grounding

## Workflow

1. Search current primary or high-quality sources before drafting content.
2. Record each usable source as a `SourceRecord` with URL, title, publisher, retrieved date, publication date when available, and provenance metadata that supports quality and freshness scoring.
3. Extract important factual claims into `ClaimRecord` entries before final approval.
4. When fresh web research replaces placeholder seeds, repair weak or missing claim and artifact source dependencies before the next verification pass.
5. Build a `research_freshness_ledger` after source discovery or repair so the run has query-level proof of accepted sources, placeholder seeds, and refresh risks.
6. Mark each claim as `supported`, `needs_review`, or `unsupported`; the Claim Verification worker must persist status changes back to durable claim records instead of only reporting counts.
7. Use the Source Ledger worker to refresh source, claim, artifact, quality, and freshness coverage into a durable `source_ledger` artifact.
8. Use the Data Analyst worker to turn the current source ledger, claim table, and artifact dependencies into a durable `data_brief` artifact with source rows, claim rows, content angles, caveats, chart suggestions, and publish risks.
9. Use the Artifact Librarian worker to persist an `artifact_index` with source, claim, workflow, parent revision, review, and retrieval facets.
10. Pass only grounded briefs to content agents. If a claim has no support, either remove it or preserve it as an explicit open question.

## Source Standards

- Prefer primary docs, papers, official announcements, data releases, and reputable reporting.
- Use current web search for time-sensitive facts.
- Keep citation IDs stable within a run so drafts can refer back to the source ledger.
- Record retrieval timestamps because social content often depends on current model, pricing, product, or benchmark state.
- Replace placeholder search seeds before approval; weak, stale, or unknown-freshness sources referenced by publishable artifacts should block or hold publish readiness until reviewed.

## Outputs

- `research_brief`
- `research_freshness_ledger`
- `data_brief`
- `source_ledger`
- `source_ledger_snapshot`
- `artifact_index`
- `claim_records`
- `unsupported_claim_report`
