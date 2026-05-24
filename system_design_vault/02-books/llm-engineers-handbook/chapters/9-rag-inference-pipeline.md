---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "LLM Engineer's Handbook"
authors: "Paul Iusztin; Maxime Labonne"
chapter: "9"
chapter_title: "RAG Inference Pipeline"
source_path: "/Users/saumyamehta/DS interview prep/books/LLM Engineers Handbook.pdf"
rights_status: user_provided_local
source_lines: "11666-13003"
updated: 2026-05-17
cross_check_note_path: "system_design_vault/01-sources/official-open/llm-engineers-handbook-cross-check.md"
---

# 9 - RAG Inference Pipeline

## Reading Status

Direct source reading and official cross-check completed for chapter 9. This note is original synthesis only and does not include raw book text or long excerpts.

## Core Idea

The RAG inference path is where retrieval decisions become user-visible answers. The chapter separates the already-built feature pipeline from the request-time retrieval/generation pipeline, then implements query expansion, self-querying, filtered vector search, reranking, prompt construction, and model invocation under a modular `ContextRetriever`.

For Agent Studio, this chapter is a concrete blueprint for retrieval orchestration: user query in, query variants and metadata extraction, filtered search across collections, deduplication, reranking, context assembly, LLM call, and answer out.

## Inference Pipeline Shape

The chapter's inference flow:

- user submits query;
- query expansion creates multiple search perspectives;
- self-query extracts structured metadata filters;
- each expanded query is embedded;
- filtered vector searches run against relevant collections;
- results are aggregated and deduplicated;
- reranker scores candidate chunks against the original query;
- top chunks are serialized into context;
- prompt is built from query and context;
- LLM generates the answer.

Agent Studio implication:

- Treat retrieval as a multi-step trace, not a single function call.
- Store each query variant, metadata filter, searched collection, retrieved chunk, dedup decision, rerank score, and final context item.

## Query Expansion

Query expansion uses an LLM to generate alternative versions of the user's request, broadening the searched embedding space. This helps when the original query is underspecified, narrow, or phrased differently from indexed content.

Tradeoff:

- more query variants can improve recall;
- more query variants increase retrieval latency and cost.

Agent Studio implication:

- Expansion count should be configurable by agent and workload.
- Expanded-query searches should run in parallel where possible.
- Store generated queries and measure whether expansion improves downstream answer quality.

## Self-Querying

Self-querying extracts structured metadata from natural language, such as author identity, IDs, tags, source type, date, tenant, or corpus. Those fields become filters in vector search.

Agent Studio implication:

- Do not rely on embeddings to encode exact constraints.
- Use structured filters for rights status, source corpus, author, date, project, document type, tenant, and trust level.
- If a required filter value is ambiguous, ask for clarification or search a broader safe scope rather than guessing.

## Filtered Vector Search

Plain vector search can retrieve semantically similar but contextually wrong documents. Filtered vector search reduces search space using metadata and improves both relevance and latency.

Agent Studio implication:

- Every chunk must carry metadata that supports filtering.
- Retrieval plans should combine semantic search with exact operational constraints.
- Filtered search should be measured for both recall loss and precision gain.

## Reranking

Reranking applies a cross-encoder or similar model after initial retrieval to score query-document pairs more precisely than embedding distance alone. It is especially valuable after query expansion because expansion can produce a broad candidate pool.

Agent Studio implication:

- Keep reranking as a standard post-retrieval stage for high-stakes answers.
- Store rerank scores and dropped candidates for debugging.
- Use reranking budgets: candidate count, top-k, model ID, latency limit.

## Deduplication

Expanded queries can retrieve overlapping chunks. The chapter deduplicates aggregated candidates before reranking.

Agent Studio implication:

- Use stable chunk IDs based on source identity plus chunk policy, not only text content.
- Dedup before expensive reranking when possible.
- Preserve duplicate-hit count as a relevance signal rather than discarding all evidence of repeated retrieval.

## Prompt Construction

The chapter builds an augmented prompt from user query and retrieved context, then calls the LLM. This is simple by design, but the architecture keeps retrieval and generation modular so each can be tested independently.

Agent Studio implication:

- Context serialization should preserve source IDs and citations.
- Prompt construction should be versioned.
- Retrieval modules should be callable independently for debugging and evaluation.

## Improvement Paths

The chapter identifies several future improvements:

- conversation memory with summarization or recent-turn windows;
- routing to decide which collections to search;
- hybrid search combining vector and keyword/BM25 retrieval;
- multi-index vector structures that combine content with other fields such as platform, date, or category.

Agent Studio implication:

- Add a retrieval router before searching all collections.
- Use hybrid search for exact technical terms, filenames, APIs, and system-design concepts.
- Use memory summaries carefully; store the summary version and source conversation turns.
- Consider multi-index/search schemas for freshness, corpus, modality, and source authority.

## Failure Modes

- Expanded queries drift away from the user's intent.
- Metadata extraction invents or misreads a filter.
- Filtered search over-constrains and drops the needed evidence.
- Searches across every collection waste latency and return irrelevant candidates.
- Deduplication removes useful diversity or provenance.
- Reranker improves semantic relevance but ignores source authority or freshness.
- Final context loses source identity during serialization.
- Conversation memory grows until it becomes expensive or misleading.

## Agent Studio Design Decisions

- Implement retrieval traces with stages: original query, expansion, self-query, filters, search, dedup, rerank, context pack, generation.
- Add source-aware filters to every local book/document chunk.
- Use query expansion only where recall matters and latency budget allows.
- Add a retrieval router before searching every corpus.
- Make reranker settings explicit in the agent profile.
- Preserve retrieved-but-rejected evidence for debugging.
- Include source references in context serialization.

## Follow-Ups

- Define Agent Studio retrieval trace schema.
- Decide default expansion count and rerank top-k for local book notes.
- Canon cross-check: [[01-sources/official-open/llm-engineers-handbook-cross-check]]

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
