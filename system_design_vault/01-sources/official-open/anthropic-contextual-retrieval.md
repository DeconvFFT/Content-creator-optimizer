---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_public
provenance_status: official_anthropic_engineering_article_direct_read
sources:
  - https://www.anthropic.com/engineering/contextual-retrieval
---

# Anthropic Contextual Retrieval

## Scope

Direct-read synthesis from Anthropic's official engineering article on Contextual Retrieval, published 2024-09-19 and checked on 2026-05-18. This note captures retrieval design implications for Agent Studio. It stores no raw article text, copied prompt templates, copied examples, figures, or long excerpts.

## Core Pattern

Traditional RAG often strips a chunk away from the document context that makes it retrievable and usable. Anthropic's contextual retrieval pattern repairs that by generating compact chunk-specific context from the whole document, prepending that context to the chunk, and indexing the contextualized chunk for both embeddings and BM25-style lexical search.

The Agent Studio decision: source chunks should not be anonymous text slices. A retrieval unit should know where it came from, what surrounding document context makes it meaningful, and which contextualization process produced the searchable representation.

## Current-Source Cross-Check

The current official Anthropic article still presents Contextual Retrieval as a preprocessing pattern that prepends concise chunk-specific context before both embedding and BM25 indexing. It also still frames BM25 plus embeddings, rank fusion, reranking, prompt caching, and route-specific evals as a stack rather than a single vector-search feature.

The article's quantitative examples are useful as motivation, but Agent Studio should not hard-code them as universal guarantees. The canon decision is architectural: contextualized chunks, contextual BM25, reranking, prompt-cache economics, and top-K choices need route-specific eval evidence because source type, chunking, embedding model, query class, and context budget change the outcome.

## Retrieval Stack Implications

Anthropic's article reinforces a stacked retrieval path:

- use full-document prompting only when the knowledge base fits the context window and prompt caching makes it practical;
- for larger corpora, chunk the source material;
- index both semantic embeddings and lexical/BM25-style representations;
- add chunk-specific context before both embedding and lexical indexing;
- fuse or combine first-stage retrieval results;
- rerank a larger candidate pool down to the final context pack;
- run evals because chunking, context generation, embedding model, top-K, and reranking settings are workload-specific.

For Agent Studio, this means "vector search" is too weak as a product contract. The route must declare whether it uses exact lexical search, semantic search, metadata filters, contextualized chunks, graph traversal, fusion, and reranking.

## Chunk Context Contract

Each chunk needs a separate context record:

- source/document identity;
- local heading or section path;
- date/version if the source is time-sensitive;
- concept/entity aliases that only appear elsewhere in the document;
- compact explanation of how this chunk fits the source;
- contextualizer prompt/model/version;
- whether the context is stored, embedded, indexed lexically, or only used at query time;
- rights/sensitivity boundary for the contextual text.

This is especially important for Agent Studio because many sources are long technical PDFs, lecture notes, docs, and cross-checks. A chunk like "this improves latency" is useless unless the system knows which route, engine, metric, model, and workload the sentence belongs to.

## Hybrid Retrieval Baseline

The article's BM25 discussion matters for technical system design sources. Embeddings can miss exact identifiers: error codes, API names, model names, filenames, paper acronyms, route IDs, schema object names, library flags, and version strings. Lexical retrieval should be a first-class peer to embeddings.

Agent Studio should default to:

- lexical/BM25 for exact names, identifiers, and rare technical terms;
- embeddings for semantic paraphrases;
- metadata filters for source class, rights, recency, owner, and topic;
- graph search for relationships and dependency paths;
- reranking after deduplication when the candidate pool is broad.

## Reranking Contract

Reranking is a precision layer over a broad first-stage pool. It can reduce irrelevant context and downstream cost, but it adds runtime latency and can introduce false negatives if the reranker is miscalibrated.

Every reranked retrieval trace should record:

- first-stage candidate count;
- retrieval modes used;
- fusion/dedup policy;
- reranker provider/model/version;
- reranked candidate count;
- final kept count;
- dropped evidence and rejection reason;
- latency/cost;
- false-negative audit sample.

## Evaluation Contract

Anthropic evaluates contextual retrieval with retrieval failure over top-K results. Agent Studio should apply the same spirit but make it route-specific:

- define relevant source/chunk labels before tuning;
- track Recall@K for source-backed answers where missing evidence is dangerous;
- track Precision@K and rejected-context reasons where context budget is tight;
- evaluate K values separately for quick answers, deep synthesis, and canon-update routes;
- compare raw chunks, contextualized chunks, hybrid retrieval, and reranked contextual hybrid retrieval;
- evaluate final answer faithfulness separately from retrieval recall.

## Caching And Cost

Context generation can be expensive if the whole document is repeatedly passed for every chunk. Prompt caching makes contextualization more practical when the stable document prefix can be cached. For Agent Studio, contextualization jobs should be batch/background ingestion runs with cache policy, cost estimate, and retry/idempotency records.

Do not contextualize every source blindly. Use it where chunk ambiguity hurts recall or where source-backed answers are high value: books, official docs, Stanford lecture notes, design canon, API docs, route-change proposals, incident notes, and eval failure corpora.

## Datastore Additions

- `chunk_context_record`: generated chunk-specific context, contextualizer route, source/document refs, section path, context hash, rights/sensitivity labels, and review status.
- `contextualization_run`: batch job that generates chunk contexts with model, prompt version, cache policy, source scope, attempted/succeeded/failed chunks, cost, and latency.
- `hybrid_retrieval_policy`: lexical, semantic, metadata, graph, fusion, rerank, and final top-K settings for a route.
- `retrieval_fusion_record`: candidate lists, fusion method, dedup keys, score/rank normalization caveats, and selected pool.
- `rerank_audit_sample`: dropped candidate, expected relevance, reranker score, reviewer label, false-negative flag, and action.
- `retrieval_k_experiment`: K value, candidate pool size, final context count, recall/precision/MRR/MAP/NDCG metrics, cost, latency, and decision.
- `contextual_retrieval_release_gate`: promotion gate binding source snapshot, chunk policy, contextualizer prompt/model/version, context hash policy, embedding/BM25 indexing flags, hybrid retrieval policy, fusion policy, reranker policy, K experiment, prompt-cache evidence, dropped-evidence audit, retrieval evals, final-answer faithfulness evals, and rollback condition.

## Release Gates

Do not promote a retrieval route when:

- chunks lack document/section/source identity;
- contextualizer prompts are unversioned;
- chunk context is mixed with source text without provenance;
- lexical search is absent for identifier-heavy technical corpora;
- reranking drops relevant minority/source-family evidence without audit;
- K was tuned on a final test set;
- retrieval recall is inferred only from final answer quality;
- prompt-cache savings are claimed without cache hit/miss and invalidation evidence.

## Release Gate

A contextual retrieval route cannot be promoted unless a `contextual_retrieval_release_gate` proves source/chunk snapshot identity, contextualizer versioning, derived-context provenance, embedding and lexical indexing flags, hybrid retrieval/fusion policy, reranker policy, K selection experiment, prompt-cache and cost evidence, false-negative audit samples for dropped candidates, retrieval evals, final-answer faithfulness evals, and a rollback path to raw chunks or the prior retrieval policy.

## Agent Studio Decision

This note is canon-ready for Agent Studio retrieval design. Use contextual retrieval for the system-design vault where source chunks are likely to be ambiguous outside their source. Store contextualized representations as derived retrieval artifacts, not as replacement source truth. Final claims still cite source records/chunks; contextualized text is a retrieval aid and must remain traceable to the original source snapshot.
