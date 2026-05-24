---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_or_open_public
provenance_status: official_litellm_cloudflare_portkey_openrouter_docs_direct_read
sources:
  - https://docs.litellm.ai/
  - https://docs.litellm.ai/docs/routing
  - https://docs.litellm.ai/docs/proxy/virtual_keys
  - https://developers.cloudflare.com/ai-gateway/
  - https://developers.cloudflare.com/ai-gateway/features/dynamic-routing/
  - https://developers.cloudflare.com/ai-gateway/features/caching/
  - https://developers.cloudflare.com/ai-gateway/features/rate-limiting/
  - https://portkey.ai/docs/product/ai-gateway
  - https://portkey.ai/docs/product/ai-gateway/fallbacks
  - https://openrouter.ai/docs/guides/routing/provider-selection
  - https://openrouter.ai/docs/guides/routing/routers/auto-router
---

# Model Gateway And Provider Routing Runtime

## Scope

Direct-read synthesis from official LiteLLM, Cloudflare AI Gateway, Portkey AI Gateway, and OpenRouter routing docs. This note captures Agent Studio model-gateway and provider-routing implications. It stores no provider keys, request bodies, prompt text, code samples, or long excerpts.

## Core Pattern

A model gateway is a control plane in front of model providers. It is not just a convenience wrapper. It centralizes:

- provider/model aliases;
- authentication and virtual keys;
- per-user, per-team, per-project, or per-route budgets;
- RPM/TPM/request limits;
- routing policy and load balancing;
- fallbacks and retry policy;
- cache behavior;
- provider selection constraints;
- logging, metrics, and cost attribution;
- model/provider rollout and rollback.

For Agent Studio, gateway decisions are product behavior. If the same prompt sometimes goes to a cheaper model, a lower-latency provider, a fallback endpoint, or a cached response, the run trace must preserve why that happened and whether the output still satisfies the route's eval, privacy, and source-grounding contract.

## Cross-Provider Design Signals

LiteLLM frames the proxy as a central LLM gateway for platform teams, with a unified OpenAI-style interface across many providers, authentication/authorization hooks, virtual keys, spend tracking, budgets, rate limiting, caching, guardrails, and observability. Its router docs expose deployment groups, model aliases, load balancing, cooldowns, fallbacks, timeouts, retries, request prioritization, health-check-driven routing, RPM/TPM-aware routing, latency-based routing, and cost-based routing. The practical warning is that routing strategy has performance cost; usage-aware routing can add latency and infrastructure dependencies such as Redis.

Cloudflare AI Gateway frames the gateway as an observability and control layer: analytics, logging, caching, rate limiting, request retries, model fallback, provider support, authenticated gateways, DLP/guardrails, and dynamic routing. Its dynamic routing docs make route versions first-class and expose conditional nodes, percentage rollout nodes, model nodes, rate-limit nodes, budget-limit nodes, metadata-driven rules, and rollback. Its caching docs show that cache keys include provider, endpoint, model, auth header, and full request body by default, and that cache hits/misses should be observable.

Portkey AI Gateway adds gateway strategies as configurable product policy: universal API, simple/semantic cache, MCP support, fallbacks, conditional routing, automatic retries, circuit breakers, load balancing across keys, canary testing, request timeouts, budget limits, rate limits, custom hosts, and self-hosting. Its fallback docs make fallback order and trigger status codes explicit.

OpenRouter routing docs separate model routing from provider routing. The Auto Router selects a model and returns the actual model used. Provider routing exposes provider order, fallback allowance, parameter support requirements, data-collection constraints, provider sorting by price/throughput/latency, endpoint/region variants, and allowed-model patterns. For Agent Studio, that means requested model, selected model, provider endpoint, fallback policy, and data-retention constraints must be separate trace fields.

## Current-Source Cross-Check

Current LiteLLM routing docs still support the gateway as a routing and reliability plane: model aliases, deployment groups, weighted routing, RPM/TPM-aware pre-call checks, health/cooldown state, retries, fallbacks, timeouts, latency routing, cost routing, request prioritization, and Redis-backed usage tracking can all change the selected model/provider and the latency/cost profile.

Current Cloudflare AI Gateway dynamic routing docs make named route versions, conditional nodes, percentage nodes, model nodes, rate-limit nodes, budget-limit nodes, metadata rules, deployment, and instant rollback explicit. That supports treating route versions and node graphs as release artifacts, not prompt configuration.

Current OpenRouter provider-routing docs reinforce that provider choice is a separate product contract: provider order, fallback enablement, parameter support, data collection policy, ZDR enforcement, endpoint/region targeting, quantization, max price, and price/throughput/latency sorting should all be durable route fields.

## Agent Studio Design Implications

- Do not hide gateway routing behind a provider SDK call. Every route needs a model-gateway policy record.
- Store requested model/route alias separately from selected model, selected provider, selected endpoint, and response model.
- Virtual keys should be scoped to route/team/user/project, with allowed models, expiry, budgets, RPM/TPM limits, owner, and rotation status.
- Dynamic route versions are release artifacts. Conditional routing, percentage rollout, budget-limit nodes, and fallback nodes need version IDs and rollback state.
- Gateway cache policy must record cache-key fields, TTL, skip/override behavior, hit/miss status, and source/privacy scope.
- Fallback is not automatically safe. A fallback model may change tool support, output schema reliability, context length, latency, cost, data retention, safety filters, or answer quality.
- Provider constraints such as parameter support, provider order, endpoint region, data-collection posture, and allowed-model patterns should be release-gated.
- Gateway logs are sensitive because they may include prompts, responses, keys, user metadata, and provider errors. Store hashes/refs and redacted summaries by default.
- Budget exhaustion should degrade by policy: cheaper model, delayed batch, human review, retrieval-only answer, or refusal. It should not silently skip source checks or publish lower-quality artifacts.
- Model canaries and A/B routes need eval-linked promotion, not only percentage rollout.

## Datastore Additions

| Object | Purpose | Key fields |
|---|---|---|
| `model_gateway_record` | Gateway deployment or managed gateway boundary | `gateway_id`, `gateway_provider`, `hosting_mode`, `base_url_or_ref`, `supported_provider_refs`, `auth_mode`, `log_policy_id`, `cache_support`, `routing_support`, `owner`, `status` |
| `model_gateway_route_version` | Versioned dynamic route or gateway alias | `gateway_route_version_id`, `gateway_id`, `route_alias`, `version`, `node_graph_hash`, `condition_refs`, `percentage_split_refs`, `budget_limit_refs`, `rate_limit_refs`, `fallback_chain_ref`, `deployed_at`, `rollback_ref`, `status` |
| `gateway_virtual_key_record` | Scoped model-gateway credential | `virtual_key_id`, `gateway_id`, `owner_scope`, `allowed_model_patterns`, `allowed_provider_refs`, `rpm_limit`, `tpm_limit`, `max_budget`, `budget_window`, `expires_at`, `rotation_state`, `status` |
| `provider_route_decision` | Per-call routing evidence | `decision_id`, `run_id`, `gateway_route_version_id`, `requested_model_or_alias`, `selected_model`, `selected_provider`, `selected_endpoint`, `routing_strategy`, `decision_reason`, `fallback_attempt_refs`, `cache_decision_ref`, `created_at` |
| `provider_fallback_chain` | Ordered fallback policy for a model route | `fallback_chain_id`, `route_id`, `trigger_status_codes`, `trigger_error_classes`, `target_order`, `allow_cross_provider`, `schema_compatibility_requirement`, `quality_floor_ref`, `cost_latency_caveat`, `status` |
| `gateway_cache_policy` | Gateway-level or route-level cache behavior | `gateway_cache_policy_id`, `route_id`, `cacheable_surfaces`, `cache_key_fields`, `ttl`, `skip_header_or_flag`, `custom_key_policy`, `privacy_scope`, `source_freshness_dependency`, `status` |
| `gateway_cache_event` | Per-call cache hit/miss evidence | `cache_event_id`, `decision_id`, `cache_policy_id`, `cache_status`, `cache_key_hash`, `ttl_remaining`, `served_from_cache`, `correctness_review_ref`, `created_at` |
| `provider_constraint_policy` | Provider selection constraints before routing | `constraint_policy_id`, `route_id`, `provider_order`, `provider_sort`, `allow_fallbacks`, `require_parameters`, `allowed_model_patterns`, `endpoint_region_policy`, `data_collection_policy`, `status` |
| `gateway_budget_event` | Budget/rate limit admission or rejection | `budget_event_id`, `gateway_id`, `virtual_key_id`, `route_id`, `limit_type`, `window`, `used_amount`, `limit_amount`, `decision`, `fallback_or_degradation_ref`, `created_at` |
| `gateway_route_canary` | Model/provider gateway canary or A/B rollout | `canary_id`, `gateway_route_version_id`, `candidate_target_ref`, `traffic_percentage`, `eval_refs`, `cost_latency_delta`, `rollback_trigger`, `promotion_decision`, `status` |
| `model_gateway_release_gate` | Promotion gate for gateway route and provider-routing changes | `gate_id`, `route_id`, `candidate_gateway_route_version_id`, `model_gateway_record_refs`, `virtual_key_refs`, `provider_constraint_policy_refs`, `fallback_chain_refs`, `gateway_cache_policy_refs`, `budget_rate_limit_refs`, `route_canary_refs`, `eval_refs`, `privacy_data_policy_refs`, `log_redaction_policy_refs`, `degradation_policy_refs`, `rollback_ref`, `decision`, `reviewed_at` |

## Release Gates

Do not promote a model-gateway route when:

- requested model alias and selected provider/model are not traceable;
- virtual key scope, expiry, budget, and model allowlist are missing;
- fallback can change schema/tool support/context length without eval evidence;
- cache keys ignore user, source, privacy, or freshness boundaries;
- provider data-retention or data-collection constraints are not recorded;
- dynamic route versions cannot be rolled back;
- rate-limit and budget exhaustion have no user-visible degradation policy;
- gateway logs can store raw prompts/responses without redaction and retention policy;
- canary rollout lacks eval, cost, latency, and rollback evidence.

## Agent Studio Decision

This note is canon-ready for Agent Studio provider-routing architecture. Build Agent Studio around an explicit model-gateway control plane. The gateway may be self-hosted, managed, or a thin internal wrapper, but the durable contract is the same: route version, virtual key, provider constraint policy, route decision, fallback chain, cache event, budget event, canary result, release gate, and redacted observability evidence for every provider-backed call.
