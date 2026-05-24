---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/
  - https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/context_precision/
  - https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/context_recall/
  - https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/faithfulness/
  - https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/agents/
  - https://docs.langchain.com/langsmith/evaluation-concepts
  - https://docs.langchain.com/langsmith/evaluation-types
  - https://docs.langchain.com/langsmith/evaluate-rag-tutorial
  - https://docs.langchain.com/langsmith/evaluators
  - https://docs.langchain.com/langsmith/attach-user-feedback
related:
  - "[[../../03-patterns/evaluation/retrieval-eval-templates]]"
  - "[[../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../03-patterns/retrieval/reranking-search-kg-patterns]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Ragas And LangSmith RAG / Agent Evals

## Scope

Direct-read synthesis from current official Ragas metric docs and LangSmith evaluation, RAG-evaluation, evaluator-management, evaluation-type, and feedback docs. This note records original Agent Studio design implications only. It does not store copied examples, raw traces, or long source excerpts.

## Core Reading

Ragas is useful as a metric taxonomy for separating RAG quality into retrieval quality, answer support, and agent/tool behavior. LangSmith is useful as an operating workflow for binding datasets, application runs, evaluator outputs, traces, online evaluation, human annotation, and user feedback into one improvement loop.

Agent Studio should combine these lessons as a contract:

- metric definitions must name the layer they judge;
- a metric result must be tied to the route version, source snapshot, trace, and evaluator version;
- RAG scores should not be treated as generic "answer quality" scores;
- agent scores should separate tool-path correctness from final-goal success;
- production feedback should become curated eval cases, not just dashboard telemetry.

## RAG Metric Boundaries

Context precision tests whether relevant retrieved contexts are ranked above irrelevant contexts. It is a ranking-quality signal and should be read with top-k, candidate-universe, reference policy, and reranker policy. It can look good while recall is poor if the system retrieved a small clean set but missed necessary evidence.

Context recall tests whether required information was retrieved. It is a coverage signal and needs a reference answer, reference contexts, or stable context IDs. For Agent Studio, ID-based recall is especially important because the vault already has source IDs, note IDs, chunk IDs, and graph IDs; using these avoids storing private source text inside eval records.

Faithfulness tests whether response claims are supported by retrieved context. It belongs after retrieval and answer generation, not before. A route can have strong retrieval recall and still fail faithfulness if the generator adds unsupported dates, product details, recommendations, or policy claims.

Response relevance, groundedness, factual correctness, and semantic similarity are complementary signals, but none should hide the precision/recall/faithfulness split. Agent Studio should display these as a metric vector.

## Agent And Tool Metrics

Tool-call accuracy is strict: it fits cases where exact tool names, arguments, and order matter. Tool-call F1 is softer: it catches over-calling and under-calling without requiring perfect path identity. Agent-goal accuracy is outcome-oriented and fits tasks where multiple valid tool paths can reach the same correct final state.

This creates a useful release rule:

- strict tool-call accuracy for side-effecting, security-sensitive, or workflow-order-dependent routes;
- tool-call F1 for onboarding, regression triage, and routes with partial-credit repair;
- goal accuracy for user-outcome tasks where internal path variety is acceptable;
- trajectory review whenever a correct-looking final answer could hide unsafe or wasteful behavior.

## Offline, Online, And Feedback Loops

LangSmith separates offline evaluations over datasets from online evaluations over production runs and threads. Offline evaluations need curated examples, reference outputs where possible, experiment comparisons, and evaluator outputs. Online evaluations inspect production traces without gold answers and are better for anomaly detection, degradation monitoring, and surfacing new edge cases.

Agent Studio should therefore make eval lifecycle explicit:

1. build or import a dataset from source-backed cases;
2. run route versions on the same dataset;
3. store experiment outputs, evaluator scores, and execution traces;
4. compare baseline and candidate by slice, not just mean score;
5. sample failed or anomalous production traces into annotation queues;
6. convert approved feedback into new regression cases.

Feedback should attach to the relevant trace span when possible. For RAG routes, a user or reviewer may need to critique retrieval, reranking, graph traversal, answer assembly, or citation rendering separately. Span-level feedback prevents one broad thumbs-down from becoming unusable training or eval data.

## Evaluator Governance

Workspace-level evaluators are convenient, but shared evaluators become policy objects. Agent Studio should version evaluator prompts/code, calibration sets, expected input shape, output key, threshold, and attached resources. Changing a shared evaluator can change many route gates at once, so evaluator edits need release notes and backtesting against prior traces.

Use deterministic code evaluators where the assertion is structural, such as JSON validity, required fields, tool-name allowlists, citation ID existence, or no raw-text leakage. Use LLM judges where semantic judgment is needed, and calibrate them against human annotations before they block release.

## Current-Source Cross-Check

The current Ragas metric docs still preserve the core separation Agent Studio needs: context precision is a ranking signal, context recall is required-evidence coverage, ID-based precision/recall avoid copying source text into eval data, faithfulness checks response claims against retrieved context, and agent metrics distinguish strict tool-call correctness, F1-style tool-call coverage, and binary goal completion.

The current LangSmith evaluation docs still support the operating model: offline evaluations run over datasets/examples with references where available, online evaluations run over production runs/threads without gold references, evaluators are workspace-level resources, and feedback can attach to child spans such as retrieval or generation. That makes the source canon-ready for the Agent Studio trace-to-eval and route-release layer.

## Canon Decision

Agent Studio should treat RAG and agent evaluation as a route-release gate, not a dashboard. A RAG/agent route is not promotable unless the route release binds metric contracts, dataset or production-trace selectors, evaluator versions, trace/span coverage, precision/recall/faithfulness scorecards, tool-path and goal-outcome evidence, failure-slice regressions, reviewer override policy, and rollback conditions.

The release gate should fail closed when a route has only aggregate answer quality, only whole-run thumbs feedback, or only final-goal success. Retrieval, context packing, grounding, tool trajectory, and final outcome can each fail independently.

## Agent Studio Datastore Implications

Add or strengthen these objects:

- `rag_eval_metric_contract`: metric name, evaluated layer, required inputs, reference policy, scorer type, evaluator version, threshold, calibration status, and route surfaces covered.
- `rag_eval_result`: metric contract, route version, source snapshot, eval case, trace ref, score/value, concise rationale summary, failure category, and reviewer override.
- `context_precision_result`: retrieved context IDs, relevance labels, ranking cutoff, rank movement, false positives, and reranker/fusion policy.
- `context_recall_result`: expected source/context IDs, retrieved IDs, missing required evidence, reference source, and coverage severity.
- `faithfulness_claim_check`: response claim ID, retrieved context refs, support status, contradiction status, unsupported status, and mitigation.
- `agent_tool_metric_result`: expected tool calls, observed tool calls, strict-match score, F1-style score, extra/missing/wrong-argument categories, and side-effect risk.
- `agent_goal_metric_result`: goal definition, allowed paths, outcome evidence, final-state score, and residual risk.
- `trace_feedback_annotation`: trace/span ref, annotator class, feedback key, value/score, comment summary, linked eval case, dataset-promotion status, and retention policy.
- `evaluator_registry_record`: evaluator owner, type, prompt/code artifact, input contract, output key, calibration data, attached resources, and change history.
- `online_eval_rule`: production run/thread selector, evaluator refs, anomaly rule, sampling policy, action policy, and dataset-backfill policy.
- `rag_agent_eval_release_gate`: route release, metric contracts, eval dataset or online selector, evaluator versions, trace/span coverage, baseline/candidate comparison, failure slices, cost/latency thresholds, reviewer override policy, and rollback condition.

## Agent Studio Design Implications

- The eval UI should show metric families by layer: retrieval, context packing, answer grounding, tool trajectory, goal completion, safety, latency, and cost.
- RAG scorecards should force precision, recall, and faithfulness to remain separate columns.
- Agent scorecards should show tool-path and goal-outcome evidence side by side.
- Trace viewer feedback should support span-level annotation, not only whole-run ratings.
- Dataset curation should preserve where a case came from: expert-authored, source-backed, production trace, synthetic, or user report.
- Promotion gates should bind evaluator versions to route versions so a later evaluator change does not silently rewrite historical release evidence.

## Follow-Up Queue

1. Add concrete eval-case examples for Agent Studio source recall, citation faithfulness, and tool trajectory without storing raw source excerpts.
2. Cross-check evaluator registry requirements against OpenAI graders and Vertex AI evaluation docs.
3. Add route-change checklist fields for evaluator-version diffs and online-to-offline dataset promotion.
