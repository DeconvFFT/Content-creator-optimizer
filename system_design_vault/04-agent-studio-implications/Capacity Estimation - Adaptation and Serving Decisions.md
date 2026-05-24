---
type: agent-studio-implication
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - [[../02-lectures/stanford/cs324-large-language-models]]
  - [[../02-lectures/stanford/cs25-future-of-pretraining]]
  - [[../02-lectures/stanford/cs25-production-inference]]
  - [[../02-lectures/stanford/cs349d-ai-inference-infrastructure]]
  - [[../02-lectures/stanford/cs224r-reward-reasoning-world-models]]
  - https://web.stanford.edu/class/cs25/index.html
  - [[../02-lectures/stanford/cs25-parameters-context-generalization]]
  - https://nanotron-ultrascale-playbook.static.hf.space/
  - https://github.com/huggingface/nanotron
  - https://cs336.stanford.edu/
  - https://docs.vllm.ai/en/stable/
  - https://docs.vllm.ai/en/stable/usage/metrics/
  - https://docs.nvidia.com/tensorrt-llm/
  - [[../01-sources/official-open/nvidia-dynamo-disaggregated-inference]]
  - https://docs.ray.io/en/latest/serve/llm/index.html
  - https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/model_analyzer/README.html
  - [[../02-books/deep-learning-book/generalization-optimization-sequence-systems]]
  - [[../02-books/math-for-ml/chapters/7-continuous-optimization-route-tuning]]
  - [[../02-books/probabilistic-ml-advanced/approximate-inference-shift-interpretability]]
related:
  - "[[02-lectures/stanford/cs25-ultra-scale-training]]"
  - "[[../03-patterns/transformer-systems/cs25-transformer-systems-canon]]"
  - "[[01-sources/official-open/inference-engineering-cross-check]]"
  - "[[03-patterns/inference/realtime-and-inference-patterns]]"
  - "[[04-agent-studio-implications/LLD - Agent Studio System Design]]"
  - "[[04-agent-studio-implications/Route Change Proposal Template]]"
---

# Capacity Estimation - Adaptation And Serving Decisions

## Purpose

Before Agent Studio decides to fine-tune, distill, extend context length, self-host, quantize, or add a dedicated serving lane, it needs a capacity estimate. This template prevents vague "we should train a model" decisions when retrieval, prompt design, eval data, routing, or source-ledger fixes would solve the problem with lower risk.

This is original synthesis from the Stanford CS25 ultra-scale training source cluster, CS336/inference sources, and official serving/runtime docs. It stores decision structure only, not source excerpts.

## Decision Ladder

Use the lowest-risk intervention that fixes the measured failure:

| Symptom | First intervention | Escalate only if |
|---|---|---|
| Missing or stale facts | Add/update source, chunking, retrieval, metadata, graph links | Retrieval evals show the source exists but model cannot use it reliably |
| Weak grounding or citations | Improve retrieval trace, context packing, citation checks, claim verification | Grounded context is correct but generation repeatedly fails |
| Bad format or style | Prompt/template change, examples, output schema, critique agent | Prompt route is saturated and evals show stable learnable preference |
| Domain terminology miss | Glossary, source ledger, examples, reranking, small eval slice | Repeated failures persist with correct retrieved evidence |
| Latency/cost issue | Route split, caching, batching, quantization, provider choice | Provider/shared API cannot meet measured SLO or cost envelope |
| Repeated task skill gap | Tooling, workflow graph, demonstrations, SFT candidate | The task requires behavior not recoverable from tools/retrieval/prompting |
| Privacy or deployment control | Dedicated provider config or self-hosted route | Compliance or data boundary cannot be met by managed routes |
| Weak reasoning under fixed answer budget | Add verifier, best-of-N, critique/rewrite, or planner/evaluator loop with bounded test-time compute | Score-vs-cost curve proves quality gains and long-horizon safety evals still pass |
| Planning side effects | Add explicit state model, transition checks, and human approval | World-model policy has coverage, uncertainty, and exploit checks |

## Required Estimate

Every adaptation or serving proposal should include:

| Field | Meaning |
|---|---|
| `problem_statement` | Exact production failure or capability gap |
| `evidence` | Eval failures, traces, user feedback, or cost/latency measurements |
| `candidate_intervention` | Retrieval, prompt, tool, SFT, preference tuning, distillation, quantization, self-hosting, or provider switch |
| `baseline_route` | Current model/provider/retriever/runtime profile |
| `expected_gain` | Quality, latency, cost, privacy, control, or reliability improvement |
| `data_requirement` | Source records, eval cases, preference pairs, demonstrations, or training examples needed |
| `compute_requirement` | Training, fine-tuning, indexing, evaluation, or serving capacity |
| `serving_requirement` | TTFT, TPOT, throughput, concurrency, context length, region, and fallback |
| `risk` | Quality regression, data leakage, stale memory, latency variance, cost overrun, rollback complexity |
| `promotion_gate` | Evals and telemetry required before release |
| `rollback_plan` | How to return to the previous route |

## Training And Adaptation Checklist

Use this when considering SFT, preference tuning, distillation, or long-context adaptation:

- Is the failure caused by missing knowledge that should remain external and updateable?
- Are source provenance and rights clear for any training examples?
- Is there a held-out eval set before generating training data?
- Does the model need new behavior, or only better context/retrieval?
- What sequence length and batch-token target are required?
- What memory is needed for parameters, gradients, optimizer state, and activations?
- What precision, recomputation, and sharding assumptions are being made?
- What parallelism strategy is required: data, tensor, pipeline, context, expert, or none?
- What checkpoint, resume, and artifact retention policy is required?
- What eval slice proves the adaptation helped without degrading grounding, safety, style, or latency?

Default answer: do not fine-tune for source freshness, citation support, or simple terminology coverage until retrieval and eval traces prove that lighter interventions failed.

CS324 tightens the default: do not adapt a model unless rights, contamination, source documentation, tokenizer impact, and lifecycle cost are explicit. A training or adaptation win is not useful if it depends on unclear source permission, eval leakage, unaudited private data, or an avoidable serving-cost increase.

Promote finetuning, adapters, prompt/prefix tuning, distillation, self-hosting, or model-objective changes only after a `model_adaptation_lifecycle_release_gate` proves observed behavior evidence, mechanism assumptions, dataset documentation, rights policy, contamination checks, tokenizer and tokenization impact, objective family, rejected simpler interventions, capacity estimate, lifecycle cost, serving impact, fallback, and rollback.

CS25 future-of-pretraining tightens the knowledge-placement default: do not move knowledge into weights when it needs freshness, citation, access control, or rights review. Treat retrieval capacity, source-ledger coverage, and reference-world evals as first-class alternatives to model adaptation.

Promote a route on pretraining capability only after a `pretraining_assumption_release_gate` proves the exact model/source assumption, data allocation rationale, retrieval budget, source-ledger coverage, reference-world evals, objective/data caveats, contamination and rights checks, simpler route interventions tried, reasoning-failure diagnosis, product-slice regressions, fallback, and rollback.

CS224R tightens the runtime-scaling default: if the failure is reasoning depth rather than knowledge or format, first measure test-time compute. A route may need more samples, verifier calls, parallel branches, or planning time, but those budgets are release artifacts with cost, latency, and safety implications.

CS224R model-based RL tightens the world-model default: a learned or symbolic model can generate rehearsal traces or support test-time planning, but those are separate release surfaces. Synthetic rollouts need start-state provenance, rollout depth, uncertainty, and model-error budgets. Live planning should be receding-horizon by default for risky side effects: execute one safe action, observe real state, then replan. Terminal value estimators can help long-horizon planning, but they add judge/value-model bias that must be evaluated before promotion.

## Capacity And Regularization Addendum

The Deep Learning foundation pass tightens capacity estimates: route capacity is not just model size. Effective capacity is shaped by the model, prompt, graph, tools, context size, data quality, optimization procedure, and regularization constraints.

Deep Learning Chapter 11 adds an operating rule: capacity changes should follow metric target, baseline, bottleneck diagnosis, and debug-fixture evidence. If a route cannot solve tiny deterministic cases or its highest-confidence mistakes reveal source/extraction/tool bugs, increasing model size or adding agents is premature.

Deep Learning Chapter 7 adds the regularization rule: a capacity increase is incomplete unless the route also states what transformations should leave the decision unchanged, which controls are hard constraints versus soft preferences, when tuning or self-revision stops, and which robustness perturbations or adversarial cases the route must survive.

Required additions:

| Field | Reason |
|---|---|
| `capacity_diagnosis_id` | Separates underfitting, overfitting, data defects, objective mismatch, optimization failure, retrieval failure, and software defects. |
| `regularization_policy_id` | Records route constraints such as source grounding, schemas, stop policy, tool limits, simplicity preference, invariance assumptions, component-sharing assumptions, and robustness perturbations. |
| `validation_reuse_record_id` | Prevents tuning prompts/routes repeatedly on the same eval cases while treating them as fresh release evidence. |
| `numerical_stability_record_id` | Captures score transforms, precision, clipping, invalid-value handling, and caveats for ranking/reward/confidence routes. |
| `long_context_memory_record_id` | Captures compression, truncation, explicit memory, retrieval strategy, and long-source eval coverage. |
| `rights_policy_record_id` | Confirms training/adaptation examples are allowed for the proposed use and publication surface. |
| `training_contamination_check_id` | Confirms held-out evals were not reused through prompts, retrieval, generated data, or previous route tuning. |
| `lifecycle_cost_record_id` | Records training/adaptation/serving cost, utilization, amortization caveats, and review cadence. |
| `knowledge_allocation_record_id` | Declares whether target knowledge belongs in weights, retrieval, graph memory, prompt examples, tools, or human policy. |
| `reference_world_record_id` | Names the source of truth for hallucination, grounding, or correctness evals. |
| `route_complexity_stage_id` | Shows that route complexity grew in measured stages with rollback at each stage. |
| `pretraining_assumption_release_gate_id` | Prevents vague pretraining or reasoning claims from reducing retrieval, verifier, citation, reviewer, or human-policy controls without product-slice evidence. |
| `capacity_optimization_release_gate_id` | Blocks model/route/context/memory/optimization complexity increases until bottleneck diagnosis, validation reuse, regularization, numerical stability, long-context memory, optimization diagnostics, simpler baseline, serving cost, fallback, and rollback are proven. |
| `methodology_release_gate_id` | Blocks route changes until product metric target, end-to-end baseline, bottleneck diagnosis, experiment search space, debug fixtures, worst-error review, held-out assessment, coverage/accuracy policy, fallback, and rollback are proven. |
| `route_optimization_release_gate_id` | Blocks optimizer-driven route changes until objective, constraints, sampled evidence, step policy, convergence diagnostics, tradeoff review, held-out assessment, fallback, and rollback are proven. |
| `optimization_constraint_record_id` | Declares source, safety, policy, latency, cost, privacy, or reviewer-capacity constraints that define the feasible route region. |
| `optimization_signal_batch_id` | Records the sampled eval/user/source evidence used for one optimizer step, including underrepresented slices and bias caveats. |
| `optimization_tradeoff_record_id` | Captures objective gain versus active or nearly active quality, cost, latency, safety, or review constraints. |
| `route_debug_fixture_id` | Keeps tiny deterministic source/retrieval/tool/artifact cases that must pass before blaming data or model capacity. |
| `worst_error_review_id` | Captures high-confidence failures, visible trace evidence, source/artifact examples, root-cause hypothesis, and fix status. |
| `serving_workload_profile_id` | Separates throughput, low-latency, bursty, realtime, media, and batch workloads before choosing runtime or hardware. |
| `inference_phase_measurement_id` | Breaks latency into prefill, decode, retrieval, rerank, tool, queue, cold-start, and end-to-end phases. |
| `serving_feature_compatibility_matrix_id` | Confirms batching, PagedAttention, context caching, chunked prefill, speculation, and disaggregation remain compatible for the route. |
| `serving_optimization_gate_id` | Records baseline, candidate serving feature, workload slice, performance delta, quality delta, compatibility result, rollback trigger, and promotion decision. |
| `test_time_compute_experiment_id` | Records score, cost, latency, sample/branch count, verifier budget, and promotion decision for reasoning routes. |
| `long_horizon_agent_eval_id` | Confirms route behavior at realistic time, tool, context, and parallelism budgets. |
| `world_model_policy_id` | Governs learned or symbolic transition models used for planning side effects. |
| `world_model_training_trace_set_id` | Records the real trace distribution used to fit or validate route transition models. |
| `simulated_rollout_record_id` | Stores synthetic rollout provenance, start state, horizon, predicted outcome, uncertainty, and intended use. |
| `model_error_budget_id` | Blocks world-model planning when short-horizon error, long-horizon error, or disagreement exceeds route tolerance. |
| `receding_horizon_planning_trace_id` | Captures candidate rollouts, selected first action, observation after execution, and replan decision. |
| `terminal_value_estimator_record_id` | Captures value/judge models used beyond explicit rollout horizon, including calibration and bias caveats. |
| `task_condition_record_id` | Prevents feedback or reward reuse across incompatible task families. |

The practical rule: if a route improves development examples but lacks a held-out assessment, regularization policy, and rollback trigger, it is not ready for promotion.

## Approximation And Shift Addendum

Murphy Advanced Topics tightens capacity decisions: a route estimate is often an approximation over uncertain state, not a direct measurement of truth. Capacity proposals should record the approximation method and the distribution-shift class they are expected to survive.

Required additions:

| Field | Reason |
|---|---|
| `approximate_inference_record_id` | Declares whether uncertainty comes from Laplace, variational inference, particles, samples, ensembles, bootstrap, surrogate model, or a point estimate. |
| `posterior_approximation_record_id` | Separates posterior belief about a route/source/model from the decision policy that acts on it. |
| `distribution_shift_record_id` | Labels covariate/domain, label/prior, concept/annotation, manifestation/conditional, or selection-bias risk. |
| `interpretability_review_id` | Records the explanation artifact and decision context when a route needs human inspection before promotion. |

If a route change is justified by "confidence", the proposal must say what confidence means, how it was approximated, whether it is calibrated, and where it is known to fail.

Promotion rule: a route that depends on approximate inference, posterior confidence, distribution-shift robustness, structured prediction, graph discovery, diversity selection, interpretability, or latent generative-process settings needs an `approximation_shift_release_gate`. The gate should prove approximation family, update mode, convergence or compute diagnostics, calibration or caveats, validity slices, shift-class coverage, graph review, diversity tradeoff, explanation fidelity, generative-process reproducibility, fallback, and rollback.

## Serving Checklist

Use this when considering a new model route, self-hosting, quantization, batching, cache strategy, or provider switch:

- What workload class is served: realtime voice, interactive critique, long synthesis, ingestion, reranking, eval, or backfill?
- What are the SLOs for TTFT, TPOT, end-to-end latency, error rate, and availability?
- What are expected input/output token distributions, not just max context?
- Is prefill or decode the bottleneck?
- What batching and queueing policy is allowed for this workload?
- What KV-cache, prefix-cache, or prompt-cache behavior is expected?
- What quantization or precision change is proposed, and what quality delta is acceptable?
- What concurrency and autoscaling policy is needed?
- What telemetry proves the route is healthy: queue depth, GPU/cache utilization, batch size, TTFT, TPOT, throughput, cost, errors?
- What fallback route is allowed when the serving profile degrades?

Budget admission is part of serving design, not a later finance report. After the capacity estimate identifies the bottleneck and feasible runtime shape, [[../03-patterns/inference/cost-latency-budget-control]] owns route-level workload class, usage budget, rate-limit headroom, cache scope, quota-aware retry, low-priority lane eligibility, fallback, and cost attribution before the route scales.

## Disaggregated Serving Addendum

NVIDIA Dynamo adds a stronger requirement for long-context and high-throughput routes: capacity estimates must say whether the bottleneck is prefill, decode, KV transfer, queueing, cold start, or cache miss behavior. Prefill/decode disaggregation and KV-aware routing are not generic speedups; they are topology changes that need route-level evidence.

Required additions:

| Field | Reason |
|---|---|
| `inference_topology_record_id` | Declares aggregated, disaggregated, multimodal EPD, or mixed topology before comparing performance. |
| `prefill_decode_lane_record_ids` | Separates prefill and decode worker capacity, queue, scale, and parallelism assumptions. |
| `kv_cache_policy_record_id` | Records cache key, overlap policy, memory tier, eviction, and safe reuse boundary. |
| `kv_routing_decision_refs` | Captures routing evidence and fallback behavior when cache-aware routing is used. |
| `cache_transfer_trace_refs` | Measures KV transfer timing and failure between prefill/decode workers without storing cache contents. |
| `llm_autoscaling_decision_refs` | Shows whether the planner scaled for TTFT, TPOT, throughput, queue pressure, or burst load. |
| `inference_fault_event_refs` | Captures cancellation, migration, rejection, worker failure, scale-down, or router recovery events. |
| `serving_topology_benchmark_id` | Compares aggregated versus disaggregated or cache-aware topologies on the actual workload slice. |

Do not promote a disaggregated or KV-aware serving route on aggregate latency alone. It must show the phase that improved, the phase that regressed, and whether fairness, quality, grounding, and cost remained inside the release contract.

## CS25 Systems Addendum

The CS25 transformer-systems canon tightens this template: capacity estimates must distinguish knowledge fixes, agent-environment fixes, architecture changes, and infrastructure changes.

Required additions:

| Field | Reason |
|---|---|
| `knowledge_memory_choice` | Separates parametric model memory from external source/index/graph memory. |
| `agent_environment_scope` | Declares the workspace state, tools, observations, approvals, and feedback available to the route. |
| `architecture_profile_id` | Captures whether the route is attention-only, SSM-like, hybrid, MoE, multimodal, embedding, reranker, or specialized runtime. |
| `source_recall_eval_required` | Prevents long-context or compressed-memory routes from bypassing citation/recall tests. |
| `workload_slice_measurements` | Forces latency, cost, recall, and quality to be measured by task class instead of averaged across unlike work. |

## Parameter Versus Context Addendum

The CS25 parameter/context generalization slice tightens adaptation decisions: learning through model weights and learning through retrieved or prompted context can produce different generalization behavior. Fine-tuning is therefore not a neutral storage choice for source knowledge.

Required additions:

| Field | Reason |
|---|---|
| `generalization_requirement` | Declares whether the route needs reversal, deduction, composition, extrapolation, source recall, style transfer, or workflow recovery. |
| `context_vs_weight_rationale` | Explains why knowledge belongs in weights, retrieved context, prompts, graph memory, skills, or human policy. |
| `latent_generalization_eval_id` | Links to evals that prove behavior transfers beyond seen examples. |
| `retrieval_as_memory_required` | Marks claims that must remain external, updateable, inspectable, and citeable. |

Promotion rule: a route that moves knowledge between weights, retrieval, graph memory, prompt examples, skills, tools, or human policy needs a `knowledge_allocation_release_gate`. The gate should prove knowledge subject, freshness, rights, citation need, volatility, chosen memory location, generalization requirement, context-versus-weight rationale, lighter interventions tried, latent generalization evals, retrieval-as-memory requirement, adaptation proposal, capacity estimate, serving impact, grounding/source-diversity/safety/style/latency/cost regressions, fallback, rollback, and human approval.

## Route Registry Fields

Add or preserve these fields in `route_registry_entries` and `serving_profiles`:

| Field | Reason |
|---|---|
| `architecture_class` | Dense, MoE, hybrid, SSM-like, multimodal, reranker, embedding, realtime |
| `adaptation_method` | Base, prompt-only, RAG, SFT, preference-tuned, distilled, quantized |
| `context_contract` | Target and max context, cache policy, source-context limits |
| `runtime_stack` | Managed provider, vLLM, TensorRT-LLM, Ray Serve, Triton, other |
| `parallelism_profile` | Tensor, pipeline, data, context, expert, replicas |
| `precision_profile` | BF16, FP16, FP8, INT8, INT4, mixed, unknown |
| `latency_profile` | TTFT, TPOT, p50/p95/p99 end-to-end latency by workload |
| `throughput_profile` | Tokens/sec, requests/sec, batch behavior, concurrency |
| `cost_profile` | Cost per request, cost per output token, idle cost, eval cost |
| `eval_gate_ids` | Required quality, grounding, safety, and regression suites |
| `rollback_route_id` | Last known good route |

## Promotion Gates

An adaptation or serving change can be promoted only when:

- the failure it targets is linked to eval cases or production traces;
- the baseline and candidate ran on the same eval slices;
- quality, grounding, safety, latency, and cost deltas are recorded separately;
- regression failures have owner decisions;
- the route has a rollback path;
- the source/retrieval index version used by the eval is recorded;
- human review approves any release-blocking tradeoff.

## Agent Studio Design Implications

- Capacity estimation should be a product workflow, not an engineering afterthought.
- The system should ask "retrieval, routing, prompt, tool, or model adaptation?" before any training work.
- Fine-tuning proposals should be blocked if the source-ledger or eval suite is too weak to prove improvement.
- Serving profiles must be workload-specific; one model route should not carry realtime voice, deep synthesis, and batch ingestion by default.
- Route quality and infrastructure telemetry need to join in the same release record.
- Long-context routes need special tests with book-length/source-heavy traces.

## Initial Implementation Path

1. Add a capacity-estimation checklist to [[Route Change Proposal Template]].
2. Require `serving_profile_id` and `eval_gate_ids` on every production route.
3. Add a "lighter intervention attempted" field before any fine-tuning proposal.
4. Create eval slices for long-context source reading, RAG citation validity, realtime latency, and batch ingestion throughput.
5. Promote only routes with measured deltas and rollback paths.
