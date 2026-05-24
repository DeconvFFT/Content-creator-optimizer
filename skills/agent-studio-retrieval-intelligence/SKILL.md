---
name: agent-studio-retrieval-intelligence
description: "Improve retrieval quality for source-backed content. Use when rewriting search queries, optimizing sparse/dense/web retrieval, fusing ranked lists, reranking candidates, building knowledge graph coverage, or auditing false positives, false negatives, recall, precision, and evidence coverage."
---

# Agent Studio Retrieval Intelligence

## Workflow

1. Rewrite the user topic into exact-keyword, semantic, entity, freshness, and contradiction-check queries.
2. Gather candidates from web search, source ledgers, sparse/full-text search, dense pgvector retrieval, metadata filters, and knowledge graph traversal.
3. Fuse candidates with Reciprocal Rank Fusion before expensive reranking.
4. Rerank the fused top-K candidates with a cross-encoder, late-interaction model, or deterministic fallback score when model providers are unavailable.
5. Build or refresh entity, source, claim, topic, artifact, and relationship graph coverage.
6. Record precision risks such as stale sources, weak publishers, unsupported claims, and low-rerank candidates.
7. Record recall risks such as missing source diversity, missing publication dates, low accepted source count, or untraversed graph neighborhoods.
8. Pass only accepted evidence into drafting and context packets.
9. Mark unsupported or under-covered claims explicitly instead of letting writers smooth over evidence gaps.

## Quality Targets

- High precision: accepted candidates should directly support the claims they are used for.
- High recall: the candidate window should include multiple source types and enough source diversity before reranking.
- Coverage: important entities, claims, and content artifacts should have traceable source and graph coverage.
- Low false positives: weak, stale, contradictory, or merely adjacent evidence should not enter final synthesis.
- Low false negatives: query expansion and graph traversal should reduce missed relevant sources.

## Outputs

- `retrieval_quality_ledger`
- `retrieval_candidates`
- `rerank_decisions`
- `knowledge_graph_nodes`
- `knowledge_graph_edges`
- `coverage_gaps`
- `recommended_queries`
