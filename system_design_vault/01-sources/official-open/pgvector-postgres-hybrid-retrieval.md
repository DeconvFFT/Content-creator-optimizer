---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://github.com/pgvector/pgvector
  - https://www.postgresql.org/docs/current/indexes.html
  - https://www.postgresql.org/docs/current/functions-textsearch.html
---

# pgvector And Postgres Hybrid Retrieval

## Source Boundary

This note synthesizes the official pgvector repository documentation and current PostgreSQL 18 docs for indexes and text-search functions. It focuses on Agent Studio's local-first retrieval store, not on replacing dedicated vector databases for every future scale point.

## Core Design Lessons

pgvector keeps embeddings inside Postgres, which means source chunks, claims, rights metadata, run state, user feedback, and vectors can share ACID transactions, joins, backups, PITR, and relational constraints. That is why it fits Agent Studio's durable local plane: retrieval evidence can stay close to source provenance instead of being split across a separate vector service before the product has proven it needs that operational boundary.

The important caveat is recall. pgvector exact nearest-neighbor search has perfect recall, while HNSW and IVFFlat are approximate indexes that trade recall for speed. Adding an approximate index can change query results. Agent Studio therefore needs a route release record for every vector index setting and a recall benchmark before promoting an approximate index to production retrieval.

Distance metric is a schema contract. L2, inner product, cosine, L1, Hamming, and Jaccard require compatible vector types and operator classes. The route should not infer similarity semantics from a generic `embedding` column. It should store embedding model, dimensions, vector type, distance metric, operator class, and whether returned scores are distances, similarities, or transformed values.

HNSW and IVFFlat have different lifecycle behavior. HNSW has stronger speed/recall behavior but slower builds and higher memory use; it can be created without a training step. IVFFlat needs enough representative data before index creation and is tuned through list/probe choices. Agent Studio should treat both as index releases with build evidence, parameter snapshots, and rollback targets.

Query-time settings are product behavior. HNSW search uses a dynamic candidate-list setting; IVFFlat uses probes and max probes. These affect latency and recall at runtime, not only at migration time. Retrieval traces should capture the effective settings used for each query class.

Filters are not free. Combining approximate vector search with metadata filters can return fewer usable results if the index scan does not inspect enough candidates after filtering. Agent Studio should keep filter selectivity, required rights/freshness filters, iterative scan posture, exact fallback conditions, and post-filter candidate counts in the trace.

Postgres full-text search is the local lexical partner. `tsvector`, `tsquery`, `ts_rank`, `ts_rank_cd`, query rewriting, phrase queries, JSON-to-tsvector conversion, and headline/debug functions support exact API names, filenames, source titles, dates, and structured source-card fields that embeddings often blur. Hybrid retrieval should fuse vector distance, text-search rank, metadata quality, and graph/source authority before reranking.

Precision and compression choices are release decisions. `halfvec`, binary quantization, sparse vectors, and subvector strategies can reduce storage or index footprint, but they alter recall, ranking, and sometimes supported dimensions. They should be stored as a vector precision policy with eval evidence, not hidden inside DDL.

## Current-Source Cross-Check

Current pgvector docs still present the same local-retrieval contract: vectors live with Postgres data, exact nearest-neighbor search is the default, approximate HNSW/IVFFlat indexes trade recall for speed, distance operators and operator classes define similarity semantics, HNSW/IVFFlat build and query parameters alter recall/latency, and precision/quantization/vector-type choices are explicit data-shape decisions. The docs also still emphasize Postgres operational benefits such as joins, ACID behavior, and point-in-time recovery, which is why pgvector remains the first durable retrieval backend for Agent Studio.

Current PostgreSQL 18 index and text-search docs reinforce that local retrieval is not a single vector call. Index selection, index maintenance, text-search vectors/queries, rank functions, phrase/query rewrites, JSON-to-text-vector conversion, and lexical ranking are separate controls. Cross-checking these docs with the existing retrieval canon means local hybrid retrieval must have release evidence for both semantic vector behavior and lexical full-text behavior.

## Agent Studio Implications

Use pgvector as the first durable retrieval backend because it preserves locality, provenance, transactionality, and simple operational recovery. Use managed vector services later only when scale, tenancy, latency, or specialized retrieval behavior justifies the provider boundary.

Every retrieval route should be able to answer:

- which source snapshot and chunking policy produced the rows;
- which embedding model and dimension contract is stored;
- which vector type and distance metric is used;
- whether the query is exact or approximate;
- which HNSW/IVFFlat settings and query-time knobs were active;
- which metadata and rights filters ran before or after vector scoring;
- which lexical full-text fields and rank functions contributed to fusion;
- what recall/latency benchmark justified the current index;
- which rollback index or exact-search fallback exists.

## Datastore Requirements

Agent Studio needs local retrieval records for:

- embedding table release: table, vector column, dimensions, vector type, source snapshot, chunk policy, constraints, and owner;
- ANN index release: index type, operator class, distance metric, HNSW/IVFFlat parameters, build status, memory estimate, recall benchmark, and rollback index;
- query setting policy: route class, `ef_search` or probes, timeout, exact fallback, and expected latency/recall band;
- local filter execution: required metadata filters, expected selectivity, post-filter candidate count, iterative/exact fallback, and false-negative risk;
- Postgres hybrid plan: text-search config, weighted fields, rank function, query rewrite policy, vector search policy, fusion method, and reranker policy;
- precision policy: vector type, half/binary/sparse/subvector choice, storage savings, recall delta, and migration plan;
- maintenance event: index build, reindex, analyze/vacuum, extension version, Postgres version, restore drill, and benchmark rerun.
- `local_retrieval_release_gate`: promotion gate binding embedding table release, source/chunk snapshot, exact or approximate mode, ANN index release, distance/operator-class policy, query-setting policy, rights/filter execution policy, full-text search plan, fusion/rerank policy, precision policy, recall/latency benchmark, index maintenance/restore evidence, exact-search fallback, and rollback target.

## Operating Rule

For Agent Studio, pgvector is not just embeddings in a table. It is a governed retrieval subsystem inside the durable product database. Exact search, approximate indexes, filters, lexical search, precision choices, and query-time knobs all need release evidence because they can change which sources the agents see.

## Release Gate

A local Postgres/pgvector retrieval route cannot be promoted unless a `local_retrieval_release_gate` proves embedding table contract, chunk/source snapshot, vector dimensions/type, distance operator class, exact-versus-approximate mode, HNSW/IVFFlat parameters, query-time knobs, metadata/rights filter path, full-text search plan, fusion/rerank policy, precision/compression policy, recall and latency benchmark, index maintenance posture, exact fallback, and rollback target.

## Canon Decision

This note is canon-ready for Agent Studio local retrieval architecture. pgvector should be the default durable retrieval plane while the product is local-first, but every index, distance metric, filter path, precision choice, lexical fusion rule, and query knob must be treated as release-managed retrieval behavior, not incidental SQL.
