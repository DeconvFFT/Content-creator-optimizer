---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_urls:
  - https://developers.googleblog.com/en/developers-guide-to-ai-agent-protocols/
  - https://a2a-protocol.org/latest/specification/
  - https://adk.dev/runtime/resume/
  - https://developers.googleblog.com/en/build-long-running-ai-agents-that-pause-resume-and-never-lose-context-with-adk/
source_status: official_public
---

# Google A2A Protocols And ADK Resume

## Direct-Read Scope

This pass read Google's official agent-protocol guide, the current A2A specification, ADK's public resume-agent docs, and Google's long-running ADK implementation guide. Current-source check on 2026-05-18 confirmed the A2A site exposes the 1.0.0 specification and the ADK resume page now documents resumability support in ADK Python 1.14.0+ with configurable workflow resumability in 1.16+. This note stores original synthesis only, not source text or code excerpts.

## Protocol Layering

The useful design split is:

- MCP connects an agent to tools, APIs, and data sources.
- A2A connects one agent system to another without requiring shared internals.
- Commerce/UI protocols sit on top only when the route needs purchasing, authorization, or dynamic remote UI.

Agent Studio should therefore avoid one generic "external integration" bucket. Tool access, remote specialist calls, payment authorization, and UI rendering have different contracts, credentials, traces, and failure modes.

## A2A Implementation Lessons

- Discovery is a first-class runtime operation. A remote agent exposes an Agent Card, normally at `/.well-known/agent-card.json`, with identity, endpoint, capabilities, skills, auth, protocol support, and version information.
- A2A is task-centered. Complex work returns a `Task` rather than only a final message. The task carries status, context, history, artifacts, metadata, and terminal states.
- Content is typed into parts. Text, file references, and structured data should not be collapsed into a single prompt string.
- Streaming and async are built into the protocol shape. A route can send a message, stream task status/artifact updates, subscribe to an existing task, or configure push notifications for long-running work.
- The spec deliberately supports opaque remote execution. A caller should not need the remote agent's private memory, tool graph, chain of thought, or implementation language.
- Security belongs in the card and transport boundary, not in ad hoc prompt text. The card declares security schemes; credentials should be handled out of band or through standard auth surfaces, and cards should not expose secrets or internal implementation detail.
- Agent-card freshness matters. Version, cache headers, ETags, signatures, and capability validation affect whether a route can safely trust a remote agent card.
- Task monitoring is a protocol surface. A2A includes get/list/cancel task behavior, stream subscription to existing tasks, terminal states, push-notification config, webhook delivery, and idempotent deletion of notification configs. Agent Studio should not model remote specialist calls as one fire-and-forget chat message.

## ADK Resume Lessons

- Resume is a state problem, not a prompt trick. Long-running routes need persistent session storage so a restart, cold start, or idle period does not erase in-flight work.
- Human approval and external-event waiting should be explicit state transitions. A route pauses with pending work, then resumes when a function response, webhook, or event arrives.
- State deltas should be small and typed. The resume path should update session state with the minimum fact needed to advance the workflow.
- Event-driven wakeup beats polling. Webhooks or task notifications should hydrate a persisted session and continue the run from a checkpoint.
- Tool callbacks and after-call processing are the right place to validate, override, or annotate state changes before the model continues.
- Resume is not automatic for every custom agent. ADK's docs call out that custom agents need explicit work to support incremental resume. Agent Studio should record resume eligibility, invocation/session IDs, event-history availability, and custom-agent resume support before claiming a route is durable.

## Canon Cross-Check

This note is now canon-ready because it cross-checks against the MCP tooling note, agent-route canon, long-running-agent patterns, OpenAI Responses runtime, LangSmith Agent Server runtime, Google Agent Platform runtime, HLD, and datastore schema. The shared boundary is clear: A2A owns agent identity, discovery, skill selection, task lifecycle, typed artifacts, streaming/subscription, push notifications, cancellation, and opaque remote execution. MCP owns tools/resources/prompts. Provider runtime notes own provider-specific state. Workflow/runtime notes own local checkpointing and replay.

Agent Studio should therefore treat A2A-style handoff as a release-managed protocol boundary. A route can remain local-first, but it should already produce the records needed for public A2A compatibility: card hash, selected skill, task ID, context ID, stream events, artifact parts, auth scheme, push subscription, cancellation policy, idempotency key, resume token, and terminal outcome.

## Agent Studio Design Implications

- Add a local Agent Card registry before exposing public A2A. Internal agents should have the same shape: name, owner, version, endpoint or route ref, skills, input/output modes, security, rate limits, eval coverage, and redaction policy.
- Treat remote agents as governed dependencies. A route release should pin the card version or hash it used, the selected skill, auth boundary, and fallback policy.
- Replace opaque handoffs with A2A-like tasks. Every specialist invocation should create a task record with context ID, lifecycle status, artifacts, stream events, cancellation policy, and terminal outcome.
- Store artifacts as typed parts. Drafts, source sets, media files, structured JSON, citations, and eval results need separate references so downstream routes can validate them without parsing chat text.
- Make long-running routes resumable by construction. Runs need durable session state, event log replay, external-event subscriptions, human-resume requests, idempotency keys, and wakeup traces.
- Keep local compatibility pragmatic. V1 does not need to expose a public `/.well-known/agent-card.json`, but its internal schema should be close enough that public A2A support is an adapter, not a rewrite.

## Datastore Requirements

- `agent_card_record`: remote/local card identity, owner, version, endpoint, protocols, capabilities, skills, security schemes, supported modalities, cache metadata, signature status, and trust tier.
- `agent_skill_record`: skill ID, card ref, description, input modes, output modes, task type, eval coverage, rate limits, and failure policy.
- `a2a_task_record`: task ID, context ID, caller route, remote card/skill refs, status, message refs, artifact refs, metadata, cancellation status, terminal state, and error summary.
- `agent_artifact_part_record`: artifact ID, task ID, part type, storage ref, content hash, schema ref, rights/sensitivity label, and validation status.
- `agent_stream_event`: task ID, event type, sequence, status delta, artifact delta, emitted_at, source endpoint, and replay status.
- `push_notification_subscription`: task ID, webhook URL ref, auth profile, subscribed event types, expiry, delivery attempts, last delivery status, and revocation state.
- `human_resume_request`: run/task ID, approval or external fact needed, requested action, deadline, approved/denied/provided value, reviewer, and resume event ref.
- `session_store_record`: session ID, storage backend, checkpoint policy, state schema, last persisted event, hydration status, and retention/redaction policy.
- `protocol_security_scheme`: card or endpoint ref, auth method, credential scope, token storage policy, rotation cadence, and least-privilege review.
- `protocol_idempotency_record`: route/task operation, idempotency key, request hash, first response ref, retry status, conflict policy, and expiry.
- `a2a_handoff_release_gate`: promotion decision proving card freshness/hash, selected skill, auth boundary, task lifecycle mapping, stream/push/cancel support, artifact-part validation, idempotency, resume eligibility, fallback route, and terminal-state handling.

## Failure Modes

- Treating a remote agent card as permanently true after one fetch.
- Passing credentials or privileged instructions through task payloads.
- Storing only final text and losing task status, intermediate artifacts, or cancellation evidence.
- Building resume as a chat-memory summary instead of durable state plus replayable events.
- Using public A2A exposure before internal agent cards, auth, tracing, and eval coverage exist.
- Claiming ADK/agent resume without proving workflow resumability, invocation/session recovery, event history, custom-agent resume support, and external-event wakeup behavior.

## Next Targets

- Cross-check Agent Studio's internal agent-card fields against A2A Agent Card required and optional fields before implementation.
- Add route-release checks that reject remote-agent calls without card hash, selected skill, auth scope, and fallback policy.
- Evaluate whether long-running social-media generation workflows should expose push-notification style updates to the UI.

## Canon Decision

Agent Studio should model every specialist handoff as an A2A-like task even before it exposes public A2A endpoints. Remote or local specialist routes need a versioned Agent Card, selected skill, task lifecycle, typed artifact parts, stream/push events, cancellation semantics, auth boundary, idempotency key, resume policy, terminal state, and fallback. Public A2A exposure is a later adapter; the durable task/handoff ledger is required now.
