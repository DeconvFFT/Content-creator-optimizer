---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
  - https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
related:
  - "[[../../03-patterns/system-design/production-agent-studio-canon]]"
  - "[[../../03-patterns/agent-systems/long-running-agent-patterns]]"
  - "[[../../03-patterns/inference/realtime-and-inference-patterns]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# OpenTelemetry GenAI Observability

## Reading Status

Direct-read synthesis from the official OpenTelemetry semantic conventions for GenAI client spans and GenAI agent/framework spans. Current-source check on 2026-05-18 confirmed OpenTelemetry semantic conventions 1.41.0 still mark GenAI spans as Development and preserve a transition/opt-in model for newer GenAI conventions. Agent Studio should therefore treat exact attribute names as a compatibility target with version pinning rather than a permanent database contract.

## Why It Matters

Agent Studio needs a trace model that can survive provider swaps, agent topology changes, and privacy review. OpenTelemetry gives a vendor-neutral vocabulary for the important runtime boundaries: model inference, embeddings, retrieval, tool execution, agent creation, agent invocation, workflow invocation, conversation/session correlation, usage tokens, errors, and opt-in content capture.

The key design lesson is separation: a trace should record operations, timing, model/provider identity, token usage, data-source identity, tool names, and errors by default, while prompt bodies, output messages, system instructions, retrieval query text, tool definitions, and tool outputs should be explicit opt-in fields behind a redaction policy.

OpenTelemetry now also exposes GenAI semantic-convention groups for MCP and provider-specific systems. Agent Studio should use those as exporter/adapter compatibility targets, while keeping local route/run/source/artifact/checkpoint IDs as the product truth.

## Trace Boundary Model

Use operation-specific spans rather than a single generic model-call record:

- `chat`, `generate_content`, and `text_completion` spans represent response-generating model calls.
- `embeddings` spans represent representation generation and need embedding dimension/encoding information where available.
- `retrieval` spans represent data-source search and should capture data-source identity, document ids, scores, and query lineage without assuming query text is always safe to persist.
- `execute_tool` spans represent application or framework tool execution and should be internal spans when the tool runs inside Agent Studio.
- `create_agent`, `invoke_agent`, and `invoke_workflow` spans distinguish remote agent services, local framework agents, and workflow-level orchestration.

This split gives reviewers a way to answer whether a failure came from search, reranking, context assembly, tool behavior, provider latency, model behavior, workflow routing, or agent handoff.

Because the conventions are still development status, every route release that depends on these spans should record the emitted semantic-convention version and whether the implementation uses legacy, latest-experimental, provider-specific, or local-normalized fields.

## GenAI Client Spans

The required minimum for provider calls is operation name, provider name, error type when failed, and model/server identity where available. Agent Studio should store requested model and response model separately because gateways, hosted endpoints, fallbacks, or aliases can make them differ.

Recommended runtime evidence includes temperature/top-p/top-k/max-token settings, response id, finish reasons, streaming flag, time to first chunk, input tokens, output tokens, cache-created tokens, cache-read tokens, and reasoning-token counts when exposed by the provider. These fields let the route ledger compare quality, latency, and cost without reading raw prompts.

The current transition guidance matters operationally: instrumentation may continue emitting older GenAI conventions unless explicitly opted into latest experimental behavior. Agent Studio should capture semantic-convention version and opt-in setting next to span ingestion so dashboards do not mix incompatible attribute names silently.

For streaming calls, first-chunk latency is a first-class signal. It should sit beside TTFT, TPOT, queue time, retrieval time, rerank time, and end-to-end route latency in Agent Studio serving records.

## Agent And Tool Spans

Agent spans extend GenAI spans; they do not replace lower-level model and tool spans. Agent Studio should represent the hierarchy as:

- workflow span: route-level orchestration;
- agent span: specialist or remote-agent invocation;
- model spans: provider calls made by that agent;
- retrieval spans: grounding searches used by the agent;
- tool spans: side-effecting or information-gathering calls;
- checkpoint/resume events: durable state transitions outside the provider call.

Tool spans need names, side-effect class, arguments/output retention policy, error class, latency, and associated approval or idempotency records. For MCP-like or A2A-like calls, tool and agent spans should also link to protocol security scheme, task id, artifact refs, and stream events.

## Privacy And Redaction

OpenTelemetry treats input messages, output messages, system instructions, retrieval query text, retrieval documents, and tool definitions as content-bearing fields. Several are opt-in or explicitly privacy-sensitive. Agent Studio should therefore default to content references, hashes, structured summaries, and artifact ids rather than raw bodies.

The retention contract should be attached before a route is promoted:

- whether content-bearing telemetry is disabled, redacted, sampled, truncated, or exported;
- whether local book/user material can enter traces;
- who can read rich traces;
- how long prompts, outputs, screenshots, source chunks, and tool outputs are retained;
- what anonymizer/redactor version processed an exported trace.

## Datastore Implications

Add or strengthen these schema concepts:

- `genai_trace_span`: normalized operation span with parent/child links, operation name, provider name, span kind, status, error type, route/run ids, model ids, server address, timing, and sampling decision inputs.
- `model_usage_record`: token/cost counters by request, response, cache creation, cache read, and reasoning tokens.
- `retrieval_span_record`: data-source id, query refs, retrieved document refs, scores, filters, and sensitivity label.
- `tool_invocation_span`: tool name/version, side-effect class, approval refs, idempotency refs, argument/output artifact refs, latency, and error type.
- `agent_invocation_span`: agent name/id, operation type, workflow id, conversation/session id, task refs, child span refs, and handoff refs.
- `trace_content_policy`: route-level rule for whether messages, instructions, retrieval query text, documents, and tool definitions may be recorded.
- `observability_semconv_release_gate`: promotion decision proving semantic-convention version, opt-in mode, span taxonomy, provider/model mapping, trace-content policy, redaction/export policy, token/cost counters, first-chunk latency capture, tool/agent/retrieval span linkage, sampling policy, and compatibility tests.

These objects should be queryable independently from the richer `run_trace` so observability dashboards can work without loading private content.

## Canon Cross-Check

This note is now canon-ready because it cross-checks against LangSmith Agent Server runtime, LangChain memory/checkpointing, OpenAI evals, OpenAI Responses runtime, Anthropic tool/computer-use runtime, privacy/retention, agent-route canon, HLD, and datastore schema. The stable decision is provider-neutral span records plus product-native route/run/source/artifact/checkpoint IDs.

OpenTelemetry owns the operation taxonomy and attribute compatibility surface. Agent Studio owns release evidence, redaction, retention, route identity, source/artifact lineage, eval linkage, and dashboards. Hosted observability products can read or display traces, but they are not the sole source of truth.

## Agent Studio Design Implications

- Do not treat LangSmith, provider dashboards, or raw application logs as the only source of truth. Agent Studio needs a provider-neutral span model that can export to or ingest from observability systems.
- Keep operation-level spans stable even if provider SDKs change. Store provider-specific attributes as extensions, not as the only schema.
- Use conversation/session ids to correlate turns, but keep route ids, workflow ids, checkpoints, source snapshots, and artifact ids as first-class product objects.
- Trace sampling should happen with operation/provider/model/server metadata available at span creation time; do not rely on prompt text to decide sampling.
- Raw prompt/output capture is a risk feature, not the default observability feature.
- Promote observability changes only when semantic-convention version, content capture, redaction/export, sampling, provider mapping, token/cost usage, first-chunk latency, and span-linkage tests are explicit.
