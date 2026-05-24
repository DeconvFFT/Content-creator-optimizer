---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_documentation
rights_status: official_public
sources:
  - https://qdrant.tech/documentation/manage-data/collections/
  - https://qdrant.tech/documentation/concepts/points/
  - https://qdrant.tech/documentation/manage-data/vectors/
  - https://qdrant.tech/documentation/concepts/payload/
  - https://qdrant.tech/documentation/search/filtering/
  - https://qdrant.tech/documentation/manage-data/indexing/
  - https://qdrant.tech/documentation/concepts/search/
  - https://qdrant.tech/documentation/search/hybrid-queries/
  - https://qdrant.tech/documentation/manage-data/quantization/
  - https://qdrant.tech/documentation/operations/snapshots/
---

# Qdrant Production Vector Retrieval

## Read Scope

This note is original synthesis from official Qdrant documentation for collections, points, vectors, payloads, filtering, indexing, search, hybrid queries, quantization, snapshots, and operational collection behavior. It stores no raw documentation text, code samples, screenshots, or long excerpts.

## Core Reading

Qdrant makes the vector database a release-managed subsystem rather than a hidden retriever helper. Collections define the searchable boundary: vector dimensions, distance metrics, named-vector families, sparse vectors, multivectors, shard and replica behavior, write consistency, HNSW and optimizer settings, quantization posture, and on-disk storage options can all change retrieval behavior. Agent Studio should therefore treat collection creation and collection updates as source-index releases tied to source snapshots and route releases.

Payloads are not just incidental metadata. They are the source-ledger fields that make retrieval enforceable: source ID, workspace or tenant, rights status, freshness state, section path, source class, sensitivity label, entity tags, and route eligibility. Payload indexes and full-text indexes are separate operational choices. They improve filtered search and query planning, but they also cost memory, can affect write/update behavior, and should be built deliberately around the filters the product actually uses.

Filtering must stay explicit in the route trace. A vector result without the tenant, source, freshness, rights, and sensitivity filters that allowed it is not audit-ready. Qdrant's filter model supports exact, range, full-text, geo, nested, and boolean-style conditions; Agent Studio should record which filters were required, which were optional ranking signals, and which failed or were unavailable.

Hybrid search is a first-class query plan, not a vague "use embeddings plus keywords" toggle. Dense and sparse retrieval can be prefetched separately and fused with a named policy such as reciprocal-rank fusion. Agent Studio should store the dense vector profile, sparse vector profile, candidate limits, fusion rule, reranking rule, and route surface that consumed the result.

Named vectors, sparse vectors, and multivectors make multi-representation retrieval practical. A single source chunk can carry different representations for semantic text, exact-token sparse search, visual embeddings, code embeddings, or late-interaction retrieval. For Agent Studio, this argues for vector-field records rather than one `embedding` column. Multivectors are especially important for ColBERT-style retrieval, but they increase memory/index cost and need recall/latency evaluation before becoming a default route.

Quantization is a release decision. Scalar, product, binary, and newer compressed representations can reduce RAM or improve speed, but they can change recall and may need rescoring or oversampling. Agent Studio should not enable quantization as an invisible infrastructure optimization. It should attach quality deltas, latency/cost deltas, rollback targets, and query-time tuning parameters to the index release.

Aliases and snapshots are production controls. Aliases let a stable route name point at a different collection after a candidate index passes validation, which supports zero-downtime promotion and rollback. Snapshots make collection state recoverable and reproducible. Agent Studio should promote retrieval indexes through candidate, validated, active, previous-good, and retired states with snapshot evidence attached.

Partitioning and multitenancy are design boundaries. Payload-based partitioning can be efficient, while multiple collections can improve isolation when that isolation is worth the operational overhead. For Agent Studio, tenant, workspace, source snapshot, and route-release boundaries must be explicit. A payload filter alone is not a permission model unless the access check and query filter are both enforced and tested.

## Current-Source Cross-Check

Current Qdrant docs still make collections the primary schema and operational boundary: vector size, distance metric, named vectors, optimizer settings, HNSW settings, WAL, sharding, on-disk payload, quantization, and strict-mode options can all affect retrieval behavior. The current docs also continue to frame multitenancy as a choice between payload-based partitioning and separate collections with isolation and overhead tradeoffs.

Current hybrid-query docs still represent retrieval as a staged query plan with prefetches and fusion rather than a single vector call. Current snapshot docs still make recovery explicit at collection or full-storage level, which confirms that vector index state needs snapshot and restore evidence before a route depends on it. Cross-checking these with the retrieval canon means a Qdrant-backed route must release collection schema, vector fields, payload filters, hybrid plan, quantization, aliases, snapshots, and partition policy together.

## Agent Studio Design Implications

| Datastore object | Purpose | Key fields |
|---|---|---|
| `vector_collection_record` | Release-managed vector collection | `collection_id`, `backend`, `collection_name`, `source_snapshot_id`, `route_release_ids`, `distance_defaults`, `shard_count`, `replica_count`, `write_consistency`, `on_disk_policy`, `optimizer_policy_id`, `status` |
| `vector_field_profile` | One dense, sparse, or multivector representation | `vector_field_id`, `collection_id`, `name`, `representation_type`, `dimension`, `embedding_model_ref`, `distance_metric`, `datatype`, `multivector_comparator`, `hnsw_config_ref`, `quantization_profile_id`, `created_at` |
| `payload_schema_record` | Filterable source metadata contract | `payload_schema_id`, `collection_id`, `field_name`, `field_type`, `source_ledger_role`, `filter_required`, `rights_or_freshness_role`, `sensitivity_class`, `owner` |
| `payload_index_record` | Payload or full-text index release | `payload_index_id`, `collection_id`, `field_name`, `index_type`, `index_params`, `on_disk`, `build_status`, `query_surfaces`, `rebuild_policy`, `created_at` |
| `vector_filter_policy` | Allowed and required query filters | `filter_policy_id`, `route_id`, `required_filters`, `optional_filters`, `tenant_boundary`, `rights_boundary`, `freshness_boundary`, `fallback_behavior`, `test_case_refs`, `status` |
| `hybrid_vector_query_plan` | Dense/sparse/vector query composition | `query_plan_id`, `route_id`, `collection_alias`, `dense_vector_field`, `sparse_vector_field`, `prefetch_limits`, `fusion_policy`, `reranker_ref`, `candidate_k`, `final_k`, `eval_refs` |
| `multivector_retrieval_profile` | Late-interaction retrieval settings | `multivector_profile_id`, `vector_field_id`, `model_ref`, `per_document_vector_count`, `comparator`, `memory_cost_estimate`, `latency_eval_refs`, `recall_eval_refs`, `status` |
| `vector_quantization_profile` | Compression and recall tradeoff record | `quantization_profile_id`, `collection_id`, `vector_field_id`, `method`, `bits_or_compression`, `rescoring_enabled`, `oversampling_policy`, `ram_delta`, `latency_delta`, `recall_delta`, `rollback_target` |
| `vector_alias_record` | Stable query name and rollback pointer | `alias_id`, `alias_name`, `active_collection_id`, `candidate_collection_id`, `previous_collection_id`, `validation_gate_ref`, `switched_at`, `rollback_reason` |
| `vector_snapshot_record` | Recovery and reproducibility evidence | `snapshot_id`, `collection_id`, `source_snapshot_id`, `snapshot_uri`, `created_by_run`, `restore_drill_ref`, `retention_policy`, `status` |
| `vector_optimizer_policy` | Segment/index/storage tuning record | `optimizer_policy_id`, `collection_id`, `hnsw_config`, `indexing_threshold`, `memmap_or_on_disk_policy`, `segment_thresholds`, `compaction_policy`, `benchmark_refs` |
| `vector_partition_policy` | Tenant/workspace/source isolation design | `partition_policy_id`, `collection_id`, `partition_strategy`, `tenant_key`, `workspace_key`, `source_snapshot_boundary`, `access_test_refs`, `migration_policy`, `status` |
| `vector_store_release_gate` | Promotion gate for Qdrant or equivalent vector-store routes | `gate_id`, `route_id`, `collection_ref`, `source_snapshot_ref`, `vector_field_refs`, `payload_schema_refs`, `payload_index_refs`, `filter_policy_ref`, `hybrid_query_plan_ref`, `multivector_profile_refs`, `quantization_profile_refs`, `alias_ref`, `snapshot_refs`, `optimizer_policy_ref`, `partition_policy_ref`, `recall_eval_refs`, `latency_cost_refs`, `restore_drill_ref`, `rollback_target_ref`, `decision`, `reviewed_at` |

## Design Commitments

- Do not model "vector store" as one dependency. Model collection, vector fields, payload schema, indexes, filters, aliases, snapshots, and quantization separately.
- Pin collection and index schema to source snapshots and route releases.
- Use aliases for index promotion, rollback, and embedding-model migration.
- Evaluate multivectors and quantization with recall, latency, and cost evidence before production use.
- Keep tenant, rights, freshness, and sensitivity filters explicit in the retrieval trace.
- Treat snapshots and restore drills as release evidence, not backup housekeeping.

## Release Gate

A Qdrant-backed retrieval route cannot be promoted unless a `vector_store_release_gate` proves collection schema, source snapshot, vector fields, payload schema and indexes, required filter policy, hybrid query plan, multivector profile where applicable, quantization profile, alias/rollback pointer, snapshot and restore evidence, optimizer policy, partition policy, recall and latency/cost evals, and rollback target.

## Canon Decision

This note is canon-ready for Agent Studio production vector-store architecture. Qdrant-style vector retrieval should be treated as release-managed source-evidence infrastructure: collection schema, payload filters, hybrid plans, aliases, snapshots, quantization, and partitioning all affect which evidence agents see.
