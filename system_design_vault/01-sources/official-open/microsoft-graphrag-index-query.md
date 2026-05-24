---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_public
provenance_status: official_microsoft_graphrag_docs_direct_read
sources:
  - https://microsoft.github.io/graphrag/index/overview/
  - https://microsoft.github.io/graphrag/index/architecture/
  - https://microsoft.github.io/graphrag/index/default_dataflow/
  - https://microsoft.github.io/graphrag/index/outputs/
  - https://microsoft.github.io/graphrag/index/byog/
  - https://microsoft.github.io/graphrag/prompt_tuning/overview/
  - https://microsoft.github.io/graphrag/query/overview/
  - https://microsoft.github.io/graphrag/query/local_search/
  - https://microsoft.github.io/graphrag/query/global_search/
  - https://microsoft.github.io/graphrag/query/drift_search/
  - https://microsoft.github.io/graphrag/query/question_generation/
---

# Microsoft GraphRAG - Index And Query Architecture

## Scope

Direct-read synthesis from current official Microsoft GraphRAG documentation for indexing, architecture, dataflow, outputs, bring-your-own graph, prompt tuning, and query modes. This note records implementation-relevant patterns for Agent Studio. It does not store raw documentation text, generated graph outputs, prompt templates, copied tables, or long excerpts.

## Core Pattern

GraphRAG is an indexing and query architecture, not just a retrieval option. It turns unstructured text into structured graph artifacts, community summaries, embeddings, and query-time context builders. For Agent Studio, the durable lesson is that graph retrieval requires a lifecycle: source ingestion, text-unit construction, entity/relationship/claim extraction, graph augmentation, community-report generation, embedding, query-mode selection, and eval.

The graph is therefore a product artifact. It should be versioned, evaluated, refreshed, and rolled back like an index or model route.

Current-doc check on 2026-05-18 confirms that this remains a release-sensitive pipeline: indexing is a configurable workflow system with standard/custom steps, prompt templates, input/output adapters, LLM cache behavior, pluggable providers, Parquet output tables, and vector-store embeddings; BYO graph expects entity, relationship, and optional text-unit tables; local/global/DRIFT/question-generation modes have distinct context-building behavior; and prompt tuning can adapt graph-generation prompts to the corpus domain.

## Indexing Pipeline

The official pipeline frames these stages:

- compose source documents into text units;
- link documents back to text units for provenance;
- extract entities, relationships, and optional claims from text units;
- summarize repeated entity and relationship descriptions;
- detect hierarchical communities over the graph;
- generate and summarize community reports;
- embed text units, entity descriptions, and community reports for downstream search.

Agent Studio implications:

- `TextUnit` maps cleanly to source chunks, but graph extraction needs stronger provenance than ordinary chunking. Every extracted entity, relationship, claim, and community report should retain source/chunk references and extraction-run identity.
- Chunk size is a quality/speed tradeoff. Larger chunks can be faster but lower fidelity for graph references. The route should record chunk policy and graph-extraction loss risk.
- Claim extraction should be optional and gated. It is powerful for claim verification and risk review, but it should not be treated as default truth because LLM-derived claims need prompt tuning, status, source text linkage, and reviewer policy.
- LLM cache/idempotency is part of graph indexing reliability. Graph extraction retries can otherwise create cost spikes, duplicate work, or inconsistent graph versions.

## Output Model

The official output model is useful for Agent Studio schema design:

- documents: imported source records and links to text units;
- text units: chunks with token counts, source document link, and extracted graph refs;
- entities: titles/types/descriptions, source text-unit refs, frequency, and degree;
- relationships: source entity, target entity, description, weight, graph-degree signal, and source text-unit refs;
- communities: hierarchical graph clusters with parent/children, level, member entities, relationships, and text units;
- community reports: generated summaries/findings/rankings over communities;
- covariates: optional extracted claims with subject/object, status, dates, and source text-unit ref.

Agent Studio should preserve the separation between raw source chunks, extracted graph facts, and generated community reports. Community reports are helpful synthesis artifacts, but they are not primary evidence for citation-critical claims.

## Query Modes

### Local Search

Local search starts from entities related to the user query, then uses the graph to gather connected text units, relationships, entities, covariates, and community reports. It is best for entity-specific or claim-specific questions where the answer lives near known objects.

Agent Studio use:

- claim verification around a cited source, artifact, person, product, paper, route, or concept;
- "why did we cite this?" provenance questions;
- source lineage and dependency inspection;
- localized contradiction search.

### Global Search

Global search uses community reports to answer corpus-level questions. It is useful for "what themes exist across this vault?" style questions. The cost/quality tradeoff depends on community hierarchy level, report volume, map/reduce token budget, and concurrency.

Agent Studio use:

- synthesis across books, official docs, Stanford lectures, and white papers;
- architecture canon creation;
- design-review prep where the answer is a theme, not a single fact.

Global search should not be used for citation-critical answers unless the final claims are traced back to primary source chunks or source records.

### DRIFT Search

DRIFT combines community context with local exploration. It begins with broader community-relevant context, generates follow-up directions, and refines with localized searches. This is useful when a user question is specific but underspecified or when local search is too narrow.

Agent Studio use:

- ambiguous architecture questions where the right subtopic is not known upfront;
- multi-hop retrieval where an initial entity needs broader topic context;
- gap discovery for source ingestion and eval case generation.

### Question Generation

Question generation uses the same graph/context-building machinery to propose follow-up questions. For Agent Studio, this can drive active learning: "what should we inspect next?", "which source family is under-covered?", and "what eval cases would expose missing graph edges?"

## Bring-Your-Own Graph

The BYO graph path is important for Agent Studio because the vault already has structured source records, notes, claims, artifacts, runs, and feedback. Agent Studio should not always re-extract a graph from prose. It can supply typed entities, relationships, and text units directly, then run graph summarization and query workflows over them.

Initial BYO graph contract:

- entities: source, chunk, claim, artifact, route, concept, person/org/tool/model/provider, eval, feedback item;
- relationships: supports, contradicts, mentions, derived_from, depends_on, same_entity_as, belongs_to_community, retrieved_for, rejected_for, reviewed_by, revised_by, supersedes;
- text units: source-backed chunks or note sections with rights and provenance IDs;
- weights: explicit relation strength or confidence, not raw mention count alone.

## Prompt Tuning

Graph extraction depends on prompts and domain assumptions. Official docs distinguish default, auto, and manual tuning. For Agent Studio, graph prompts are route artifacts and must be versioned like extraction code.

Use auto/domain tuning for:

- local corpus vocabulary;
- book/source-note structure;
- route/artifact/eval terminology;
- safety and rights labels;
- claim/relationship categories.

Do not silently change graph prompts. A prompt change can alter extracted entities, edge weights, communities, and downstream answers.

## Agent Studio Datastore Implications

Add or strengthen:

- `graph_index_release`: source snapshot, extraction prompts, model/provider, workflow set, output tables, embeddings, vector store refs, eval status, and rollback target.
- `text_unit_record`: chunk identity, source/document refs, token count, chunk policy, boundary policy, rights/sensitivity labels, extraction-run refs.
- `graph_extraction_run`: extractor prompt versions, model refs, cache policy, attempted text units, extracted entities/relationships/claims, failures, and cost/latency.
- `community_detection_run`: algorithm, graph version, level/depth policy, community size thresholds, output community refs, and stability metrics.
- `community_report_record`: community ref, generated summary artifact, finding refs, rank/rating caveats, source text-unit refs, and citation suitability.
- `graphrag_query_route`: query mode, context builder, community level, token budget, local/global/DRIFT parameters, allow-general-knowledge flag, and fallback mode.
- `drift_query_state`: initial community refs, follow-up questions, local search branches, confidence/stop signals, intermediate answers, and final hierarchy refs.
- `graph_prompt_version`: graph extraction, claim extraction, community report, map/reduce, local search, DRIFT, and question-generation prompt versions.
- `graph_eval_case`: entity resolution, relationship precision, claim status, community usefulness, query-mode fit, source traceability, and hallucination leakage checks.
- `graphrag_release_gate`: promotion decision for graph index and query routes, binding source snapshot, text-unit policy, graph index release, extraction run, community detection/report records, BYO graph validation, query-route policy, prompt versions, cache/provider settings, evals, citation policy, cost/latency evidence, and rollback target.

## Release Gates

Do not promote a GraphRAG route when:

- extracted graph edges lack source text-unit refs;
- community reports are used as primary citation evidence without source-chunk support;
- graph extraction prompt or model changed without graph diff/eval;
- BYO graph weights are uncalibrated but used for ranking;
- global search answers are allowed to use outside/general knowledge in source-grounded routes;
- DRIFT query expansion lacks stop criteria and accepted/rejected branch records;
- claim extraction is enabled without claim-status eval and reviewer policy;
- graph refresh cannot explain which source snapshot produced a route answer.
- no GraphRAG release gate proves source snapshot, text-unit policy, extraction run, prompt versions, community reports, query-mode policy, source traceability, evals, and rollback.

## Agent Studio Decision

Use GraphRAG as a routed capability:

- simple exact source questions: lexical/vector/metadata first;
- entity-specific questions: local graph search;
- corpus-wide themes: global/community search;
- ambiguous local questions: DRIFT;
- ingestion planning and eval discovery: question generation.

The graph should improve recall and source navigation, but final public claims still need source-ledger support from primary source records or source chunks.
