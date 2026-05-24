---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_source_note
rights_status: official_open_docs
sources:
  - https://langfuse.com/docs
  - https://langfuse.com/docs/evaluation/overview
  - https://arize.com/docs/phoenix
  - https://www.trulens.org/
  - https://www.trulens.org/getting_started/core_concepts/
  - https://deepeval.com/docs/introduction
  - https://deepeval.com/docs/metrics-introduction
---

# Open LLM Observability And Eval Platforms

## Direct-Read Scope

Direct-read pass over current official docs for Langfuse, Arize Phoenix, TruLens, and DeepEval. This note stores original synthesis only; it does not copy platform examples, code, traces, prompts, or long excerpts.

Current-doc check on 2026-05-18: Langfuse still presents tracing, prompt management, evaluation, production traces, datasets, experiments, user feedback, annotation queues, custom scores, cost, and latency as one lifecycle. Phoenix still frames traces as OpenTelemetry/OpenInference-backed records for model calls, retrieval, tools, custom logic, evaluations, prompt iteration, datasets, experiments, span replay, and human labels. TruLens still emphasizes component-level agent/RAG evaluation over retrieved context, tool calls, plans, groundedness, context relevance, answer relevance, safety, sentiment, fairness, and trace-level regressions. DeepEval still frames test cases, datasets, metrics, traces, span-level scores, agent/RAG/MCP/conversational/safety/multimodal metrics, and local-first test execution as the evaluation harness.

## Source Signals

Langfuse frames production LLM operations as one connected lifecycle: trace application runs, manage and version prompts, run offline experiments against datasets, run online evals on live traces, collect user or human annotation feedback, and compare quality, latency, and cost by prompt or route version.

Phoenix emphasizes an OpenTelemetry/OpenInference trace spine. Its workflow starts from traces that capture model calls, retrieval, tools, and custom logic, then attaches evaluations, prompt experiments, datasets, span replay, and side-by-side comparisons so changes can be tested on the same inputs before rollout.

TruLens focuses on component-level evaluation of agent and RAG execution flow. Its useful production signal is that evals should target retrieved context, tool calls, plans, answer relevance, groundedness, harmfulness, sentiment, fairness, and other route-specific metrics, not just final answer quality.

DeepEval contributes the test-harness perspective: end-to-end checks are useful for simple or black-box routes, while component-level trace/span evals are better for agents, tool workflows, MCP-style systems, retrievers, generators, and planners. Its metric guidance also reinforces a small, explicit metric set rather than an oversized dashboard.

## Canon Lessons

- Treat observability and evaluation as one workflow. A trace without scores does not guide releases; a score without span context does not explain failures.
- Use provider-neutral traces as the common substrate, then attach platform-specific views, experiments, datasets, prompt versions, and feedback.
- Evaluate at the smallest meaningful component: retriever, reranker, prompt assembly, tool choice, tool arguments, planner step, generator, final answer, and human handoff.
- Separate offline datasets and experiments from online monitoring. Offline evals compare candidate changes under controlled inputs; online evals sample production traces and feed new failures back into datasets.
- Version prompts and routes together. Prompt performance is not a property of a string alone; it depends on model, parameters, retrieval snapshot, tools, schema, safety policy, and route graph.
- Human feedback is typed data, not a note in a transcript. Feedback needs annotator class, target trace/span, value type, rubric, dataset-promotion state, and retention policy.
- Keep evaluator definitions governed. LLM judges, heuristic scorers, code checks, and human rubrics need owners, versions, input contracts, output keys, calibration evidence, and change history.
- Limit production scorecards to a small number of release-relevant metrics. Extra metrics can remain diagnostic, but release gates should name what can block promotion.

## Agent Studio Design Implications

Agent Studio should expose a trace-to-eval loop rather than separate "logs" and "evals" products. The source ledger, route registry, prompt registry, eval datasets, annotation queue, and release gate should all point at the same run/span IDs.

For Agent Studio, the durable unit is not just a trace. It is:

- trace and span tree;
- route release and prompt version;
- retrieval/source snapshot;
- evaluator version;
- dataset or live-sampling rule;
- score plus compact rationale summary;
- human feedback or override;
- promotion, rollback, or dataset-backfill decision.

This is especially important for multi-agent content routes. A polished final post can hide a bad source selection, over-broad retrieval, wrong tool call, stale prompt version, or unsafe handoff. Span-level evals make those failures visible before route promotion.

## Datastore Additions

- `observability_project_record`: workspace, environment, owner, retention class, redaction policy, trace-sampling policy, and linked route set.
- `trace_score_record`: trace/span ref, evaluator ref, score key, value type, value, rationale summary, threshold, calibration status, and promotion impact.
- `eval_dataset_example_record`: dataset ref, input artifact refs, expected behavior, forbidden behavior, source snapshot refs, risk tags, generator/reviewer provenance, and lifecycle status.
- `prompt_experiment_record`: baseline prompt version, candidate prompt version, route release, dataset, experiment run, evaluator set, metric deltas, regression slices, decision, and rollback target.
- `component_eval_target`: route component type, span selector, required inputs, allowed metrics, failure taxonomy, and release-blocking flag.
- `trace_export_policy`: target platform, exported fields, redaction policy, sampling policy, retention period, privacy review, and replay eligibility.
- `annotation_queue_item`: trace/span ref, rubric ref, annotator class, priority, assignment state, label output, disagreement status, and dataset-promotion decision.
- `observability_eval_loop_gate`: promotion gate proving trace capture, span-level scoring, evaluator governance, prompt experiments, datasets, online evals, annotation queues, export/privacy policy, and release decisions are bound into one operational loop.

## Observability Eval Loop Gate

`observability_eval_loop_gate` is the promotion gate for routes whose quality, safety, cost, latency, or agent behavior depends on trace/eval feedback. It ensures observability is release evidence, not a dashboard that engineers inspect after regressions escape.

Required evidence:

- `gate_id`, `route_id`, `candidate_release_id`, `observability_project_ref`, `route_release_ref`, `prompt_version_refs`, `model_provider_refs`, `retrieval_source_snapshot_refs`, `tool_or_agent_graph_refs`, and `environment`;
- `trace_schema_ref`, `trace_sampling_policy_ref`, `required_span_taxonomy`, `component_eval_target_refs`, `trace_span_coverage`, and `missing_span_exceptions`;
- `evaluator_registry_refs`, `metric_contract_refs`, `score_key_policy`, `threshold_policy_refs`, `calibration_refs`, and `judge_model_or_code_refs`;
- `offline_dataset_refs`, `prompt_experiment_refs`, `baseline_candidate_comparison_refs`, `regression_slice_refs`, and `same_input_replay_refs`;
- `online_eval_rule_refs`, `live_sampling_refs`, `anomaly_or_alert_policy_refs`, `dataset_backfill_policy_ref`, and `incident_feedback_refs`;
- `annotation_queue_refs`, `rubric_refs`, `annotator_class_refs`, `disagreement_policy_ref`, `reviewer_override_policy_ref`, and `dataset_promotion_refs`;
- `cost_latency_score_refs`, `safety_score_refs`, `rag_or_agent_metric_refs`, `multimodal_metric_refs`, and `mcp_or_tool_metric_refs` when those surfaces are in scope;
- `trace_export_policy_ref`, `redaction_policy_ref`, `retention_policy_ref`, `privacy_review_ref`, `self_hosted_or_saas_boundary_ref`, `rollback_target_ref`, `decision`, and `reviewed_at`.

Do not promote a route when:

- traces omit retrieval, tool, agent, prompt, model, or output spans needed to diagnose the release risk;
- final-answer scores are present but component/span failures are invisible;
- evaluator prompts, code, judge models, thresholds, or calibration datasets are unversioned;
- online evals sample production traces but do not backfill datasets, incidents, or route-change proposals;
- human feedback lacks rubric, annotator class, disagreement handling, retention policy, or dataset-promotion status;
- prompt experiments compare different inputs, source snapshots, tools, or route graphs without recording the confound;
- trace export sends private source content, user data, prompts, files, or tool outputs beyond the approved boundary.

## Open Caveats

These platforms move quickly. Implementation should version-pin API contracts, SDK behavior, OpenTelemetry/OpenInference semantic conventions, and hosted-versus-self-hosted retention guarantees before migrations are written.
