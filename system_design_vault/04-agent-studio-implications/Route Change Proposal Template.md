---
type: agent-studio-implication
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - [[Capacity Estimation - Adaptation and Serving Decisions]]
  - [[../01-sources/official-open/openai-production-readiness]]
  - [[../03-patterns/evaluation/retrieval-eval-templates]]
  - [[../03-patterns/agent-systems/agent-route-architecture-canon]]
  - [[../01-sources/official-open/uber-prd-reviewer-agent]]
  - [[../01-sources/official-open/annotation-human-feedback-data-ops]]
  - [[../01-sources/official-open/feature-flags-experimentation-release-controls]]
  - [[Datastore Schema - Agent Studio Source and Route Ledger]]
  - [[LLD - Agent Studio System Design]]
related:
  - "[[Capacity Estimation - Adaptation and Serving Decisions]]"
  - "[[../03-patterns/evaluation/retrieval-eval-templates]]"
  - "[[Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Route Change Proposal Template

## Purpose

Agent Studio route changes should be reviewable artifacts. A route change can alter a prompt, model, provider, graph, retriever, reranker, tool policy, guardrail, eval grader, source snapshot, capacity profile, or serving runtime. Any of those can improve one slice while quietly damaging another.

This template turns route changes into versioned decisions with evidence, eval gates, capacity estimates, rollout conditions, rollback paths, and owner accountability.

## Proposal Header

| Field | Required content |
|---|---|
| `proposal_id` | Stable ID for the decision record |
| `proposal_type` | prompt, model, provider, graph, retriever, reranker, grader, guardrail, serving, source snapshot, or mixed |
| `owner` | Human or agent owner responsible for the change |
| `created_at` | Date created |
| `target_route_id` | Existing route being changed or new route candidate |
| `agent_justification` | Why this route needs agentic workflow control, or `not_agentic` with simpler route rationale |
| `deterministic_alternative` | Deterministic, retrieval-only, prompt-only, or single-agent alternative considered first |
| `task_decomposition_evidence` | Required for multi-agent routes; why the task is parallelizable or needs distinct specialist checks |
| `loop_stop_policy` | Required for debate, critique, search, or evolution loops; cost, latency, quality-gain, and review limits |
| `candidate_pool_policy` | Required when routes generate alternatives; how candidates, rankings, critiques, and rejected outputs are retained |
| `domain_safety_boundary` | What the route is not allowed to decide, publish, claim, or automate |
| `human_expert_gate` | Required approver role for safety-critical, source-critical, or expertise-heavy outputs |
| `feedback_origin_policy_id` | Required when the change learns from review data: independent human labels, edited suggestions, weak labels, active-learning batches, production feedback, and allowed reuse |
| `feature_flag_policy_id` | Required when the change introduces, modifies, removes, or depends on runtime flags: flag class, safe default, targeting, exposure logging, rollout/experiment plan, and cleanup due date |
| `baseline_release_id` | Last known good release |
| `candidate_release_id` | Proposed release bundle |
| `capacity_estimate_id` | Required for model/provider/runtime/fine-tuning/distillation/quantization changes |
| `provider_readiness_gate_id` | Required for provider-backed routes: API-key boundary, billing/usage caps, safety identifiers, rate-limit handling, latency/cost policy, and reporting loop |
| `route_success_contract_id` | Required success criteria, quality dimensions, thresholds, and blocked tradeoffs |
| `eval_gate_ids` | Required eval suites before promotion |
| `rollback_route_id` | Route to restore if promotion fails |
| `decision_status` | draft, ready_for_eval, blocked, approved, rejected, rolled_back |

## Change Summary

Capture the smallest precise diff:

| Surface | What changed | Why it changed | Expected effect |
|---|---|---|---|
| Prompt/template |  |  |  |
| Model/provider |  |  |  |
| Agent graph/handoff |  |  |  |
| Graph edge typing |  |  |  |
| Retriever/reranker |  |  |  |
| Source snapshot/index |  |  |  |
| Tool/guardrail policy |  |  |  |
| Trust boundary/redaction |  |  |  |
| Serving/runtime profile |  |  |  |
| Feature flag or release-control policy |  |  |  |

If a row is irrelevant, mark it as `unchanged`. Do not leave ambiguity about which layer changed.

## Evidence Required

Every proposal needs at least one evidence class:

- production trace showing a real failure;
- eval run showing a regression or improvement opportunity;
- user feedback routed into a structured issue;
- cost, latency, or capacity measurement;
- source freshness/provenance issue;
- security, privacy, or guardrail requirement;
- explicit product requirement from a design owner.

Evidence should reference IDs or notes. It should not paste raw book text, transcripts, or long source excerpts.

If evidence comes from annotation or human feedback, include the annotation project, schema version, guideline version, assignment policy, response state, suggestion/pre-annotation source, and promotion status. Do not treat accepted model suggestions, weak labels, or active-learning samples as unbiased independent human evidence.

If evidence comes from a feature-flag rollout or experiment, include the flag definition, variation IDs, assignment unit, exposure events, metric/outcome join, guardrail metrics, sample-size caveats, rollback/pause state, and stale-flag cleanup status. Do not treat a gradual rollout as an experiment unless stable exposure/outcome evidence exists.

If the proposal chooses among prompt, model, retriever, reranker, graph, or agent-route candidates, include the selection run, candidate set, selected candidate rationale, held-out or shadow assessment run, split labels, resampling or bootstrap evidence where data is scarce, metric uncertainty, validation-reuse status, leakage checks, regression slices, fallback, and rollback. Do not treat the eval slice used to choose the candidate as the final release proof.

If the proposal changes retrieval order, reranker output, source priority, memory selection, candidate lists, or recommendation feeds, include the ranking surface, candidate universe, cutoff K, relevance-grade rubric, ranking list snapshots, Precision/Recall/MRR/MAP/NDCG results where applicable, coverage/diversity metrics, false-positive and false-negative reviews, minority-evidence slices, online-feedback caveats, position-bias caveats, latency/cost evidence, fallback, and rollback. Do not use a single average score or engagement metric as release proof.

If the proposal changes confidence-driven action, publication, state mutation, escalation, abstention, or review-reduction behavior, include uncertainty signals, calibration evidence, expected-loss decision policy, allowed actions, abstention and escalation evals, evidence-dependency edges, graph messages, failure hypotheses, reviewer override, fallback, and rollback. Do not use confidence as a release threshold without the decision cost model that acts on it.

If the proposal increases model size, route graph complexity, tool count, context length, memory scope, adaptation depth, optimizer settings, or critique-loop budget, include the bottleneck diagnosis, train/dev and held-out behavior, validation-reuse status, regularization policy, numerical-stability record, long-context memory record, optimization diagnostics, simpler baseline, complexity burden, serving cost/latency evidence, robustness evals, fallback, and rollback. Do not use "more capacity" as a fix without proving which bottleneck it addresses.

If the proposal changes feedback adaptation, graph authority, personalization, memory scoring, source trust scoring, adaptive reranking, or hidden route-state tracking, include calibration evidence, route-complexity justification, feedback window, update rule, regret proxy, graph transition and damping assumptions, manipulation checks, observed-versus-inferred belief-state snapshots, candidate-diversity metrics, degeneracy thresholds, fallback, and rollback. Do not let a stream of feedback silently mutate production behavior without an adaptive-state gate.

If the proposal changes approximate inference, posterior confidence, distribution-shift monitoring, structured prediction, graph discovery, diversity selection, interpretability review, or a latent generative-process route, include approximation family, update mode, convergence or compute diagnostics, calibration or caveats, validity slice, shift-class coverage, graph-structure hypotheses, diversity tradeoff rationale, explanation fidelity check, generative-process settings, fallback, and rollback. Do not let an inferred score, graph edge, explanation, or generated-media setting act as exact evidence without its approximation record.

If the proposal changes a transformer task pipeline, tokenization/context assembly, QA/RAG reader-generator split, generated-text metric, few-label strategy, compression/deployment profile, or pretraining plan, include the task pipeline, tokenization eval, context assembly trace, QA pipeline, generated metric caveats, deployment benchmark, compression record, few-label strategy, pretraining run plan where applicable, privacy/rights review, fallback, and rollback. Do not treat a transformer route as a generic prompt change when its tokenizer, task head, retrieval boundary, metric, or serving runtime changes behavior.

If the proposal changes a bounded classic ML route, feature pipeline, threshold policy, class-imbalance handling, managed AI service dependency, OCR/moderation/vision API path, or restricted visual capability, include the model artifact, fitted preprocessing, label definition, business-cost metric, class distribution, calibration, threshold policy, reviewer-capacity assumption, dimensionality-reduction caveat, provider/API version and drift review, privacy/responsible-AI access review, fallback, and rollback. Do not ship aggregate accuracy or a transient managed-service score as production evidence by itself.

If the proposal changes a scikit-learn pipeline, PyTorch support model, graph-ML support route, or agent-eval environment, include the estimator pipeline, preprocessing fit record, training loop trace, model artifact identity, dependency lock, classical baseline comparison, graph schema/features where applicable, eval environment fixtures/actions/success criteria, unsafe-action boundary, fallback, and rollback. Do not treat notebook success, a saved `.pt` file, or an environment description as reproducible route evidence without the fitted state and eval contract.

If the proposal changes a generated-media pipeline, editing route, media adapter, audio route, synthetic voice route, or local/open-model media runtime, include model-card/license constraints, full media pipeline trace, control/adaptor inputs, adaptation training rights and validation, audio representation, voice consent or rights record, local runtime memory/latency profile, watermark/provenance decision, safety/rights review, human review, fallback, and rollback. Do not treat a prompt plus final media file as enough evidence for publication, identity-affecting edits, or reusable media generation behavior.

If the proposal changes a generative model family, representation path, diffusion or latent-diffusion sampler, multimodal bridge, upsampler/decoder stage, world-model simulation, music/audio generator, or originality-sensitive media route, include the model profile, sampler settings, bridge architecture, upsampler stage refs, attribute-binding/rendered-text/alignment evals, simulation transfer checks, music/audio tokenization, nearest-training-neighbor originality review, rights review, latency/quality tradeoff, fallback, and rollback. Do not approve a model-family swap because samples look better without proving the route's visible failure slices.

If the proposal changes a GAN-family route, image-translation route, synthetic-data source, latent-control surface, conditional generation policy, or adversarial-media eval path, include generator and critic profile, synthetic media lineage, generator/discriminator evals, mode-collapse and seed-sensitivity checks, latent interpolation traces, condition schema, preserved and forbidden transformations, adversarial-media cases, rights review, human review, fallback, and rollback. Do not treat critic confidence, FID-like distribution scores, or attractive samples as final product approval.

If the proposal changes a source-ingestion NLP adapter, sentence splitter, tokenizer, normalization policy, grammar/dependency extraction path, embedding adapter, RAG adapter recipe, or notebook-derived ingestion runtime, include adapter profile, text-boundary records, normalization policy, grammar-extraction candidates, embedding compatibility decision, RAG traces, dependency/model version locks, PII/privacy review, boundary/extraction/retrieval evals, fallback, and rollback. Do not let recipe-level preprocessing silently change source chunks, claims, entities, or retrieval candidates without a release gate.

## First-Pass Reviewer Gate

Before human approval, production or canon-impacting proposals should pass through a first-pass reviewer route. The reviewer is not the approver; it prepares the artifact for sharper human judgment.

Required reviewer outputs:

| Output | Required content |
|---|---|
| `review_artifact_id` | Draft proposal, PRD, source-ingestion plan, publishing packet, or release candidate under review |
| `context_assembly_id` | Linked docs, discovered adjacent docs, prior experiments, policies, metrics, and retrieval traces used by the reviewer |
| `proposal_risk_classification_id` | Review depth and specialized scrutiny flags |
| `readiness_scorecard_id` | Structured readiness result with dimension scores, evidence, and decision status |
| `critical_gap_ids` | Blocking missing evidence, weak assumptions, unsafe dependencies, or absent guardrails |
| `revision_action_item_ids` | Ordered repairs split into critical requirements and optimizations |
| `first_pass_review_release_gate_id` | Gate proving artifact identity, access-bounded context assembly, risk-classified review depth, readiness dimensions, critical gaps, first fix, evidence refs, human-authority boundary, override policy, and post-review outcome policy |

The reviewer should prioritize the first fix and cite evidence for findings. A high prose-quality proposal with missing metrics, source snapshots, guardrails, rollback, or dependency evidence should remain `request_changes`.

The reviewer route cannot approve the proposal. A scorecard can advance a draft to sharper human review, request changes, or block until missing evidence is supplied; final approval remains with the human expert gate or the governed release gate for the affected surface.

## Capacity Decision

Use [[Capacity Estimation - Adaptation and Serving Decisions]] when the change touches model adaptation or serving capacity.

Required decision:

| Question | Answer |
|---|---|
| What lighter intervention was attempted first? |  |
| Why is a route change needed instead of source/retrieval/prompt/tool repair? |  |
| What is the expected quality, latency, cost, privacy, or reliability gain? |  |
| What is the new compute or serving requirement? |  |
| What is the fallback if capacity assumptions fail? |  |

No fine-tuning, distillation, quantization replacement, self-hosted runtime, or provider switch should be approved without this section.

## Eval Gates

Attach eval suites by surface:

Before selecting eval suites, bind the proposal to a `route_success_contract_id`. The contract should define the route objective, task distribution, quality dimensions, per-dimension thresholds, regression budget, and non-negotiable blocked tradeoffs. Do not use aggregate score improvements to hide release-blocking regressions.

| Change surface | Required eval gate |
|---|---|
| Prompt/template | output schema, representative task cases, citation/grounding if source-backed |
| Model/provider | task quality, safety, latency, cost, regression slices |
| Retriever/index | source recall, context precision/recall, citation validity, stale-source acceptance |
| Reranker | false-positive removal, false-negative introduction, rank movement, latency |
| Agent graph/handoff | trace grading, tool choice, handoff target, loop prevention, state preservation |
| Graph edge typing | input/output schema, edge type, trust class, approval edge, terminal behavior |
| Tool policy | tool-call arguments, approval behavior, failure recovery, unsafe action blocks |
| Guardrail | jailbreak, over-refusal, unsafe pass-through, source-leak prevention |
| Serving/runtime | TTFT, TPOT, throughput, queueing, cost, error rate, fallback behavior |
| Feature flag or experiment | safe default, targeting rule, context-field privacy, cohort stability, exposure logging, metric join, guarded-rollout regression rule, stale-flag cleanup |

Provider-backed changes also need a readiness gate covering API-key scope, provider project/billing boundary, usage budget, safety identifier policy, rate-limit observation, quota-aware retry/backoff, per-user/bulk caps, and user-reporting channel.

Record baseline and candidate on the same eval slices. Aggregate score alone is not enough; failure slices must be visible.

## Source And Retrieval Snapshot

Route changes that affect source-backed work must declare:

- `source_snapshot_id`;
- `retrieval_index_version`;
- `embedding_model`;
- `chunk_policy`;
- `graph_schema_version`;
- accepted and rejected evidence trace availability;
- stale-source policy;
- blocked or excluded source classes.

This prevents a route from appearing better because it silently used a different source corpus.

## Trust Boundary And Approval Snapshot

Tool-using, browser/computer-use, retrieval, upload, or publishing routes must declare:

- `trust_boundary_policy_id`;
- untrusted input sources allowed into the route;
- extraction or structured-output schemas before tool use;
- `trace_redaction_policy_id`;
- `safety_identifier_policy_id`;
- `provider_usage_budget_id`;
- `rate_limit_observation_id`;
- approval edges for external mutation, publishing, deletion, purchase, account action, or sensitive-data exposure;
- tool credential scope and expiration;
- reviewer override policy.

Untrusted source text, comments, webpages, transcripts, captions, and uploads must not be injected into developer/system instructions. They should enter as user/context data and become typed fields only after validation.

## Rollout Plan

| Stage | Traffic or scope | Required evidence | Stop condition |
|---|---|---|---|
| offline_eval | no production traffic | eval run passes required gates | release-blocking failure |
| shadow | production-like traces, no user-visible output | trace and latency match expectations | unsafe or unsupported output |
| limited_canary | small owner-approved scope | quality, cost, latency, feedback acceptable | regression by critical slice |
| full_release | approved route bundle | release record and rollback path complete | post-release guardrail breach |

For local/offline workflows, "traffic" means task scope, source scope, or agent scope rather than user percentage.

## Feature Flag And Experiment Plan

Use this section when a route change adds or changes runtime release controls.

| Field | Required content |
|---|---|
| `flag_class` | release, experiment, operational, kill_switch, permission, or config |
| `safe_default` | Value or route behavior used when the provider is unavailable or evaluation fails |
| `evaluation_context_fields` | Allowed context fields, privacy class, source of truth, and hashing/redaction policy |
| `targeting_or_rollout_rule` | Segment, constraint, prerequisite, percentage, progressive step, or guarded rollout rule |
| `variation_ids` | Baseline and candidate values or payloads |
| `exposure_event_policy` | How assignment is logged and joined to route metrics, evals, feedback, incidents, or cost events |
| `release_control_gate_id` | Required for production rollout: linked flag definitions, safe defaults, targeting, exposure/outcome join, guarded-rollout or experiment decision, kill-switch test, and stale-flag cleanup |
| `experiment_policy` | Required only for experiments: assignment unit, metrics, guardrails, analysis method, and stop rule |
| `cleanup_due_at` | Date or release condition for removing release/experiment/operational flags after promotion |

## Rollback Plan

Minimum rollback fields:

| Field | Required content |
|---|---|
| `rollback_route_id` | Last known good route |
| `rollback_trigger` | Metric, eval failure, guardrail event, user feedback, or incident condition |
| `state_migration_risk` | Whether traces, memory, source snapshots, or artifacts need conversion |
| `data_cleanup` | Whether generated outputs, embeddings, caches, or eval artifacts must be invalidated |
| `owner_to_execute` | Human or agent responsible |

Rollback is part of approval, not an incident improvisation.

## Review Decision

| Decision field | Required content |
|---|---|
| `decision` | approve, reject, request_changes, limited_canary, rollback |
| `approved_by` | Human owner for production/canon-impacting routes |
| `approval_scope` | offline, canary, production, local-only, experimental |
| `known_tradeoffs` | Explicit accepted regressions or risks |
| `follow_up_eval_cases` | New cases created from failures or uncertainty |
| `next_review_date` | Required for temporary exceptions |

## Agent Studio Design Implications

- Route proposals become the bridge between research notes, evals, and implementation.
- The platform should not allow hidden route changes for source-backed production workflows.
- Eval artifacts, capacity estimates, and rollback plans need IDs that can be linked from releases.
- Prompt-only changes can stay lightweight, but model/provider/runtime changes require capacity evidence.
- Source-backed route changes must pin the source snapshot and retrieval index used during evaluation.

## Initial Use Cases

1. Promote a retrieval-index update after adding GraphRAG community reports.
2. Replace a reranker while preserving recall for minority evidence.
3. Add a long-context synthesis route for book-heavy tasks.
4. Quantize or switch a model route for lower cost while preserving groundedness.
5. Enable a realtime voice provider for conversational turns without moving deep synthesis into the realtime path.
