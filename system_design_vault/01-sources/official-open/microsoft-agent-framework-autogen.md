---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_source_note
rights_status: official_public
source_urls:
  - https://learn.microsoft.com/en-us/agent-framework/
  - https://learn.microsoft.com/en-us/agent-framework/overview/
  - https://learn.microsoft.com/en-us/agent-framework/get-started/memory
  - https://learn.microsoft.com/en-us/agent-framework/workflows/
  - https://learn.microsoft.com/en-us/agent-framework/integrations/a2a
  - https://learn.microsoft.com/ro-ro/agent-framework/migration-guide/from-autogen/
  - https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html
  - https://www.microsoft.com/en-us/research/blog/autogen-v0-4-reimagining-the-foundation-of-agentic-ai-for-scale-extensibility-and-robustness/
---

# Microsoft Agent Framework And AutoGen Lineage

## Direct-Read Scope

This note is original synthesis from Microsoft Learn Agent Framework documentation, the AutoGen-to-Agent-Framework migration guide, current AutoGen AgentChat docs, and the Microsoft Research AutoGen v0.4 article. It focuses on architecture patterns that affect Agent Studio: agent-versus-workflow choice, session state, context providers, typed graph workflows, human-in-the-loop request/response, checkpointing, A2A integration, AutoGen group-chat lineage, observability, and third-party boundary risk.

No copied code blocks, raw documentation text, or long excerpts are stored here.

Current-doc check on 2026-05-18: Microsoft Agent Framework docs were last updated in April 2026 for the overview, memory, and workflows pages. The current docs still separate agents from workflows, recommend ordinary functions for deterministic work, expose graph workflows with executors, typed edges, events, HITL request/response, checkpointing, and multi-agent orchestration, and make A2A discovery, context IDs, streaming, long-running continuation tokens, and authentication explicit protocol surfaces. The memory page still distinguishes sessions, chat/history providers, context providers, audit stores, and credential choice; it warns that broad development credentials are risky in production. The migration guide still frames Agent Framework as the typed workflow successor for AutoGen team patterns while preserving AutoGen as useful pattern vocabulary.

## Core Reading

Microsoft Agent Framework separates agents from workflows. Agents are LLM-driven components that can use tools and decide dynamic steps. Workflows are explicit business processes that connect agents and functions through graph-based control flow, typed routing, checkpointing, and human-in-the-loop interactions. This distinction is directly useful for Agent Studio: a production route should declare whether it needs model-driven agency or a controlled workflow with agents as components.

The overview makes the conservative rule explicit: if the task can be handled by a normal function, use a function instead of an AI agent. That aligns with the vault's existing topology ladder. Agent Studio should require a rejected deterministic alternative before promoting a route to agentic execution.

Agent Framework combines AutoGen's agent/multi-agent abstractions with Semantic Kernel-style enterprise features: sessions, type safety, middleware, telemetry, model/provider support, and graph-based workflows. The migration guide frames Agent Framework as the next foundation from the AutoGen and Semantic Kernel teams, with AutoGen patterns still relevant but mapped into typed workflows, sessions, hosted tools, middleware, and observability.

## Design Implications

Agent Framework's memory and persistence docs distinguish chat history, session state, context providers, and audit stores. This is an important correction to naive "memory" designs. Agent Studio should not treat memory as a monolithic vector store or chat transcript. It needs:

- run/session state for multi-turn continuity;
- history providers for replayed conversational context;
- context providers that inject derived context;
- audit stores for what was injected, not just what was said;
- explicit rule that only one provider should replay a given message stream into the same invocation.

The docs also warn that broad development credentials can be convenient but risky in production. Agent Studio's provider boundary should prefer managed identity or specific credentials over fallback credential chains, and each route should record the credential selection rationale.

Workflows add stronger control surfaces than open-ended agent loops:

- type-safe message routing;
- executor and edge records;
- conditional routing;
- parallel and dynamic paths;
- request/response integration for external systems or people;
- checkpoints for recovery and long-running process resumption;
- built-in multi-agent patterns such as sequential, concurrent, handoff, and Magentic-style orchestration.

Agent Studio should therefore maintain two graph layers: route topology chosen by product design, and run-time event/step records that prove what actually happened. A visual graph alone is insufficient unless its typed edges, executor inputs/outputs, checkpoints, and resume states are durable.

## AutoGen Lineage

AutoGen AgentChat remains relevant as a vocabulary source for multi-agent patterns: agents, teams, selector group chat, swarm/local handoff, Magentic-One, GraphFlow workflows, memory/RAG, logging, serialization, tracing, and observability. The important design lesson is pattern specificity. "Multi-agent" is not one pattern:

- round-robin or fixed teams are predictable but can waste turns;
- selector-based teams centralize routing decisions over shared context;
- swarm/local handoff patterns decentralize routing and raise authority/trace risk;
- graph workflows make dependencies explicit;
- Magentic-style generalist systems are powerful for open-ended work but need strong stop conditions, web/file/tool boundaries, and eval environments.

Microsoft Research's AutoGen v0.4 article also highlights developer-tool requirements: real-time agent action streams, mid-execution pause/redirect/team-adjust/resume, user proxy input, message-flow visualization, drag-and-drop team building, external component galleries, benchmarking, and low-code prototyping. Agent Studio should borrow those requirements without assuming low-code prototypes are production releases. A prototype team needs promotion gates before it becomes a governed route.

## A2A And Third-Party Boundaries

Agent Framework's A2A integration reinforces protocol layering. Agent Studio should be able to expose or call agents through A2A, but an A2A bridge is not the same as an internal route graph. It needs an integration record, card/capability snapshot, auth policy, endpoint owner, event mapping, and failure semantics.

The overview's third-party warning is especially relevant for Agent Studio. If a route uses third-party agents, servers, models, code, hosted tools, component galleries, or non-Azure-direct models, then data boundary, retention, cost, license, location, and responsible-AI mitigations become the builder's responsibility. The route ledger should capture third-party flow review before exposing private local sources, screenshots, social accounts, or publishing tools.

## Agent Studio Datastore Additions

- `agent_framework_component_choice`: function, agent, workflow, multi-agent team, or external A2A route, with rejected simpler alternative and rationale.
- `agent_session_record`: session ID, route, user/workspace scope, history provider refs, context provider refs, state hash, and retention policy.
- `context_provider_record`: provider source ID, injected context type, before/after run hooks, storage boundary, replay behavior, and audit policy.
- `history_provider_record`: store type, load-message behavior, store-context behavior, source priority, duplication guard, and sensitivity label.
- `workflow_executor_record`: workflow executor/function/agent node with input/output types, owner, side-effect class, and retry/checkpoint policy.
- `workflow_edge_type_record`: typed data route between executors with condition, fan-out/fan-in behavior, validation, and failure policy.
- `workflow_request_response_record`: external or human request/response wait point with requester, responder, payload schema, timeout, and resume state.
- `agent_framework_checkpoint`: workflow checkpoint with executor state, edge state, session state, resume token, and promotion eligibility.
- `multi_agent_team_pattern_record`: round-robin, selector, swarm, graph, Magentic, custom planner, or orchestrator pattern with authority and stop policy.
- `team_composition_change`: mid-run pause, redirect, agent add/remove, role change, or resume action with actor, reason, and trace impact.
- `agent_message_flow_record`: message path, sender, receiver, dependency edge, visible context, and artifact/result refs.
- `agent_benchmark_run`: benchmark suite, task environment, team config, tools, model/provider refs, metrics, cost, latency, and failure slices.
- `third_party_agent_boundary_review`: external server/agent/model/tool/code dependency with data shared, retention/location caveats, license/cost owner, and responsible-AI mitigation.
- `credential_selection_record`: credential type, route scope, environment, fallback behavior, managed-identity status, least-privilege review, and production approval.

## Design Commitments

- Agent Studio should choose functions before agents when the task is deterministic.
- Workflows should be used for explicit business processes; agents should be components inside workflows when dynamic reasoning is needed.
- Session, history, context provider, and audit store records should be separate.
- Multi-agent team patterns need names, authority boundaries, stop conditions, and eval evidence.
- Mid-execution pause, redirect, team edit, and resume should be durable events.
- A2A integrations should be governed protocol boundaries, not invisible internal calls.
- Third-party model/tool/agent/code use requires explicit data-boundary and responsible-AI review before private-source or publishing routes can use it.

## Agent Framework Runtime Release Gate

Promote Microsoft Agent Framework-style or equivalent routes only after an `agent_framework_runtime_release_gate` is approved. The gate should bind route ID, framework version, component choice, rejected deterministic alternative, agent/workflow/team/A2A mode, model/provider binding, credential selection, session policy, history provider policy, context provider policy, audit-store policy, workflow executor contracts, typed edge contracts, HITL request/response waits, checkpoint/resume policy, A2A integration/card/capability snapshot, context ID mapping, streaming/background continuation policy, middleware policy, MCP/tool bindings, multi-agent team pattern, stop policy, team composition change policy, observability/OTel policy, benchmark/eval evidence, third-party boundary review, responsible-AI mitigations, fallback route, and rollback target.

This gate is separate from generic workflow and crew gates because Agent Framework routes can change behavior through provider credential fallback, context provider injection, history replay duplication, typed-edge schema changes, checkpoint semantics, A2A card/capability changes, or third-party server/model/tool exposure without a visible product UX change.
