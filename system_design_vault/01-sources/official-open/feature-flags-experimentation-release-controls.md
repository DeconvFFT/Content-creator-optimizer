---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_doc_page
rights_status: official_or_open_public
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://openfeature.dev/specification/
  - https://openfeature.dev/specification/sections/flag-evaluation/
  - https://openfeature.dev/specification/sections/evaluation-context/
  - https://openfeature.dev/specification/sections/hooks/
  - https://openfeature.dev/specification/sections/tracking/
  - https://launchdarkly.com/docs/home/flags/target
  - https://launchdarkly.com/docs/home/releases/percentage-rollouts
  - https://launchdarkly.com/docs/home/releases/progressive-rollouts
  - https://launchdarkly.com/docs/home/releases/guarded-rollouts
  - https://launchdarkly.com/docs/home/experimentation
  - https://docs.getunleash.io/concepts/feature-flags
  - https://docs.getunleash.io/concepts/activation-strategies
  - https://docs.getunleash.io/concepts/strategy-variants
  - https://docs.getunleash.io/concepts/unleash-context
related:
  - [[../../03-patterns/system-design/production-agent-studio-canon]]
  - [[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]
  - [[model-gateway-provider-routing-runtime]]
  - [[kserve-model-serving-rollouts]]
---

# Feature Flags, Experimentation, And Release Controls

## Source Scope

This note synthesizes current official OpenFeature, LaunchDarkly, and Unleash documentation. It is not an SDK tutorial and does not store code examples, raw page text, or long excerpts. The focus is the durable release-control contract Agent Studio needs for model/provider routes, retrieval changes, agent graph changes, tool authority, guardrails, publishing capability, and cost controls.

## Core Synthesis

Feature flags are a runtime decision plane. They should not be treated as prompt variables or informal environment switches. A production flag decision combines:

- a stable flag key;
- a provider and provider-readiness state;
- a typed default value;
- a merged evaluation context;
- targeting rules, constraints, prerequisites, or segments;
- a selected variation or fallback value;
- evaluation reason, error, and provider metadata when available;
- exposure or tracking events that connect the decision to later quality, cost, latency, safety, or business metrics.

OpenFeature provides the cleanest vendor-neutral contract. Typed evaluation should return a default rather than breaking the application on abnormal execution, while detailed evaluation should preserve the flag key, value, variant, reason, error code, and metadata when the provider can supply them. This maps directly to Agent Studio's need to fail closed: if a route-control flag cannot be evaluated, the safe default must be explicit and visible.

Evaluation context is the main boundary between product state and release policy. Context may include user, workspace, tenant, application, host, region, environment, session, route, or custom fields. Because targeting and fractional assignment depend on context, Agent Studio needs an allowlist of context fields, privacy class, source of truth, and precedence rules. A missing or malformed targeting key can silently change rollout behavior.

Hooks turn flag evaluation into an observable lifecycle. Before hooks can add validated context; after, error, and finally hooks can emit telemetry or audits. This is important for Agent Studio because route flags will sit in hot paths: logging every failure from the client path can become operational noise, but structured hook events can preserve enough evidence for release debugging.

Tracking separates exposure from outcome. A flag exposure or assignment is not an experiment result until it is linked to later metric events. Agent Studio should record both: flag evaluation/exposure for traceability, and outcome events for eval, SLO, cost, latency, reviewer feedback, or publishing success.

LaunchDarkly highlights rollout mechanics that matter for route safety. Targeting uses contexts and attributes; flags can include prerequisites, individual targets, targeting rules, and default behavior. Percentage rollouts assign contexts by a stable partitioning logic; two independently configured percentage rollouts are not guaranteed to target the same cohort. Progressive rollouts automate percentage changes over time, while guarded rollouts attach metrics and can pause or roll back on detected regressions. Experiments connect flag or AI-config variations to metrics so teams can compare behavior and decide whether to expand, stop, or roll back.

Unleash emphasizes operational hygiene. Flags live by project and environment, use activation strategies, and can include variants with weights, payloads, and stickiness. Strategies can combine gradual rollout, targeting, constraints, and segments; multiple strategies act as an OR, while constraints inside a strategy act as an AND. Flag types matter because they carry different expected lifetimes: release and experiment flags should be cleaned up, operational flags should be short-lived, while kill switches and permission flags may be permanent. Lifecycle/stale/archived states and unknown-flag checks are core debt controls, not admin niceties.

## Agent Studio Release-Control Model

Agent Studio should classify flags by intent:

| Flag class | Use in Agent Studio | Safe default |
|---|---|---|
| `release` | Enable a new prompt, route graph, retriever, reranker, model, provider, media path, or UI affordance. | Previous known-good route. |
| `experiment` | Assign stable cohorts for A/B/n, A/A, bandit, prompt, retrieval, or ranking comparisons. | Baseline variation. |
| `operational` | Temporarily shift implementation path, cache mode, batch mode, index alias, or provider gateway policy. | Stable implementation. |
| `kill_switch` | Disable risky capabilities such as publishing, browser/computer-use, code execution, external mutation, expensive inference, or unreviewed memory writes. | Disabled or degraded mode. |
| `permission` | Gate tool access, platform publishing, workspace feature access, private-source access, or reviewer-only flows. | Deny unless explicitly allowed. |
| `config` | Select bounded runtime parameters such as retrieval top-k, reranker cutoff, model alias, reasoning effort, trace sampling, cache TTL, or voice provider. | Reviewed route default. |

Route flags should be attached to route releases and route proposals, not scattered through code. A flag that changes model/provider selection, retrieval policy, memory scope, authority, publishing, or evaluation behavior is a route behavior change and needs release evidence.

## Datastore Commitments

Agent Studio should add these durable records:

| Record | Purpose | Minimum fields |
|---|---|---|
| `release_control_gate` | Promotion gate for runtime-control flags, guarded rollouts, experiments, and stale-flag cleanup before a route behavior change ships. | `gate_id`, `route_id`, `release_ref`, `flag_definition_refs`, `safe_default_refs`, `targeting_rule_refs`, `evaluation_context_policy_ref`, `exposure_event_refs`, `metric_join_refs`, `guarded_rollout_refs`, `experiment_refs`, `kill_switch_test_refs`, `flag_debt_refs`, `decision`, `reviewer`, `created_at` |
| `feature_flag_definition` | Stable identity and intent of a runtime-control flag. | `flag_id`, `flag_key`, `flag_class`, `owner`, `route_refs`, `provider_ref`, `default_value`, `safe_default_rationale`, `expected_lifetime`, `cleanup_due_at`, `status` |
| `flag_variation_definition` | Values a flag can return. | `variation_id`, `flag_id`, `variation_key`, `typed_value_ref`, `payload_schema_ref`, `is_baseline`, `risk_level`, `status` |
| `flag_targeting_rule` | Rule, constraint, segment, prerequisite, or rollout policy. | `rule_id`, `flag_id`, `environment`, `context_field_refs`, `operator_policy`, `segment_refs`, `prerequisite_flag_refs`, `rollout_percent`, `stickiness_key`, `starts_at`, `ends_at`, `status` |
| `flag_evaluation_event` | Per-call decision evidence. | `evaluation_id`, `run_id`, `route_id`, `flag_id`, `provider_ref`, `context_hash`, `targeting_key_hash`, `default_used`, `variation_id`, `reason`, `error_code`, `metadata_hash`, `created_at` |
| `flag_exposure_event` | Assignment event used for experiment or rollout analysis. | `exposure_id`, `evaluation_id`, `experiment_id`, `cohort_key_hash`, `variation_id`, `surface`, `created_at` |
| `release_experiment_record` | Controlled comparison attached to route behavior. | `experiment_id`, `route_id`, `flag_id`, `baseline_variation_id`, `candidate_variation_ids`, `assignment_unit`, `metric_refs`, `guardrail_metric_refs`, `analysis_method`, `decision`, `status` |
| `guarded_rollout_record` | Metric-monitored rollout with pause or rollback authority. | `guarded_rollout_id`, `flag_id`, `route_release_id`, `step_policy`, `metric_refs`, `minimum_context_requirement`, `regression_rule`, `auto_rollback_enabled`, `current_state`, `decision` |
| `flag_debt_record` | Cleanup and stale-reference control. | `debt_id`, `flag_id`, `stale_state`, `last_evaluated_at`, `unknown_reference_count`, `cleanup_ticket_ref`, `archive_or_remove_decision`, `owner`, `status` |

These records complement `canary_rollout_record` and `traffic_split_record`. Canary traffic split says where production traffic went; flag evaluation says why a specific request or route took a behavior path; experiment exposure says which cohort assignment later metrics should join against.

## Canon Cross-Check

- Route-change proposals already require feature-flag policy evidence when a change introduces, modifies, removes, or depends on runtime flags; this note defines the durable records that make that evidence auditable.
- KServe and serving-rollout notes own candidate revision traffic movement; this note owns runtime behavior selection, safe defaults, exposure events, cohort stability, and stale-flag cleanup.
- Model gateway/provider routing owns provider fallback chains, virtual keys, budgets, and cache behavior; this note owns whether those runtime paths are enabled by governed flags with explicit context and rollback policy.
- Production canon and HLD already require flags as a release-control plane; this pass makes that requirement canon-ready and attaches it to a release gate.
- Boundary: experiment/eval canon owns metric design and offline/online evaluation validity; feature-flag canon owns assignment, exposure, rollout/rollback control, and whether the metric join is present before experiment claims are trusted.

## Design Implications

- Do not hide model switches, provider fallbacks, retrieval K changes, reranker changes, memory modes, guardrail changes, or publishing ability behind untracked environment variables.
- Treat evaluation context as sensitive product data. Hash or reference user/workspace/tenant IDs and keep raw attributes out of traces unless the route explicitly permits them.
- Separate rollout from experiment. A gradual rollout reduces deployment risk; an experiment needs stable assignment, exposure logging, metrics, and an analysis plan.
- Keep kill switches boring and tested. They need a safe default, operator surface, alert/incident link, and post-use cleanup path.
- Add flag prerequisites carefully. Parent-child dependencies can encode safety policy, but hidden prerequisite chains make route behavior hard to reason about.
- Stale flags are architectural debt. A release flag that survives after full rollout should create a cleanup record; an unknown flag reference should block release until explained.

## Anti-Patterns To Avoid

- Using a flag with no owner, expected lifetime, or cleanup path.
- Letting missing flag-provider state silently enable high-authority behavior.
- Mixing user segmentation, workspace entitlement, experiment assignment, and emergency rollback into one flag.
- Reusing the same flag key after deletion or archive.
- Calling a metric-monitored rollout an experiment when no exposure/outcome join exists.
- Recording aggregate experiment results without the assignment unit, cohort stability, guardrail metrics, and stopped/rolled-back state.

## Next Agent Studio Move

Add release-control gates to the route-change workflow. Every production route proposal should declare whether it introduces, modifies, or removes feature flags; whether a guarded rollout or experiment is involved; what the safe defaults are; how exposures join to outcomes; which kill switch was tested; and how stale flags will be retired after promotion.
