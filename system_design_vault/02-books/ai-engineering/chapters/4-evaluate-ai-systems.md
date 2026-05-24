---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "AI Engineering"
authors: "Chip Huyen"
chapter: "4"
chapter_title: "Evaluate AI Systems"
source_path: "/Users/saumyamehta/DS interview prep/books/AI Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 4 - Evaluate AI Systems

## Reading Status

Direct source reading pass completed for chapter 4 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied tables, copied figures, copied prompts, and long excerpts.

## Core Idea

Evaluation must be designed before and during application development, not bolted on after launch. Chapter 4 turns evaluation from a model-quality exercise into an operating discipline: define success criteria, pick models against those criteria, distrust generic public benchmarks as final evidence, and build an evaluation pipeline that measures the system at component, turn, task, and business-outcome levels.

For Agent Studio, this chapter reinforces that the data store must make evaluation reproducible. Model choice, prompt changes, retrieval changes, guardrail changes, and provider changes should all leave eval evidence tied to exact data slices, rubrics, judge versions, route versions, costs, and latency.

## Evaluation-Driven Development

The chapter argues that an unevaluated deployed application is worse than an undeployed one because it has cost, risk, and unclear value. AI work should therefore start with evaluation criteria before implementation.

Agent Studio intake should capture:

- what business outcome the workflow is meant to change;
- what quality threshold makes it useful;
- what failure threshold makes it unsafe or not worth deploying;
- which criteria are domain-specific, generation-quality, instruction-following, safety, cost, and latency;
- which criteria are must-have versus nice-to-have;
- which criteria can be exact tests and which require human or AI judgment.

Agent Studio implication: every proposed route should have an evaluation contract before it gets implementation work beyond a prototype.

## Evaluation Criteria

Chapter 4 groups evaluation criteria into practical buckets.

Domain-specific capability checks whether the model can do the job at all: coding, math, legal analysis, translation, tool use, retrieval, summarization, planning, or other domain tasks. Exact evaluation is preferred when possible, especially for code, SQL, classification, and workflow completion.

Generation capability checks qualities of open-ended outputs: factual consistency, relevance, coherence, fluency, safety, helpfulness, concision, and style. The chapter emphasizes factual consistency because unsupported claims can cause real harm. It distinguishes local consistency against provided context from global consistency against open knowledge.

Instruction-following checks whether the model obeys constraints such as format, language, length, forbidden words, role behavior, tone, or structured output. This is separate from domain capability: a model may know the answer but fail the requested output contract.

Cost and latency checks decide whether quality is usable. Time to first token, time per token, total task time, token cost, throughput, and scale limits belong in the same evaluation conversation as correctness.

Agent Studio implication: eval records should store criterion category and pass/fail thresholds separately. A single aggregate score hides whether a route failed because it was wrong, unsafe, slow, too expensive, badly formatted, or merely less preferred.

## Factuality And Safety

The chapter frames factual consistency as context-sensitive. A response can be evaluated against explicit context, retrieved evidence, or broader external knowledge. Local factuality is especially important for RAG, customer support, source-grounded writing, and business analysis. Global factuality requires source discovery and source trust decisions before claim checking.

Safety spans harmful recommendations, hate speech, violent content, stereotypes, political or religious bias, and other undesirable outputs. General-purpose judges can help, but specialized classifiers and moderation models are often cheaper and faster.

Agent Studio implication:

- Source-grounded workflows need claim-level support checks, not only answer-level scores.
- The source ledger should distinguish context supplied by the user, retrieved internal evidence, retrieved external evidence, and generated claims.
- Safety evals should be slice-based: policy-sensitive topics, vulnerable users, high-impact decisions, and adversarial phrasing should be separate eval sets.
- Moderation should be measured as its own subsystem because over-refusal and under-refusal are both product failures.

## Model Selection

The chapter separates hard attributes from soft attributes. Hard attributes include license, privacy, hosting constraints, data lineage, provider access, model size, and on-device requirements. Soft attributes include qualities that may improve through prompting, routing, retrieval, fine-tuning, or inference optimization.

The model-selection workflow is iterative:

- filter candidates by hard constraints;
- use public information to shortlist;
- run private evals on the application’s own data and criteria;
- monitor production and feed results back into model choice.

Build-versus-buy is not a one-time decision. APIs can give fast access, scalability, tool/function support, structured-output support, and managed operations. Self-hosting can give privacy, control, freezing, logprobs, intermediate outputs, custom tuning, and on-device options. Both have costs and risks.

Agent Studio implication: route registry entries should include hard-constraint decisions and reevaluation triggers. A provider route should not be treated as equivalent to a self-hosted route even if they use the same underlying open-weight model.

## Benchmark And Leaderboard Caution

Public benchmarks are useful for filtering obviously weak models, but they are not sufficient for production selection. Benchmarks may be poorly aligned with the application, correlated with each other, saturated, aggregated with arbitrary weights, expensive to run, or contaminated by training data. Leaderboards compress high-dimensional capability into a simple rank, which can be misleading for a specific workflow.

Design implications:

- Build a private leaderboard from the criteria that matter to the application.
- Track which public benchmarks influenced shortlisting, but do not use them as the final promotion gate.
- Prefer fresh, private, task-specific eval sets for route decisions.
- Treat benchmark contamination as a real risk, especially when benchmark data is public before model training.
- Store benchmark correlation and weighting choices if benchmark aggregation drives model selection.

Agent Studio implication: route-change proposals should include public benchmark context only as supporting evidence. The decisive evidence should be private eval performance on Agent Studio slices.

## Evaluation Pipeline

The evaluation pipeline should measure the whole system and its components.

Levels:

- component-level: extraction, retrieval, reranking, tool selection, schema generation, safety filter, source verifier;
- intermediate-output level: rewritten query, retrieved documents, generated plan, tool parameters, draft response;
- turn-level: quality of one system response;
- task-level: whether the user achieved the goal and how many turns/actions it took;
- production-level: user feedback, business metric movement, incident rate, cost, and latency.

The chapter’s practical sequence:

- define what the application should and should not do;
- create criteria and rubrics with examples;
- map evaluation metrics to business metrics and usefulness thresholds;
- choose methods per criterion;
- annotate data from real production-like examples where possible;
- slice eval sets by user type, traffic source, topic, length, format, known failure modes, typos, and out-of-scope inputs;
- estimate whether the dataset is large enough through variance checks;
- evaluate the evaluation pipeline itself;
- track every variable that can change.

Agent Studio implication: eval datasets should be versioned and sliced. Promotion gates should show both aggregate quality and slice-level failures because aggregate wins can hide subgroup regressions.

## Datastore Additions

Chapter 4 strengthens these Agent Studio records:

- `route_candidate`: model/provider, hosting mode, hard constraints, soft improvement plan, license, privacy class, data-lineage notes, API feature support, and freeze/rollback options.
- `eval_contract`: business metric, usefulness threshold, non-negotiable constraints, criteria list, methods, slices, and required sample sizes.
- `eval_slice`: production-like, known-failure, out-of-scope, typo/noisy, high-risk, long-context, low-resource-language, roleplay, and safety-sensitive subsets.
- `component_eval`: named component, input artifact, output artifact, metric, pass/fail, and failure reason.
- `task_eval`: goal boundary, turn count, action count, completion result, recovery behavior, and user-visible outcome.
- `benchmark_source`: public/private, contamination risk, benchmark version, metric, aggregation weight, and correlation notes.
- `eval_pipeline_version`: data version, rubric version, judge version, scorer version, prompt version, sampling config, and cost/latency of evaluation.

## Failure Modes

- Shipping a workflow before defining how success will be measured.
- Using public benchmarks to choose a model without private task-specific evals.
- Treating instruction-following failure as domain incapability, or the reverse.
- Measuring factuality globally when the product promise is local source grounding.
- Ignoring cost and latency until after model quality looks good.
- Failing to record whether a route relies on API features such as function calling, structured output, logprobs, or fine-tuning.
- Assuming open-weight means license-safe, commercially safe, or data-lineage transparent.
- Letting contaminated benchmarks drive model-selection decisions.
- Evaluating only end-to-end output and losing visibility into which component failed.
- Reporting only aggregate scores while slice-level regressions remain hidden.
- Changing eval data, rubrics, judges, or prompts without versioning them.

## Agent Studio Design Implications

- Evaluation contracts should be required artifacts for agents, routes, and source-ingestion pipelines.
- Model shortlists should be produced by hard constraints first, then private eval evidence, then cost/latency fit.
- The cockpit should present quality, safety, cost, latency, and business thresholds together.
- Every route promotion should include component evals, task evals, slice evals, and production-monitoring hooks.
- Source-grounded agents need separate gates for retrieval quality, source support, final-answer factuality, and citation validity.
- Tool-capable agents need functional checks on tool parameters and side effects, not just answer text review.
- Eval pipelines should be tested for reliability: repeated runs, bootstrap variance, metric correlation, judge drift, and cost/latency overhead.
- User feedback should be routed into eval slices with typed labels so future changes are tested against real product failures.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
