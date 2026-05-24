---
type: ingestion-coverage-note
project: agent-studio-system-design
status: active
updated: 2026-05-21
source_manifest: "05-ingestion-runs/source-records-official-open-urls.json"
---

# Official/Open URL Coverage Priority

## Purpose

The per-URL manifest now separates citation from coverage. A URL can be cited by a cross-check, covered by a deep-read note, covered by a canon note, or merely inventoried for future ingestion. This prevents the vault from pretending that an inventory link is already a source-understood note.

This note is original synthesis from the current manifest only. It stores no raw source text or long excerpts.

## Current Coverage

| Coverage status | Count | Meaning |
|---|---:|---|
| `covered_by_canon_note` | 879 | At least one citing note is canon-ready and uses the source in architecture-grade synthesis. |
| `covered_by_deep_read_note` | 0 | At least one citing note is deep-read-pass but not necessarily promoted to canon. |
| `covered_by_process_note` | 2 | The URLs informed the ingestion workflow only and are not architecture-source canon. |
| `inventory_or_worklist_only` | 0 | The URL is listed or used as worklist context but lacks deep-read/canon coverage in this manifest. |

The manifest contains 881 deduplicated official/open URL records across 159 domains.

The URL manifest's `citing_note_statuses` were recomputed from current vault note frontmatter on 2026-05-21. Current citing-note status counts are 887 `canon_ready`, 91 `active`, 2 `process_note`, and 0 stale `deep_read_pass_1` markers. Coverage status is still intentionally stricter than citation: a URL is canon-covered only when at least one current citing note is canon-ready.

## Priority Queue

The manifest flags 0 records for follow-up:

- 0 records currently meet the direct-read/source-check threshold before use as architecture evidence.
- 0 records have deep-read-only coverage requiring cross-check or promotion.

Highest-priority direct-read/source-note targets:

No current official/open URL records remain inventory-only. Exact inventory overview URLs for Kafka, PostgreSQL, DDIA, OpenAI guardrails, OpenAI Responses state/tool runtime, OpenAI file search/vector stores/web search, OpenAI model-behavior policy sources, provider batch inference runtime docs, provider image/video generation runtime docs, document layout/OCR ingestion runtime docs, model gateway/provider routing runtime docs, code execution sandbox runtime docs, OpenAI Apps SDK/ChatGPT Apps, OpenAI Agent Builder/ChatKit, OpenAI production readiness, Anthropic tool/computer-use runtime docs, Google Cloud GenAI operations/evaluation, Google Cloud agentic architecture patterns, Google secure AI agents/Model Armor, Google Agent Platform managed runtime docs, LangSmith Agent Server deployment/runtime docs, CrewAI crews/flows/runtime docs, Ragas/LangSmith eval docs, Langfuse/Phoenix/TruLens/DeepEval observability docs, object/artifact storage lifecycle docs, annotation and human-feedback data-ops docs, feature-flag/release-control docs, web-source acquisition/crawl-governance docs, Meta Instagram and broader social publishing API docs, speech/dialogue/IE runtime docs, content provenance and synthetic-media disclosure sources, AWS Bedrock AgentCore/Agents docs, Hugging Face smolagents docs, Hugging Face Hub model/dataset governance docs, LlamaIndex workflow/RAG/eval docs, Microsoft Agent Framework and AutoGen docs, Qdrant production vector retrieval docs, Neo4j GraphRAG/graph retrieval docs, pgvector/Postgres hybrid retrieval docs, feature store and online/offline parity docs, data quality validation contract docs, model/dataset/route card governance sources, privacy/retention/data-boundary sources, Pinecone managed vector retrieval docs, Weaviate named-vector/hybrid retrieval docs, Elasticsearch semantic/hybrid search docs, Cohere/Voyage/Jina/SentenceTransformers reranker docs, CS329X human-centered LLM materials, CS25 transformer-foundation/open-alignment/LM-intuition/whole-part materials, CS224G public lecture PDFs, CS349D inference-infrastructure source map, CS336 Assignment 4 data-pipeline handout, CS336 current 2026 Lecture 15 mid/post-training PDF, CS234 policy-gradient/PPO public slides, and Microsoft GraphRAG index/query docs now resolve to deep-read or canon-covered notes. The Obsidian workflow article and official Obsidian linking help resolve to process notes only.

Highest-priority promote/cross-check targets:

No deep-read records require promote/cross-check action. Public video and lecture-level notes still remain valid ingestion targets, but they are tracked as source-work scope rather than per-URL coverage gaps.

## Agent Studio Design Implications

- The datastore should keep `coverage_status` separate from `rights_status` and `source_class`.
- Inventory URLs should not be used as architecture evidence until a note records original synthesis.
- Canon notes can cite many URLs, but high-risk sources still deserve dedicated notes when they govern security, evals, autonomy, or multimodal behavior.
- URL records now carry `recommended_next_action` so ingestion can proceed autonomously without re-reading the whole MOC.
- Redirecting or legacy URLs should be normalized to canonical current docs during the next official-doc refresh.

## Next Ingestion Move

Continue source work from value and risk rather than from inventory-only URL cleanup:

1. Continue direct-reading high-value official docs that affect route safety, source governance, retrieval quality, or serving reliability; no current URL-manifest item is inventory-only.
2. Keep the Obsidian workflow article as process-only workflow context, not architecture canon.
3. Continue public Stanford video/lecture notes separately; they remain tracked by source notes and availability checks rather than as per-URL architecture gaps.
