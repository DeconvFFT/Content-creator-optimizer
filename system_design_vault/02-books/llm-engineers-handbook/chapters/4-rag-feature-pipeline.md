---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "LLM Engineer's Handbook"
authors: "Paul Iusztin; Maxime Labonne"
chapter: "4"
chapter_title: "RAG Feature Pipeline"
source_path: "/Users/saumyamehta/DS interview prep/books/LLM Engineers Handbook.pdf"
rights_status: user_provided_local
source_lines: "4046-6844"
updated: 2026-05-17
cross_check_note_path: "system_design_vault/01-sources/official-open/llm-engineers-handbook-cross-check.md"
---

# 4 - RAG Feature Pipeline

## Reading Status

Direct source reading and official cross-check completed for chapter 4. This note is original synthesis only and does not include raw book text or long excerpts.

## Core Idea

RAG is not only an inference-time retrieval trick. A production RAG system needs a feature pipeline that turns raw source material into retrieval-ready, versioned, observable features. The chapter separates RAG into ingestion, retrieval, and generation, then focuses on the ingestion/feature side: extract, clean, chunk, embed, and load data into a vector-backed feature store.

For Agent Studio, this maps directly to the data store lane. The vault should not only hold notes; it should preserve source identity, cleaning policy, chunking policy, embedding model, vector-store metadata, and ingestion-run evidence so future agents can reason about where knowledge came from and how it was transformed.

## RAG Responsibilities

RAG addresses two practical LLM limitations:

- knowledge freshness and private/source-specific data;
- hallucination risk when answers are not grounded in supplied context.

The chapter frames the LLM as the reasoning/generation layer and retrieved context as the source-of-truth layer. That is useful, but Agent Studio should enforce it operationally: generation should be judged against retrieved and cited evidence, not against model confidence.

## Vanilla RAG Components

The chapter breaks RAG into three independent modules:

- Ingestion pipeline: extract raw documents, clean them, chunk them, embed chunks, and load vectors plus metadata into the vector store.
- Retrieval pipeline: embed the user query into the same vector space and retrieve similar entries from the vector store.
- Generation pipeline: construct a prompt from system instructions, user query, and retrieved context, then call the LLM.

Agent Studio implication:

- Keep ingestion, retrieval, and generation as separately observable components.
- Version prompt templates, embedding models, chunking parameters, retriever settings, and model versions together with run outputs.
- Treat training-serving skew analogously in RAG: query preprocessing and document preprocessing must be compatible, or retrieval quality will degrade.

## Embeddings And Vector Stores

Embeddings convert text, images, audio, code, or other objects into dense vectors where similarity can be computed. The chapter emphasizes that embedding choice depends on data type, task, hardware, and quality requirements. Cross-modal search requires models that place different modalities in a shared vector space.

Vector DBs add production DB capabilities around ANN search: CRUD, metadata filtering, scaling, updates, backups, access control, and monitoring. Standalone vector indexes can be useful, but production systems often need database behavior as much as similarity search.

Agent Studio implication:

- Store embedding model ID, embedding dimension, max input length, device/runtime, and embedding run ID.
- Use vector storage that supports metadata filtering, backups, access control, and operational monitoring.
- For multimodal sources, do not compare vectors across modalities unless the embedding model explicitly supports a shared vector space.

## Advanced RAG Stages

The chapter organizes advanced RAG into three optimization stages:

- Pre-retrieval: improve indexed data and improve the user query before vector search.
- Retrieval: improve embedding models and use DB filter/search features.
- Post-retrieval: reduce noise after retrieval before generation.

Agent Studio should preserve this structure because it gives clear ownership boundaries:

- Context Engineering owns cleaning, chunking, source metadata, and query rewriting policy.
- Retrieval Intelligence owns retriever selection, filters, hybrid search, and reranking.
- Source Ledger owns evidence selection, rejected evidence, final citations, and provenance.

## Pre-Retrieval Design

Important techniques:

- Sliding windows preserve context across chunk boundaries.
- Granularity improvements remove irrelevant, stale, duplicated, or noisy data before indexing.
- Metadata such as dates, URLs, source IDs, chapter markers, authors, categories, and external IDs enables filtering and auditing.
- Multi-index and chunk-size variants let the system retrieve with one representation while generating from a broader one.
- Small-to-big retrieval uses small chunks for accurate retrieval and wider stored context for generation.
- Query routing decides which data source, retrieval mode, prompt template, or no-retrieval path should handle a request.
- Query rewriting, expansion, HyDE, subqueries, and self-querying adapt user language into retrieval-friendly form.

Agent Studio implication:

- Chunking should be source-type-specific: books, docs, code, posts, lectures, artifacts, and feedback should not share one fixed policy.
- Metadata must be treated as retrieval infrastructure, not optional decoration.
- Query rewrites should be logged with original query, rewrite, route, confidence, and whether clarification was safer than guessing.

## Retrieval Design

The chapter recommends starting with practical retrieval upgrades:

- filtered vector search using metadata;
- hybrid search combining keyword matching and semantic vector search;
- domain-adapted embedding models or instruction-conditioned embeddings when generic embeddings do not understand domain terms.

Agent Studio implication:

- Use metadata filters before or alongside vector search for source, rights, date, corpus, project, author, modality, and trust level.
- Use hybrid retrieval where exact terms, filenames, IDs, APIs, classes, error codes, and paper names matter.
- Fine-tune or replace embedding models only after retrieval evals show generic embeddings are the bottleneck.

## Post-Retrieval Design

The chapter calls out two post-retrieval patterns:

- Prompt compression removes unnecessary retrieved detail while preserving answer-relevant information.
- Reranking uses a cross-encoder or similar model to score query-document pairs after first-stage retrieval.

Agent Studio implication:

- Rerank before generation when candidate sets are noisy or context windows are tight.
- Store reranker model, candidate count, kept count, dropped evidence, and latency.
- Compression should be auditable because over-compression can remove the evidence needed for faithful answers.

## Feature Pipeline Architecture

The chapter's LLM Twin design uses a feature pipeline rather than a one-off ingestion script. Raw data lives in a warehouse; processed data lives in a logical feature store. The feature store serves both:

- online RAG via vector DB records;
- offline training/fine-tuning via versioned artifacts.

Agent Studio implication:

- Separate raw source storage from processed retrieval features.
- Do not pollute raw source records with use-case-specific cleaning or chunking decisions.
- Store multiple processed snapshots when different downstream tasks need different representations.

## Batch, Streaming, And CDC

The chapter chooses batch ingestion for the LLM Twin because the dataset is small and minute-level freshness is acceptable. It also explains when streaming or change data capture becomes necessary.

Batch is appropriate when:

- the corpus is small enough to reprocess cheaply;
- immediate freshness is not required;
- simplicity is more valuable than low-latency synchronization.

CDC or streaming becomes important when:

- corpus size grows to millions of records;
- deletes and updates must propagate precisely;
- reprocessing everything is wasteful;
- freshness requirements tighten.

Agent Studio implication:

- Start local book/docs ingestion as batch, because the corpus is bounded and user-controlled.
- Add CDC-style manifests before adding streaming: source file hash, extraction timestamp, chunk policy version, embedding policy version, deletion handling, and last processed marker.
- Use log-based or event-driven ingestion only when the data sources become live and high volume.

## Implementation Patterns

The chapter uses several software design patterns that transfer well:

- Pydantic settings for typed configuration and environment overrides.
- ZenML pipelines and artifacts for repeatable, observable batch steps.
- Pydantic domain entities for runtime validation.
- State plus category modeling: cleaned documents, chunks, embedded chunks across posts, articles, repositories.
- Object-vector mapping over Qdrant, analogous to ORM/ODM patterns.
- Dispatcher/factory/strategy patterns to select cleaning, chunking, and embedding logic by data category.
- Singleton wrapper for embedding model loading so the model is loaded once and accessed consistently.

Agent Studio implication:

- Build ingestion as typed stages with contracts, not ad hoc file parsing.
- Use source-type handlers instead of global cleaning/chunking functions.
- Record per-step metadata: document count, chunk count, chunk size/overlap, embedding model, vector dimensions, failures, and collection names.
- Batch embedding calls for throughput.

## Failure Modes

- Query and document preprocessing diverge, causing retrieval skew.
- Generic chunking cuts semantically important boundaries.
- Vector-only retrieval misses exact entity names, filenames, IDs, or code symbols.
- Metadata is incomplete, so filtering, auditing, and freshness controls are weak.
- The feature store and source warehouse drift out of sync.
- Deletes and updates in raw data are not reflected in retrieval features.
- Cleaning optimized for one use case destroys information needed by another.
- Reranking/compression improves apparent relevance but drops necessary evidence.
- Embedding models are swapped without re-embedding and versioned provenance.
- Ingestion pipelines lack run metadata, making retrieval failures hard to debug.

## Agent Studio Design Decisions

- Use a batch feature pipeline for local books, official PDFs/docs, and curated lecture notes.
- Track source file hash and extraction hash before creating chunks.
- Keep raw extraction artifacts out of notes unless needed for local processing; notes should contain original synthesis.
- Store cleaned source metadata separately from chunk embeddings.
- Use source-type-specific handlers for books, official docs, lectures, white papers, code docs, and feedback.
- Store retrieval features with source ID, rights status, provenance, corpus, section/chapter, chunk policy, embedding model, and freshness timestamp.
- Implement hybrid retrieval and metadata filters as baseline design requirements.
- Keep ingestion manifests as first-class vault artifacts.

## Follow-Ups

- Define the Agent Studio ingestion manifest schema.
- Define handlers for local books, official docs, Stanford lecture notes, and white papers.
- Canon cross-check: [[01-sources/official-open/llm-engineers-handbook-cross-check]]

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "How I Learned to Stop Worrying and Love the Transformer" ([YouTube](https://www.youtube.com/watch?v=1GbDTTK3aR4)).
