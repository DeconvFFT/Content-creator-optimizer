---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-19
sources:
  - "[[../../01-sources/official-open/web-source-acquisition-and-crawl-governance]]"
  - "[[../../01-sources/official-open/caching-rate-limits-and-cost-control]]"
  - "[[../evaluation/source-claim-evidence-ledger]]"
  - "[[../system-design/distributed-data-contracts]]"
  - "[[../../01-sources/official-open/object-artifact-storage-lifecycle]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
stores_raw_source_text: false
stores_long_excerpts: false
---

# Source Freshness And Invalidation

## Purpose

Agent Studio needs a governed freshness lifecycle because source-backed artifacts are only as trustworthy as the source snapshot, extraction, index, cache, claim ledger, eval, and approval state they depend on. A source refresh is not just a new fetch. It can invalidate retrieval results, generated claims, cached responses, reviewer approvals, eval baselines, route cards, and published artifacts.

This pattern defines what must happen when a source, rights state, extraction transform, route policy, cache boundary, or retrieval index changes.

## Freshness Surfaces

| Surface | Freshness signal | Invalidation target |
|---|---|---|
| Web source | ETag, Last-Modified, sitemap `lastmod`, canonical conflict, docs changelog, manual availability check. | `source_record`, extraction jobs, chunks, embeddings, claim ledgers, source notes. |
| Local source | File hash, metadata hash, user-provided replacement, filename/provenance review. | Local chapter notes, source manifests, extraction spans, support/canon status. |
| Rights/provenance | Terms review, license change, gated/public boundary, user-rights confirmation change. | Retrieval eligibility, quote/citation policy, cache keys, publishability, training/tuning permission. |
| Extraction/parser | Parser version, layout/OCR quality, known-loss record, page/section boundary change. | Chunks, table/figure claims, offsets, evidence refs, eval examples generated from extracted content. |
| Retrieval/index | Chunk policy, embedding model, distance metric, reranker, filters, graph extraction, index alias. | Retrieval traces, accepted/rejected evidence, citation evals, source coverage metrics. |
| Cache | Prompt prefix, cache key, TTL, source snapshot, route version, rights/user scope. | Cached answers, provider prompt cache eligibility, semantic/application cache entries. |
| Artifact/review | Draft text, media edit, approval, route card, eval baseline, published item. | Approval state, reviewer decision, publication readiness, rollback/correction requirement. |

## Lifecycle

1. Detect a candidate change: scheduled refresh, source-watch event, file hash change, user replacement, provider docs update, terms review, or route/index/cache release.
2. Classify the change: content, metadata, rights, provenance, extraction, retrieval, cache, policy, model, or route behavior.
3. Compute dependency impact: source notes, chunks, embeddings, graph nodes, claim ledgers, eval examples, route cards, approvals, and publishable artifacts.
4. Mark stale before recomputing: downstream objects should show `stale_pending_refresh`, `stale_rights_review`, or `stale_policy_review` rather than silently serving old evidence.
5. Rebuild the minimum necessary projections: extraction, chunking, indexes, graph extraction, claim checks, evals, and caches.
6. Compare old and new evidence: added/removed claims, changed citations, changed support states, recall/precision deltas, latency/cost deltas, and approval deltas.
7. Decide promotion: keep old snapshot, promote new snapshot, quarantine affected claims, require human review, or trigger rollback/correction.

## Invalidation Rules

- Content changes invalidate accepted evidence and claim support unless the claim is explicitly source-snapshot scoped.
- Rights or terms changes invalidate use, not just retrieval. A cached answer can become unusable even when the text has not changed.
- Parser or OCR changes invalidate offsets, table/figure evidence, and page/section references.
- Chunking, embedding, filtering, or reranking changes invalidate retrieval metrics and accepted/rejected evidence decisions.
- Cache keys must include source snapshot, route version, tenant/user scope, and rights state for source-backed routes.
- Published artifacts need correction or rollback policy when refreshed evidence contradicts or weakens a public claim.
- Eval examples generated from source material inherit the source snapshot and rights status; refreshing the source can invalidate the eval set.

## Datastore Additions

Use existing schema objects where possible, but add these dependency records explicitly:

| Record | Purpose | Minimum fields |
|---|---|---|
| `source_freshness_observation` | Captures the signal that something may have changed. | `observation_id`, `source_ref`, `signal_type`, `signal_value_hash`, `observed_at`, `observer`, `confidence`, `recommended_action` |
| `source_dependency_edge` | Connects a source snapshot to derived artifacts. | `edge_id`, `source_snapshot_ref`, `derived_object_ref`, `derived_object_type`, `dependency_type`, `created_by_run_ref`, `status` |
| `source_invalidation_event` | Marks derived objects stale or blocked after a change. | `invalidation_id`, `source_ref`, `change_class`, `affected_object_refs`, `stale_reason`, `required_refresh_refs`, `review_required`, `created_at`, `status` |
| `source_refresh_diff` | Compares old and new source-derived evidence. | `diff_id`, `old_snapshot_ref`, `new_snapshot_ref`, `content_hash_delta`, `claim_delta_refs`, `retrieval_metric_delta_refs`, `rights_delta`, `decision` |
| `stale_artifact_review` | Human or automated decision for affected artifacts. | `review_id`, `artifact_ref`, `invalidation_ref`, `support_state_before`, `support_state_after`, `publish_or_route_impact`, `decision`, `reviewed_at` |

These records complement `web_source_refresh_policy`, `cache_invalidation_event`, `source_claim_evidence_ledger`, `state_transition_record`, and `object_lifecycle_event`.

## Release Gate

Use `source_freshness_invalidation_release_gate` before a source refresh, index refresh, parser change, rights change, cache-policy change, or source-backed route release becomes production evidence.

Required evidence:

- source freshness observation, source snapshot identity, fetch/hash/metadata evidence, rights/provenance status, and refresh policy;
- dependency graph from source snapshot to notes, chunks, embeddings, graph nodes, claims, evals, approvals, caches, route cards, and published artifacts;
- invalidation event with stale reason, affected objects, required rebuilds, and human-review requirements;
- old versus new diff for content, rights, extraction quality, retrieval metrics, claim support states, cache eligibility, and publication impact;
- rebuilt projection refs, claim-ledger updates, cache invalidation events, eval reruns where needed, and rollback or correction path.

Do not promote when:

- a refreshed source silently overwrites the prior snapshot without dependency impact analysis;
- derived notes or artifacts keep `canon_ready` or `approved` state after their evidence becomes stale;
- cache hits can bypass a source/rights/policy refresh;
- changed retrieval indexes reuse old accepted-evidence decisions;
- public artifacts have no correction path when source support weakens.

## Agent Studio Design Implications

- Source cards should show freshness state and downstream impact count, not just last-updated date.
- Route cards should list source snapshots and whether any dependency is stale, quarantined, or pending review.
- The creator UI should warn when an artifact is based on stale-current evidence or rights-stale evidence.
- Autopilot should prefer refresh-and-recheck over rewriting prose when a source-backed claim becomes stale.
- Caches and generated summaries should be invalidated by source snapshot, rights state, route version, and policy version.
- Weekly audits should include stale dependency counts and correction/rollback queues, not only link/path integrity.

## Canon Decision

Agent Studio should treat freshness as a dependency graph problem. A source refresh is production-safe only when the datastore can show what changed, what depends on it, what was invalidated, what was rebuilt, which claims changed support state, which artifacts need review, and how rollback or correction will happen.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
