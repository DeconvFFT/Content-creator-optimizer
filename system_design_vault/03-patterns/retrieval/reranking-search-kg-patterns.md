---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - [[../../02-books/nlp-with-transformers/chapters/7-question-answering]]
  - [[../../01-sources/official-open/anthropic-contextual-retrieval]]
  - [[../../01-sources/official-open/microsoft-graphrag-index-query]]
  - [[../../02-books/probabilistic-ml-advanced/approximate-inference-shift-interpretability]]
  - [[../../02-books/hands-on-generative-ai/generative-media-pipelines]]
  - https://microsoft.github.io/graphrag/index/overview/
  - https://microsoft.github.io/graphrag/query/overview/
  - https://www.microsoft.com/en-us/research/blog/graphrag-improving-global-search-via-dynamic-community-selection/
  - https://docs.cloud.google.com/architecture/gen-ai-graphrag-spanner
  - https://neo4j.com/developer/genai-ecosystem/hybrid-search/
  - https://neo4j.com/labs/genai-ecosystem/graphrag/
  - [[../../01-sources/official-open/neo4j-graphrag-graph-retrieval]]
  - [[../../01-sources/official-open/pgvector-postgres-hybrid-retrieval]]
  - [[../../01-sources/official-open/official-docs-whitepapers-expansion]]
  - https://developers.openai.com/api/docs/guides/retrieval
  - https://sbert.net/docs/package_reference/cross_encoder/cross_encoder.html
  - https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/
  - https://docs.langchain.com/oss/python/deepagents/memory
  - https://huggingface.co/blog/open-deep-research
  - https://developers.openai.com/api/docs/guides/realtime
  - [[../../01-sources/official-open/qdrant-production-vector-retrieval]]
  - [[../../01-sources/official-open/pinecone-managed-vector-retrieval]]
  - [[../../01-sources/official-open/weaviate-named-vector-hybrid-retrieval]]
  - [[../../01-sources/official-open/elasticsearch-semantic-hybrid-search]]
  - [[../../01-sources/official-open/reranker-provider-runtime-contracts]]
  - [[../../02-books/recommendation-system-metrics/ranking-and-recommendation-eval]]
  - [[../../02-books/probabilistic-ml/uncertainty-ranking-online-inference]]
  - [[../../02-books/python-nlp-cookbook/source-ingestion-nlp-recipes]]
  - [[../../02-books/speech-language-processing/rag-dialogue-speech-ie]]
  - [[../../02-books/speech-language-processing/chapters/14-question-answering-ir-rag]]
  - [[../../01-sources/official-open/llamaindex-agent-workflows-rag-eval]]
  - [[../../01-sources/official-open/openai-file-search-vector-stores-web-search]]
---

# Reranking, Search, And Knowledge Graph Patterns

## Objective

Minimize false positives and false negatives in source-backed answers. The system should retrieve enough coverage to answer correctly, then aggressively reject weak or irrelevant candidates before claims reach drafts.

LlamaIndex corrective RAG adds a workflow-level retrieval pattern: retrieve candidates, evaluate relevance, extract usable evidence, transform the query or fall back to another search path when evidence is weak, then synthesize. Agent Studio should store that as a `corrective_rag_step` rather than treating fallback search as a hidden retriever behavior.

OpenAI hosted file search and web search add a provider-managed retrieval path. The design point is not to skip retrieval infrastructure; it is to make the provider retrieval settings auditable. Vector-store identity, file processing status, expiration, chunking strategy, metadata filters, ranking options, max result count, web domain filters, live-access mode, user-location policy, source-list inclusion, and citation visibility are route settings and trace evidence.

Speech and Language Processing Chapter 14 adds the textbook QA/RAG split: a query expresses an information need against a bounded collection; retrieval ranks documents or passages; a reader/generator answers from the evidence pack; and QA evals must distinguish retrieval ranking from final answer correctness. Agent Studio should therefore version retrieval collections, sparse/dense retrieval profiles, reader prompts, ANN recall checks, and QA eval surfaces separately.

Natural Language Processing with Transformers Chapter 7 adds the implementation contract behind that split: QA routes need metadata-filtered document stores, sliding passage windows with source offsets, impossible-answer policy, retriever recall@K, reader EM/F1, whole-pipeline eval, domain-adaptation records, and score-normalization caveats before answer spans or generated RAG responses become product evidence.

## Retrieval Stack

1. Query understanding: identify entities, time bounds, required source types, freshness needs, and unsupported assumptions.
2. Query expansion: generate synonyms, entity aliases, adjacent concepts, and counterfactual checks.
3. Hybrid first-stage retrieval: combine keyword/BM25-style matching, vector search, metadata filters, and graph neighbors.
4. Fusion: use reciprocal rank fusion or a stable weighted merge so no single retriever dominates.
5. Reranking: apply a cross-encoder, LLM judge, or deterministic scorer depending on cost/risk.
6. Coverage check: ensure each required subtopic has accepted evidence.
7. Claim mapping: every major claim maps to a source record or is marked unsupported.
8. Feedback loop: labeled relevance updates precision/recall metrics and query policies.

Use [[../evaluation/source-claim-evidence-ledger]] after retrieval and reranking. Retrieval traces explain how evidence was found; the claim/evidence ledger decides whether the final claim is supported, caveated, needs review, unsupported, contradicted, stale, or out of scope.

For QA-style routes, keep the retriever and reader/generator contract separate. Retriever recall, passage windowing, reader score semantics, and final answer support can each fail independently. A high answer score from one passage is not necessarily comparable to a score from another passage when the reader normalizes within each passage or overlapping window.

Chapter 14 also reinforces that sparse retrieval is not obsolete. BM25/tf-idf-style retrieval, inverted indexes, and analyzer policies remain important for rare terms, filenames, source titles, field names, and exact provenance queries. Dense retrieval adds semantic matching, but bi-encoder compression, late-interaction storage/scoring cost, and ANN approximation all need explicit release evidence.

Hands-On Generative AI's RAG appendix reinforces that chunk size, overlap, embedding model, top-K, reranking, query rewriting, PII redaction, caching, and input guardrails are production route settings. They should be stored in the retrieval trace or route release, not buried inside helper code.

The pgvector and PostgreSQL docs sharpen the local retrieval side of that rule: exact search, HNSW, IVFFlat, distance operator classes, query-time knobs, half-precision, binary, sparse vectors, filtering, hybrid full-text search, and re-ranking each change recall/speed/cost behavior. Agent Studio should not treat `pgvector` as one retrieval mode. It should store embedding table release, index release, distance metric, vector type/precision, HNSW or IVFFlat parameters, query setting policy, filter path, hybrid lexical/vector fusion policy, recall benchmark, and post-retrieval reranker.

The Qdrant documentation sharpens the operational vector-store side of the same rule: collection schema, named vectors, sparse vectors, multivectors, payload schemas, payload indexes, filters, quantization, aliases, snapshots, and partitioning are release artifacts. Agent Studio should store collection alias, vector-field profile, payload filter policy, quantization profile, source snapshot, and snapshot/restore evidence for every retrieval route that depends on a vector database.

Qdrant-backed route promotion needs a vector-store release gate. The gate should prove collection schema, source snapshot, vector fields, payload schema/indexes, required filter policy, hybrid query plan, multivector profile, quantization profile, alias/rollback pointer, snapshot and restore evidence, optimizer policy, partition policy, recall evals, latency/cost evals, and rollback target.

Pinecone's managed-vector docs add the hosted-service boundary: index schema, ranking fields, namespaces, metadata indexing, hybrid pattern, hosted reranking, backups, imports, and cost units can change both quality and operating cost. Agent Studio should store namespace policy, metadata filter schema, managed hybrid plan, managed rerank policy, backup record, import job, and search-cost record for retrieval routes that use a managed vector provider.

Pinecone-style managed vector routes need a managed-vector release gate. Promotion should prove managed index schema, source snapshot, ranking fields, namespace/isolation policy, metadata filter schema, hybrid pattern and alpha/fusion evals, rerank policy where enabled, backup/restore or import evidence, usage/cost budget, relevance and latency evals, privacy boundary, and rollback target.

Weaviate adds the named-vector and filtered-search boundary: one source object can carry multiple vector targets, hybrid search needs an explicit alpha/fusion policy, and selective filters can change both correctness and performance. Agent Studio should store named vector targets, multi-target query plans, hybrid alpha policy, filtered vector execution policy, collection schema release, tenant state, diversity policy, module bindings, and backup/restore records.

Weaviate-style named-vector routes need a named-vector retrieval release gate. Promotion should prove collection schema release, source snapshot, named vector targets, multi-target query plan, hybrid alpha/fusion policy, filter execution strategy, tenant state, diversity policy, module/reranker binding, backup/restore evidence, relevance evals, latency evals, privacy boundary, and rollback target.

Elasticsearch adds the search-engine retrieval boundary: lexical analyzers, `semantic_text` fields, vector fields, retriever trees, RRF or linear fusion, semantic rerankers, aliases, reindex jobs, and snapshots are all release-sensitive. Agent Studio should store search index release, semantic field profile, lexical analyzer profile, retriever tree, fusion strategy, reranker policy/event, alias release, reindex job, and search snapshot evidence.

Elasticsearch-style search routes need a search-engine release gate. Promotion should prove search index release, source snapshot, semantic field behavior, lexical analyzer settings, vector field refs, retriever tree plan, fusion strategy, semantic reranker policy, alias release, reindex validation, snapshot/restore evidence, access boundary, relevance evals, latency evals, and rollback target.

Hosted and local reranker providers add a separate runtime boundary: query/document request shape, candidate-pool size, output cutoff, rank-field serialization, truncation policy, usage units, latency, quota, privacy, fallback, and false-negative audit behavior are route settings. Agent Studio should store provider capability, reranker route policy, reranker request event, score snapshots, provider evals, false-negative reviews, local CrossEncoder profiles, and reranker privacy policies before treating reranking as production behavior.

Reranked routes need a reranker release gate. Promotion should prove provider/local capability, candidate-pool and final-output settings, rank-field serialization, truncation behavior, privacy/retention posture, timeout/retry/quota/budget controls, local fallback or deterministic degradation, score-snapshot capture, false-negative audit coverage, provider eval comparison, latency/cost evidence, and rollback to the prior reranker or no-rerank policy.

Neo4j's GraphRAG and hybrid-search docs sharpen the graph side of the rule: graph schema, KG extraction pipeline, entity resolution, vector/full-text indexes, Vector Cypher expansion, Text2Cypher policy, structural embeddings, and graph traversal limits are product behavior. Agent Studio should store graph schema release, extraction run, entity-resolution decisions, graph hybrid retrieval plan, vector-cypher plan, Text2Cypher attempts, graph index release, structural embedding release, and expansion trace before trusting graph retrieval as architecture evidence.

Neo4j-backed graph routes need a graph retrieval release gate. Promotion should prove graph schema, KG extraction pipeline, entity-resolution policy and decisions, vector/full-text/structural index releases, graph hybrid plan, Vector Cypher expansion bounds, Text2Cypher policy where enabled, graph expansion traces, path-validity evals, entity precision evals, fanout/latency/cost evidence, fallback behavior, and rollback target.

Anthropic's contextual-retrieval article turns chunk context into an explicit derived artifact. For Agent Studio, a chunk used for retrieval should carry source/document identity, section path, version or date, aliases, contextualizer prompt/model version, context hash, and rights/sensitivity labels. Contextualized chunks improve retrieval, but they are not replacement source truth; final claims still cite source records or original chunks.

Contextual retrieval should be release-gated before it becomes the default for a route. Promotion needs source/chunk snapshot identity, contextualizer prompt/model/version, derived-context provenance, embedding and lexical indexing flags, hybrid retrieval/fusion policy, reranker policy, K selection experiment, prompt-cache evidence, dropped-evidence audit, retrieval evals, faithfulness evals, and rollback to raw chunks or the prior retrieval policy.

Document layout/OCR ingestion adds a pre-retrieval gate: PDF, image, DOC, and DOCX chunks should know which parser produced them, which pages were covered, which layout elements or tables they came from, and whether OCR/layout quality was good enough for retrieval. A flat text chunk from an unverified parser should not be treated as equal to a layout-aware chunk with page, heading, table, and quality evidence.

## GraphRAG Modes

GraphRAG is not one retrieval method. The official/open sources point to several modes that should be modeled separately:

| Mode | Best for | Agent Studio use |
|---|---|---|
| Local graph search | Entity-specific questions where relevant facts live around a known source, claim, entity, or chunk. | Claim verification, "why did we cite this?", source lineage, artifact dependency checks. |
| Global/community search | Corpus-level synthesis where the answer needs themes across many documents. | "What best practices repeat across books/docs/lectures?", architecture canon synthesis, design-review prep. |
| DRIFT-style search | Local questions that need community context and follow-up query expansion. | Ambiguous product questions where a direct entity hit is too narrow. |
| Dynamic community selection | Global search where static map-reduce over all communities is too expensive or noisy. | Large vault synthesis where only some topic communities should be summarized. |
| NL-to-graph query | Structured questions where graph schema is reliable enough for precise query generation. | "Which claims depend on this source?", "which artifacts cite stale docs?", "which feedback changed a route?" |

GraphRAG should therefore be a routed capability. It should not run for every query, and it should not replace lexical/vector retrieval where simple search is sufficient.

Microsoft's GraphRAG docs add the implementation lifecycle behind these modes: document-to-text-unit construction, entity/relationship/claim extraction, hierarchical community detection, community-report generation, embeddings, and query-time context building. Agent Studio should version this as a `graph_index_release`, not as loose graph tables.

Speech and Language Processing Chapter 20 adds the ingestion-side warning: relation, event, time, and template extraction should create reviewed candidates before graph writes. Pattern extraction, supervised relation classifiers, bootstrapping, distant supervision, and Open IE have different precision/recall and schema-canonicalization risks. Agent Studio should store relation candidates, extraction patterns, bootstrapping iterations, distant-supervision bags, Open IE triples, sampled precision/yield evals, event mentions, temporal links, and template slot fills before using extracted structure as retrieval graph evidence.

GraphRAG index/query routes need a GraphRAG release gate before they affect source-backed answers or canon synthesis. Promotion should prove source snapshot, text-unit policy, graph index release, extraction run, community detection and report records, BYO graph validation where used, query-route mode policy, DRIFT branch policy, prompt versions, LLM cache/provider settings, graph eval cases, source-traceability policy, cost/latency evidence, and rollback target.

Neo4j adds an implementation guardrail for BYO graph retrieval: Text2Cypher is useful for exact structured questions, but it must be schema-pinned, read-only, bounded by row/time limits, linted, and logged. Vector Cypher retrieval is safer for many source-backed routes because it starts from known vector hits and then expands over allowed labels, relationship types, depth, and fanout. In both cases, the graph path is evidence and must be stored.

## Precision Controls

- Metadata filters before vector similarity where filters are reliable.
- Source quality tiers.
- Freshness gates for time-sensitive facts.
- Claim/source overlap checks.
- Rejection reasons on every discarded candidate.
- Separate source ledger for accepted and rejected evidence.
- Cross-encoder or LLM reranking only after a broad first-stage pool is deduplicated.
- Graph traversal depth limits and allowed edge-type filters.
- Community-report relevance classification before expensive global summarization.

## Recall Controls

- Entity alias expansion.
- Multi-hop graph traversal from accepted entities and source records.
- Contradiction search.
- Missing-topic detection.
- Follow-up query recommendations.
- Escalation to Web Research Agent when local memory is insufficient.
- Multiple retrieval modes in parallel: lexical, semantic, metadata, graph-neighbor, and structural similarity.
- Larger source-level candidate pools before fusion, then smaller context packs after reranking.
- Corpus-level community summaries for broad synthesis questions.
- Contextualized chunks for long books, docs, lectures, route proposals, incident notes, eval failures, and other places where local chunk text is ambiguous without document context.

## Fusion And Reranking

First-stage retrievers produce incompatible scores. A vector similarity score, lexical score, graph traversal score, and source-quality score should not be naively averaged. Use rank-based fusion or an explicitly calibrated scorer.

Reranking choices:

- deterministic scorer: cheap, explainable, useful for source authority and metadata rules;
- cross-encoder: stronger query-document relevance scoring, but cannot precompute standalone document embeddings and adds latency;
- LLM judge: useful for complex relevance or citation-support judgments, but more expensive and more bias-prone;
- graph-aware scorer: useful when relation type, path length, community, or source dependency matters.

Agent Studio should record reranker provider, endpoint/deployment mode, model, candidate count, kept count, dropped count, rank fields, truncation behavior, latency, cost or usage units, rejected reasons, and false-negative audit samples. Reranking is a product behavior, not an invisible helper.

## Evaluation Metrics

Use separate metrics so the broken stage is visible:

| Layer | Metrics |
|---|---|
| Retrieval | context precision, context recall, entity recall, source coverage, stale-source rate, duplicate rate |
| Reranking | rank movement, accepted-evidence position, false-positive removal, false-negative introduction, latency |
| Generation | faithfulness, response relevancy, groundedness, citation validity, unsupported claim count |
| Agent workflow | tool-call accuracy, goal accuracy, feedback acceptance, revision burden |
| Graph | entity resolution accuracy, relationship precision, traversal usefulness, community-summary utility |

Ranking metrics must be selected by surface:

- use `Recall@K` when missing required sources is the main risk;
- use `Precision@K` when context budget and irrelevant evidence are the main risk;
- use `MRR` when the first useful item determines success;
- use `MAP` when several relevant sources should appear early;
- use `NDCG` when relevance is graded, such as primary source, cross-check source, background source, stale source, or weakly related source;
- use coverage/diversity metrics to detect over-reliance on one source family, topic cluster, or candidate style;
- use CTR, dwell, acceptance, conversion, and revision burden only as online product signals, not factual-grounding proof.

Every ranking metric needs its candidate universe, cutoff K, relevance judgment protocol, and workflow surface. Without those fields, the metric cannot guide a route change.

## Graph Authority And Ranking Feedback

Murphy's PageRank and Markov-chain material adds a useful caution for memory and source ranking: authority is produced by a transition model. If Agent Studio ranks sources, notes, claims, or memories by graph centrality, it should store transition assumptions, damping or escape behavior, refresh schedule, and manipulation caveats.

Graph authority should be used as a prior for source discovery, not as a replacement for query relevance or claim support. Generated notes, self-referential links, repeated mentions, and user-feedback loops can inflate authority, so graph-ranked surfaces need anomaly checks and exposure metrics.

Murphy Advanced Topics adds two graph cautions. First, pairwise relevance networks can become dense because indirect dependencies create nonzero association; do not promote raw co-occurrence or mutual information into an explanatory KG edge. Second, diversity-aware subset selection, such as DPP-style repulsion, is a different objective from top-score ranking and should be explicit when the product needs source, topic, or visual-reference breadth.

## Knowledge Graph Shape

Minimum graph nodes:

- source,
- source chunk,
- claim,
- entity,
- community/topic cluster,
- artifact,
- agent,
- run,
- topic,
- feedback item,
- memory record.

Minimum edge types:

- supports,
- contradicts,
- mentions,
- derived_from,
- reviewed_by,
- revised_by,
- depends_on,
- same_entity_as,
- covers_topic.
- belongs_to_community,
- retrieved_for,
- rejected_for,
- supersedes,
- stale_after.

## Graph Construction Rules

- Do not extract an unbounded graph from every note by default.
- Start with a minimal typed schema: source, chunk, claim, entity, topic, artifact, run, feedback.
- Keep extracted entities linked to source/chunk IDs and extraction run IDs.
- Keep graph facts separate from generated summaries.
- Store confidence, extractor version, and reviewer status on graph edges.
- Refresh structural embeddings when graph topology changes materially.
- Prefer graph traversal for relationships and coverage; prefer original source chunks for quoted or claim-level evidence.
- Treat graph centrality and PageRank-like scores as calibrated priors with damping, refresh, and manipulation checks.
- Promote graph-authority, source-priority, memory-ranking, or adaptive reranking policies only after an adaptive-belief-state gate proves calibration, transition assumptions, damping or escape behavior, feedback-window/regret controls, exposure caveats, manipulation checks, candidate-diversity health, fallback, and rollback.
- Distinguish dependency, correlation, causal claim, retrieval relation, workflow dependency, and ontology relation before using graph edges in route decisions.
- Store diversity-selection rationale when choosing source packs, evidence packs, visual references, candidate drafts, or review batches.
- Gate graph retrieval releases before they affect answer context, canon notes, or route decisions.
- Treat community reports as generated synthesis artifacts. They are useful for broad search and question generation, but public claims still need source-chunk or source-record support.
- Prefer bring-your-own graph when Agent Studio already has structured source, claim, artifact, route, run, and feedback records. Re-extracting the same graph from prose should be a fallback, not the default.

## Retrieval Trace Contract

Every source-backed answer should store:

- original query;
- rewritten/expanded queries;
- retrieval mode;
- metadata filters;
- searched stores/indexes;
- graph start nodes and traversal limits;
- first-stage candidates;
- fusion policy;
- dedup decisions;
- reranker and scores;
- accepted context;
- rejected context with reasons;
- missing coverage flags;
- final cited source IDs;
- retrieval, rerank, and graph traversal latency.
- embedding model, embedding dimensions, chunk size, chunk overlap, and chunker version for simple vector RAG routes;
- pgvector embedding table release, ANN index release, distance operator class, vector representation, exact-versus-approximate mode, HNSW/IVFFlat settings, query-time knobs, filter execution policy, precision policy, maintenance event, hybrid full-text fusion policy, and local retrieval release gate where local Postgres retrieval is used;
- vector collection ID, active alias, vector-field profile, payload schema/index refs, required filter policy, quantization profile, partition policy, snapshot/index release evidence, and vector-store release gate where Qdrant or a production vector database is used;
- managed index ID, namespace, ranking-field schema, metadata filter schema, hybrid pattern, hosted reranker policy, backup/import refs, read/rerank usage units, cost budget, and managed-vector release gate where a managed vector provider is used;
- named vector target, multi-target weights, hybrid alpha/fusion policy, filter execution strategy, tenant state, diversity policy, module binding, backup/restore evidence, and named-vector retrieval release gate where Weaviate-style named-vector retrieval is used;
- semantic field profile, lexical analyzer profile, retriever-tree plan, RRF or linear fusion strategy, semantic reranker event, alias release, reindex job, search snapshot refs, access boundary, and search-engine release gate where Elasticsearch-style search-engine retrieval is used;
- reranker provider capability, route policy, request event, rank fields, truncation flag, usage units, score snapshots, provider eval ref, privacy policy, local CrossEncoder fallback profile, and reranker release gate where hosted or local reranking is used;
- query rewriting, PII redaction, cache, and input-guardrail decisions where enabled.
- contextualization run, context hash, contextualizer prompt/model version, whether context was embedded/indexed lexically, hybrid retrieval policy, fusion record, rerank audit sample, and contextual retrieval release gate where contextual retrieval is used.
- provider vector store ID, vector-store file status, provider file ID, chunking release, metadata filter policy, ranking options, score threshold, hybrid weights, returned search-result policy, file-citation annotations, web-search tool-choice policy, domain filters, live-access setting, source-list inclusion, approximate-location policy, and clickable citation check where hosted OpenAI retrieval or web search is used.
- NLP ingestion adapter changes need an `nlp_ingestion_adapter_release_gate` before they affect extraction, chunking, retrieval, eval, or canon notes. The gate should prove adapter profile, text-boundary records, normalization policy, grammar-extraction candidates, embedding compatibility, RAG traces, runtime/dependency locks, PII/privacy review, boundary/extraction/retrieval evals, fallback, and rollback.

QA/RAG traces additionally need:

- retriever type and document store;
- metadata filters;
- top-K retriever and top-K reader/generator settings;
- passage window and stride;
- source-to-window-to-answer offset mapping;
- no-answer threshold and impossible-answer behavior;
- reader/generator score normalization caveats;
- answer-span or citation-support evidence;
- retriever recall and MAP-style ranking results where the answer depends on early relevant evidence.
- reader EM/F1 and whole-pipeline eval results, with gold-context versus retrieved-context settings separated.
- context precision, context recall, and faithfulness metric contracts with route version, evaluator version, source snapshot, and reference policy.
- ranking-quality release gate refs when retrieval order, reranker output, source priority, memory selection, or candidate lists change; the gate binds candidate universe, cutoff K, relevance-grade rubric, ranking metric results, coverage/diversity guardrails, false-positive/false-negative reviews, online-feedback caveats, latency/cost evidence, fallback, and rollback.
- answer support records that separate retrieved evidence from the reader/generator's final text;
- retrieval collection release refs, sparse retrieval profile refs, dense retrieval profile refs, ANN recall benchmarks, RAG reader prompt refs, and QA eval surface records for source-backed QA routes;
- mention candidates, referentiality decisions, coreference merge decisions, entity candidate sets, NIL decisions, canonicalization records, and entity/coreference links used to resolve pronouns, aliases, and discourse entities before graph insertion or claim verification;
- relation candidates, extraction patterns, bootstrapping/distant-supervision provenance, Open IE triples, sampled precision/yield evals, event mentions, temporal links, and template-fill records when retrieved evidence becomes structured memory.

## Agent Studio Implications

- Retrieval Intelligence Agent owns query strategy and retrieval metrics.
- Knowledge Graph Curator owns entity normalization and graph traversal.
- Claim Verification owns source-to-claim support.
- Source Ledger Agent owns accepted/rejected evidence transparency.
- Product Manager and Forward Deployed Engineer use FP/FN metrics as gates before publishing.
- Data Store lane owns source/chunk/claim/entity graph schema and ingestion-time graph extraction.
- Eval lane owns retrieval and groundedness eval suites before route promotion.

## Failure Modes

- GraphRAG is enabled globally and increases latency/noise for simple exact-match queries.
- LLM-extracted graph edges become trusted facts without source IDs or reviewer status.
- Community summaries replace primary evidence in citation-critical answers.
- Graph traversal pulls in adjacent but irrelevant entities because edge type and depth were unconstrained.
- Reranking removes minority/edge-case evidence because the query was too narrow.
- Hybrid retrieval appears to improve recall but silently increases false positives without a coverage ledger.
- Generated notes and source chunks are indexed together without provenance classes.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
