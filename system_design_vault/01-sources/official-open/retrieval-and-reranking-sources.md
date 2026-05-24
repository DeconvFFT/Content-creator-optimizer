---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
sources:
  - https://www.anthropic.com/research/contextual-retrieval
  - https://microsoft.github.io/graphrag/index/overview/
  - https://microsoft.github.io/graphrag/query/overview/
  - https://www.microsoft.com/en-us/research/blog/graphrag-improving-global-search-via-dynamic-community-selection/
  - https://docs.cloud.google.com/architecture/gen-ai-graphrag-spanner
  - https://neo4j.com/developer/genai-ecosystem/hybrid-search/
  - https://neo4j.com/labs/genai-ecosystem/graphrag/
  - https://github.com/pgvector/pgvector
  - https://developers.openai.com/api/docs/guides/retrieval
  - https://www.elastic.co/guide/en/elasticsearch/reference/current/rrf.html
  - https://sbert.net/docs/package_reference/cross_encoder/cross_encoder.html
  - https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/
source_status: official_public
---

# Retrieval And Reranking Sources

## Why It Matters

The user explicitly wants high precision, high recall, broad coverage, and low false positives/false negatives. The retrieval layer must therefore be evaluated as a system, not just vector search.

## Key Takeaways

- Contextual retrieval adds chunk-specific context before embedding and keyword indexing.
- Microsoft GraphRAG treats graph construction as an indexing pipeline: extract entities, relationships, and claims; detect communities; generate summaries/reports; embed text; and query the completed index.
- GraphRAG query modes should be selected by question type: local search for entity-specific questions, global search for corpus-level synthesis, and DRIFT-style search when community context should broaden local retrieval.
- Dynamic community selection is a cost/quality optimization for global GraphRAG: classify relevant community reports before expensive map-reduce summarization.
- Google Cloud's GraphRAG architecture separates ingestion and serving, and frames GraphRAG as vector search plus knowledge-graph query over interconnected data.
- Neo4j's hybrid search pattern combines lexical, semantic, and structural graph signals, often with weighted reciprocal-rank fusion before graph expansion or reranking.
- pgvector keeps vector search close to durable Postgres state.
- Reciprocal rank fusion is a stable way to combine multiple retrieval result lists.
- Cross-encoders rerank query/document pairs but cost more than first-stage retrieval.
- OpenAI retrieval documentation reinforces source attributes, chunking strategy, batch ingestion, and vector-store lifecycle as first-class retrieval controls.
- Ragas separates RAG evaluation dimensions such as context precision, context recall, entity recall, response relevancy, faithfulness, groundedness, and agent/tool metrics.

## Agent Studio Design Implications

- Build hybrid retrieval: lexical, vector, metadata, graph.
- Fuse first-stage candidates before reranking.
- Record accepted and rejected evidence with reasons.
- Measure precision, recall, false positives, false negatives, and coverage.
- Use local graph search for entity- or claim-specific questions.
- Use global/community search for "what themes/patterns does this corpus show?" questions.
- Use dynamic community selection when global search is too expensive or too noisy.
- Use graph traversal for recall repair and multi-hop evidence, not unreviewed policy memory.
- Track retrieval mode, source list, fusion policy, graph traversal depth, reranker, metric suite, and dropped evidence in `retrieval_trace`.

## Open Questions

- Which reranker provider should follow the deterministic local reranker?
- Should entity graph traversal be limited by topic, source quality, or run-specific scope first?
- How should freshness-sensitive claims trigger web search versus local retrieval?
- Which graph schema is sufficient for Agent Studio's first production slice: source/chunk/claim/entity/topic only, or source/chunk/claim/entity/topic/artifact/run/feedback?
