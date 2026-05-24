---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
sources:
  - https://developers.openai.com/api/docs/guides/evaluation-best-practices
  - https://developers.openai.com/api/docs/guides/evals
  - https://developers.openai.com/api/docs/guides/agent-evals
  - https://developers.openai.com/api/docs/guides/trace-grading
  - https://developers.openai.com/api/docs/guides/retrieval
  - https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/
  - [[../../01-sources/official-open/ragas-langsmith-rag-agent-evals]]
  - https://microsoft.github.io/graphrag/query/overview/
  - https://www.microsoft.com/en-us/research/blog/graphrag-improving-global-search-via-dynamic-community-selection/
  - https://docs.cloud.google.com/architecture/gen-ai-graphrag-spanner
  - https://neo4j.com/developer/genai-ecosystem/hybrid-search/
  - https://sbert.net/docs/package_reference/cross_encoder/cross_encoder.html
  - [[../../02-books/recommendation-system-metrics/ranking-and-recommendation-eval]]
related:
  - "[[01-sources/official-open/openai-evals-and-agent-evals]]"
  - "[[01-sources/official-open/retrieval-and-reranking-sources]]"
  - "[[01-sources/official-open/ragas-langsmith-rag-agent-evals]]"
  - "[[03-patterns/retrieval/reranking-search-kg-patterns]]"
  - "[[04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
  - "[[04-agent-studio-implications/Route Change Proposal Template]]"
---

# Retrieval Eval Templates

## Purpose

Agent Studio needs retrieval evals that isolate where source-grounded workflows fail. The eval should not only ask whether the final answer sounds right. It should measure whether retrieval found the right source set, whether reranking preserved important evidence, whether graph traversal added useful context, and whether the final answer used citations honestly.

This note is original synthesis from the linked official/open eval, retrieval, GraphRAG, hybrid-search, and reranking sources. It is a reusable template for vault ingestion and production Agent Studio gates.

## Dataset Slices

| Slice | What it tests | Example source of cases |
|---|---|---|
| Exact source lookup | Can the system find a known chapter, lecture, doc, or white paper? | Vault notes, source inventory, user corrections |
| Concept recall | Can it retrieve all major source families for a concept? | Book synthesis notes, official docs, lecture notes |
| Entity recall | Can it recover aliases, products, papers, systems, and people without overmatching? | Knowledge graph nodes, source metadata |
| Multi-hop graph retrieval | Can it traverse useful relationships without pulling adjacent noise? | claim-source-topic-artifact graph |
| Global/community synthesis | Can it select relevant communities before summarizing broad themes? | GraphRAG community reports |
| Freshness-sensitive retrieval | Can it prefer current official docs and flag stale local knowledge? | official docs, provider pages, release notes |
| Contradiction and dissent | Can it find sources that qualify or contradict a claim? | cross-check notes, rejected evidence ledger |
| Citation support | Do cited sources actually support the generated claim? | claim verification traces |
| Negative retrieval | Does the system abstain when the corpus lacks support? | adversarial cases and known missing topics |

## Eval Case Schema

Minimum fields:

| Field | Purpose |
|---|---|
| `case_id` | Stable identifier for regression tracking |
| `slice_tags` | Eval surfaces such as `entity_recall`, `citation_support`, `graph_traversal` |
| `query` | User-facing retrieval or answer request |
| `expected_source_ids` | Sources that should be present in accepted evidence |
| `forbidden_source_ids` | Sources that should not be accepted for this query |
| `expected_entities` | Required entities, aliases, products, papers, or concepts |
| `required_claims` | Claims the answer must support from accepted evidence |
| `freshness_policy` | Static, current-docs-required, or stale-allowed |
| `retrieval_modes_allowed` | lexical, vector, hybrid, local graph, global/community, DRIFT-style, NL-to-graph |
| `risk_level` | Low, medium, high, or release-blocking |
| `human_rationale` | Short original explanation of why this case matters |
| `cutoff_k` | Top-K cutoff used for precision, recall, hit rate, MAP, MRR, or NDCG |
| `relevance_grade_rubric` | Binary or graded relevance policy, including primary/cross-check/background/stale distinctions |
| `candidate_universe_ref` | Snapshot of candidates the ranking metric was computed over |

Avoid storing source excerpts in the eval case. Store source IDs, section references, claim IDs, and short reviewer-authored rationales.

## Metrics

Use separate metrics by layer:

| Layer | Required metrics |
|---|---|
| First-stage retrieval | context recall, source coverage, entity recall, stale-source rate |
| Fusion | source diversity, duplicate rate, lost-required-source count |
| Reranking | accepted-evidence rank, false-positive removal, false-negative introduction, rerank latency |
| Graph traversal | useful-edge precision, path-length distribution, community-report utility, unrelated-neighbor rate |
| Answer generation | citation validity, unsupported claim count, faithfulness, groundedness, response relevancy |
| Workflow trace | correct retrieval mode, correct filters, correct fallback, correct abstention |

No aggregate retrieval score should ship alone. A route can improve average answer quality while silently losing minority evidence or increasing unsupported citations.

Ragas/LangSmith coverage adds one more discipline: metric records must say whether they are judging ranking quality, evidence coverage, response support, tool path, or final goal success. Context precision, context recall, faithfulness, strict tool-call accuracy, tool-call F1, and goal accuracy should remain separate release columns, each tied to route version, source snapshot, trace, evaluator version, and reference policy.

For ranking metrics:

- `Precision@K` and `Recall@K` must name K and the candidate universe;
- `HitRate@K` is a health signal, not proof that all required evidence was retrieved;
- `MRR` fits "first useful item" workflows;
- `MAP` fits workflows where multiple relevant items must appear early;
- `NDCG` fits graded relevance and should record the grade rubric;
- source/topic coverage and diversity should be tracked separately from relevance;
- online metrics such as click, dwell, accept, conversion, and revision burden should be segmented and labeled as behavioral outcomes.

Ranking policy promotion needs a `ranking_quality_release_gate`: route changes that alter retrieval order, reranker output, source priority queues, candidate lists, memories, creative alternatives, or recommendation feeds must prove the ranking surface, candidate universe, cutoff K, relevance rubric, metric set, coverage/diversity guardrails, false-positive and false-negative reviews, online-feedback caveats, latency/cost evidence, fallback, and rollback.

## Template 1 - Source Recall

Use when changing chunking, embeddings, vector database, metadata filters, source inventory shape, or ingestion logic.

Required assertions:

- at least one expected source appears in the first-stage pool;
- all release-blocking expected source IDs appear before context packing;
- source quality tiers and freshness gates are respected;
- duplicate chunks do not crowd out distinct sources;
- missing expected sources produce an explicit coverage flag.

Promotion gate:

- no release-blocking source recall failures;
- no increase in stale-source acceptance for current-docs-required cases;
- reviewer-approved explanation for any accepted recall regression.

## Template 2 - Reranking Precision

Use when changing cross-encoder models, LLM rerankers, deterministic scoring, reciprocal-rank fusion, or source-quality weights.

Required assertions:

- irrelevant candidates are demoted or rejected with reasons;
- required minority evidence is not removed;
- reranking improves accepted evidence position without hiding recall loss;
- rank movement is recorded for each candidate;
- latency and cost remain within route budget.

Promotion gate:

- improved or unchanged citation-support precision on high-risk cases;
- no false-negative introduction for release-blocking expected sources;
- reranker version and scoring policy captured in `retrieval_trace`.

## Template 3 - Graph Traversal Usefulness

Use when enabling local graph search, global/community search, DRIFT-style retrieval, dynamic community selection, or NL-to-graph query.

Required assertions:

- selected retrieval mode matches the question type;
- graph start nodes are source-grounded and auditable;
- traversal respects allowed edge types and depth;
- community reports supplement rather than replace primary evidence;
- graph-expanded results add coverage or contradiction, not just adjacent noise.

Promotion gate:

- unrelated-neighbor rate below the route threshold;
- accepted graph evidence has source IDs and reviewer status;
- global/community search records which communities were considered, accepted, and rejected.

## Template 4 - Citation Validity And Grounding

Use when changing prompt templates, answer assembly, citation rendering, claim verification, or context packing.

Required assertions:

- every major claim maps to an accepted source ID or is marked unsupported;
- citations point to the source actually used, not a nearby source from the same topic;
- synthesized claims that combine multiple sources keep all required citations;
- the answer abstains or asks for more retrieval when evidence is missing;
- retrieved untrusted text cannot become control instructions.

Promotion gate:

- zero unsupported release-blocking claims;
- citation validity above the route threshold;
- trace grader identifies the failing span for every citation failure.

## Template 5 - Negative And Missing-Evidence Cases

Use when evaluating hallucination resistance and retrieval fallback behavior.

Required assertions:

- the retriever does not invent evidence for absent material;
- web-search escalation is triggered only when policy allows current external lookup;
- local-only workflows say the corpus lacks evidence instead of fabricating a source;
- unsupported claims are not converted into confident answer text;
- missing-evidence outcomes are stored as useful eval artifacts.

Promotion gate:

- no fabricated source IDs;
- no ungrounded answer on release-blocking negative cases;
- missing-coverage flags appear in the trace and final reviewer view.

## Trace Fields Required

Every retrieval eval run should persist:

- query and query rewrites;
- retrieval mode and fallback sequence;
- metadata filters;
- searched indexes and graph stores;
- candidate IDs before and after fusion;
- reranker version, scores, and rank movement;
- graph start nodes, edge filters, depth, and selected communities;
- accepted evidence and rejected evidence with reasons;
- source IDs cited in the final answer;
- missing coverage flags;
- latency and cost by retrieval, reranking, graph traversal, and generation stage;
- grader version and reviewer override if present.

## Agent Studio Design Implications

- Eval cases become release assets, not QA scratch work.
- Retrieval trace storage is mandatory before route promotion.
- Source IDs, chunk IDs, graph IDs, and claim IDs must be stable enough to survive re-indexing.
- Human corrections should create new eval cases tagged by failure mode.
- Reranking and GraphRAG changes need their own gates because both can improve some queries while harming others.
- Ranking-quality gates prevent average NDCG, hit rate, click, or acceptance gains from hiding lost minority evidence, weak source coverage, novelty overuse, or position-biased feedback.
- The production UI should expose accepted and rejected evidence so reviewers can diagnose false positives and false negatives.
- Route changes that touch retrieval, reranking, graph traversal, source snapshots, or citation rendering should attach these eval gates through [[../../04-agent-studio-implications/Route Change Proposal Template]].

## Initial Eval Queue

1. Retrieval of AI Engineering chapter 6 plus official RAG cross-check sources.
2. Retrieval of LLM Engineers Handbook chapter 9 plus GraphRAG and contextual-retrieval sources.
3. Retrieval of DMLS monitoring chapters plus cloud MLOps monitoring docs.
4. Negative case where no current CS336 2026 alignment materials are published yet.
5. Global/community query asking for recurring production RAG design principles across books, docs, and Stanford lectures.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
