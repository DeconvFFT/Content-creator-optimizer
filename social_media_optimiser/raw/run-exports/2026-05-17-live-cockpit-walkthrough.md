---
type: raw-run-export
project: agent-studio
status: captured
updated: 2026-05-17
run_id: f34c732f-1168-4582-86f7-8bd6efcd0b02
source_artifacts:
  - artifacts/live-cockpit-walkthrough/demo-run.json
  - artifacts/live-cockpit-walkthrough/cockpit-walkthrough-ledger-refreshed.json
  - artifacts/live-cockpit-walkthrough/model-routing-ledger.json
  - artifacts/live-cockpit-walkthrough/provider-ops-ledger.json
  - artifacts/live-cockpit-walkthrough/checkpoint.json
derived_wiki:
  - [[../../01-work-tracking/Current Sprint]]
  - [[../../wiki/ops/active-codex-context]]
---

# Raw Run Export - Live Cockpit Walkthrough

## Summary

Live Postgres + pgvector was started through Docker and `setup-durable-storage` completed successfully. A provider-free cockpit demo run was seeded against the real Postgres store, then checkpoint, model-routing, provider-ops, runtime-health, and cockpit-walkthrough ledgers were recorded.

## Run

- Run id: `f34c732f-1168-4582-86f7-8bd6efcd0b02`
- Latest walkthrough status: `blocked`
- Required walkthrough readiness: `4/6` required steps ready.
- Runtime health: `ready`

## Ready Evidence

- `runtime-health`: ready after live Postgres store evidence and a run checkpoint were recorded.
- `provider-free-demo`: ready with seeded sources, claims, artifacts, feedback gate, and project memory.
- `source-ledger-coverage`: ready with accepted retrieval source coverage and supported claims.
- `provider-observability`: ready after model-routing and provider-operations ledgers were recorded.

## Remaining Blockers

- `provider-readiness`: blocked because provider keys/endpoints are not configured in `.env`.
- `realtime-provider-smoke`: blocked because provider-backed smoke is not ready, no realtime session is recorded, no realtime dialogue ledger exists, and no realtime turn is recorded.
- `feedback-loop`: optional needs review because the demo feedback gate remains open.

## Provider Config Observed

No secret values were printed or stored. Presence check showed:

- Missing: `HF_TOKEN`, Gemma endpoint URLs, OpenAI Realtime key, ElevenLabs key/agent id, Cartesia key/voice id, Tavily key, SerpAPI key.
- Selected defaults: `openai_realtime` and `tavily`.

## Database Evidence

Postgres artifact counts for the run included:

- `cockpit_walkthrough_ledger`: 2
- `runtime_health_ledger`: 2
- `model_routing_ledger`: 1
- `provider_operations_ledger`: 1
- `retrieval_quality_ledger`: 1
- `source_ledger`: 1
- `post`, `reel_script`, `substack_article`: 1 each

## Next

Configure provider credentials/endpoints, create a realtime session, route one voice/text turn, build realtime dialogue ledger, resolve or intentionally keep open the demo feedback gate, then rebuild `POST /api/runs/{run_id}/cockpit-walkthrough-ledger`.

## Addendum - 2026-05-17 Realtime Rehearsal

After adding provider-free realtime rehearsal mode, the live run recorded:

- Rehearsal session id: `7e8fd8e2-085c-4092-b3a0-a93a1f810a67`
- Rehearsal provider: `local_realtime_rehearsal`
- Rehearsal metadata: `dry_run = true`, `not_provider_backed = true`, `provider_under_test = openai_realtime`
- Routed realtime turn summary: `Routed realtime voice turn as revise_content.`
- Realtime dialogue ledger status: `needs_attention` because one host follow-up task remains pending.
- Latest cockpit walkthrough status: `blocked`
- Latest required readiness under the stricter provider-backed smoke check: `3/6` ready, `1/6` needs review, `2/6` blocked.

The realtime provider smoke step now shows rehearsal evidence but remains blocked until provider readiness is true and a non-rehearsal `openai_realtime` session exists.
