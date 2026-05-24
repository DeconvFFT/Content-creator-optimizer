---
type: research
project: agent-studio
status: active
updated: 2026-05-17
owners:
  - retrieval-intelligence-agent
  - knowledge-graph-curator-agent
  - source-ledger-agent
---

# Retrieval Intelligence and Knowledge Graph Research

## Goal

The system must retrieve the best available information with high precision, high recall, and broad coverage. We want to reduce false positives and false negatives before content generation and before final answers.

## Working Architecture

1. Query understanding.
2. Query rewriting and subquery generation.
3. Parallel candidate retrieval:
   - BM25 or Postgres full-text search.
   - Dense pgvector search.
   - Web search providers.
   - Metadata filters.
   - Knowledge graph traversal.
4. Reciprocal Rank Fusion across candidate lists.
5. Cross-encoder or late-interaction reranking of the fused top-K.
6. Source quality, freshness, contradiction, and coverage checks.
7. Context packet assembly using only accepted evidence and explicit unsupported labels.

## 2026-05-17 Deep Research Update

Source capture: [[../raw/articles/2026-05-17-realtime-voice-and-retrieval-research-pass]].

Best direction is a multi-stage retrieval system, not a single "smart search" call:

1. Generate multiple query forms: literal, semantic, entity-focused, platform/content-intent, and freshness-focused.
2. Retrieve candidates in parallel from lexical search, dense vectors, web search, metadata filters, and graph neighborhoods.
3. Fuse result lists before reranking so no one retriever can dominate recall.
4. Rerank only the fused top-K with a stronger scorer.
5. Accept evidence only after source-quality, freshness, contradiction, and coverage checks.
6. Feed accepted evidence into source ledgers, claim verification, context packets, and writer revisions.

The durable store remains Postgres + pgvector in v1. Dedicated retrieval infrastructure such as Qdrant, Elasticsearch, or Neo4j can be added behind provider interfaces when benchmark evidence shows pgvector/full-text plus the Rust reranker is not enough.

## Retrieval Quality Strategy

### Candidate Generation

Use candidate fanout to reduce false negatives:

- exact keyword and phrase search for names, acronyms, numeric facts, paper titles, and API parameters;
- dense vector search for paraphrases and conceptual matches;
- web search for freshness and source diversity;
- metadata filters for date, source type, platform, model/provider, and trust tier;
- graph neighborhood expansion for entity-linked and multi-hop questions.

### Fusion

Use reciprocal rank fusion or weighted fusion before reranking:

- RRF is robust when retrievers return differently scaled scores.
- Weighted fusion is useful after enough evaluation data exists to tune retriever weights.
- Fusion output must keep each candidate's source retriever, original rank, and reason so later review can explain why it entered the context window.

### Reranking

Rerank the fused top-K, not the full corpus:

- deterministic local reranker remains the testable fallback;
- Rust reranker is the low-latency local provider path;
- cross-encoder or late-interaction reranking is the stronger semantic option when model/runtime cost is acceptable;
- rerank output must include score, decision reason, accepted/rejected status, and risks.

### Knowledge Graph

Build the graph around production evidence, not generic encyclopedia structure:

- nodes: source, claim, topic, entity, artifact, author/provider, model/tool, dataset, run, feedback item;
- edges: supports, contradicts, mentions, derived_from, revises, depends_on, same_entity_as, freshness_supersedes;
- traversal: bounded 1-2 hop expansion unless a task explicitly asks for multi-hop research;
- rule: graph edges identify candidate evidence; they do not validate claims by themselves.

### Evaluation

Every serious retrieval run should produce measurable quality output:

- precision over accepted evidence;
- recall against labeled expected source ids, tags, or wiki notes when available;
- false-positive ids;
- false-negative ids;
- topic/entity/source-diversity coverage;
- freshness gaps;
- contradiction gaps;
- recommended follow-up queries.

This is how the system minimizes false positives and false negatives before the writing agents see context.

## Precision Controls

- Rerank candidate evidence before synthesis.
- Require major claims to map to source records.
- Block weak, stale, or unsupported evidence from final publishing.
- Record contradiction checks.
- Keep source quality and freshness in the source ledger.

## Recall Controls

- Use multi-query expansion.
- Keep exact keyword search alongside dense semantic search.
- Use graph traversal for entity-linked and multi-hop questions.
- Keep a larger candidate pool before reranking.
- Record missed-source audits when review finds missing evidence.

## Coverage Controls

- Build entity, claim, source, artifact, and topic nodes.
- Link claims to source records and artifacts.
- Track source diversity and freshness.
- Record coverage gaps as retrieval evaluation artifacts.

## Implementation Requirements

- Done: add Retrieval Intelligence Agent.
- Done: add Knowledge Graph Curator Agent.
- Done: make Retrieval Intelligence Agent an executable worker that builds retrieval-quality ledgers rather than falling through to generic deterministic/Gemma output.
- Done: make Knowledge Graph Curator Agent an executable worker that records source/claim/artifact graph coverage, traversal edges, and gap counts rather than falling through to generic deterministic/Gemma output.
- Done: create bounded Web Research Agent follow-ups from non-ready retrieval-quality ledgers so recall and coverage gaps become actionable A2A work.
- Done: architecture review now distinguishes concrete worker executor coverage from default worker-list membership.
- Done: add retrieval candidate records to the Postgres schema.
- Done: add rerank decision records to the Postgres schema.
- Done: add knowledge graph node and edge records to the Postgres schema.
- Done: add retrieval evaluation records to the Postgres schema.
- Done: add `retrieval_quality_ledger` artifact and endpoint.
- Done: add source-ledger integration so claim verification can see accepted retrieval evidence and rejected/at-risk source context.
- Add Obsidian review output for retrieval quality decisions.

## Current Worker Contract

- `retrieval-intelligence-agent` owns retrieval-quality ledgers, accepted-source counts, precision/recall/coverage risk summaries, reranker fallback proof, and Web Research follow-ups for non-ready ledgers.
- `knowledge-graph-curator-agent` owns graph coverage summaries over source, claim, and artifact nodes. Its traversal edges are provenance evidence only; graph proximity does not count as factual claim support. Claims are labeled `supported_by` only when their coverage status is covered; non-supported claims with source ids are `candidate_evidence` until claim verification upgrades them.
- `web-research-agent` owns provider-backed source acquisition for follow-up queries raised by retrieval-quality gaps.
- Architecture review must flag any roster agent that is not covered by a concrete worker executor, even if the agent appears in the default worker cycle.

## Sources To Keep Reviewing

- pgvector official repository: https://github.com/pgvector/pgvector
- Elasticsearch Reciprocal Rank Fusion docs: https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion
- Microsoft GraphRAG docs: https://microsoft.github.io/graphrag/
- Microsoft Research GraphRAG project: https://www.microsoft.com/en-us/research/project/graphrag/
- ColBERT paper: https://arxiv.org/abs/2004.12832
- Anthropic Contextual Retrieval: https://www.anthropic.com/engineering/contextual-retrieval
- Sentence Transformers CrossEncoder docs: https://www.sbert.net/docs/package_reference/cross_encoder/model.html
- OpenAI Retrieval docs: https://developers.openai.com/api/docs/guides/retrieval
