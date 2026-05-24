---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_source_note
rights_status: official_public
source_urls:
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html
  - https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
  - https://docs.aws.amazon.com/bedrock/latest/userguide/agents-build-modify.html
  - https://docs.aws.amazon.com/bedrock/latest/userguide/agents-how.html
  - https://docs.aws.amazon.com/bedrock/latest/userguide/agents-permissions.html
  - https://aws.amazon.com/bedrock/agentcore/
  - https://aws.amazon.com/id/bedrock/agentcore/faqs/
---

# AWS Bedrock AgentCore Managed Runtime

## Direct-Read Scope

This note is original synthesis from official AWS documentation and AWS product pages for Amazon Bedrock AgentCore and Amazon Bedrock Agents. It covers AgentCore Runtime, Memory, Gateway, Registry, Identity, observability, managed browser/code-interpreter implications, and Bedrock Agents action groups, knowledge bases, prompt templates, traces, inline agents, permissions, and service-role boundaries.

No raw documentation text, copied IAM policies, diagrams, or long excerpts are stored here.

Current-source check: the AgentCore overview now frames AgentCore as modular Runtime, Memory, Gateway, Identity, Code Interpreter, Browser, Observability, Payments, Evaluations, Policy, and Registry services. The Policy FAQ distinguishes model-level guardrails from action-level policy enforcement: guardrails govern what agents say, while Policy governs what agents do before tool execution.

## Core Reading

AgentCore is a managed operating surface for agents, not just a model endpoint. The official docs describe separate managed resources for runtime, memory, gateway, registry, identity, observability, browser/code-interpreter-style tools, and evaluations. For Agent Studio, this reinforces the architectural split already present in the vault: agent runtime, model runtime, tool runtime, memory, identity, and observability should be separate release surfaces.

AgentCore Runtime is built for serverless deployment of dynamic agents and tools, with session isolation, support for asynchronous agents, multimodal and multi-agent workloads, multiple frameworks, multiple models, and protocols such as MCP and A2A. Agent Studio should treat managed runtime portability as a route field: the same route may run locally, in LangGraph, in LlamaIndex, in Agent Framework, or in a managed AgentCore-like runtime, but the release record still needs the same session, identity, tool, trace, and rollback contracts.

AgentCore Memory separates short-term multi-turn memory from long-term memory that persists across sessions and may be shared across agents. Agent Studio should not collapse that into prompt history. Memory needs ownership, sharing scope, retention, summarization/extraction policy, conflict policy, and audit evidence before it influences another agent or session.

Gateway and Registry are the managed connector layer. A gateway can expose existing APIs, databases, Lambda functions, or OpenAPI specs as agent tools; registry catalogs agents, MCP servers, skills, tools, and custom resources with governance. Agent Studio should preserve the same distinction: a tool gateway controls executable capabilities, while a registry records discoverable assets, review state, semantic search metadata, and approval workflow.

AgentCore Policy adds a release-critical control plane that is stronger than prompt-embedded authorization. Policy integrates with Gateway to evaluate tool calls before execution and can be authored as Cedar or generated from natural language with validation against tool schemas. Agent Studio should model this as external policy enforcement, not as a prompt convention. Every managed tool route should carry a policy binding, schema alignment check, permissive/restrictive analysis result, and audit state.

AgentCore Payments adds an economic side-effect surface. If an agent can access paid APIs, MCP servers, or content through wallet-backed microtransactions, Agent Studio needs payment-operation records, spend limits, tool/payment binding, user or organization consent, audit logs, and rollback/refund policy. This should sit next to publishing and external-mutation controls, not under generic cost telemetry.

## Bedrock Agents Pattern

Bedrock Agents use action groups and knowledge bases as the primary action/context surfaces. An action group defines the callable operation, required parameters, handling path, and response contract. A knowledge base gives the agent a repository to query for augmented generation. Prompt templates exist for pre-processing, orchestration, knowledge-base response generation, and post-processing, and can be customized or disabled for troubleshooting.

The runtime loop is a useful production pattern:

1. pre-process user input when enabled;
2. orchestrate by choosing an action group or knowledge base query;
3. elicit missing parameters or reprompt when needed;
4. convert action or retrieval output into an observation;
5. continue the orchestration loop until completion or more user input is required;
6. optionally post-process the final response.

Agent Studio should store these as distinct trace stages. A "successful answer" is too coarse; review needs the chosen action, selected knowledge base, rationale, missing-slot reprompt, observation, loop count, final response, and disabled prompt stages.

Inline agents are also instructive. Bedrock lets callers specify model, instructions, action groups, guardrails, and knowledge bases at invocation time rather than predefining a durable agent. Agent Studio can support dynamic route trials, but production promotion should snapshot the effective inline configuration into a route release before repeated use.

## Security And Identity

Bedrock Agents permissions show the concrete AWS privilege surfaces: service-role trust, model invocation, S3 access to OpenAPI schemas, knowledge-base access, third-party vector-store access, collaborator-agent invocation, guardrail use, KMS decryption, S3 file access for code interpretation, and Lambda resource policies for action groups. Agent Studio should treat every managed-agent permission as a route-release object, not as deployment boilerplate.

For managed or cloud routes, credential scope matters as much as prompt scope. A route with safe instructions but broad service-role access to S3, Lambda, knowledge bases, guardrails, code interpretation files, or collaborator agents is still overprivileged. The vault should require least-privilege review, source-account/source-ARN constraints where applicable, KMS/access caveats, and resource-policy evidence.

AgentCore Identity adds the cross-service version of this problem: agents may act on behalf of users or themselves across AWS resources and third-party OAuth/API-key protected systems. Agent Studio should model this as delegated identity, consent scope, token boundary, tool scope, and audit trail.

## Observability

AgentCore observability provides built-in metrics for runtime, memory, gateway, built-in tools, and identity resources, and supports CloudWatch GenAI Observability plus ADOT/OpenTelemetry-style instrumentation for custom agent metrics, spans, and traces. It also separates default runtime logs from memory/gateway log destinations and requires explicit configuration for some resource logs.

Agent Studio implications:

- observability must be configured per resource type, not only per route;
- memory and gateway logs need their own destinations and redaction policy;
- custom agent spans should share trace IDs with model, tool, retrieval, approval, browser, code-execution, and publishing events;
- log destination, field selection, retention, and content capture are release decisions.

Bedrock Agents runtime traces include rationale, actions, queries, observations, prompts, foundation-model outputs, API responses, and knowledge-base query results. This is powerful but sensitive. Agent Studio should store trace metadata and artifact refs by default, then gate full prompt/tool payload capture behind trace-content policy and private-source redaction.

## Canon Cross-Check

Managed runtime notes from Google, LangSmith, CrewAI, OpenAI Agents SDK, MCP, and security sources all point to the same rule: deployment convenience does not remove release evidence. This AWS source is canon for the managed-agent resource split because it exposes runtime, memory, gateway, identity, tool runtime, observability, evaluation, policy, registry, and payment as separate control planes.

Security canon owns least privilege, trust boundaries, and policy enforcement. This note supplies the managed-cloud evidence: service-role trust, model invocation, S3 schemas/files, knowledge-base access, third-party vector stores, collaborator invocation, guardrail permission, KMS, Lambda action groups, browser/code-interpreter resources, delegated identity, and Gateway Policy must be release blockers.

Eval and observability notes own trace grading and metrics. This note supplies the managed-runtime trace shape: session IDs, OTEL/ADOT instrumentation, resource-specific log destinations, runtime/memory/gateway/tool/identity metrics, and trace-content redaction policy.

## Agent Studio Datastore Additions

- `managed_agent_runtime_record`: provider, runtime type, supported frameworks/protocols, session-isolation mode, async support, model-provider support, VPC/network boundary, and status.
- `agentcore_resource_record`: runtime, memory, gateway, registry, identity, browser, code interpreter, observability, or eval resource with owner, environment, ARN/ref, and lifecycle state.
- `managed_memory_store`: short-term or long-term memory store with sharing scope, extraction policy, retention, conflict policy, and audit status.
- `tool_gateway_record`: gateway source, wrapped API/Lambda/OpenAPI/database, MCP exposure, auth mode, allowed routes, and review state.
- `agent_registry_entry`: discoverable agent/MCP/tool/skill/custom resource with semantic metadata, review workflow, approval state, and deprecation state.
- `agent_identity_delegation`: acting-as user/service mode, consent refs, OAuth/API-key/IAM boundary, scope, expiry, and audit refs.
- `bedrock_agent_action_group`: action schema, required parameters, handler type, Lambda/API ref, response contract, and permission refs.
- `bedrock_agent_knowledge_base_binding`: knowledge base ref, retrieval policy, data source scope, vector-store type, first-party/third-party status, and permissions.
- `bedrock_prompt_stage_config`: pre-processing, orchestration, knowledge-base-response, or post-processing prompt template with enabled state, version, and troubleshooting notes.
- `agent_orchestration_trace_stage`: pre-process, action select, knowledge-base query, slot elicit, observation, loop decision, post-process, and final response stage with trace refs.
- `inline_agent_snapshot`: invocation-time model, instructions, action groups, knowledge bases, guardrails, and prompt-stage config captured for promotion review.
- `agent_service_role_review`: trust policy, source constraints, model/KMS/S3/Lambda/KB/guardrail/collaborator permissions, resource policies, and least-privilege review.
- `agent_observability_resource_config`: resource type, metrics enabled, tracing enabled, log destination, ADOT/custom instrumentation state, field selection, retention, and redaction policy.
- `managed_tool_runtime_record`: browser, code interpreter, or built-in tool runtime with sandbox, network, file, credential, observability, and cleanup policy.
- `agent_policy_binding`: Gateway/Cedar policy ref, tool schema refs, natural-language policy source if any, validation state, permissive/restrictive analysis, and enforcement status.
- `agent_payment_operation`: wallet/provider, paid endpoint or MCP server, spend limit, consent refs, policy refs, operation status, observability refs, refund/rollback state, and audit refs.
- `managed_agent_runtime_release_gate`: runtime/resource release gate linking package source, runtime revision, memory/gateway/identity/policy/payment/observability/tool resources, permission reviews, evals, traffic split, rollback, and reviewer decision.

## Design Commitments

- Agent Studio should separate managed runtime, memory, identity, gateway, registry, tool runtime, and observability resources in release records.
- Managed-agent memory should not be treated as ordinary chat history; shared memory requires scope, extraction, retention, and audit policy.
- Gateway-exposed tools need the same model-facing tests and side-effect approvals as local MCP tools.
- Inline or dynamically configured agents should be snapshotted before repeated production use.
- Service roles, delegated identity, KMS, S3, Lambda, third-party vector-store, guardrail, collaborator-agent, browser, and code-interpreter permissions are release blockers until reviewed.
- Runtime traces are useful for debugging but must be governed by redaction, retention, and private-source content-capture policy.
- Managed-agent routes should not receive production traffic until a managed-agent runtime release gate proves runtime revision, session isolation, memory scope, gateway tools, policy enforcement, payment controls when applicable, identity delegation, service-role permissions, observability, eval coverage, traffic split, and rollback target.
