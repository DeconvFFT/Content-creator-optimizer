---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_source_note
rights_status: official_public
source_urls:
  - https://docs.langchain.com/langsmith/deployment
  - https://docs.langchain.com/langsmith/agent-server
  - https://docs.langchain.com/oss/python/langgraph/application-structure
  - https://docs.langchain.com/langsmith/assistants
  - https://docs.langchain.com/langsmith/use-threads
  - https://docs.langchain.com/langsmith/streaming
  - https://docs.langchain.com/oss/python/langgraph/interrupts
  - https://docs.langchain.com/oss/python/langgraph/use-time-travel
  - https://docs.langchain.com/langsmith/cron-jobs
  - https://docs.langchain.com/langsmith/core-capabilities
  - https://docs.langchain.com/langsmith/agent-server-scale
---

# LangSmith Agent Server Deployment Runtime

## Direct-Read Scope

This note is original synthesis from current official LangChain/LangSmith docs for LangSmith Deployment, Agent Server, LangGraph application structure, assistants, threads, streaming, interrupts, time travel, cron jobs, core capabilities, and Agent Server scale guidance. Current-source check on 2026-05-18 confirmed Agent Server still centers assistants, threads, runs, cron jobs, persistence, task queues, graph deployments, joinable/resumable streaming, core MCP/A2A/webhook capabilities, and scale controls.

It extends the earlier LangChain memory/checkpoint note from local graph semantics into deployment/runtime semantics. No raw documentation text, copied code, API payload dumps, or long excerpts are stored here.

## Runtime Model

LangSmith Deployment frames production agent hosting as a workflow orchestration runtime for stateful, long-running agents. The transferable architecture is Agent Server: one deployment contains one or more graphs, persistence, and a task queue. Cloud, standalone, hybrid, and self-hosted options can run the same runtime/API shape while changing who owns infrastructure and data-plane operations.

For Agent Studio, this is the closest official counterpart to the desired local-first durable orchestrator:

- a graph is the executable workflow blueprint;
- an assistant is a graph plus configuration;
- a thread is persistent state for repeated or long-running interaction;
- a run is one execution of an assistant on a thread or threadless input;
- task queue and persistence are runtime dependencies, not application conveniences;
- Studio/observability/evals are operating surfaces around the same graph.

Agent Studio should preserve this vocabulary even if the first implementation is local Postgres plus a custom worker. It prevents the product from treating a chat completion, a graph definition, and a user-specific configured agent as the same object.

Current docs make the persistence boundary explicit: core resources such as assistants, threads, runs, and cron jobs are stored in PostgreSQL; checkpoints are short-term execution memory; stores are long-term memory; Redis is used for signaling, cancellation, and streaming pub/sub rather than durable user/run data. Agent Studio should preserve that split even if it does not use LangSmith.

## Application Packaging

The LangGraph application structure docs require a configuration file, graph entrypoints, dependency specification, and environment variables. That maps directly to Agent Studio release evidence: a route graph should not be promoted unless the graph ID, source path, dependency lock, environment variable policy, secret boundary, and deploy target are known.

This also separates graph code from assistant configuration. One graph can support multiple assistants with different prompts, models, tools, environments, or customer/user variants. That is a useful Agent Studio pattern for platform-specific content routes: keep the durable workflow shape stable while varying model, prompt, persona, language, or tool policy through versioned assistant configs.

## Assistants, Threads, And Runs

Assistants are versioned configurations for a deployed graph. Editing assistant configuration creates a version history and allows promotion/rollback without changing graph code. Agent Studio should therefore treat prompt/model/tool changes as assistant-version releases, not as invisible prompt edits.

Threads hold state across runs. They support multi-turn conversations, long-running tasks, user-specific state, state inspection, copying, and prepopulated state for migration or testing. Threads are not the same as long-term semantic memory: they are execution/conversation containers. Agent Studio should use threads for route continuity and checkpoint history, then promote durable memory separately through evidence-backed memory records.

Runs combine assistant and thread. A run can stream updates, run in the background, join an active stream, or be observed through thread-level streaming. This gives Agent Studio a runtime contract for the cockpit UI: user navigation or client disconnect should not cancel server-side work unless the user explicitly cancels it.

## Streaming, Join, And UI Resilience

The streaming docs distinguish single-run streaming from thread streaming, and they support joining an active background run. This is critical for a realtime content studio:

- run streaming is for one interaction or job;
- thread streaming is for a durable workspace timeline that can include multiple runs, resumptions, and background updates;
- join/rejoin avoids coupling UI connection lifetime to server execution lifetime;
- stream mode should be route-specific: messages, updates, custom events, debug, or final state have different privacy and UX costs.

Agent Studio should store stream subscriptions and last-event checkpoints. A cockpit tab refresh, mobile sleep, or network drop should reattach to the run/thread rather than starting duplicate work or losing progress.

Thread streaming is the important product-level abstraction. A run stream is one execution view; a thread stream can represent a durable workspace timeline with multiple runs, resumptions, and background updates. Agent Studio's cockpit should prefer join/rejoin with last event IDs over polling or duplicate run starts.

## Human-In-The-Loop And Time Travel

LangGraph interrupts pause execution, persist state, and resume with explicit external input. The docs also warn that side effects before an interrupt need idempotency, and that replay/time travel re-executes nodes after the selected checkpoint.

Agent Studio should model interrupts as typed work items:

- approval interrupt for publish/delete/account/tool side effects;
- edit-state interrupt for reviewer repair of an artifact or plan;
- clarification interrupt for missing source, rights, audience, or platform decision;
- resume command that references the exact checkpoint/run/thread;
- idempotency policy for any side effect before or after the interrupt.

Time travel is useful for debugging and alternative drafts, but it is not a cache read. Replaying after a checkpoint can re-run model calls, tools, APIs, and interrupts. Agent Studio should mark replay/fork runs as experimental until their side-effect safety and provenance are reviewed.

## Scheduled And Background Work

Cron jobs provide scheduled assistant execution against a thread/input and run in the background. This maps to Agent Studio's autonomous ingestion lane: source refresh, stale-link checks, eval backfills, weekly vault audits, and memory consolidation can be scheduled runs rather than ad hoc scripts.

The important design constraint is that scheduled runs still need source scope, route version, thread state, input payload, timezone/UTC policy, idempotency key, owner, and output/eval policy. A cron that silently updates shared memory or source status is an unreviewed agent.

## Protocols, Webhooks, And Scale

The core-capabilities docs name MCP endpoint, A2A endpoint, webhooks, distributed tracing, double-texting, and streaming/HITL as Agent Server capabilities. For Agent Studio, this reinforces a clean boundary:

- expose agents as capabilities through MCP/A2A only after assistant config, tool scopes, and auth are versioned;
- handle external run events through webhook subscriptions with delivery, retry, and signature policy;
- define double-texting behavior before accepting new user input while a run is active;
- carry distributed trace context across API, graph, model, tool, and background worker boundaries.

Scale guidance adds operational discipline: use filters, TTLs for old thread data, join/stream instead of polling, and configure autoscaling for bursty self-hosted deployments. Agent Studio should treat polling-heavy dashboards, unbounded thread retention, and shared worker queues as design smells.

The Agent Server runtime architecture also separates API servers from queue workers. API servers create/read/stream, while queue workers execute graphs, acquire leases, write checkpoints, and release run slots. Agent Studio should model this split as runtime release evidence: worker pool, queue backend, lease policy, cancellation signal, stream pub/sub, per-thread concurrency, autoscaling target, and orphan-run prevention.

## Canon Cross-Check

This note is now canon-ready because it cross-checks against the LangChain memory/checkpoint note, A2A handoff note, MCP tooling note, async workflow/queue reliability, autoscaling/admission control, agent-route canon, long-running-agent patterns, HLD, and datastore schema. The boundary is stable:

- LangGraph memory owns checkpoint and memory semantics;
- LangSmith Agent Server owns deployed runtime objects and operational topology;
- A2A/MCP own protocol exposure;
- async queue and autoscaling notes own queue/retry/backpressure and capacity evidence;
- Agent Studio owns the local ledger that makes these runtime objects auditable.

The promotion rule is that a long-running agent route is not production-ready because a graph runs once. It needs graph blueprint, assistant config/version, thread state, run record, task queue, persistence backend, worker topology, stream subscription, interrupt/time-travel policy, scheduled-job policy, protocol endpoint policy, webhook policy, double-texting behavior, scale policy, and rollback.

## Agent Studio Datastore Additions

- `agent_server_deployment`: deployment target, hosting mode, runtime version, graph refs, persistence backend, task-queue backend, control-plane owner, and data-plane owner.
- `langgraph_application_spec`: config file ref, graph entrypoints, dependency spec, env var policy, secret boundary, monorepo path, and build/deploy refs.
- `graph_blueprint_record`: graph ID, code artifact, input/output state schema refs, node/edge contract refs, framework version, and compatibility status.
- `assistant_configuration`: assistant ID, graph ID, prompt/model/tool/config values, owner, environment, personalization scope, and active status.
- `assistant_version_record`: assistant config hash, changed fields, evaluation refs, promoted/rollback state, created by, and created at.
- `thread_state_container`: thread ID, graph/assistant eligibility, current checkpoint, status, metadata, TTL policy, privacy scope, and copied-from ref.
- `deployment_run_record`: run ID, thread ID, assistant version, input artifact refs, stream mode, background flag, status, cost/latency summary, and terminal state.
- `run_stream_subscription`: run/thread stream, subscriber, stream modes, last event ID, reconnect policy, visibility policy, and retention.
- `hitl_interrupt_work_item`: interrupt ID, run ID, thread ID, checkpoint ref, payload schema, reviewer/actor, decision, resume command, side-effect class, and status.
- `time_travel_replay_record`: source checkpoint, replay/fork mode, updated state, re-executed nodes, side-effect risk, comparison refs, and promotion eligibility.
- `scheduled_agent_job`: cron expression, timezone/UTC handling, assistant/thread/input refs, idempotency key policy, owner, next run, and output policy.
- `agent_protocol_endpoint`: MCP or A2A exposure for an assistant/graph with auth policy, capability snapshot, card/tool schema hash, and allowed client classes.
- `agent_webhook_subscription`: event types, target endpoint, signing policy, retry policy, dead-letter policy, and subscriber owner.
- `double_texting_policy`: behavior when new input arrives during active run, queue/cancel/interrupt/fork choice, user-visible status, and conflict policy.
- `agent_server_scale_policy`: filtering policy, thread TTL, polling ban/join-stream rule, autoscaling target, queue depth threshold, and retention budget.
- `agent_server_runtime_release_gate`: promotion decision proving graph blueprint, assistant version, thread/run persistence, queue/worker topology, lease/cancel policy, stream rejoin, interrupt/time-travel policy, scheduled-job policy, protocol endpoint exposure, webhook policy, double-texting behavior, scale/TTL settings, and rollback.

## Design Commitments

- Agent Studio should distinguish graph blueprint, assistant configuration, thread state, run execution, stream subscription, interrupt, and scheduled job.
- Prompt/model/tool config changes should create assistant-version records even when graph code does not change.
- Threads are durable execution state, not long-term semantic memory.
- Streaming should support join/rejoin and thread-level timelines so UI connection loss does not erase server-side work.
- HITL approvals should be typed interrupts with checkpoint refs, resume commands, and idempotency policy.
- Time travel/forking should be marked as replayed execution with side-effect safety review.
- Scheduled ingestion and memory work should run as governed agent jobs, not silent background scripts.
- MCP/A2A/webhook exposure requires versioned capability, auth, retry, and trace records before production use.

## Canon Decision

Agent Studio should model deployed agent execution as a runtime plane with separate graph, assistant, thread, run, stream, interrupt, cron, protocol endpoint, webhook, task queue, worker, and persistence records. The first implementation may be local Postgres and workers, but the datastore should already preserve the runtime split so background ingestion, memory consolidation, source refresh, eval backfills, and user-facing cockpit runs are joinable, resumable, cancellable, observable, and rollback-safe.
