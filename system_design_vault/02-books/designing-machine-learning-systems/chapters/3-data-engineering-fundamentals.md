---
type: book-chapter-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
source_title: "Designing Machine Learning Systems"
source_author: "Chip Huyen"
source_path: "/Users/saumyamehta/DS interview prep/books/Designing machine learning systems - an iterative process.pdf"
rights_status: user_provided_local
chapter: 3
chapter_title: "Data Engineering Fundamentals"
source_lines: "2473-3741"
---

# Chapter 3 - Data Engineering Fundamentals

## Core Thesis

ML systems depend on data infrastructure: sources, formats, data models, storage engines, processing patterns, and dataflow between services. These decisions shape what the system can retrieve, compute, debug, and evolve.

For Agent Studio, the chapter is directly relevant to the system-design vault and production datastore. The source corpus is not just files on disk; it needs schemas, storage boundaries, retrieval paths, streaming/batch workflows, and privacy rules.

## Data Sources

The chapter distinguishes several production data sources:

- user input, which is malformed, latency-sensitive, and untrusted;
- system logs, which are high-volume and essential for debugging;
- user behavior data, which is valuable but privacy-sensitive;
- internal databases, which carry operational state;
- third-party data, which introduces provenance, privacy, and policy risk.

## Agent Studio Implications

- Treat local books, official docs, lecture pages, YouTube playlists, user edits, trace logs, and reviewer feedback as different source classes.
- Do not mix trust levels. A user-owned local book, official OpenAI docs, a public webpage, and a generated draft need different provenance and freshness metadata.
- Logs should be queryable but not infinite. Keep high-value trace fields long term and move verbose payloads to retention-limited storage.
- User behavior signals such as accepted edits, rejected citations, and approval decisions are product data and should have explicit retention/access rules.

## Formats And Access Patterns

The chapter frames data formats through access patterns. Row-oriented formats fit example-level writes and reads; column-oriented formats fit feature/field scans and analytics. Text formats are human-readable but larger and weaker for precision; binary formats are compact and efficient but require readers that understand the layout.

## Agent Studio Implications

- Keep Obsidian notes as Markdown because they are human-editable canonical synthesis.
- Store structured run, source, chunk, trace, and eval metadata in relational tables.
- Store large extracted text, rendered media, thumbnails, and intermediate artifacts outside notes with pointers and hashes.
- Use column-friendly analytics exports for eval dashboards and usage/cost analysis.
- Avoid treating JSON blobs as a substitute for schema design when fields are queried frequently.

## Data Models

The chapter compares relational, document, and graph models:

- relational models enforce structure, reduce duplication, and support SQL-style joins;
- document models improve locality and tolerate changing shapes but push schema responsibility to readers;
- graph models make relationship traversal first-class.

Agent Studio needs all three patterns.

| Model | Agent Studio use |
|---|---|
| Relational | source manifests, runs, artifacts, eval datasets, graders, permissions, workflow versions |
| Document | provider responses, raw metadata, extracted structured fields, flexible agent state snapshots |
| Graph | source-to-claim links, concept maps, citation paths, agent handoffs, prerequisite relationships |

## Structured And Unstructured Data

The chapter treats structured versus unstructured data as a question of who accepts schema responsibility. Structured data makes querying easier but schema changes are costly. Unstructured data arrives faster and flexibly, but downstream readers must impose structure later.

## Agent Studio Implications

- Ingest raw files into a lake-like area only as intermediate material, not as the usable knowledge layer.
- Promote extracted, validated, attributed synthesis into structured notes and indexes.
- Record extraction schema versions so old chunks and new chunks can be compared.
- Do not let unstructured retrieved text control agent behavior directly; extract structured claims, fields, citations, or tasks first.

## Storage And Processing

The chapter distinguishes transactional and analytical workloads while noting that modern systems increasingly blur this line and decouple storage from compute.

Agent Studio needs both:

- transactional paths for user-facing runs, approvals, edits, tool actions, and workflow state;
- analytical paths for eval results, trace mining, cost/latency dashboards, retrieval quality, and corpus coverage.

The storage design should not force one database shape to do everything. Postgres can be the durable control plane, while object storage, vector indexes, graph tables, and analytical exports serve different access patterns.

## ETL And ELT

ETL validates and transforms before loading into a target schema. ELT loads quickly first, then transforms later. The chapter frames this as a tradeoff between early structure and fast arrival.

Agent Studio should use a hybrid:

- preserve the original source pointer, hash, and rights/provenance first;
- extract and validate before anything becomes searchable or canonical;
- promote only compact original synthesis to Obsidian;
- keep failed extraction and rejected chunks visible for debugging.

## Dataflow

The chapter covers three modes:

- database-mediated transfer;
- request/response services;
- real-time transports such as pubsub or queues.

Request-driven service calls are simple but create tight coupling and cascading failures. Event-driven transport helps data-heavy systems decouple producers from consumers.

## Agent Studio Implications

- Use request/response for interactive operations that need immediate answers.
- Use event-driven jobs for source ingestion, extraction, embedding, indexing, eval runs, and note-promotion workflows.
- Emit events for `source_added`, `extraction_completed`, `chunk_indexed`, `eval_failed`, `note_promoted`, and `artifact_published`.
- Keep idempotency keys and checkpoint state so retries do not duplicate notes or corrupt indexes.

## Batch And Stream Processing

Batch processing fits historical data and static features. Stream processing fits fast-changing signals and stateful updates. Many production systems need both.

For Agent Studio:

- batch jobs should refresh corpora, re-embed changed sources, run nightly evals, and compute coverage reports;
- stream or nearline jobs should update run traces, user feedback, tool events, and fresh source alerts;
- retrieval should know whether a feature or source is batch-stale or recently updated.

## Design Commitments

- Separate raw source storage, structured metadata, vector retrieval, graph relationships, and Obsidian synthesis.
- Design around access patterns, not tool convenience.
- Keep schema evolution explicit.
- Use graph traversal for evidence and concept relationships, not only vector search.
- Treat ingestion as an evented pipeline with retries, checkpoints, and auditability.

## Follow-Ups

- Add datastore table groups for source, extraction, chunk, embedding, trace, eval, artifact, and graph edges.
- Define event names for the ingestion and note-promotion pipeline.
- Decide which trace/log fields are long-retention versus short-retention.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
