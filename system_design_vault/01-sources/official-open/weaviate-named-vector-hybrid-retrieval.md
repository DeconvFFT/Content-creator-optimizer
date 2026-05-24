---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_documentation
rights_status: official_public
sources:
  - https://docs.weaviate.io/weaviate/concepts/search/vector-search
  - https://docs.weaviate.io/weaviate/search/hybrid
  - https://docs.weaviate.io/weaviate/search/similarity
  - https://docs.weaviate.io/weaviate/search/filters
  - https://docs.weaviate.io/weaviate/concepts/filtering
  - https://docs.weaviate.io/weaviate/concepts/data
  - https://docs.weaviate.io/weaviate/manage-collections/vector-config
  - https://docs.weaviate.io/weaviate/manage-collections/multi-tenancy
  - https://docs.weaviate.io/deploy/configuration/backups
  - https://docs.weaviate.io/weaviate/model-providers/transformers/reranker
---

# Weaviate Named-Vector Hybrid Retrieval

## Read Scope

This note is original synthesis from official Weaviate documentation for vector search, hybrid search, similarity search, filters, filtering internals, data/schema concepts, vector configuration, multi-tenancy, backups, and reranker integrations. It stores no raw documentation text, copied code samples, screenshots, or long excerpts.

## Core Reading

Weaviate adds a useful retrieval design pattern for Agent Studio: named vectors as first-class representations on the same object. A source chunk, claim, image, artifact, or user-feedback item can carry multiple vector embeddings for different meanings: title, body, code, visual reference, caption, policy metadata, or feedback intent. Multi-target vector search can query several named vectors and combine the result. Agent Studio should therefore distinguish `object_id` from `vector_target`, not treat each object as having one embedding.

Current-doc check on 2026-05-18 confirms that this remains a release-sensitive boundary: Weaviate hybrid search exposes target vectors, explainable scores, alpha weighting, and fusion method; named vectors can have distinct vectorizer and index settings; multi-vector embeddings are named-vector scoped; multi-tenancy has active/inactive/offloaded tenant states; ACORN filtering is designed for restrictive or weakly correlated HNSW filters; locally hosted transformer reranking is a module-backed second stage; and backups have deployment, version, incremental, and tenant-state caveats, including offloaded tenant exclusions.

The collection schema is a product contract. Vectorizer choice, vector index type, distance metric, HNSW parameters, quantizer settings, named-vector definitions, property tokenization, indexable/filterable flags, and module configuration are all release-sensitive. Some collection and vector settings are fixed after creation. Agent Studio should record schema immutability and migration paths before promising that an index setting can be changed safely.

Hybrid search combines vector and keyword/BM25-style scoring with a weighting parameter. That parameter is not tuning trivia: it controls whether semantic paraphrase or exact term match dominates. Agent Studio should record the hybrid alpha or fusion setting, selected query properties, vector target, keyword query, and rank explanation where available. This is especially important for system-design notes where API names, filenames, model names, and exact error strings matter.

Filtered vector search has its own performance and recall behavior. Weaviate's filtering guidance distinguishes pre-filtering and sweeping-style behavior, and newer ACORN-style filtered vector search optimizes cases where filters are selective or poorly correlated with vector neighborhoods. Agent Studio should store whether a filter is a governance boundary, ranking hint, or performance hint; tenant, rights, source freshness, and sensitivity filters must be enforced and tested, not left as optional query adornments.

Multi-tenancy is a collection-level design choice. Tenant state, tenant activation, and tenant movement affect read/write behavior. For Agent Studio, tenant can mean user, workspace, corpus, source snapshot, customer, or route-release sandbox. If a collection is not created with the right tenancy shape, later migration may require reindexing or data movement. This should be represented as a retrieval release risk.

Reranking is a separate module/integration stage. Weaviate can call configured reranker providers, and routes can use additional ranking logic such as maximum marginal relevance for diversity. Agent Studio should not hide this behind "search." Store the reranker model/provider, top-k input, top-n output, ranking fields, diversity policy, latency, and false-negative audit evidence.

Backups are operationally scoped. Backup support, included collections, excluded collections, tenant behavior, async status, and restore caveats vary by deployment and version. Agent Studio should attach backup/restore evidence to index releases that are used in production or evaluation baselines. A source-backed route is not reproducible if its search index cannot be restored or rebuilt from a source snapshot.

## Agent Studio Datastore Additions

| Datastore object | Purpose | Key fields |
|---|---|---|
| `named_vector_target` | Named representation on a source object | `target_id`, `collection_id`, `name`, `object_type`, `source_property_refs`, `embedding_model_ref`, `distance_metric`, `vector_index_ref`, `enabled_routes`, `status` |
| `multi_target_query_plan` | Query that searches multiple named vectors | `multi_target_plan_id`, `route_id`, `collection_id`, `target_names`, `target_weights`, `join_or_merge_strategy`, `query_vector_refs`, `final_k`, `eval_refs` |
| `hybrid_alpha_policy` | Vector/BM25 weighting decision | `hybrid_alpha_policy_id`, `route_id`, `collection_id`, `vector_target`, `keyword_properties`, `alpha`, `fusion_policy`, `calibration_dataset_id`, `decision_status` |
| `filtered_vector_execution_policy` | Filter behavior and performance guardrail | `filter_execution_policy_id`, `route_id`, `collection_id`, `required_filters`, `governance_filters`, `performance_filters`, `filter_strategy`, `selectivity_expectation`, `fallback_policy`, `test_refs` |
| `weaviate_collection_schema_release` | Collection schema and module release | `schema_release_id`, `collection_name`, `vectorizer_config`, `named_vectors`, `property_indexing_flags`, `module_configs`, `immutable_settings`, `migration_plan_ref`, `status` |
| `weaviate_tenant_state_record` | Tenant lifecycle for a collection | `tenant_state_id`, `collection_id`, `tenant_key`, `tenant_state`, `activity_status`, `source_snapshot_scope`, `migration_refs`, `updated_at` |
| `search_diversity_policy` | MMR or diversity-aware result selection | `diversity_policy_id`, `route_id`, `candidate_pool_ref`, `method`, `lambda_or_diversity_weight`, `coverage_goal`, `false_negative_risk`, `eval_refs` |
| `search_module_binding` | Reranker/vectorizer/generative module dependency | `module_binding_id`, `route_id`, `collection_id`, `module_type`, `provider`, `model`, `credentials_scope`, `version_or_config_hash`, `fallback_policy`, `status` |
| `collection_backup_restore_record` | Collection and tenant backup evidence | `backup_restore_id`, `collection_ids`, `tenant_scope`, `backup_backend`, `backup_status`, `restore_target`, `restore_status`, `version_caveats`, `created_at` |
| `named_vector_retrieval_release_gate` | Promotion gate for Weaviate-style named-vector retrieval routes | `gate_id`, `route_id`, `collection_schema_release_ref`, `source_snapshot_ref`, `named_vector_target_refs`, `multi_target_query_plan_ref`, `hybrid_alpha_policy_ref`, `filtered_vector_execution_policy_ref`, `tenant_state_refs`, `diversity_policy_ref`, `module_binding_refs`, `backup_restore_refs`, `relevance_eval_refs`, `latency_eval_refs`, `privacy_boundary_ref`, `rollback_target_ref`, `decision`, `reviewed_at` |

## Design Commitments

- Model named vectors as route-visible retrieval targets, not as anonymous embeddings.
- Store hybrid alpha/fusion settings and exact keyword properties; system-design retrieval needs exact terms and semantic paraphrase together.
- Treat selective filters as both correctness and performance controls. Required tenant/rights/freshness filters need tests.
- Make collection tenancy a release decision before ingestion begins.
- Keep reranking, diversity selection, and module/provider bindings visible in traces and route releases.
- Attach backup/restore or rebuild evidence to any collection used as production retrieval evidence.
- Promote Weaviate-style named-vector routes only after a named-vector retrieval release gate proves schema release, source snapshot, target-vector contract, multi-target plan, hybrid alpha/fusion policy, filter strategy, tenant state, reranker/module binding, backup posture, relevance/latency evidence, privacy boundary, and rollback target.
