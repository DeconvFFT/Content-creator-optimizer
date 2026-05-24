---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_documentation
rights_status: official_public
sources:
  - https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/semantic-text
  - https://www.elastic.co/docs/solutions/search/semantic-search
  - https://www.elastic.co/docs/solutions/search/vector
  - https://www.elastic.co/docs/solutions/search/hybrid-semantic-text
  - https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-search
  - https://www.elastic.co/docs/solutions/search/ranking/semantic-reranking
  - https://www.elastic.co/docs/manage-data/data-store/aliases
  - https://www.elastic.co/docs/deploy-manage/tools/snapshot-and-restore
  - https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reindex-indices
---

# Elasticsearch Semantic And Hybrid Search

## Read Scope

This note is original synthesis from official Elasticsearch documentation for `semantic_text`, semantic search, vector search, hybrid semantic search, the search API retriever tree, semantic reranking, aliases, snapshot/restore, and reindexing. It stores no raw documentation text, copied code samples, screenshots, or long excerpts.

## Core Reading

Elasticsearch adds the mature search-engine perspective to Agent Studio retrieval. It is not only a vector store: it combines lexical analyzers, BM25-style matching, structured filters, dense vectors, sparse vectors, semantic text fields, RRF or linear fusion, retriever trees, query rules, pinned results, semantic rerankers, aliases, reindexing, snapshots, and cross-index search. Agent Studio should treat this as a search route release, not a generic "retriever" setting.

Current-doc check on 2026-05-18 confirms that this remains a release-sensitive boundary: `semantic_text` can default inference endpoints unless pinned; semantic fields can specify separate indexing and search inference endpoints plus chunking and vector index options; the Search API retriever object is generally available and covers nested standard, text-similarity reranker, linear, pinned, diversify, and related retrievers; semantic reranking depends on an inference endpoint and rank window; alias filters only apply through Query DSL paths; and snapshots are the supported cluster-backup mechanism with compatibility limits.

The `semantic_text` field is a high-level semantic-search contract. It can automate chunking, inference, embedding storage, and query behavior. That convenience is useful, but it shifts hidden decisions into index mapping and inference endpoints. Agent Studio should store the semantic field name, inference endpoint, chunking behavior, ingestion/search endpoint split, query-time filters, license/deployment caveats, and source snapshot used to build the field.

Manual vector search remains a separate contract. Dense-vector and sparse-vector fields expose more control over dimensions, similarity, quantization, candidates, oversampling, rescoring, and filters. A route that needs strict reproducibility or custom embedding models should not pretend it is the same as a `semantic_text` route. Agent Studio should record whether vector generation is managed by Elasticsearch, a local embedding service, or a provider pipeline.

Retriever trees make multi-stage retrieval explicit. The search API can compose standard, kNN, RRF, text-similarity reranker, rule, rescorer, linear, pinned, and diversify retrievers. This is a good fit for Agent Studio's route traces: each child retriever should have a name, candidate size, filter, score policy, and latency; fusion or reranking should be a visible stage with its own parameters and failure modes.

RRF and linear fusion solve different problems. RRF combines ranked lists without requiring score calibration; linear fusion requires normalization or weighting choices. Agent Studio should not let "hybrid search" hide this choice. The trace needs the child retrievers, `rank_window_size`, rank constant or weights, normalizer, candidate overlap, and which results were promoted or suppressed.

Semantic reranking is a second-stage precision layer. Elasticsearch reranking uses inference endpoints and operates over a bounded candidate window. It can improve BM25, semantic, or hybrid retrieval, but it adds model dependency, latency, cost, truncation behavior, and false-negative risk. Agent Studio should record reranker endpoint, model/provider, field, rank window, chunk rescoring mode, input/output counts, usage, latency, and audit labels for dropped evidence.

Aliases are production release controls. Aliases can redirect reads and writes, query multiple indices, swap backing indices without downtime, and apply filters in Query DSL paths. The important caveat is that alias filters are not universal access control; direct document retrieval paths can bypass them. Agent Studio should use aliases for index promotion and rollback, but tenant/rights boundaries still need application-side policy and trace evidence.

Snapshots and reindexing are reproducibility and migration controls. Snapshots can preserve data streams, indices, aliases, and cluster/feature state within compatibility limits. Reindexing can copy data through transforms or pipelines into a new index. Agent Studio should attach snapshot, reindex, and restore-drill evidence to any search index release that supports production claims or eval baselines.

## Agent Studio Datastore Additions

| Datastore object | Purpose | Key fields |
|---|---|---|
| `search_index_release` | Search-engine index release for lexical/vector/semantic retrieval | `search_index_id`, `engine`, `index_name`, `source_snapshot_id`, `mapping_hash`, `settings_hash`, `analyzer_profile_id`, `semantic_field_refs`, `vector_field_refs`, `alias_refs`, `status` |
| `semantic_text_field_profile` | Managed semantic field behavior | `semantic_field_id`, `search_index_id`, `field_name`, `inference_endpoint_ref`, `chunking_policy`, `embedding_storage_policy`, `query_filter_policy`, `license_or_deployment_caveat`, `created_at` |
| `lexical_analyzer_profile` | BM25/exact-match analyzer contract | `analyzer_profile_id`, `index_name`, `field_name`, `analyzer`, `normalizer`, `keyword_subfields`, `synonym_policy_ref`, `token_filter_refs`, `eval_refs` |
| `retriever_tree_plan` | Search API retriever composition | `retriever_tree_id`, `route_id`, `root_retriever_type`, `child_retrievers`, `rank_window_size`, `filters`, `named_retrievers`, `latency_budget_ms`, `eval_refs` |
| `fusion_strategy_record` | RRF or linear retrieval fusion policy | `fusion_strategy_id`, `retriever_tree_id`, `method`, `rank_constant`, `weights`, `normalizer`, `candidate_overlap`, `promoted_result_refs`, `suppressed_result_refs` |
| `semantic_reranker_policy` | Search-engine reranker stage | `reranker_policy_id`, `route_id`, `engine`, `inference_endpoint_ref`, `model_ref`, `field`, `rank_window_size`, `chunk_rescorer_policy`, `latency_slo`, `eval_refs`, `status` |
| `semantic_reranker_event` | Query-time reranker evidence | `reranker_event_id`, `retrieval_trace_id`, `reranker_policy_id`, `input_count`, `output_count`, `rank_movement`, `dropped_candidate_ids`, `latency_ms`, `false_negative_audit_refs` |
| `search_alias_release` | Mutable search alias with rollback audit | `search_alias_id`, `alias_name`, `active_index`, `candidate_index`, `write_index`, `filter_policy_ref`, `swap_event_ref`, `rollback_target`, `access_caveat` |
| `search_reindex_job` | Search-index migration or rebuild job | `reindex_job_id`, `source_index`, `target_index`, `source_snapshot_id`, `pipeline_ref`, `script_or_transform_hash`, `started_at`, `completed_at`, `status`, `validation_refs` |
| `search_snapshot_record` | Snapshot/restore evidence for search index releases | `search_snapshot_id`, `repository`, `snapshot_name`, `included_indices`, `included_aliases`, `feature_state_policy`, `version_caveat`, `restore_drill_ref`, `retention_policy` |
| `search_engine_release_gate` | Promotion gate for Elasticsearch-style search-engine retrieval routes | `gate_id`, `route_id`, `search_index_release_ref`, `source_snapshot_ref`, `semantic_text_field_refs`, `lexical_analyzer_refs`, `vector_field_refs`, `retriever_tree_plan_ref`, `fusion_strategy_ref`, `semantic_reranker_policy_ref`, `alias_release_ref`, `reindex_job_refs`, `snapshot_restore_refs`, `access_boundary_ref`, `relevance_eval_refs`, `latency_eval_refs`, `rollback_target_ref`, `decision`, `reviewed_at` |

## Design Commitments

- Model search-engine retrieval separately from vector-database retrieval. Lexical analyzers, semantic fields, vector fields, retriever trees, aliases, and snapshots all affect product behavior.
- Treat `semantic_text` convenience as a release artifact with inference endpoint, chunking, and field behavior recorded.
- Preserve BM25/exact-match analyzer settings for API names, file names, IDs, model names, paper titles, and error strings.
- Store RRF/linear fusion and semantic reranking as visible trace stages, not hidden helper code.
- Use aliases for zero-downtime index promotion and rollback, while keeping tenant/rights checks outside alias filters.
- Attach reindex and snapshot/restore evidence to every search-index migration that changes production retrieval.
- Promote Elasticsearch-style routes only after a search-engine release gate proves index release, source snapshot, semantic field behavior, lexical analyzer settings, vector fields, retriever tree, fusion strategy, semantic reranker policy, alias swap, reindex evidence, snapshot/restore evidence, access boundary, relevance/latency evals, and rollback target.
