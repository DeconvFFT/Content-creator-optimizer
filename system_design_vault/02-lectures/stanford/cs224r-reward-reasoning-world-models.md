---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_public
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://cs224r.stanford.edu/
  - https://cs224r.stanford.edu/slides/08_cs224r_reward_learning_2026.pdf
  - https://cs224r.stanford.edu/slides/10_cs224r_rl_for_llms_reasoning_2026.pdf
  - https://cs224r.stanford.edu/slides/11_cs224r_mbrl_2026.pdf
  - https://cs224r.stanford.edu/slides/12_cs224r_mtrl_gcrl_2026.pdf
related:
  - "[[../../03-patterns/alignment/preference-alignment-systems-canon]]"
  - "[[../../03-patterns/agent-systems/agent-route-architecture-canon]]"
  - "[[../../03-patterns/transformer-systems/cs25-transformer-systems-canon]]"
  - "[[../../04-agent-studio-implications/Capacity Estimation - Adaptation and Serving Decisions]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
  - "[[cs224r-preference-optimization-rlhf-dpo]]"
---

# CS224R - Reward Learning, Reasoning, And World Models

## Reading Scope

Direct-read pass over the official Stanford CS224R Spring 2026 course page and public slides for Reward Learning, RL for LLMs: Reasoning, Model-Based RL, and Multi-Task / Goal-Conditioned RL. Current-source check on 2026-05-18 verified the course timeline and public slide URLs. The Model-Based RL slide deck was re-read in this pass to deepen the Agent Studio world-model planning contract. This note uses official Stanford course material only. It does not claim Canvas video coverage, transcript-level video ingestion, raw slide storage, or copied derivations.

## Core Pattern

CS224R adds four design lessons that are directly relevant to Agent Studio:

1. reward and task specification are hard, and proxy rewards are exploitable;
2. reasoning quality increasingly depends on test-time compute, not only model weights;
3. learned dynamics/world models are useful for planning but unsafe when data coverage or model uncertainty is weak;
4. generalist agents need explicit task conditioning, not vague "do everything" routing.

For Agent Studio, these are not training-only ideas. They become route-release fields: what objective is being optimized, how much inference/search budget is allowed, what simulator or state model is trusted, and which task distribution a route is expected to cover.

## Reward Specification Is A First-Class Object

The reward-learning lecture frames reward as a task-specification problem. Direct imitation can copy actions without understanding outcomes; classifiers or reward models can encode goals; preference feedback can compare rollouts or responses. The production warning is that anything optimized hard enough can exploit blind spots in the reward signal.

Agent Studio should therefore separate:

- user/product objective;
- observable success proxy;
- learned reward or judge;
- human preference signal;
- verifier result;
- source-grounding requirement;
- style/platform preference;
- safety/rights constraint.

Those signals should not be collapsed into one score. A source-backed educational artifact can score well on style and still fail grounding. A generated code result can pass tests and still leak source text. A long reasoning trace can look convincing and still exceed cost or safety budget.

## Test-Time Compute Is A Route Budget

The reasoning lecture treats inference-time search, sampling, consensus, and long-horizon scaffolding as a separate scaling dimension. This matters for Agent Studio because route quality may improve by spending more compute at run time: best-of-N drafts, verifier loops, critic/rewrite cycles, tool-use planning, long-running research agents, or multi-agent parallel search.

The design implication is not "always spend more." Test-time compute must be governed by route:

- maximum samples, branches, revisions, verifier calls, and wall-clock duration;
- whether search is serial chain-of-thought, parallel candidate generation, consensus, or planner/evaluator loop;
- marginal gain curve against cost and latency;
- safety and preparedness eval budget that matches the route's possible deployment budget;
- stop policy for long-running or persistent agents.

Agent Studio should evaluate score versus compute and time. A route that passes at a tiny eval budget may fail once given more time, tools, context, or parallel branches. Conversely, a high-quality research route may be acceptable only when explicitly marked as slow, expensive, and reviewer-gated.

## World Models Need Coverage And Uncertainty Gates

The model-based RL lecture makes learned simulators/world models attractive because they can generate data and enable planning. It also makes the failure mode clear: planning inside an inaccurate model can optimize model error. Data coverage, domain difficulty, short rollouts, ensembles, value functions, and uncertainty controls determine whether the model is useful.

Agent Studio uses "world models" in a product sense whenever it predicts consequences before acting: artifact dependency graphs, source freshness effects, publishing consequences, workflow state transitions, user-memory changes, or social post rollout risk.

Required gates:

- state representation is explicit;
- transition model source and training/evidence coverage are recorded;
- uncertainty or disagreement is measured;
- simulated rollouts are short enough or corrected by real evidence;
- plans that depend on model predictions get human or verifier review before side effects.

## Model-Based Planning Deepening

The Model-Based RL lecture splits world-model use into two distinct modes: synthetic data generation and test-time planning. Agent Studio needs the same split. A route can use a learned or symbolic transition model to generate rehearsal traces, but that is not the same as using the model to choose a live action with external side effects.

For synthetic route rehearsal, the main risk is distribution shift. If the model is trained on traces from one policy and then generates states for a changed policy, the route can optimize artifacts that look good only inside the model. Agent Studio should therefore tie every simulated rollout to the real trace distribution it started from, the candidate route/policy that generated it, and the maximum rollout depth. Short partial rollouts from real states are usually safer than long imagined trajectories from arbitrary initial states.

For test-time planning, the route samples or proposes candidate action sequences, predicts their consequences, scores the imagined outcomes, and executes an action. The lecture's operational lesson is that this planning process is itself the policy. Agent Studio should store it as such: candidate actions, rollout horizon, scoring function, uncertainty/disagreement, selected action, whether only the first action was executed, and when replanning occurred.

Long-horizon planning needs an additional value estimate or terminal evaluator. Without that, a short horizon can become myopic. With it, the route takes on a new model/evaluator dependency that can be wrong. Agent Studio should treat terminal value functions, judge models, heuristic evaluators, and long-horizon route scorers as release-managed artifacts.

Practical Agent Studio cases:

- source ingestion: simulate whether reading another source is likely to change a design decision before spending time;
- publishing: predict downstream approval, policy, rights, and platform risks before scheduling a post;
- long-running agents: use receding-horizon planning, execute one safe step, observe, then replan;
- retrieval repair: use short imagined retrieval/rerank changes from real query states before mutating indexes;
- memory promotion: simulate affected routes before writing durable cross-thread memory.

The default guardrail is conservative: learned world models can recommend, rehearse, or prioritize, but they should not authorize irreversible side effects without real observations, deterministic checks, or human approval.

## Generalist Agents Need Task Conditioning

The multi-task and goal-conditioned RL lecture frames a task as a distribution over state spaces, action spaces, dynamics, and rewards. Generalist systems can share learning across tasks, but only if the task condition is explicit and data sharing is controlled.

Agent Studio should not ship one vague "agent" route for writing, retrieval, critique, publishing, code execution, and governance. It should condition route behavior on a task record:

- task family and user goal;
- allowed sources, tools, side effects, and reward/eval signals;
- expected artifact type;
- task-specific constraints and blocked actions;
- route memory eligibility;
- feedback and outcome metrics for that task family.

Task conditioning also matters for retrieval and feedback learning. A thumbs-up on a concise LinkedIn caption should not train the same preference as a thumbs-up on a source-backed architecture memo. Feedback is only reusable when task context, audience, source requirements, and success criteria match.

## Datastore Additions

| Object | Purpose | Key fields |
|---|---|---|
| `reward_specification_record` | Route-level objective decomposition before optimization or feedback learning | `reward_spec_id`, `route_id`, `user_objective`, `success_proxy_refs`, `preference_signal_refs`, `verifier_refs`, `grounding_requirement_refs`, `style_signal_refs`, `safety_constraint_refs`, `known_blind_spots`, `status` |
| `reward_signal_event` | One human, model, verifier, metric, or product feedback signal | `reward_signal_id`, `run_id`, `route_id`, `task_condition_id`, `signal_type`, `source`, `score_or_label`, `reason_ref`, `artifact_refs`, `rater_or_judge_ref`, `created_at` |
| `reward_model_blind_spot` | Known exploit or coverage gap in a reward/judge/verifier | `blind_spot_id`, `reward_model_ref`, `failure_mode`, `trigger_examples_ref`, `affected_task_conditions`, `mitigation_refs`, `release_blocking`, `status` |
| `test_time_compute_experiment` | Score/cost/latency curve for a reasoning route | `experiment_id`, `route_id`, `strategy`, `sample_or_branch_counts`, `verifier_budget`, `wall_clock_budget`, `score_curve_ref`, `cost_curve_ref`, `latency_curve_ref`, `promotion_decision` |
| `long_horizon_agent_eval` | Evaluation at realistic time/tool/context budgets | `eval_id`, `route_id`, `time_budget`, `tool_budget`, `context_budget`, `parallelism_budget`, `capability_or_safety_target`, `trace_refs`, `decision_status` |
| `world_model_policy` | Governed use of learned or symbolic transition models for planning | `world_model_policy_id`, `route_id`, `state_schema_ref`, `transition_model_ref`, `coverage_evidence_refs`, `uncertainty_policy`, `max_rollout_depth`, `human_review_requirement`, `status` |
| `world_model_training_trace_set` | Real traces used to fit or validate a route transition model | `trace_set_id`, `route_id`, `source_policy_ref`, `state_action_next_state_refs`, `coverage_summary`, `known_missing_regions`, `created_at`, `status` |
| `simulated_rollout_record` | Synthetic rollout generated by a world model | `rollout_id`, `route_id`, `world_model_policy_id`, `start_state_ref`, `candidate_action_sequence`, `rollout_depth`, `predicted_state_refs`, `predicted_reward_or_score_refs`, `uncertainty_summary`, `used_for_training_or_planning`, `created_at` |
| `model_error_budget` | Allowed prediction error and uncertainty bounds for planning use | `error_budget_id`, `route_id`, `transition_model_ref`, `validation_slice_refs`, `short_horizon_error`, `long_horizon_error`, `uncertainty_threshold`, `blocked_action_classes`, `status` |
| `receding_horizon_planning_trace` | Test-time plan-execute-observe-replan evidence | `planning_trace_id`, `run_id`, `route_id`, `candidate_rollout_refs`, `horizon`, `terminal_value_ref`, `selected_first_action_ref`, `observation_after_action_ref`, `replan_decision`, `stop_reason` |
| `terminal_value_estimator_record` | Value or judge used beyond the explicit rollout horizon | `value_estimator_id`, `route_id`, `estimator_type`, `training_or_calibration_refs`, `applies_to_state_class`, `known_biases`, `fallback_policy`, `status` |
| `task_condition_record` | Explicit task identity for generalist route behavior and feedback reuse | `task_condition_id`, `route_id`, `task_family`, `goal_ref`, `state_space_ref`, `action_space_ref`, `reward_spec_id`, `allowed_tool_refs`, `source_policy_ref`, `artifact_type`, `memory_policy_ref`, `status` |
| `reward_reasoning_world_model_release_gate` | Promotion gate for routes that learn from reward signals, spend reasoning compute, plan through a world model, or reuse feedback across task families | `gate_id`, `route_id`, `candidate_release_id`, `task_condition_ref`, `reward_specification_ref`, `reward_signal_refs`, `reward_type_separation_policy_ref`, `reward_blind_spot_refs`, `verifier_scope_refs`, `test_time_compute_policy_ref`, `test_time_compute_experiment_refs`, `long_horizon_eval_refs`, `world_model_policy_ref`, `state_schema_ref`, `transition_model_ref`, `coverage_evidence_refs`, `uncertainty_policy_ref`, `max_rollout_depth`, `simulation_exploit_check_refs`, `feedback_reuse_boundary_ref`, `allowed_tool_refs`, `source_policy_ref`, `memory_policy_ref`, `side_effect_policy_ref`, `human_review_requirement`, `fallback_route_ref`, `rollback_target_ref`, `decision`, `reviewed_at` |

## Release Gate Contract

`reward_reasoning_world_model_release_gate` is required before a route can optimize against a learned reward, raise test-time compute, plan side effects using a predicted state transition, or reuse feedback across task families.

The gate should reject promotion unless:

- the task condition names the task family, goal, state/action surfaces, allowed tools, source policy, artifact type, and memory policy;
- the reward specification separates product objective, proxy metric, human preference, verifier, grounding, style, safety, and operational signals;
- known reward/judge/verifier blind spots are linked to mitigations and release-blocking slices;
- test-time compute is governed by sample/branch/revision/verifier/wall-clock/cost limits and measured against score, latency, and cost curves;
- long-horizon evals run at the same tool, time, context, and parallelism budgets the route can use after release;
- any world model or simulator declares its state schema, transition model, evidence coverage, uncertainty/disagreement policy, maximum rollout depth, and simulation-to-real validation;
- synthetic rollouts record start states from real traces, rollout depth, predicted outcomes, uncertainty, and whether they are used for training, rehearsal, or live planning;
- receding-horizon planning records candidate rollouts, terminal-value estimator, selected first action, observation after execution, and replan decision;
- model error budgets define which action classes are blocked when short-horizon error, long-horizon error, or ensemble disagreement is too high;
- plans depending on predicted state transitions have human review or deterministic verifier review before irreversible side effects;
- feedback reuse is limited to compatible task conditions rather than globally updating a vague generalist agent route;
- fallback and rollback targets are named before the new route can affect production artifacts, memory, publishing, or source indexes.

## Agent Studio Decision

Agent Studio should treat rewards, reasoning compute, world models, and task conditioning as release artifacts. A route cannot safely learn from feedback, spend large inference budgets, plan side effects, or generalize across task families unless these objects are explicit in the ledger, tied to eval evidence, and approved through `reward_reasoning_world_model_release_gate`.
