---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-19
sources:
  - [[../../02-lectures/stanford/cs25-future-of-pretraining]]
  - [[../../02-lectures/stanford/cs324-large-language-models]]
  - [[../../02-books/applied-ml-ai-engineers/applied-ml-engineering-patterns]]
  - [[../../02-books/probabilistic-ml-advanced/approximate-inference-shift-interpretability]]
  - [[../../01-sources/official-open/anthropic-eval-design]]
  - [[../../01-sources/official-open/openai-evals-and-agent-evals]]
  - [[../../01-sources/official-open/google-cloud-genai-operations-evaluation]]
  - [[../../01-sources/official-open/ragas-langsmith-rag-agent-evals]]
  - [[../../01-sources/official-open/open-llm-observability-eval-platforms]]
  - [[../../01-sources/official-open/annotation-human-feedback-data-ops]]
  - [[../../01-sources/official-open/llamaindex-agent-workflows-rag-eval]]
  - [[../../02-lectures/stanford/cs329x-human-centered-llms]]
  - [[../../02-books/islp/statistical-learning-validation]]
  - [[../../02-books/islp/chapters/4-classification-decision-thresholds]]
  - [[../../02-books/prml/probabilistic-decision-graphical-models]]
  - [[../../02-books/prml/chapters/8-graphical-models-route-evidence]]
  - [[../../02-books/math-for-ml/chapters/7-continuous-optimization-route-tuning]]
  - [[../../02-books/deep-learning-book/generalization-optimization-sequence-systems]]
  - [[../../02-books/deep-learning-book/chapters/11-practical-methodology]]
  - [[../../02-books/prompt-engineering-for-llms/chapters/10-evaluating-llm-applications]]
  - [[prompt-workflow-eval-datasets]]
  - [[../../04-agent-studio-implications/Route Change Proposal Template]]
  - [[../../01-sources/official-open/uber-prd-reviewer-agent]]
---

# Eval Design Canon

## Scope

Cross-check synthesis from Anthropic eval-design docs, OpenAI eval/agent-eval/trace-grading docs, Prompt Engineering for LLMs chapter 10, and the existing Agent Studio prompt/workflow eval templates. This note records durable eval-design decisions only and stores no raw source text.

## Canon Decision

Every Agent Studio route needs a success contract before prompt, model, retrieval, or graph optimization. The contract defines what good behavior means, which eval surfaces prove it, which failures block release, and which metrics are allowed to trade off.

Eval design is therefore part of the route architecture, not post-hoc QA.

LlamaIndex's eval guidance reinforces a split that Agent Studio should keep explicit: response faithfulness and retrieval quality are different eval surfaces. A generated answer can be faithful to a weak context, and a retriever can find the right nodes while the final response still makes unsupported claims. Source-backed routes therefore need both retrieval relevance metrics and response faithfulness/grounding checks.

## Required Success Contract

Each production or canon-impacting route should define:

- `objective`: user/product job the route must satisfy;
- `task_distribution`: typical, edge, adversarial, long-context, and source-backed cases;
- `quality_dimensions`: grounding, relevance, completeness, artifact fidelity, style/platform fit, safety, latency, and cost;
- `thresholds`: pass/fail gates and tolerated regression bounds per dimension;
- `business_or_user_relevance`: why the threshold matters;
- `blocked_tradeoffs`: regressions that cannot be hidden by aggregate quality gains.

## Eval Surface Separation

Agent Studio should not collapse all evals into one score. It needs separate surfaces:

- prompt unit behavior;
- retrieval/source grounding;
- tool choice and tool arguments;
- workflow trace and handoff behavior;
- artifact-state preservation;
- human approval behavior;
- guardrail/safety behavior;
- latency, cost, and operational stability;
- online outcome once a route reaches real users.

Route promotion can use aggregate summaries, but failure slices must remain visible.

## Grader Ladder

Use the narrowest reliable grader first:

1. schema or exact checks;
2. executable/functional checks;
3. retrieval/citation checks;
4. pairwise or pass/fail model judging;
5. ordinal rubric model judging;
6. human review for high-risk or weakly automatable judgment.

Model judges must be calibrated against human review before they gate releases. Store scores and concise rationale summaries, not hidden reasoning.

Generated text metrics such as BLEU and ROUGE belong in this ladder as diagnostic overlap metrics, not standalone graders. They need tokenization protocol, reference policy, and route-specific caveats. For source-backed answers, add factuality and citation checks; for code-like outputs, add executable tests; for editorial content, add human or calibrated style review.

## Dataset Provenance

Eval cases should be provenance-aware:

- expert-authored cases for known requirements;
- production/user-feedback cases for realism;
- adversarial cases for safety and robustness;
- synthetic cases only with generator metadata and review status;
- source-backed cases with source snapshot and retrieval-index references.

Synthetic cases are useful for coverage, but cannot be the only evidence for a release-critical route change.

## Selection Versus Assessment

ISLP adds a statistical-learning discipline that the agent eval stack needs: route selection and route assessment are different jobs. The eval slice used to choose among candidates is not enough to prove that the selected candidate will generalize.

Agent Studio should therefore label eval runs by purpose:

- `selection_run`: compares candidate prompts, routes, retrievers, rerankers, graph shapes, or models;
- `assessment_run`: tests the selected candidate on held-out or shadow cases before promotion;
- `monitoring_run`: tracks production or post-release behavior.

When eval data is scarce, use repeated splits, k-fold-style comparisons, or bootstrap-style uncertainty estimates rather than pretending that a tiny average-score delta is stable.

Deep Learning adds a related warning: validation data is part of the tuning process. When a prompt, reranker, model route, or agent graph is repeatedly optimized against the same eval pack, that eval pack becomes stale selection evidence. Agent Studio should record validation reuse and require a fresh assessment slice for promotion when reuse is high.

Deep Learning Chapter 11 adds the methodology layer: route improvement should start with a product metric target, simple end-to-end baseline, bottleneck diagnosis, and debug fixture before adding data, capacity, tools, memory, agents, or optimizer search. High-confidence failures and visible trace inspection are release evidence, not just debugging convenience.

For release decisions, this becomes a `selection_assessment_release_gate`: candidate choice can be based on development or validation evidence, but promotion needs a separately identified held-out or shadow assessment run, split provenance, resampling or uncertainty evidence where appropriate, validation-reuse status, leakage checks, regression slices, reviewer override policy, fallback, and rollback.

ISLP Chapter 4 adds the classifier-decision discipline: any route that turns a probability, margin, judge score, risk score, or similarity score into a product action needs an explicit label contract, threshold policy, confusion matrix, class-specific metrics, and cost rationale. A high aggregate accuracy is not enough for rare-risk decisions such as unsafe output, unsupported claims, source rejection, publish/block, retrieve-more, or human-review escalation.

## Prompt Variant Comparison

Prompt variants should be compared as route artifacts, not loose strings. A comparison should bind:

- baseline prompt version;
- candidate prompt version;
- variables and rendered prompt hash;
- model/provider settings;
- eval dataset version;
- per-surface metric deltas;
- regression slices;
- ship/no-ship decision.

This keeps prompt iteration compatible with later graph, tool, retrieval, and model changes.

## Route Promotion Rule

A route change can move forward only when:

- the success contract exists;
- eval cases cover the changed surfaces;
- baseline and candidate run on the same relevant eval slices;
- model-judge graders are calibrated or marked advisory;
- selection evidence and assessment evidence are separated when a candidate was chosen through prompt, model, retriever, reranker, graph, or agent-route comparison;
- human approval gates are tested when side effects are possible;
- latency/cost regressions are visible;
- new failures are converted into follow-up eval cases or explicitly accepted by a reviewer.

## Uncertainty And Decision Policy

PRML adds a decision-theory layer that the eval system needs: a score is an estimate, not a decision. Agent Studio should store the uncertainty signal separately from the policy that acts on it.

For release and route decisions:

- a high score is not enough when the downside of a wrong action is high;
- an abstain, ask-user, retrieve-more, or human-review outcome can be correct behavior;
- promotion thresholds should reflect expected loss, not only average quality;
- confidence should identify which evidence changed the route belief and which caveats remain.

This matters most for public publishing, source-backed factual claims, tool actions, private-data workflows, and canon-changing notes.

Murphy's probabilistic ML treatment adds a calibration layer: margin scores, similarity scores, judge ratings, and fitted classifier probabilities are not automatically calibrated posterior predictive confidence. Evals should therefore check both correctness and confidence quality. When a route uses a scorer to decide publish, abstain, retrieve-more, or human-review, the eval record should show the calibration source, evidence coverage, and whether confidence degrades outside the tested slice.

Murphy Advanced Topics adds a shift layer: an eval run should name the distribution-shift class it is meant to detect. Covariate/domain shift, label/prior shift, concept/annotation shift, conditional/manifestation shift, and selection bias require different monitoring and mitigation. A route can pass a source-distribution eval while still being unsafe for a new platform, language, reviewer rubric, source style, or media format.

Applied ML/AI for Engineers adds a practical metric-cost layer: classification quality must expose false-positive and false-negative costs, not just aggregate accuracy. Confusion matrices, precision, recall, specificity, class weights, threshold choices, and class distribution belong in the release evidence for any scoring route. This is especially important for publish/block/escalate decisions, source-quality filters, content moderation, and rare-risk workflows.

CS324 adds contamination discipline: benchmark, eval, prompt-example, retrieval-index, and training-data overlap can make a route look better than it generalizes. For source-backed Agent Studio work, contamination includes not only pretraining leakage but also eval cases that were previously used as prompt examples, notes that were indexed into retrieval, or generated training data derived from held-out assessment cases.

CS25 future-of-pretraining adds a reference-world discipline for hallucination evals. A generated answer can be wrong relative to public reality, unsupported by the retrieved source, inconsistent with a product policy, stale relative to current official docs, or correct but unverified. Evals should name the reference world and conflict policy before judging hallucination or grounding.

Pretraining or reasoning-capability claims also need eval gates before they weaken source controls. A `pretraining_assumption_release_gate` should prove exact model/source assumptions, retrieval budget, source-ledger coverage, reference-world evals, objective/data caveats, contamination and rights checks, simpler route interventions tried, reasoning-failure diagnosis, product-slice regressions, fallback, and rollback before a route reduces retrieval, citation, verifier, reviewer, or human-policy controls.

Uber's PRD Evaluator adds a pre-approval review discipline. First-pass reviewer agents should not optimize for pleasant prose or final approval. They should assemble context, classify proposal risk, evaluate against explicit readiness dimensions, identify critical gaps, and produce prioritized repair actions with evidence before humans spend review-room time.

Google Cloud GenAI operations adds a lifecycle and trajectory-eval discipline. A route eval should identify the prompted component being tested, including model/provider, prompt template, examples, grounding snapshot, chain definition, tools, and safety policy. Agent evals should separately record final-response quality and trajectory quality, because a correct-looking final answer can hide wrong tool order, stale grounding, unsafe action choice, or a chain step that only happened to recover.

For RAG and GraphRAG routes, evals must cover ingestion quality and serving behavior separately. Ingestion evals check parsing, chunking, embedding/index refresh, graph extraction, entity/relation quality, and source freshness. Serving evals check query embedding, retrieval policy, graph traversal, prompt assembly, model response, safety filtering, citation grounding, latency, and monitoring.

Ragas and LangSmith add a metric-governance layer. RAG routes need separate metric contracts for ranking precision, required-evidence recall, claim faithfulness, response relevance, and source/citation validity. Agent routes need separate contracts for strict tool-call correctness, softer over-call/under-call F1, and final goal achievement. Online evals should sample production traces into human annotation and offline regression datasets instead of leaving failures as dashboard-only telemetry.

For source-backed artifacts, use [[source-claim-evidence-ledger]] as the support-state contract. A generated claim can be `supported`, `supported_with_caveat`, `needs_review`, `unsupported`, `contradicted`, `stale_or_unverified_current`, or `out_of_scope_source`; the eval surface must preserve the reference world, accepted evidence, rejected evidence, verifier, caveat, and decision reference.

Langfuse, Phoenix, TruLens, and DeepEval add an observability-platform discipline: evals should attach to traces and spans, not only to final outputs. Agent Studio should score retrievers, prompt assembly, tool choice, tool arguments, planner steps, generator outputs, and final artifacts separately, then bind those scores to prompt versions, route releases, datasets, experiments, and annotation queues. This keeps regression analysis actionable when a multi-agent route succeeds in the final answer but fails in one component.

Label Studio, Argilla, and Snorkel add an annotation data-ops discipline: human feedback has a task schema, guideline version, assignment policy, suggestion/pre-annotation source, annotator role, response state, export format, and promotion status. A reviewer accepting a model suggestion is not the same evidence as an independent label; an active-learning batch is not an unbiased assessment slice; and weak labels from rules, models, crowds, or LLM prompts need separate trust and conflict records.

CS329X adds a human-interaction layer: final artifact quality is not enough when the route is collaborative. Evals should measure whether the interaction preserved user agency, reduced user effort, repaired misunderstandings, exposed intervention points, respected personalization boundaries, and handled disagreement or pluralistic preferences explicitly.

## Datastore Implications

Strengthen these records:

- `business_cost_metric_record`: false-positive cost, false-negative cost, precision target, recall target, specificity target, threshold, and reviewer-capacity assumptions.
- `class_imbalance_record`: class distribution, stratification policy, class weights, threshold candidates, minority-class metrics, and caveats.
- `classification_label_contract`: label space, positive class, allowed abstain/review states, ordinal assumptions, score semantics, and action mapping.
- `classification_metric_profile`: confusion matrix, class distribution, sensitivity, specificity, precision, recall, false-positive rate, false-negative rate, and sample counts.
- `threshold_policy_record`: candidate thresholds, selected threshold, cost rationale, reviewer-capacity impact, abstention band, and rerun trigger.
- `classification_decision_release_gate`: promotion gate proving label contract, baseline comparison, threshold policy, confusion matrix, rare-class behavior, calibration evidence, confounding slice review, fallback, and rollback.
- `training_contamination_check`: eval/source artifact, possible training/retrieval/prompt overlap, check method, contamination class, mitigation, and residual risk.
- `agent_trajectory_eval_case`: expected tool/action sequence, allowed alternatives, final response requirement, grounding requirement, and risk tags.
- `agent_trajectory_eval_result`: predicted trajectory, mismatch type, failing step, final-response score, reviewer override, and promotion impact.
- `reference_world_record`: source snapshot, official-doc version, database, policy, user brief, or reviewer decision that defines correctness for a route or eval case.
- `annotation_schema_version`: fields, questions, label/rating/ranking/span/text schema, guidelines, required responses, and changed-rubric compatibility policy.
- `preannotation_suggestion`: model, LLM, weak-label, or imported prediction shown to annotators, with score, visibility, accepted/edited/rejected outcome, and bias caveat.
- `active_learning_batch`: selection policy, uncertainty/informativeness signal, model version, sample scope, and assessment-bias caveat.
- `weak_label_source`: heuristic, ruleset, model, crowd, LLM prompt, or labeling-function source with coverage, conflict, confidence, and promotion status.
- `annotation_data_release_gate`: project, schema/guideline versions, assignment policy, reviewer classes, suggestion lineage, active-learning and weak-label provenance, export/storage manifests, disagreement review, draft/discard filters, dataset-promotion policy, downstream-use policy, and rollback target before feedback changes evals, tuning, source filters, retrievers/rankers, or route releases.
- `hallucination_eval_case`: reference world, conflict policy, expected support behavior, unsupported behavior, factual-wrongness behavior, and mitigation path.
- `route_success_contract`: route objective, task distribution, quality dimensions, thresholds, and blocked tradeoffs.
- `eval_case`: surface, source/artifact inputs, expected behavior, forbidden behavior, risk level, and grader policy.
- `grader_rubric`: criterion, scale, anchors, model/human calibration, threshold, and override policy.
- `prompt_variant`: template, variables, rendered hash, model/provider settings, and reason for change.
- `eval_comparison`: baseline, candidate, dataset version, per-metric deltas, regressions, and decision.
- `eval_generation_record`: generator, seed cases, reviewer edits, synthetic caveats, and approved coverage.
- `eval_split`: partition, leakage rules, route surfaces covered, and reuse policy.
- `selection_run`: candidate set, split policy, selected candidate, and selection rationale.
- `assessment_run`: held-out split, promotion decision, regression slices, and reviewer override.
- `selection_assessment_release_gate`: split labels, selection runs, held-out or shadow assessment run, resampling evidence, uncertainty, validation-reuse status, leakage checks, small-delta policy, fallback, and rollback.
- `methodology_release_gate`: metric target, baseline, bottleneck diagnosis, experiment search space, debug fixtures, worst-error review, held-out assessment, coverage/accuracy policy, fallback, and rollback.
- `worst_error_review`: high-confidence mistakes, failure cluster, source/artifact examples, root-cause hypothesis, and fix status.
- `metric_uncertainty`: sample count, interval, resampling method, and caveats for key reported metrics.
- `calibration_record`: scoring surface, raw score type, calibration data, calibration method, reliability result, and known caveats.
- `route_complexity_record`: added route components, simpler baseline, complexity burden, held-out benefit, and justification.
- `online_update_record`: feedback window, update target, learning rule or policy change, rolling metrics, regret proxy, and rollback trigger.
- `adaptive_belief_state_release_gate`: calibration, route-complexity, online-update/regret, graph-authority, belief-state, ranking-exposure, candidate-diversity, fallback, and rollback evidence before adaptive behavior changes production routes.
- `uncertainty_signal`: prior, evidence refs, posterior confidence summary, calibration source, and caveats for a score or claim.
- `decision_policy`: available actions, risk weights or loss matrix, abstention rule, escalation rule, and override policy.
- `decision_outcome`: selected action, expected-loss rationale, rejected actions, evidence refs, and escalation/abstention reason.
- `uncertainty_decision_release_gate`: uncertainty signals, calibration, expected-loss policy, abstention/escalation evals, evidence-dependency edges, graph messages, failure hypotheses, fallback, and rollback before confidence drives action or promotion.
- `conditional_independence_claim`: graph claim that variables can be separated under a specific conditioning context and graph version.
- `graph_inference_trace`: message-passing or local-propagation trace with schedule, messages, convergence, and caveats.
- `graph_route_release_gate`: route-graph promotion gate proving graph semantics, factor definitions, independence claims, approximation caveats, fallback, and rollback.
- `validation_reuse_record`: eval set, route versions tuned against it, reuse count, staleness warning, and assessment replacement plan.
- `route_optimization_run`: optimizer target, objective refs, constraint refs, sampled-evidence policy, baseline route, and status for prompt, threshold, retrieval, route, or model tuning.
- `optimization_step_record`: one update with direction signal, step-size class, changed fields, before/after deltas, and rollback status.
- `optimization_signal_batch`: sampled eval or feedback evidence used for an optimizer step, including slice coverage and bias caveats.
- `optimization_constraint_record`: source, safety, policy, latency, cost, privacy, or reviewer-capacity constraint that defines the feasible route region.
- `constraint_violation_record`: candidate behavior that improves an objective while violating a declared constraint.
- `optimization_convergence_record`: stop reason, oscillation/divergence flags, and local-minimum caveats for route improvement loops.
- `optimization_tradeoff_record`: objective gain versus active or nearly active constraints.
- `route_optimization_release_gate`: objective, constraints, sampled evidence, step policy, convergence, tradeoffs, held-out assessment, fallback, and rollback before optimizer-driven route changes affect production.
- `pretraining_assumption_release_gate`: model/source assumption, retrieval/source coverage, reference-world evals, contamination/rights checks, simpler interventions tried, reasoning-failure diagnosis, regressions, fallback, and rollback before relying on pretrained capability.
- `generated_text_metric_record`: metric, tokenization protocol, reference policy, semantic limitations, route relevance, and required complementary checks.
- `approximate_inference_record`: target variable, approximation family, update mode, evidence refs, convergence diagnostics, compute profile, validity slice, and caveats.
- `posterior_approximation_record`: posterior subject, prior summary, likelihood/evidence refs, approximation type, calibration result, uncertainty summary, and stale-after policy.
- `distribution_shift_record`: shift class, source distribution, target distribution, affected route, detected signal, slice, mitigation, and monitoring plan.
- `interpretability_review`: explanation target, user/decision context, explanation method, evidence artifact, fidelity check, reviewer outcome, and resulting action.
- `review_artifact_record`: draft PRD, route proposal, content packet, or release candidate under first-pass review.
- `context_assembly_record`: linked and discovered docs, prior experiments, policies, metrics, adjacent artifacts, and access boundaries used by the reviewer.
- `proposal_risk_classification`: review-depth decision, risk category, specialized scrutiny flags, and rationale.
- `readiness_scorecard`: readiness rating, dimension scores, evidence refs, critical gaps, first-fix pointer, and decision status.
- `critical_gap_record`: blocking gap, missing evidence, affected dimension, suggested fix, owner, and status.
- `revision_action_item`: ordered repair task marked as critical requirement or optimization.
- `review_conversation_outcome`: later human-review signal used to judge whether the AI first pass improved review quality.
- `rag_eval_metric_contract`: metric name, evaluated layer, required inputs, reference policy, scorer type, evaluator version, threshold, calibration status, and route surfaces covered.
- `rag_eval_result`: metric contract, route version, source snapshot, eval case, trace ref, score/value, rationale summary, failure category, and reviewer override.
- `trace_feedback_annotation`: trace/span ref, annotator class, feedback key, value/score, comment summary, linked eval case, dataset-promotion status, and retention policy.
- `evaluator_registry_record`: evaluator owner, type, prompt/code artifact, input contract, output key, calibration data, attached resources, and change history.
- `online_eval_rule`: production run/thread selector, evaluator refs, anomaly rule, sampling policy, action policy, and dataset-backfill policy.
- `observability_project_record`: workspace/environment boundary, owner, route set, retention class, redaction policy, sampling policy, and export policy.
- `trace_score_record`: trace/span ref, evaluator ref, score key, value type, threshold, rationale summary, calibration status, and promotion impact.
- `eval_dataset_example_record`: dataset ref, input artifacts, expected and forbidden behavior, source snapshot refs, risk tags, generator/reviewer provenance, and lifecycle status.
- `prompt_experiment_record`: baseline prompt, candidate prompt, route release, dataset, evaluator set, metric deltas, regression slices, decision, and rollback target.
- `component_eval_target`: route component type, span selector, required inputs, allowed metrics, failure taxonomy, and release-blocking flag.
- `annotation_queue_item`: trace/span ref, rubric ref, annotator class, priority, assignment state, label output, disagreement status, and dataset-promotion decision.
- `human_interaction_eval_case`: user goal, route autonomy mode, expected collaboration behavior, forbidden overreach, repair requirement, and user-effort target.
- `collaboration_process_metric`: user effort, repair count, interruption count, initiative balance, clarification quality, satisfaction signal, and reviewer caveat.
- `preference_perspective_record`: reviewer/user group, value dimension, preference source, disagreement signal, aggregation policy, and caveats.

## Agent Studio Design Implications

- Route creation UI should ask for success criteria before prompt text.
- Eval datasets should be browsable by route surface and failure slice.
- Prompt optimizer output should create candidate variants, not mutate production prompts directly.
- Trace grading should be required for graph, tool, guardrail, and handoff changes.
- Human-review queues should feed new eval cases back into the dataset.
- Trace views should show component scores beside latency, cost, prompt version, route version, retrieval snapshot, and evaluator version.
- Collaborative routes should show process metrics beside final artifact metrics so "good output after painful interaction" is still visible as a regression.
- Cost and latency are success criteria, not observability afterthoughts.
- Interpretability artifacts should be attached to a decision context, such as debugging, recourse, reviewer override, safety inspection, or route promotion.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
