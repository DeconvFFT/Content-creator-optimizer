---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_documentation
rights_status: official_public
sources:
  - https://neo4j.com/docs/neo4j-graphrag-python/current/
  - https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html
  - https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html
  - https://neo4j.com/developer/genai-ecosystem/hybrid-search/
  - https://neo4j.com/labs/genai-ecosystem/graphrag/
  - https://neo4j.com/docs/cypher-manual/25/indexes/semantic-indexes/vector-indexes/
  - https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/full-text-indexes/
  - https://neo4j.com/docs/graph-data-science/current/introduction/
  - https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/fastrp/
---

# Neo4j GraphRAG And Graph Retrieval

## Read Scope

This note is original synthesis from official Neo4j documentation and developer material for Neo4j GraphRAG for Python, vector indexes, full-text indexes, hybrid search, knowledge-graph construction, Text2Cypher retrieval, entity resolution, Graph Data Science, and FastRP structural embeddings. It stores no raw documentation text, copied code samples, screenshots, or long excerpts.

## Core Reading

Neo4j's GraphRAG stack separates several retrieval modes that Agent Studio should not collapse:

- vector retrieval over graph nodes or relationships;
- hybrid retrieval over vector and full-text indexes;
- vector-plus-Cypher retrieval that expands context around vector hits;
- Text2Cypher retrieval for exact structured questions;
- tool-style retrieval that chooses among multiple retrieval tools;
- graph construction pipelines that extract entities, relationships, schema, and provenance from source text.

The important design point is that GraphRAG is not just "add a graph after vector search." The graph schema, extraction prompt, entity resolution policy, index release, retriever type, Cypher expansion, and answer prompt all change product behavior. Agent Studio should version them as route artifacts.

Neo4j's hybrid-search guidance treats hybrid search as a pattern rather than a special index. Each source branch returns a ranked candidate list; lexical, semantic, structural, graph-algorithm, exact traversal, or external-ranker signals can be fused. This is a good fit for Agent Studio because source-backed content needs exact terms, semantic paraphrase, graph neighborhood, and source-quality signals at the same time.

Vector indexes in Neo4j are schemaful operational objects. Dimensions, similarity function, vector property, node labels or relationship types, optional filterable properties, HNSW settings, quantization, and index state all matter. Newly created indexes can be unavailable while they populate. The preferred query surface is moving toward Cypher `SEARCH` on newer Neo4j versions; older procedures still exist but should be treated as versioned compatibility behavior.

Full-text indexes remain necessary for exact terminology: API names, book titles, error strings, entity aliases, identifiers, and policy terms. A graph retriever that skips lexical search will miss high-value exact matches, while a lexical-only retriever will miss paraphrase and relationship context. Agent Studio should fuse both, then expand graph context only after candidate quality and source bounds are known.

Vector Cypher retrieval is the critical GraphRAG bridge. It first finds similar nodes, then runs a Cypher retrieval query to fetch related nodes, relationships, properties, or source snippets around each hit. This gives Agent Studio a route to implement bounded graph expansion: start from accepted chunks, claims, entities, artifacts, or source records; traverse allowed edge types; cap depth and fanout; and preserve the path that justified each context item.

Text2Cypher is powerful but risky. It uses an LLM to generate Cypher from a natural-language question, then answers from query results. The generated query may be syntactically invalid or semantically wrong. For Agent Studio, Text2Cypher should be a governed route with a visible schema snapshot, example set, allowed labels/relationships/properties, read-only enforcement, timeout, row limit, cost estimate, query linting, and failure record. It should not be a hidden fallback inside normal answer generation.

The KG Builder pipeline turns source text into entities and relations through loader, splitter, schema extraction or schema guidance, entity/relation extraction, graph writing, and entity resolution. The schema settings matter: allowing extra node types, relationships, patterns, or properties changes graph shape and retrieval behavior. Structured output support can improve extraction reliability when available, but it does not remove the need for review, provenance, and schema-drift checks.

Entity resolution is a separate source of truth risk. Exact-name merging is fast and deterministic but can miss aliases. Fuzzy or embedding-based resolution can improve recall but can merge distinct entities. Agent Studio should store resolver type, candidate pairs, merge decisions, rejected merges, reviewer overrides, and downstream retrieval impact. A bad merge can silently corrupt graph traversal and claim attribution.

Graph Data Science adds structural signals such as node embeddings, centrality, community, similarity, and path features. These are useful ranking priors, not proof. FastRP-style structural embeddings should be refreshed when topology changes enough to invalidate old embeddings. Agent Studio should treat graph algorithms as derived index artifacts with projection scope, parameters, write/mutate mode, refresh trigger, eval evidence, and staleness rules.

## Current-Source Cross-Check

Current Neo4j GraphRAG docs still separate the GraphRAG runtime into driver, retriever, LLM, prompt, retriever configuration, returned context, vector-index operations, Vector Cypher retrieval, custom retrievers, and structured-output support. That confirms the Agent Studio rule that graph retrieval behavior is a route release, not a generic "graph on" flag.

Current Neo4j KG Builder docs still frame graph construction as a pipeline with loading, splitting, schema guidance, extraction, writing, and entity resolution. Current Neo4j vector-index and full-text-index docs still make vector and lexical search operational schema objects, while Graph Data Science/FastRP docs still position structural embeddings as derived graph artifacts. Cross-checking these sources means graph schema, extraction pipeline, indexes, entity resolution, Text2Cypher policy, Vector Cypher expansion, and structural embeddings must move through one graph-retrieval release decision.

## Agent Studio Datastore Additions

| Datastore object | Purpose | Key fields |
|---|---|---|
| `kg_schema_release` | Versioned graph schema for extraction and Text2Cypher | `kg_schema_id`, `source_snapshot_id`, `node_types`, `relationship_types`, `allowed_patterns`, `property_contracts`, `extra_node_policy`, `extra_relationship_policy`, `extra_property_policy`, `status` |
| `kg_extraction_pipeline_run` | Source-to-graph construction execution | `kg_pipeline_run_id`, `source_scope`, `loader_profile`, `splitter_profile`, `schema_release_id`, `extractor_model_ref`, `structured_output_enabled`, `writer_policy`, `entity_resolver_policy_id`, `created_nodes`, `created_edges`, `review_status` |
| `entity_resolution_policy` | Merge strategy for graph entities | `resolver_policy_id`, `resolver_type`, `match_property`, `similarity_threshold`, `dependency_requirements`, `filter_query`, `review_required`, `precision_risk`, `status` |
| `entity_resolution_decision` | Accepted or rejected merge evidence | `resolution_id`, `pipeline_run_id`, `candidate_entity_ids`, `decision`, `score`, `resolver_policy_id`, `reviewer_ref`, `downstream_trace_refs`, `created_at` |
| `graph_hybrid_retrieval_plan` | Fused lexical, semantic, and structural retrieval | `graph_hybrid_plan_id`, `route_id`, `vector_index_ref`, `fulltext_index_ref`, `structural_embedding_ref`, `source_weights`, `fusion_policy`, `source_k`, `final_k`, `reranker_ref`, `eval_refs` |
| `vector_cypher_retrieval_plan` | Bounded graph expansion after vector hits | `vector_cypher_plan_id`, `route_id`, `vector_index_ref`, `retrieval_query_ref`, `allowed_labels`, `allowed_relationships`, `depth_limit`, `fanout_limit`, `return_property_policy`, `timeout_ms`, `row_limit` |
| `text2cypher_policy` | Governed natural-language-to-Cypher route | `text2cypher_policy_id`, `route_id`, `schema_release_id`, `example_set_ref`, `allowed_labels`, `allowed_relationships`, `read_only_enforced`, `query_linter_ref`, `timeout_ms`, `row_limit`, `failure_policy` |
| `text2cypher_attempt` | Query-generation and execution trace | `attempt_id`, `run_id`, `policy_id`, `question_ref`, `generated_query_hash`, `lint_result`, `execution_status`, `row_count`, `error_type`, `accepted_for_answer`, `created_at` |
| `graph_index_release` | Operational release for graph retrieval indexes | `graph_index_release_id`, `schema_release_id`, `vector_index_refs`, `fulltext_index_refs`, `search_clause_version`, `index_state_checks`, `population_evidence`, `rollback_target`, `status` |
| `structural_embedding_release` | GDS/FastRP-style topology embedding artifact | `structural_embedding_release_id`, `graph_projection_ref`, `algorithm`, `parameters`, `write_or_mutate_mode`, `topology_snapshot_id`, `refresh_trigger`, `staleness_status`, `eval_refs` |
| `graph_expansion_trace` | Traversal evidence attached to retrieval results | `expansion_trace_id`, `retrieval_trace_id`, `start_node_ids`, `edge_types`, `depth`, `fanout`, `accepted_paths`, `rejected_paths`, `pruning_reasons`, `latency_ms` |
| `graph_retrieval_release_gate` | Promotion gate for Neo4j/GraphRAG retrieval routes | `gate_id`, `route_id`, `kg_schema_release_ref`, `kg_extraction_pipeline_ref`, `entity_resolution_policy_ref`, `entity_resolution_decision_refs`, `graph_index_release_ref`, `graph_hybrid_retrieval_plan_ref`, `vector_cypher_retrieval_plan_ref`, `text2cypher_policy_ref`, `structural_embedding_release_ref`, `graph_expansion_trace_eval_refs`, `path_validity_eval_refs`, `entity_precision_eval_refs`, `latency_cost_refs`, `fallback_policy_ref`, `rollback_target_ref`, `decision`, `reviewed_at` |

## Design Commitments

- Treat graph schema, extraction pipeline, entity resolution, graph indexes, structural embeddings, and retriever policy as separate release artifacts.
- Use graph retrieval when relation structure, multi-hop evidence, entity lineage, or exact source dependency matters; do not run GraphRAG by default for simple lexical/vector questions.
- Keep Text2Cypher read-only, bounded, schema-pinned, logged, and linted.
- Store graph-expansion paths, not just final context text.
- Evaluate graph retrieval on source recall, path validity, entity-resolution precision, fanout control, latency, and false positive/negative evidence.
- Refresh structural embeddings and graph algorithm outputs when graph topology changes materially.

## Release Gate

A graph retrieval route cannot be promoted unless a `graph_retrieval_release_gate` proves graph schema, KG extraction pipeline, entity-resolution policy and decisions, vector/full-text/structural index releases, graph hybrid retrieval plan, Vector Cypher expansion bounds, Text2Cypher safety policy where enabled, graph expansion trace evals, path-validity evals, entity-resolution precision, fanout/latency/cost evidence, fallback behavior, and rollback target.

## Canon Decision

This note is canon-ready for Agent Studio graph retrieval architecture. Neo4j-style GraphRAG should be a routed, release-managed capability for relation-heavy or multi-hop source tasks, with graph paths and schema/index provenance stored as evidence.
