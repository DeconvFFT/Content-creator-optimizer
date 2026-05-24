---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Designing Machine Learning Systems"
author: "Chip Huyen"
chapter: "9"
chapter_title: "Continual Learning and Test in Production"
source_path: "/Users/saumyamehta/DS interview prep/books/Designing machine learning systems - an iterative process.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 9 - Continual Learning and Test in Production

## Reading Status

Direct source reading and official cross-check completed for chapter 9. This note is original synthesis only and does not include raw book text or long excerpts.

## Core Idea

Monitoring detects degradation; continual learning updates the system to adapt. The chapter presents continual learning as an infrastructure problem: fresh data access, label computation, model lineage, update triggers, evaluation gates, and production testing must exist before frequent updates are safe.

For Agent Studio, continual learning generalizes beyond model weights. The system must continually update source corpora, retrieval indexes, eval sets, prompt templates, model routes, tool policies, and workflow defaults without corrupting production behavior.

## Continual Learning Definition

The chapter distinguishes continual learning from training on every single incoming example. In production, updates usually happen in micro-batches. A challenger is trained or updated separately and replaces the champion only if it passes evaluation.

Agent Studio implication:

- Never mutate the production agent/model/index in place.
- Use champion/challenger for prompts, retrieval indexes, rerankers, model routes, and agent policies.
- Promote updated artifacts only after offline evals, shadow checks, or controlled production tests.

## Stateless Retraining Versus Stateful Training

Stateless retraining starts from scratch using a larger historical dataset. Stateful training continues from a previous checkpoint using fresh data. Stateful training can reduce compute and data retention needs, but it requires stronger lineage and rollback.

Agent Studio implication:

- For retrieval indexes, stateful update means appending or refreshing changed source chunks without full rebuild.
- For eval datasets, stateful update means adding reviewed failures while preserving historical cases.
- For prompts and agents, stateful update means versioned incremental changes, not editing production instructions silently.
- Periodic full rebuilds remain necessary for calibration and migration.

## Model Iteration Versus Data Iteration

The chapter separates model iteration from data iteration. Model iteration changes architecture or features; data iteration refreshes the model with new data while keeping the structure stable.

Agent Studio mapping:

- data iteration: new book chapters, source docs, approved feedback examples, updated embeddings;
- model iteration: new model provider, new reranker, new agent graph, new tool policy, new prompt schema;
- mixed iteration: changing chunking policy while ingesting new sources.

Agent Studio implication:

- Data iteration can often move faster.
- Model/architecture iteration needs broader regression coverage and stronger rollout controls.

## Fresh Data And Label Computation

Continual learning depends on access to fresh data and labels. Natural labels often exist as user behavior or feedback events, but they require computation from logs.

Agent Studio implication:

- Feedback is not useful until it is linked to the trace, source, model route, prompt version, and user-visible output.
- Label computation should turn corrections, accept/reject decisions, citation fixes, reviewer comments, and tool outcomes into structured training/eval events.
- Short feedback loops are valuable, but raw user behavior should not automatically rewrite system behavior without review.

## Evaluation Challenge

Frequent updates increase the number of chances to ship a bad model or policy. Evaluation can become the bottleneck, especially when labels are delayed or rare.

Agent Studio implication:

- Every artifact promotion needs an evaluation stage matched to risk.
- Low-risk background note formatting can use smoke tests.
- Retrieval, citation, and tool-action changes need targeted regression suites.
- User-facing autonomous workflows require offline evals plus production safeguards.
- High-impact changes should require human review.

## Four Stages

The chapter describes four maturity stages:

- manual stateless retraining;
- automated stateless retraining;
- automated stateful training;
- trigger-based continual learning.

Agent Studio maturity path:

- Stage 1: manual source ingestion and manual note updates.
- Stage 2: scheduled batch ingestion, extraction, embedding, and eval jobs.
- Stage 3: incremental source/index updates with lineage and rollback.
- Stage 4: monitored trigger-based updates from approved source additions, drift, eval failures, and reviewed feedback.

## Update Triggers

Useful triggers include time, performance, volume, and drift. Trigger-based updating requires reliable monitoring; noisy drift detection can cause unnecessary retraining.

Agent Studio triggers:

- approved new source batch;
- official docs changed;
- extraction failure rate changed;
- retrieval eval degraded;
- citation acceptance fell;
- user correction rate rose;
- model provider or route changed;
- cost/latency regression crossed threshold;
- reviewed production issue became a regression case.

## Data Freshness Experiments

The chapter recommends measuring the value of fresher data by training on historical windows and testing on more recent data. The principle is to quantify whether faster updates are worth the cost.

Agent Studio implication:

- Measure freshness value for official docs, model/provider guidance, local book indexes, retrieval corpora, and eval sets.
- Do not blindly refresh every artifact at the same cadence.
- Fast-changing docs and APIs need tighter refresh loops than foundational books.
- Production feedback-derived eval cases may deserve faster ingestion than slow-moving reference notes.

## Test In Production

Static offline tests are not enough because production distributions change. The chapter covers backtests, shadow deployment, A/B testing, canary release, interleaving, and bandits.

Agent Studio application:

- backtests: evaluate new retrieval/index/prompt changes against recent reviewed traces;
- shadow: run a candidate retrieval or model route while serving the current route;
- canary: expose a candidate workflow to a small safe traffic slice;
- A/B: compare user-facing quality metrics when traffic can be randomized;
- interleaving: compare ranking/retrieval candidates in the same user context;
- bandits: consider only when feedback loops are short and safety risk is low.

## Evaluation Ownership

The chapter warns against ad hoc evaluation owned only by the model developer. A reliable process defines tests, order, thresholds, promotion rules, and reporting.

Agent Studio implication:

- Evaluation pipelines should be product infrastructure, not personal scripts.
- Define promotion gates per artifact type: source, index, prompt, model route, tool policy, agent graph.
- Record who approved a promotion and which eval suite/version passed.

## Failure Modes

- Updating production artifacts in place with no challenger, lineage, or rollback.
- Treating feedback events as labels before computing their context.
- Updating too frequently because monitoring emits noisy false positives.
- Updating too slowly because the pipeline is manual.
- Measuring only offline static tests for a system that changed to match production drift.
- Running A/B tests without randomization or sufficient sample size.
- Using bandits where feedback is delayed, noisy, or safety-critical.
- Letting each developer choose different eval tests for the same promotion type.

## Agent Studio Design Decisions

- Use champion/challenger promotion for model routes, prompts, retrieval indexes, and agent policies.
- Store lineage for each artifact update: base version, new data, update trigger, eval suite, metrics, approver, rollout state.
- Implement label computation from trace-linked user/reviewer feedback.
- Start with scheduled batch refreshes, then add trigger-based updates only after monitoring is reliable.
- Use shadow and canary deployments before replacing high-impact production workflows.
- Maintain separate cadences for books, official docs, eval cases, prompts, models, and retrieval indexes.

## Follow-Ups

- Define Agent Studio artifact promotion gates.
- Add schemas for `artifact_update`, `promotion_gate`, `feedback_label`, and `production_experiment`.
- Canon cross-check: [[01-sources/official-open/designing-machine-learning-systems-cross-check]]

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
