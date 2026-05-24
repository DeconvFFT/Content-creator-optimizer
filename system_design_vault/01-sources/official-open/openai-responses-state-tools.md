---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_public
provenance_status: official_openai_api_docs_direct_read
sources:
  - https://developers.openai.com/api/docs/guides/migrate-to-responses
  - https://developers.openai.com/api/docs/guides/conversation-state
  - https://developers.openai.com/api/docs/guides/tools
  - https://developers.openai.com/api/docs/guides/function-calling
  - https://developers.openai.com/api/docs/guides/tools-connectors-mcp
  - https://developers.openai.com/api/docs/guides/background
  - https://developers.openai.com/api/docs/guides/streaming-responses
---

# OpenAI Responses State And Tool Runtime

## Scope

Direct-read synthesis from current official OpenAI API documentation on the Responses API, conversation state, tools, function calling, MCP/connectors, background mode, and streaming. This note captures Agent Studio route and datastore implications. It stores no copied code blocks, raw docs text, or long excerpts.

Current-source check: OpenAI's current docs expose Responses API as the core text/agentic primitive, list hosted tools including web search, MCP/connectors, skills, shell, computer use, file search, tool search, apply patch, local shell, image generation, and code interpreter, and split run-scale behavior across conversation state, background mode, streaming, WebSocket mode, webhooks, file inputs, prompt caching, safety checks, and production deployment guidance.

## Core Pattern

OpenAI positions the Responses API as the primary primitive for new agentic applications: a typed output stream of items, built-in and custom tools, multimodal input, stateful continuation, background execution, and streaming events. The durable Agent Studio lesson is that model output is no longer just a final message. A run can contain messages, reasoning context, tool calls, tool outputs, MCP tool-list events, approvals, streaming deltas, background status changes, and final artifacts.

Agent Studio should therefore store an OpenAI-backed route as a typed execution timeline, not as a chat transcript.

## State Contract

Responses can continue from prior response IDs, or a product can manage context manually. That creates three different state surfaces:

- provider-side response state;
- Agent Studio's own durable session/checkpoint state;
- product-visible conversation or artifact state.

Do not collapse them. A route should record whether it uses provider continuation, manual context reconstruction, a persistent conversation object, or stateless encrypted reasoning. It should also record retention posture, because provider-stored response objects, background polling, and conversation persistence have different data-retention implications.

For Agent Studio, `previous_response_id` is a convenience pointer, not the source of truth. The local datastore still needs enough route state, source refs, tool outputs, approval records, and artifact hashes to audit, replay, fork, or migrate a run when provider state expires or is unavailable.

## Tool Runtime Contract

OpenAI tools fall into several operational classes:

- built-in retrieval or web tools;
- built-in computer/code/image tools;
- developer-defined function calls;
- remote MCP servers and connectors;
- deferred tool discovery through tool search for supported models.

Agent Studio should treat each class as a separate permission and observability surface. A function call with a stable in-house schema is different from a remote MCP call whose tool definitions are imported from a third-party server at runtime.

Every route release should declare:

- available tools and allowed-tools subset;
- strict schema mode and JSON Schema compatibility;
- side-effect class and approval policy;
- tool-definition snapshot/hash;
- tool-call output sensitivity;
- retry/idempotency behavior;
- whether tool results are fed back into the model, stored as artifacts, or both.

## MCP And Connector Risk

OpenAI's MCP/connectors docs make remote tool servers a first-class runtime option, but also a trust boundary. Agent Studio should log both the imported tool list and each tool call. Approval should remain required for sensitive actions until the server, action type, arguments, and data-sharing pattern have been reviewed.

Production rules:

- prefer official provider-hosted MCP servers over aggregators or proxy servers;
- record the server URL, auth scope, transport, imported tool definitions, and allowed tools;
- require approval for sensitive actions, external mutation, or broad data export;
- review hidden instructions or prompt-injection risk in tool outputs;
- treat URLs returned by tool calls as untrusted until domain policy checks pass;
- maintain a periodic review record of data sent to third-party MCP servers.

## Background And Streaming Runtime

Background mode is useful for long-running reasoning or generation, but it is not just a latency flag. It changes the run lifecycle into queued, in-progress, terminal-status polling, and result retrieval. It also has retention and ZDR implications.

Streaming uses typed semantic events rather than a single final blob. The UI, trace store, and eval layer should be able to consume selected event types without treating partial deltas as final artifacts.

Agent Studio should separate:

- `response_request`: the initial provider call and parameters;
- `response_lifecycle_event`: queued, in-progress, failed, completed, cancelled, expired;
- `response_stream_event`: typed event payloads for UI and trace replay;
- `response_output_item`: final typed model/tool/message items;
- `provider_state_ref`: provider response/conversation IDs with retention and expiry expectations.

## Migration Implications

Moving from chat-only semantics to Responses semantics changes the route contract:

- output items are typed, not only assistant messages;
- function/tool definitions have different request and response shapes;
- strict function schemas should be assumed and tested;
- structured-output configuration belongs with the response text format contract;
- statefulness should be explicit, especially for ZDR or private-source routes;
- long-running routes need background lifecycle handling;
- realtime or WebSocket routes should share the same continuation semantics but use transport-specific event records.

Agent Studio should support provider-specific adapters but keep a provider-neutral internal trace. That lets OpenAI Responses, Anthropic tool use, LangGraph checkpoints, A2A tasks, and MCP server calls map into comparable route evidence.

## Canon Cross-Check

The agent-route canon already treats provider runtime state as evidence, not authority. This note is canon for OpenAI-specific runtime objects: provider response IDs, typed response items, provider-side continuation, persistent conversations, background lifecycle, streaming semantic events, hosted tools, function calls, MCP import events, and connector tool calls.

The Anthropic tool/computer-use and OpenAI guardrail notes own high-authority action boundaries. This note owns the Responses-specific packaging of those actions: tool definition snapshots, allowed-tools subsets, strict schema state, approval refs, tool-call item ordering, output sensitivity labels, and model-visible re-ingestion of tool results.

The privacy and retention notes own data-use and retention policy. This note supplies the provider-state evidence: `store` posture, previous-response links, conversation refs, background polling state, provider expiry expectations, ZDR/private-source caveats, and local fallback context needed when provider-side state is unavailable.

## Datastore Additions

- `provider_response_record`: provider, response ID, model snapshot, request hash, store flag, background flag, previous response ref, conversation ref, retention class, and terminal status.
- `provider_response_item`: typed output item with item type, provider item ID, parent response, model-visible order, content/artifact hash, sensitivity label, and validation status.
- `provider_state_ref`: provider-side state pointer with retention/expiry, replay suitability, ZDR compatibility, and local fallback context refs.
- `tool_definition_snapshot`: tool name/type, schema hash, strict mode, allowed-tools policy, imported-from-MCP flag, owner, and release version.
- `tool_call_item`: tool call ID, tool definition ref, arguments hash, approval ref, output artifact ref, error/status, latency, cost, and retry/idempotency key.
- `mcp_tool_import_event`: server ref, transport, auth scope, imported tool list hash, allowed/rejected tool list, review status, and created_at.
- `response_lifecycle_event`: provider response ref, event type, status, timestamp, terminal reason, polling attempt, and error summary.
- `response_stream_event`: provider response ref, event type, sequence number, item ref, content delta hash, UI visibility, and retention policy.
- `provider_route_capability_matrix`: route/provider/model support for tools, MCP, structured outputs, streaming, background mode, multimodal input, and state mode.
- `provider_runtime_release_gate`: promotion gate for Responses-backed routes linking provider-state policy, local replay fallback, store/retention review, background lifecycle handling, streaming finalization policy, tool-definition snapshots, MCP import reviews, strict-schema tests, approval policy, and rollback behavior.

## Release Gates

Do not promote an OpenAI Responses-backed route when:

- provider state is the only replay/audit mechanism;
- `store` and retention posture are not declared;
- background mode is enabled without lifecycle polling, terminal-state handling, and retention review;
- streaming deltas can be mistaken for final approved artifacts;
- remote MCP tools can perform sensitive actions without approval;
- imported MCP tool definitions are not snapshotted;
- tool schemas are not strict or are not tested as model-facing interfaces;
- allowed-tools subsets are not recorded;
- tool outputs can inject privileged instructions into later tool calls;
- ZDR/private-source routes depend on provider-side state without an approved alternative.
- provider runtime changes lack a release gate proving local audit/replay fallback, retention review, background/streaming lifecycle handling, tool/MCP snapshots, strict-schema tests, and approval boundaries.

## Agent Studio Decision

Use OpenAI Responses as a provider runtime adapter, not as the whole Agent Studio state model. The product should preserve provider response IDs and typed items, but the authoritative system-design ledger remains local: route release, context assembly, tool definitions, tool calls, approvals, source evidence, streaming events, background lifecycle, artifacts, evals, and retention policy.
