---
name: agent-studio-inference-reliability
description: "Design and operate reliable inference routes. Use when reviewing Gemma/HF endpoints, realtime audio providers, rerankers, streaming, batching, caching, latency/cost budgets, provider readiness, fallbacks, or provider-backed smoke evidence."
---

# Agent Studio Inference Reliability

## Workflow

1. Start with the user experience requirement: realtime dialogue, deep synthesis, multimodal review, retrieval/reranking, image generation, or artifact critique.
2. Define latency, cost, quality, modality, context-window, and availability requirements before selecting a route.
3. Keep realtime speech transport separate from Gemma expert reasoning and multimodal synthesis.
4. For each provider route, record readiness, required environment variables, smoke evidence, timeout policy, fallback policy, and provenance requirements.
5. Use provider-backed smoke tests for production readiness. Provider-free rehearsal is useful for UX checks, but it is not provider proof.
6. Consider streaming, batching, caching, warm pools, model route selection, provider retries, and graceful degradation before scaling a route.
7. Record model routing ledgers and provider operations ledgers when routes change or smoke evidence is collected.
8. Escalate to human review when fallback behavior can change content quality, source grounding, voice continuity, or cost.

## Quality Targets

- Low-latency dialogue: realtime providers handle interruption, turn-taking, and spoken output.
- Strong expert routes: Gemma/HF endpoints handle planning, writing, critique, vision, and synthesis when allowed by agent cards.
- Auditable operations: provider readiness, fallback, latency, and cost decisions are visible in run ledgers.
- Safe degradation: missing credentials or failed providers block or degrade explicitly instead of silently lowering quality.

## Outputs

- `inference_route_review`
- `provider_smoke_plan`
- `latency_cost_budget`
- `fallback_decision`
- `provider_operations_ledger`
- `model_routing_ledger`
