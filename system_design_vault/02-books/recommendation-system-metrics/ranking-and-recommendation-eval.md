---
type: book-source-note
project: agent-studio-system-design
status: canon_ready
source_id: local_books.recommendation_system_metrics
source_title: "Comprehensive Guide to Recommendation System Metrics"
source_status: user_provided_local_canon_ready
updated: 2026-05-18
local_source: "/Users/saumyamehta/DS interview prep/books/Comprehensive Guide to Recommendation System Metri.pdf"
official_sources:
  - https://www.tensorflow.org/ranking
  - https://www.tensorflow.org/recommenders/examples/listwise_ranking
  - https://www.microsoft.com/en-us/research/publication/evaluating-recommender-systems/
related:
  - "[[../../03-patterns/retrieval/reranking-search-kg-patterns]]"
  - "[[../../03-patterns/evaluation/retrieval-eval-templates]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Recommendation Metrics - Ranking And Retrieval Evaluation

## Reading Status

Canon-ready full short-document pass over the 9-page local user-provided PDF for precision/recall at K, F1, hit rate, MRR, MAP, NDCG, coverage, diversity, novelty, serendipity, CTR, conversion, dwell time, personalization, learning rate, stability/adaptability, cold start, and offline/online/user-study evaluation framing. The PDF was text-extracted to `/private/tmp` and read end-to-end on 2026-05-18; no extracted text is stored in the vault. Cross-checked against TensorFlow Ranking, TensorFlow Recommenders listwise ranking, and the Microsoft Research recommender-evaluation paper. This note stores compact original synthesis only, not raw source text or long excerpts.

## Provenance Caveat

The local PDF is useful as user-provided local material, but it is a compact guide rather than a primary standards document. Agent Studio should treat it as a metric taxonomy and decision aid. For route promotion, pair it with official or primary evaluation references, route-specific relevance judgments, and live product telemetry.

## Why This Matters

Agent Studio is not a movie or product recommender, but it repeatedly ranks candidates:

- retrieved chunks and sources;
- reranked evidence packs;
- candidate outlines, scripts, thumbnails, captions, and edits;
- agent/tool routes;
- notes or memories to reuse;
- next ingestion targets.

The central lesson is that ranking quality is multi-objective. Optimizing one metric can damage another. Precision-heavy retrieval can miss minority evidence; recall-heavy retrieval can flood the prompt with noise; click-like engagement can reward shallow outputs; novelty can hurt reliability if it is not constrained by relevance.

## Metric Families

| Family | Metrics | Agent Studio use |
|---|---|---|
| Top-K accuracy | Precision@K, Recall@K, F1@K, HitRate@K | Retrieval and candidate-pool checks. |
| Rank quality | MRR, MAP, NDCG | Evidence ordering, first-useful-source position, graded relevance. |
| Coverage | Catalog/source coverage, topic coverage | Avoid overusing a narrow source set or popular memory cluster. |
| Diversity | Intra-list diversity, source diversity, topic diversity | Prevent redundant context packs and repeated creative candidates. |
| Novelty/serendipity | Popularity-adjusted novelty, unexpected-but-relevant candidates | Useful for creative ideation, unsafe for factual grounding unless gated. |
| Behavioral outcomes | CTR, conversion, dwell time, acceptance, revision burden | Online product feedback, not offline truth. |
| Adaptation | learning rate, stability/adaptability, cold-start quality | Feedback loops, personalization, and route-memory updates. |

## Metric Selection Rules

Agent Studio should choose metrics by workflow surface:

- source-backed answer: prioritize Recall@K for required sources, NDCG/MAP for ordering, citation validity for generation, and stale-source rate;
- reranking: track false-positive removal and false-negative introduction separately;
- creative candidate generation: track diversity and novelty only after relevance and brand/quality gates pass;
- personalization: track user acceptance and revision burden, with guardrails against narrowing the user's future options;
- ingestion prioritization: track source coverage and topic coverage, not just number of notes created.
- source ingestion queue: track topic coverage, source authority, freshness, extraction quality, rights/provenance status, and marginal design value, not raw item count.
- memory reuse: track first-useful-memory position, stale-memory rate, diversity of memory namespaces, and user correction burden.

No route should ship with a single ranking score. A high NDCG does not prove enough source coverage. A high recall does not prove the top context is usable. A high CTR does not prove factual correctness.

## Precision, Recall, And Hit Rate

Precision@K answers whether the visible top-K set is clean. Recall@K answers whether the needed material was found. HitRate@K answers whether each query/user got at least one useful item.

Agent Studio implication:

- use Precision@K when context-window space is tight;
- use Recall@K when missing a source creates hallucination or incomplete analysis risk;
- use HitRate@K for broad health dashboards, not release gates;
- pair precision and recall whenever a retrieval change touches candidate-pool size, chunking, filters, embeddings, or reranking.

## MRR, MAP, And NDCG

MRR is useful when the first relevant item matters most. MAP rewards retrieving multiple relevant items early. NDCG supports graded relevance and position discounts, which makes it better for source packs where some evidence is primary, some is background, and some is weakly related.

Agent Studio implication:

- use MRR for "find the first correct source/tool/route" tasks;
- use MAP when multiple relevant sources should appear before context packing;
- use NDCG when relevance is graded, such as primary source, cross-check source, background source, or stale/weak source;
- store relevance grades and cutoff K with the eval result, because metric values are meaningless without the judgment protocol.

## Coverage, Diversity, Novelty

Coverage and diversity are long-term health metrics. They prevent the system from repeatedly using the same source family, route, agent, or creative pattern.

Agent Studio implication:

- source coverage should detect over-reliance on one book, one provider doc, or one lecture;
- topic coverage should reveal missing areas in the vault;
- diversity should be computed after deduplication and relevance filtering;
- novelty and serendipity should be used for ideation queues, not citation-critical evidence ranking.
- catalog coverage becomes source-ledger coverage in Agent Studio: how many eligible source families, domains, books, lectures, and internal notes are actually reachable by a route.
- diversity needs a redundancy check. Ten chunks from the same PDF section are not ten independent sources.

## Online Feedback Is Not Ground Truth

CTR, conversion, dwell time, acceptance rate, and revision burden are valuable product signals. They are also biased by position, interface, timing, user intent, and prior exposure.

Agent Studio implication:

- online outcomes should update monitoring and backlog priority;
- offline source-grounding evals should still gate factual and architecture-critical routes;
- position bias should be logged when comparing recommendation or retrieval UI variants;
- feedback signals should be segmented by workflow type, not averaged across source-backed research, creative ideation, and publishing.
- dwell time and acceptance should be interpreted with artifact state: a user may dwell because a source-backed answer is useful, because it is confusing, or because it requires manual verification.

## Adaptive System Metrics

The local guide's learning-rate and stability/adaptability framing maps to long-running agents. A system should learn from feedback, but not thrash after one noisy interaction.

Agent Studio implication:

- measure how quickly a route improves after explicit user correction;
- measure list overlap over time for recommendation/memory surfaces;
- track cold-start quality separately from mature-user quality;
- require rollback for personalization or memory changes that narrow source diversity or reduce grounding.
- track stability under repeated source refreshes. A retrieval route that changes its top evidence pack drastically after a small crawl refresh needs a release review.

## Failure Modes

- Optimizing Precision@K until recall collapses.
- Using HitRate@K as proof of full coverage.
- Reporting NDCG without relevance-grade definitions.
- Treating CTR or dwell time as factual-quality evidence.
- Increasing novelty in a factual workflow without source-quality gates.
- Averaging metrics across query types with different risk and K requirements.
- Ignoring position bias when online feedback drives ranking changes.

## Datastore Implications

Add or strengthen:

- `ranking_eval_case`: query/user/task, candidate universe, cutoff K, expected relevant IDs, forbidden IDs, relevance-grade rubric, and surface.
- `ranking_metric_result`: metric name, K, relevance protocol, value, sample count, segment, and caveats.
- `relevance_judgment`: candidate ID, judge type, relevance grade, rationale summary, source/eval refs, and review status.
- `ranking_list_snapshot`: ordered candidate IDs, ranking policy, retriever/reranker versions, filters, position, score, and exposure context.
- `online_feedback_metric`: impression, click, accept, dwell, conversion, revision burden, position, UI surface, and bias caveats.
- `coverage_diversity_metric`: source/topic/entity/list diversity, catalog/source coverage, novelty policy, and risk guardrails.
- `source_coverage_metric`: source families/domains/books/lectures represented in candidate lists, overused source clusters, missing authority classes, and eligibility filters.
- `ranking_bias_record`: position bias, popularity bias, source-authority bias, freshness bias, and personalization-narrowing caveats for a ranking surface.
- `ranking_quality_release_gate`: promotion gate proving a ranking, retrieval, reranking, memory-selection, route-selection, or recommendation change improves the intended ranking surface without hiding coverage, diversity, grounding, latency, or online-feedback risks.

The design principle: ranking metrics must identify their candidate set, cutoff, relevance judgment method, and workflow surface. Otherwise a number like NDCG@10 or Recall@20 is not actionable.

## Ranking-Quality Release Gate

Before a ranking policy can affect retrieval, reranking, memory reuse, candidate generation, source-priority queues, personalized surfaces, or feed-style recommendations, the release gate should prove:

- the ranking surface and workflow objective are named;
- candidate universe and cutoff K are fixed for each metric;
- relevance judgments have a rubric, judge identity, and review status;
- Precision@K, Recall@K, MRR, MAP, NDCG, coverage, diversity, and behavioral metrics are not collapsed into one score;
- false positives and false negatives are inspected separately, especially for minority or release-blocking evidence;
- online feedback is segmented by surface and marked as behavioral evidence, not factual truth;
- novelty or diversity objectives run behind relevance, rights, safety, and grounding constraints;
- cold-start and mature-user/source-rich states are evaluated separately;
- popularity, position, freshness, and personalization bias caveats are attached to online results;
- latency, cost, fallback, and rollback are recorded before promotion.

Minimum fields: `gate_id`, `route_id`, `candidate_release_id`, `ranking_surface`, `objective_ref`, `candidate_universe_ref`, `ranking_policy_ref`, `cutoff_policy_ref`, `relevance_grade_rubric_ref`, `ranking_eval_case_refs`, `relevance_judgment_refs`, `ranking_metric_result_refs`, `source_coverage_metric_refs`, `coverage_diversity_metric_refs`, `ranking_bias_record_refs`, `online_feedback_metric_refs`, `false_positive_review_refs`, `false_negative_review_refs`, `minority_evidence_slice_refs`, `position_bias_caveat_ref`, `cold_start_slice_ref`, `latency_cost_evidence_ref`, `fallback_ref`, `rollback_target_ref`, `decision`, and `reviewed_at`.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
