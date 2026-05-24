---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://modelcontextprotocol.io/specification/2025-11-25/basic
  - https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
  - https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
  - https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
  - https://modelcontextprotocol.io/specification/2025-11-25/server/tools
  - https://modelcontextprotocol.io/specification/2025-11-25/server/resources
  - https://modelcontextprotocol.io/specification/2025-11-25/server/prompts
related:
  - "[[google-a2a-protocols]]"
  - "[[opentelemetry-genai-observability]]"
  - "[[../../03-patterns/agent-systems/agent-route-architecture-canon]]"
  - "[[../../03-patterns/security/genai-security-canon]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Model Context Protocol Tooling

## Reading Status

Direct-read synthesis from the official Model Context Protocol 2025-11-25 specification pages for the base protocol, lifecycle, transports, authorization, tools, resources, and prompts. Current-source check on 2026-05-18 confirmed 2025-11-25 is the latest visible specification version and still defines MCP around JSON-RPC, lifecycle/capability negotiation, HTTP authorization, stdio and Streamable HTTP transports, server tools/resources/prompts, and client roots/sampling/elicitation/tasks. This note is about Agent Studio's connector and tool-control architecture; it does not store copied schemas or protocol examples.

## Why It Matters

Agent Studio needs three different interoperability layers:

- A2A-style agent protocols for specialist identity, skills, tasks, artifacts, and handoffs.
- MCP-style context protocols for model-accessible tools, resources, and prompt templates.
- Observability protocols for spans, trace events, token usage, security, and audit.

MCP is the right mental model for the second layer. It gives Agent Studio a way to expose local project files, source ledgers, vault notes, search indexes, browser/computer-use actions, and narrow utility APIs without hardcoding every integration into the core agent route.

## Protocol Shape

MCP uses JSON-RPC messages across a session with initialization, capability negotiation, request/response, notifications, errors, and optional features. Agent Studio should model MCP servers as versioned integration endpoints, not anonymous utility libraries.

The product-relevant boundary is capability negotiation. A route should know whether a server exposes tools, resources, prompts, logging, completions, subscriptions, tasks, sampling, roots, or elicitation before the model sees that server as available. A server capability change should invalidate route readiness and tool eval coverage until reviewed.

The current spec also makes protocol version and schema dialect release evidence. MCP messages have a TypeScript schema source of truth and JSON Schema validation rules; schemas default to JSON Schema 2020-12 unless another supported dialect is declared. Agent Studio should pin protocol version, schema dialect, unsupported-dialect handling, and request/response ID policy in connector tests.

## Tools, Resources, And Prompts

MCP separates three primitives that Agent Studio should not collapse:

- Tools are model-controlled callable actions. They can query APIs, compute values, mutate systems, or return structured/unstructured results.
- Resources are readable context objects identified by URI. They may be listed, read, templated, subscribed to, and annotated for audience, priority, and freshness.
- Prompts are user-controlled templates that clients expose for explicit selection, often as commands or reusable workflows.

This distinction matters for safety. A source file, vault note, uploaded PDF chunk, or source-ledger entry should usually be a resource, not a tool. A publish action, browser action, repo mutation, email action, or filesystem write is a tool and needs permission, approval, timeout, logging, and side-effect classification. A route-specific workflow template is a prompt artifact and should be versioned separately from model system instructions.

## Tool Contracts

MCP tool definitions reinforce the existing Agent Studio rule that schemas are product surfaces:

- tool names must be stable enough for model selection and audit;
- descriptions and titles affect model behavior and user trust;
- input schemas should be valid JSON Schema and constrained for empty-argument tools;
- output schemas should be used where structured results matter;
- structured content should be validated before it is passed back into an LLM or downstream route;
- protocol errors and tool-execution errors should be separated because only some execution errors are useful for model self-correction.

For Agent Studio, a tool result is not automatically trusted just because it came through MCP. It should be attached to a tool invocation span, content policy, source/rights class if it returns data, and a validation result if it returns structured content.

The current tool spec treats tools as model-controlled while recommending a clear human-in-loop path for exposed tools and sensitive invocations. Agent Studio should therefore distinguish MCP "available to model" from "callable without approval"; the latter should be rare for mutation-capable, credentialed, publishing, browser, filesystem, or paid operations.

## Transport And Session Contract

MCP's standard transports map to two Agent Studio deployment modes:

- `stdio`: local subprocess tools such as local source scanners, repository helpers, or vault utilities.
- Streamable HTTP: remote or long-running connectors that need POST/GET message exchange, server-sent events, session ids, resumability, redelivery, and explicit cancellation.

A dropped stream is not cancellation. Agent Studio should record explicit cancel notifications or route stop events, and it should treat reconnect/resume behavior as part of connector readiness. For HTTP MCP servers, the route should store protocol version, endpoint, session id policy, stream resumability, retry policy, and whether the server supports server-to-client notifications.

Streamable HTTP has its own security and lifecycle posture: servers should validate origins, local servers should bind to localhost, POST/GET behavior must support JSON and SSE cases, SSE reconnect may use event IDs, and a dropped stream is not the same as a tool cancellation. Those details belong in connector readiness evidence before remote or local MCP work surfaces are exposed to an agent.

## Authorization And Security

MCP authorization is optional but, when used over HTTP, follows an OAuth-style protected-resource model. Agent Studio should not pass bearer tokens through arbitrary servers or let a connector reuse broad user credentials across unrelated tools. Token audience, scope challenge, step-up authorization, PKCE, HTTPS, refresh-token handling, and secure storage are connector-release concerns.

The official tool security guidance also maps directly to release gates:

- servers validate inputs, enforce access controls, rate limit calls, and sanitize outputs;
- clients show exposed tools, prompt for sensitive operations, show inputs before high-risk calls, validate results, apply timeouts, and log tool usage.

This makes MCP support a security-sensitive product surface. A route that enables a new MCP server should go through the same review path as a new model provider or browser/computer-use capability.

The authorization page is explicit that HTTP MCP authorization is optional but, when supported, is based on OAuth-style protected-resource metadata, authorization-server discovery, scope selection, token audience, and step-up authorization. Agent Studio should reject vague "has token" evidence. A connector release needs protected-resource metadata, authorization server, client-registration posture, scopes, audience, token storage policy, refresh/expiry behavior, and least-privilege review.

## Canon Cross-Check

This note is now canon-ready because it cross-checks against the OpenAI Responses state/tools note, Anthropic tool/computer-use runtime note, OpenAI Apps SDK/ChatGPT Apps note, Google A2A protocol note, agent-route canon, security canon, HLD, and datastore schema. The shared conclusion is stable: MCP is a connector/context protocol, not an agent identity protocol, not a generic plugin bucket, and not automatically trusted just because a provider can import it.

MCP owns the protocol-level evidence: lifecycle, capability negotiation, version header, schema dialect, stdio versus Streamable HTTP transport, resource/prompt/tool separation, list-change notifications, session/resume/cancel state, OAuth-style HTTP authorization, and tool-result validation. OpenAI/Anthropic notes own provider-specific MCP connector behavior and retention caveats. A2A owns inter-agent tasks, cards, artifacts, and handoffs. Security canon owns untrusted-output and high-authority action review.

## Agent Studio Design Implications

- Keep MCP servers out of the model prompt until capability, auth, permission, and eval checks pass.
- Register resources, prompts, and tools as separate objects. Do not make every readable context object a callable tool.
- Treat tool annotations and metadata as untrusted unless the server is trusted and pinned.
- Store list-change notifications as capability drift events; a changed tool list can silently change model behavior.
- Use resource subscriptions for source/vault/index freshness, but keep source rights and note-promotion state in Agent Studio's own source ledger.
- Use prompt templates as versioned prompt artifacts with owners and eval coverage, not as hidden server-provided instructions.
- Put sensitive MCP calls behind human approval edges and least-privilege tool permissions.
- For local stdio servers, separate server logs from protocol messages; stdout must remain protocol-only.

## Datastore Implications

Add or strengthen these schema concepts:

- `mcp_server_record`: endpoint/process identity, protocol version, transport, server info, capability snapshot, auth mode, trust tier, owner, and status.
- `mcp_capability_snapshot`: negotiated client/server capabilities, list-change support, task support, and timestamp.
- `mcp_resource_record`: URI, template, mime type, size, annotations, source/rights linkage, subscription status, freshness, and sensitivity label.
- `mcp_prompt_record`: prompt name, arguments, owner, version, intended user action, linked prompt artifact, eval coverage, and change notification status.
- `mcp_tool_record`: tool name, title, description hash, input schema, output schema, annotations, task support, side-effect class, permission refs, and eval coverage.
- `mcp_tool_result_record`: invocation id, structured content validation, content refs, resource links, embedded resource refs, error class, and sanitization result.
- `mcp_session_record`: transport, endpoint, session id, protocol version header, stream ids, resume cursor, cancellation state, and expiration.
- `mcp_auth_grant`: resource server, authorization server, scopes, audience, token storage policy, step-up attempts, expiry, and least-privilege review.
- `mcp_protocol_release_gate`: promotion decision proving protocol version, capability snapshot, schema dialect, transport/session behavior, auth discovery, resource/tool/prompt separation, tool-list drift handling, human approval policy, output validation, timeout/retry/cancel policy, and retention/privacy review.

These should link to existing `tool_contract`, `tool_permission`, `tool_invocation_span`, `protocol_security_scheme`, `trace_content_policy`, and `input_safety_scan` records.

## Canon Decision

Agent Studio should expose MCP servers only through governed connector releases. A route may use MCP when protocol version, capability snapshot, transport/session behavior, authorization, resource/tool/prompt inventory, permissions, output validation, drift handling, retention, and rollback are explicit. A readable context object should remain an MCP resource unless the route truly needs model-controlled action; a mutation-capable operation should remain an MCP tool behind least privilege, approval, trace capture, and high-authority release gates.
