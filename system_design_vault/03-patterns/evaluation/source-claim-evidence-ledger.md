---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-19
sources:
  - "[[03-patterns/retrieval/reranking-search-kg-patterns]]"
  - "[[03-patterns/evaluation/eval-design-canon]]"
  - "[[01-sources/official-open/document-layout-ocr-ingestion-runtime]]"
  - "[[01-sources/official-open/web-source-acquisition-and-crawl-governance]]"
  - "[[01-sources/official-open/openai-file-search-vector-stores-web-search]]"
  - "[[01-sources/official-open/anthropic-contextual-retrieval]]"
  - "[[03-patterns/source-governance/source-freshness-invalidation]]"
  - "[[05-ingestion-runs/obsidian-ingestion-operating-model]]"
  - "[[04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
stores_raw_source_text: false
---

# Source Claim Evidence Ledger

## Purpose

This pattern defines how Agent Studio turns sources into supported claims without copying source payloads into the vault. It connects ingestion provenance, retrieval evidence, claim verification, citation validity, and architecture decisions into one auditable lifecycle.

The rule is simple: a claim is not supported because a source exists nearby. A claim is supported only when the datastore can show which source snapshot, extracted chunk or layout element, retrieval trace, accepted evidence, verification check, and decision reference justified it.

## Lifecycle

| Stage | Required record | Promotion question |
|---|---|---|
| Source identity | `source_record`, `source_terms_review`, `coverage_status` | Is this source legal, current enough, relevant, and allowed for this use? |
| Extraction | `document_extraction_job`, `layout_chunk_record`, `text_boundary_record`, `extraction_transform_record` | Did the parser preserve the page, heading, table, figure, offset, or layout context needed for the claim? |
| Retrieval | `retrieval_trace`, `retrieval_span_record`, `context_precision_result`, `context_recall_result` | Did the route find enough relevant evidence and avoid dropping required counterevidence? |
| Evidence decision | accepted/rejected evidence refs with rejection reasons | Which candidates are supporting evidence, contradictory evidence, stale evidence, or insufficient evidence? |
| Claim check | `faithfulness_claim_check`, `answer_canon_check`, `hallucination_eval_case` | Is the claim entailed, contradicted, unsupported, stale, policy-inconsistent, or outside the reference world? |
| Product decision | `decision_reference`, route/release gate refs | Which architecture note, artifact, route, or publish decision is allowed to depend on this claim? |

## Claim States

Use stable claim-support states instead of prose-only labels:

| State | Meaning | Allowed use |
|---|---|---|
| `supported` | Accepted evidence directly supports the claim under the current source snapshot and reference-world policy. | Can appear in canon notes, route proposals, and publishable artifacts when other gates pass. |
| `supported_with_caveat` | Evidence supports the claim but has scope, freshness, measurement, or extraction caveats. | Can appear with the caveat attached; cannot be generalized beyond the caveat. |
| `needs_review` | Evidence exists but support depends on interpretation, conflicting sources, weak extraction, or low-confidence retrieval. | Human review or stronger evidence required before canon/publish use. |
| `unsupported` | No accepted evidence supports the claim. | Must be removed, rewritten as an assumption, or sent to source refresh. |
| `contradicted` | Accepted evidence conflicts with the claim. | Must block publication and route promotion until resolved. |
| `stale_or_unverified_current` | The claim may have changed since the source snapshot. | Requires official/current refresh before current-state claims. |
| `out_of_scope_source` | The source exists but rights, provenance, or relevance does not permit this use. | Inventory-only; not evidence. |

## Reference-World Discipline

Every factuality check should name the reference world:

- `source_snapshot`: support is measured only against the cited local PDF/doc/web snapshot.
- `current_official_state`: support requires current official docs or public pages.
- `product_policy`: support is measured against Agent Studio policy or release-gate requirements.
- `runtime_observation`: support is measured against a live trace, smoke proof, metric, or artifact state.
- `human_decision`: support is measured against reviewer approval or rejection.

This prevents an answer from being marked "hallucinated" when the real issue is stale docs, wrong policy, weak retrieval, unsupported generalization, or unverified current state.

## Accepted And Rejected Evidence

Accepted evidence should store source/chunk refs, support type, caveat, extraction quality, and freshness. Rejected evidence should store why it was rejected: wrong entity, wrong time window, weak source, duplicate, contradiction, rights block, low extraction quality, or irrelevant after reranking.

Rejected evidence is not clutter. It is what lets Agent Studio improve recall, audit false negatives, tune rerankers, explain reviewer overrides, and avoid reusing the same weak source during source repair.

## Release Gate

Use a `source_claim_evidence_release_gate` before a source-backed route, canon note, or publishable artifact relies on generated claims. Required evidence:

- `source_record_refs`, rights/provenance status, source snapshot identity, freshness policy, and source terms review where relevant;
- extraction job, parser profile, page/section/layout coverage, text boundary, table/figure handling, and known-loss caveats;
- retrieval trace, searched indexes, query rewrites, filters, accepted and rejected evidence, reranker/fusion policy, and retrieval precision/recall checks;
- claim records with support state, contradiction state, reference-world policy, caveats, and reviewer override where applicable;
- citation validation policy, final artifact refs, decision references, unsupported-claim count, stale-current-claim count, and rollback or source-refresh action.

Do not promote when:

- claims cite a source file or URL but not a specific accepted evidence record;
- search-query seed URLs are treated as evidence before provider-backed fetch/extraction/retrieval;
- retrieval quality is missing and raw source IDs are allowed to bypass it;
- final artifacts hide unsupported, contradicted, or stale-current claims behind polished prose;
- a source-backed claim depends on raw book text, raw video transcript, comments, or long excerpts stored in the vault.

## Agent Studio Design Implications

- Source-backed generation should produce claim records before publishing artifacts.
- Claim verification should run after source refresh because accepted evidence may change even when draft text does not.
- Source refresh should trigger freshness/invalidation review before old accepted evidence, claim states, route cards, caches, eval outcomes, or artifact approvals are reused.
- The UI should show supported, needs-review, unsupported, contradicted, and stale-current counts near the draft and source panel.
- Canon notes should cite source notes and manifests, not raw extraction files.
- Local book notes should preserve page or chapter references where useful, but store compact synthesis rather than replacement summaries.
- Official/current claims should be rechecked against official sources before the route uses them as "latest" evidence.

## Canon Decision

Agent Studio should treat source support as a ledgered state transition, not as a writing style. A source-backed artifact is ready only when the datastore can answer: which claim, which source snapshot, which evidence, which retrieval trace, which verifier, which caveat, which decision, and which rollback path.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
