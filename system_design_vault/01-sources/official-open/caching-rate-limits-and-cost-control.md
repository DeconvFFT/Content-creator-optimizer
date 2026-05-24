---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://developers.openai.com/api/docs/guides/prompt-caching
  - https://developers.openai.com/api/docs/guides/cost-optimization
  - https://developers.openai.com/api/docs/guides/latency-optimization
  - https://developers.openai.com/api/docs/guides/production-best-practices
  - https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching
  - https://platform.claude.com/docs/en/api/rate-limits
  - https://docs.cloud.google.com/cdn/docs/best-practices
  - https://docs.cloud.google.com/memorystore/docs/redis/general-best-practices
source_status: official_public
verification_notes:
  - OpenAI, Anthropic, Google Cloud CDN, and Google Cloud Memorystore docs opened directly on 2026-05-18.
  - OpenAI prompt-caching docs redirected from platform.openai.com to developers.openai.com.
  - Anthropic prompt-caching docs redirected from docs.anthropic.com to platform.claude.com.
  - This note stores original synthesis only and does not copy source text or examples.
---

# Caching Rate Limits And Cost Control

## Direct-Read Scope

Direct-read pass over official OpenAI prompt caching, cost optimization, latency optimization, and production best-practice docs; Anthropic prompt caching and rate-limit docs; Google Cloud CDN cache best practices; and Google Cloud Memorystore for Redis best practices.

This note fills the cost and cache-governance gap for Agent Studio. Autoscaling controls how much capacity exists; queue contracts control when work runs; caching and rate-limit contracts decide whether repeated work is avoided, whether the right work gets priority, and whether provider cost/limit failures are visible before users hit them.

## Core Read

Provider prompt caching is prefix-sensitive. OpenAI's docs emphasize exact prompt-prefix matches and stable content at the beginning of the prompt, with variable user-specific material later. Anthropic's docs similarly make caching a prefix design problem and expose cache read/write usage fields and TTL choices. The product lesson is that prompt structure is part of runtime architecture. Tool definitions, system/developer instructions, stable style policy, and long reusable context can be cache candidates; dynamic source evidence, private user snippets, volatile retrieval results, and per-run instructions usually should not be mixed into the stable prefix.

Rate limits are not the same as cost limits. Anthropic documents separate input/output token limit behavior, cache interactions, model-specific limits, batch queue limits, managed-agent endpoint limits, and monitoring charts. OpenAI production guidance adds project separation, API-key usage tracking, and project-level rate/spend limits. For Agent Studio, provider limits should be represented as route constraints, not as incidental 429 errors.

OpenAI cost and latency guidance reinforces the simplest economics: fewer requests, fewer tokens, smaller appropriate models, batch/asynchronous work, and lower-priority processing options can reduce cost and latency. This maps to Agent Studio's workload classes: realtime/foreground work needs low latency; evals, enrichment, source refresh, and backfills can often use batch, flex, or delayed routes with explicit freshness targets.

General cache infrastructure adds different failure modes. Google Cloud CDN docs emphasize cache keys, cache-control, TTLs, avoiding user-specific content, and using invalidation carefully because invalidation is not the same as instant global consistency. Memorystore/Redis guidance emphasizes networking choices, memory monitoring, and avoiding sensitive data in resource names. For Agent Studio, application caches must carry sensitivity, freshness, key design, invalidation policy, and observability. A cache hit is not automatically correct if source rights, freshness, user scope, or route version changed.

## Current-Source Cross-Check

Current OpenAI prompt-caching guidance still supports treating stable prompt prefixes as route design rather than incidental prompt formatting. The same current OpenAI cost, latency, and production guidance supports explicit control over request count, token volume, fit-for-purpose model choice, asynchronous or background work where appropriate, and project-level usage boundaries.

Current Anthropic prompt-caching and rate-limit guidance supports the same architecture rule from a second provider surface: cache read/write accounting, TTL/cache-control choices, organization/workspace/model limits, 429 handling, and retry/rate-limit headers should be modeled as route evidence.

Current Google Cloud CDN and Memorystore guidance supports the non-LLM side of the same contract: cache keys, TTLs, user-specific caching boundaries, invalidation caveats, Redis memory behavior, networking posture, and retry behavior must be explicit before a cache is trusted for source-backed product behavior.

## Agent Studio Design Implications

- Treat prompt caching as a route contract. Record stable prefix composition, provider cache controls, TTL, cache key strategy, and which prompt segments are forbidden from cacheable prefixes.
- Put stable system instructions, tool schemas, style policy, and reusable background context before variable user/source content when the provider cache rewards exact prefixes.
- Keep private user material, current-source evidence, and per-run approval state out of shared cache keys unless the cache is scoped to the user/project/source snapshot.
- Record provider usage fields separately: uncached input tokens, cache-read tokens, cache-write tokens, output tokens, reasoning tokens, cost, rate-limit bucket, and retry-after behavior where available.
- Separate cost budget, rate limit, and latency SLO. A route can be under budget but over a rate limit, or fast but too expensive.
- Use batch/flex/low-priority routes for eval backfills, source enrichment, embedding refreshes, and noninteractive judging when freshness and user experience permit it.
- Add cache invalidation as a first-class event when source snapshots, route prompts, tool schemas, policy, model version, rights state, or user/project scope changes.
- Do not cache user-specific content in shared CDN or shared application caches. Cache keys must include enough scope to prevent cross-user or cross-project leakage.
- Monitor cache hit rate, miss rate, eviction, memory pressure, stale-hit rate, over-quota attempts, and provider 429s as product signals.
- Treat cache infrastructure as best-effort acceleration, not the source of truth. Durable state remains in Postgres/source ledgers/artifacts; caches must be rebuildable or invalidatable.

## Datastore Objects To Add

| Object | Purpose |
|---|---|
| `prompt_cache_policy` | Stable prefix, cache-control/TTL, provider behavior, forbidden segments, scope, and expected hit-rate target for one route. |
| `cache_key_policy` | Cache key components, tenant/user/source-snapshot/version scope, collision risk, and privacy review. |
| `cache_usage_record` | Provider or application cache read/write/miss evidence with tokens, hit/miss, latency delta, cost delta, and route. |
| `cache_invalidation_event` | Explicit invalidation after source, route, prompt, tool, policy, rights, or user/project scope changes. |
| `provider_rate_limit_record` | Provider/model/endpoint limit bucket, current usage, retry-after behavior, sharing scope, and alert state. |
| `usage_budget_record` | Route/project/user/workload budget for cost, tokens, requests, output tokens, batch jobs, or realtime minutes. |
| `low_priority_processing_policy` | Batch/flex/background eligibility, max staleness, expected latency, cost discount, and user-visible status. |
| `cost_attribution_record` | Per-run/route/provider cost attribution across model tokens, cache writes/reads, tools, retrieval, media, and batch work. |
| `stale_cache_risk_record` | Risk that cached content is obsolete, unauthorized, policy-stale, source-stale, or cross-scope. |
| `cache_cost_release_gate` | Promotion gate binding prompt cache policy, cache-key policy, invalidation triggers, provider rate-limit records, usage budget, retry/backoff policy, low-priority processing policy, cost attribution, stale-cache risk, correctness/rights review, and rollback condition. |

## Canon Decision

This note is canon-ready for Agent Studio route-release design. Agent Studio should treat caching and cost controls as governed runtime behavior, not just optimization. A production route needs a cache policy, cache-key scope, invalidation triggers, provider rate-limit record, usage budget, cost attribution, and stale-cache risk review. For source-backed routes, correctness and rights freshness outrank cache hit rate.

Model gateway routing extends this decision from individual provider calls to the shared control plane. A gateway cache hit, virtual-key budget rejection, provider fallback, or dynamic-route version change is product behavior and should produce route-decision, cache-event, budget-event, and canary records before it is trusted in production.
