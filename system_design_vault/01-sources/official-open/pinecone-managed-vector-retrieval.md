---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_documentation
rights_status: official_public
sources:
  - https://docs.pinecone.io/guides/index-data/indexing-overview
  - https://docs.pinecone.io/guides/index-data/create-an-index
  - https://docs.pinecone.io/guides/index-data/implement-multitenancy
  - https://docs.pinecone.io/guides/search/filter-by-metadata
  - https://docs.pinecone.io/guides/search/search-overview
  - https://docs.pinecone.io/guides/search/hybrid-search
  - https://docs.pinecone.io/guides/search/rerank-results
  - https://docs.pinecone.io/guides/manage-data/manage-indexes
  - https://docs.pinecone.io/guides/manage-data/backups-overview
---

# Pinecone Managed Vector Retrieval

## Read Scope

This note is original synthesis from official Pinecone documentation for indexing concepts, index creation, multitenancy, metadata filtering, search modes, hybrid search, hosted reranking, index management, and backups. It stores no raw documentation text, copied examples, screenshots, or long excerpts.

## Core Reading

Pinecone adds the managed-service perspective to Agent Studio's retrieval design. A Pinecone index can represent different data shapes: document schemas with full-text, dense-vector, and sparse-vector ranking fields; dense vector indexes; sparse vector indexes; and integrated-embedding indexes that turn source text into vectors inside the managed service. Agent Studio should treat this as a route decision, not a storage implementation detail.

The most important design distinction is between ranking fields and metadata. Ranking fields decide how candidate order is produced: BM25-style full-text fields, dense vectors, sparse vectors, or hybrid combinations. Metadata fields constrain or label the search: tenant, source ID, rights status, freshness, section path, source class, sensitivity, and route eligibility. A metadata filter does not replace a ranking signal, and a ranking field does not replace source governance.

Namespaces are first-class multitenancy and cost boundaries. Pinecone's guidance favors one namespace per tenant when isolation matters; all writes, reads, queries, and deletes target a namespace. This maps cleanly to Agent Studio's user, workspace, corpus, source snapshot, or route-release boundaries. Metadata filtering can handle cross-tenant or cross-group queries, but it has performance, cost, and filter-size tradeoffs and should not be treated as equivalent to namespace isolation.

Hybrid search is not one feature. Pinecone distinguishes at least three patterns:

- one vector-API index storing dense and sparse vectors for each record;
- separate dense and sparse indexes with client-side merge/dedup and optional reranking;
- document-schema indexes that combine full-text fields and vector fields, then select or merge ranking signals per query.

For Agent Studio, this means hybrid retrieval needs a plan record. The plan must say which pattern is used, how dense/sparse/BM25 scores are normalized or fused, whether an `alpha` weighting parameter is used, whether separate indexes are linked by shared IDs, where deduplication happens, and which reranker receives the merged pool.

Sparse/dense score calibration is a real failure mode. Pinecone's hybrid guidance warns that sparse or BM25-style scores can dominate dense-vector scores unless the query vectors are explicitly weighted or the route uses a document-schema pattern that avoids raw dense/sparse score mixing. Agent Studio should evaluate `alpha` or fusion settings on a labeled relevance set before promotion.

Hosted reranking turns the vector store into a two-stage retrieval platform. Pinecone supports reranking as part of search and as a standalone inference call. The production implication is that retrieval traces should record both the first-stage candidate pool and the reranker stage: model, `top_k`, `top_n`, ranking fields, document count, truncation policy, usage units, latency, false positives removed, and false negatives introduced.

Index schema and metadata indexing are release concerns. Some schema shapes cannot be changed in place, and metadata indexing rules can affect build time, query latency, and what fields can be filtered. Agent Studio should record index schema, API version, ranking fields, filterable metadata fields, namespace-level overrides, and migration/rollback paths before changing search behavior.

Backups are recovery and experimentation artifacts, not just ops housekeeping. A backup is a static, non-queryable copy of a serverless index that can be restored into a new index, but backup availability and support depend on plan, project/region, schema type, and freshness limits. Agent Studio should attach backup or import evidence to index releases that matter for production retrieval.

## Current-Source Cross-Check

Current Pinecone hybrid-search docs still split hybrid retrieval by data shape and API surface: single dense+sparse vector index, separate dense/sparse indexes with client merge, or document-schema indexes that combine full-text and vector fields. The docs still warn that sparse/BM25-style scores can dominate dense-vector scores without explicit weighting and recommend evaluating alpha/fusion values against a workload-specific relevance set.

Current Pinecone multitenancy docs still make namespaces the primary tenant isolation and cost boundary for reads, writes, queries, and deletes, while metadata filters remain secondary constraints and cross-boundary query tools with performance and design tradeoffs. Current backup docs still describe backups as static, non-queryable index copies that can be restored into a new index subject to support and freshness constraints. The cross-check is that managed vector retrieval needs a provider-specific release gate, not just a vector index name.

## Agent Studio Datastore Additions

| Datastore object | Purpose | Key fields |
|---|---|---|
| `managed_vector_index_record` | Managed vector/search index release | `managed_index_id`, `provider`, `index_name`, `cloud`, `region`, `api_version`, `data_shape`, `ranking_fields`, `metadata_indexing_policy_id`, `namespace_policy_id`, `backup_policy_id`, `status` |
| `index_ranking_field` | Searchable ranking field in a managed index | `ranking_field_id`, `managed_index_id`, `field_name`, `field_type`, `dimension`, `metric`, `embedding_model_ref`, `full_text_enabled`, `sparse_model_ref`, `schema_mutability`, `created_at` |
| `managed_namespace_policy` | Tenant/workspace/corpus namespace boundary | `namespace_policy_id`, `managed_index_id`, `namespace_strategy`, `tenant_key`, `workspace_key`, `source_snapshot_key`, `offboarding_policy`, `cross_namespace_query_policy`, `cost_model_ref`, `status` |
| `metadata_filter_schema` | Filterable metadata contract for managed search | `metadata_schema_id`, `managed_index_id`, `field_name`, `field_type`, `filterable`, `rights_or_freshness_role`, `sensitivity_class`, `namespace_override`, `migration_notes` |
| `managed_hybrid_retrieval_plan` | Dense/sparse/BM25 hybrid pattern and fusion | `hybrid_plan_id`, `route_id`, `provider`, `pattern`, `dense_index_ref`, `sparse_index_ref`, `document_index_ref`, `linkage_key`, `alpha_or_fusion_policy`, `dedup_policy`, `candidate_k`, `eval_refs` |
| `managed_rerank_policy` | Hosted or external reranking stage | `rerank_policy_id`, `route_id`, `provider`, `model`, `top_k_input`, `top_n_output`, `rank_fields`, `truncate_policy`, `usage_unit_budget`, `latency_slo`, `eval_refs`, `status` |
| `managed_rerank_event` | Query-time reranking evidence | `rerank_event_id`, `retrieval_trace_id`, `rerank_policy_id`, `input_candidate_count`, `output_candidate_count`, `rank_movement`, `dropped_candidate_ids`, `usage_units`, `latency_ms`, `created_at` |
| `managed_index_backup_record` | Backup/restore evidence for managed retrieval | `backup_id`, `managed_index_id`, `source_snapshot_id`, `namespace_count`, `record_count`, `size_bytes`, `backup_status`, `created_at`, `restore_target`, `freshness_caveat`, `retention_policy` |
| `managed_import_job` | Bulk import or reindex operation | `import_job_id`, `managed_index_id`, `source_uri`, `source_snapshot_id`, `record_count`, `namespace_scope`, `started_at`, `completed_at`, `status`, `failure_refs` |
| `managed_search_cost_record` | Query and rerank cost accounting | `cost_record_id`, `route_id`, `managed_index_id`, `namespace`, `read_units`, `rerank_units`, `storage_bytes`, `operation_type`, `usage_window`, `budget_ref` |
| `managed_vector_release_gate` | Promotion gate for Pinecone or equivalent managed vector routes | `gate_id`, `route_id`, `managed_index_ref`, `source_snapshot_ref`, `ranking_field_refs`, `namespace_policy_ref`, `metadata_filter_schema_refs`, `managed_hybrid_plan_ref`, `managed_rerank_policy_ref`, `backup_or_import_refs`, `cost_budget_ref`, `alpha_or_fusion_eval_refs`, `relevance_eval_refs`, `latency_eval_refs`, `privacy_boundary_ref`, `rollback_target_ref`, `decision`, `reviewed_at` |

## Design Commitments

- Model managed indexes as route releases with schema, namespace, filter, backup, and cost records.
- Use namespaces for isolation when user/workspace/corpus boundaries matter; use metadata filters for secondary constraints and cross-boundary queries with explicit tradeoff records.
- Treat hybrid retrieval pattern choice as product behavior: single dense+sparse index, separate dense/sparse indexes, or document-schema search each has different latency, merge, rerank, and migration costs.
- Evaluate dense/sparse weighting, BM25 filtering, and reranking on the Agent Studio relevance set before promotion.
- Keep reranking observable as a separate stage, with input pool, output pool, fields, model, usage, and false-negative audit evidence.
- Attach backup/restore or import evidence to retrieval index releases that must be recoverable or reproducible.

## Release Gate

A Pinecone-backed retrieval route cannot be promoted unless a `managed_vector_release_gate` proves managed index schema, source snapshot, ranking fields, namespace/isolation policy, metadata filter schema, hybrid pattern and alpha/fusion evals, rerank policy where enabled, backup/restore or import evidence, usage/cost budget, relevance and latency evals, privacy boundary, and rollback target.

## Canon Decision

This note is canon-ready for Agent Studio managed vector retrieval architecture. Managed vector providers are release-managed retrieval dependencies: schema, namespaces, filters, hybrid scoring, reranking, backups, imports, cost, and privacy posture all affect source evidence and must be visible before production use.
