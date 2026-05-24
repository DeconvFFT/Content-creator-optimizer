---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_google_cloud_docs
sources:
  - https://docs.cloud.google.com/architecture/agentic-ai-overview
  - https://docs.cloud.google.com/architecture/choose-agentic-ai-architecture-components
  - https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system
  - https://docs.cloud.google.com/architecture/multiagent-ai-system
  - https://docs.cloud.google.com/architecture/single-agent-ai-system-adk-cloud-run
---

# Google Cloud Agentic Architecture Patterns

## Reading Scope

This note covers Google Cloud's current official Architecture Center guidance for agentic AI architecture guides, architecture-component selection, agent design-pattern selection, single-agent ADK/Cloud Run deployment, and the multi-agent reference architecture. It is original synthesis only; it stores no raw docs text, code samples, diagrams, or copied tables.

Current-doc check on 2026-05-18 found the official Google Cloud pages still aligned with this note. The overview was last reviewed on 2025-11-25, the single-agent ADK/Cloud Run reference was last reviewed on 2025-12-09, and the current component, pattern-selection, and multi-agent guidance still emphasizes component co-selection, non-agentic alternatives, latency/cost/HITL requirements, runtime separation, scoped tools, MCP/A2A-style coordination, production simulation, and coordination reliability.

## Core Thesis

Agentic architecture is a workload-fit decision, not a default implementation style. Google Cloud's guidance repeatedly separates open-ended, tool-using, multi-step autonomy from simpler assistive or generative tasks. For Agent Studio, this means route topology must be selected from task evidence:

- use non-agentic generation when a single call or deterministic workflow is enough;
- use a single agent when one bounded tool set and one prompt can cover the goal;
- use sequential or parallel workflow agents when orchestration is known in advance;
- use multi-agent systems when specialization, context isolation, or independent critique is necessary;
- use iterative refinement only when quality gain is worth latency, cost, and loop-risk.

## Component Decisions

Google's component taxonomy maps cleanly to Agent Studio release fields:

- frontend framework: interaction mode, streaming needs, state visibility, and backend contract;
- agent development framework: graph/control abstraction, tool binding, testability, and deployment shape;
- tools: built-ins, MCP tools, API-managed tools, or custom functions;
- memory: session context, longer-term personalization, and route-specific state;
- design pattern: single-agent, sequential, parallel, orchestrated, iterative, or custom HITL pattern;
- agent runtime: where orchestration code executes;
- model runtime: managed model API, custom container, or GKE-style control plane.

The key design rule is to choose these together. A realtime UI, long-running background route, private-source ingestion route, and high-risk publishing route should not inherit the same framework, runtime, tool boundary, or memory policy just because they all use an LLM.

## Pattern Selection

Google's pattern guide starts with requirements: task complexity, latency/performance, cost, and human involvement. Agent Studio should convert that into a route topology review:

- `task_characteristics`: predefined, dynamic, open-ended, parallelizable, iterative, or high-stakes;
- `latency_class`: realtime, interactive, delayed, scheduled batch, or offline backfill;
- `cost_budget`: maximum model/tool calls, loop count, and external service budget;
- `human_involvement`: none, approval, review, override, pause/resume, or expert gate;
- `topology_choice`: non-agentic, single-agent, sequential, parallel, orchestrator, iterative refinement, or custom.

The pattern choice must include rejected alternatives. A multi-agent route without a failed simpler baseline is ungrounded architecture.

## Single-Agent Boundary

Google recommends starting with a single agent while the core logic, prompt, and tool definitions are still being refined. Agent Studio should follow that unless there is measured evidence of:

- repeated incorrect tool selection;
- prompt overload from too many responsibilities;
- context contamination between roles;
- independent checks that benefit from parallelism;
- high-risk operations that need role separation;
- latency or throughput gains from independent worker agents.

A single-agent route still needs production records: task definition, tool contract, grounding sources, memory/session policy, ambiguity handling, no-match behavior, logging, eval cases, and fallback path.

## Multi-Agent Boundary

Google's multi-agent reference architecture uses a coordinator, specialized subagents, A2A communication, MCP tool access, ADK/runtime choices, safety controls, and HITL paths. The transferable Agent Studio pattern is:

- coordinator owns user intent, routing, state, and final response assembly;
- subagents own narrow tasks and narrow context;
- evaluator/reviewer agents own quality checks, not final authority;
- refinement loops stop on quality threshold, max iterations, cost budget, or human escalation;
- response generation performs final validation, grounding checks, and user-visible assembly.

This fits Agent Studio content production: research, source validation, script drafting, visual planning, voiceover planning, platform adaptation, and review can be separate roles only when their inputs, outputs, evals, and authority boundaries are explicit.

## Security And Reliability Implications

The multi-agent guidance emphasizes human oversight, scoped autonomy, observability, least-privilege access, model/content protection, and production simulation. Agent Studio should require:

- per-agent permission scope rather than shared global credentials;
- explicit HITL paths for publishing, account actions, purchases, deletion, or high-stakes claims;
- tracing of tool selection, execution path, state changes, and inter-agent messages;
- Model Armor or equivalent prompt-injection/sensitive-data/content checks when using provider-managed stacks;
- production-like simulation before high-autonomy release;
- fault handling for subagent failure, coordinator failure, tool failure, and coordination deadlock.

The reliability lesson is that multi-agent systems fail in coordination, not only in model output. Eval and monitoring must include handoff accuracy, agent status transitions, retry behavior, loop termination, and incomplete-task recovery.

## Runtime Implications

Google distinguishes agent runtime from model runtime. Agent Studio should preserve that split:

- agent runtime runs orchestration, state, tool calls, approvals, retries, and UI/status updates;
- model runtime serves reasoning or generation;
- tool runtime serves side effects and external data access.

Mixing these hides operational tradeoffs. A route can run orchestration locally or on Cloud Run while using a managed model API, or it can use self-hosted models for cost/control while keeping orchestration and tool access separately governed.

## Agent Studio Datastore Implications

Add or strengthen these records:

- `agentic_component_choice`: selected frontend/framework/tool/memory/runtime/model-runtime components, rejected alternatives, workload rationale, and review date.
- `agent_design_pattern_decision`: selected pattern, task characteristics, latency/cost class, human-involvement requirement, rejected patterns, and reassessment trigger.
- `agent_runtime_profile`: orchestration runtime, deployment target, scaling policy, state backend, streaming support, network boundary, and operations owner.
- `model_runtime_choice`: provider/runtime, model family, hosting mode, control level, latency/cost/security rationale, and fallback.
- `multi_agent_coordination_contract`: coordinator, subagent roles, handoff edges, shared context policy, authority boundaries, loop limits, and terminal states.
- `subagent_permission_scope`: agent ref, tool/API/data scopes, credential boundary, approval requirement, and expiry.
- `agent_simulation_run`: production-like scenario, injected failures, coordination findings, eval results, and release blockers.
- `coordination_failure_record`: failed handoff, stuck loop, missing artifact, conflicting authority, retry exhaustion, or human escalation.
- `agentic_architecture_release_gate`: route-level promotion gate linking component choice, pattern decision, runtime/model/tool/memory split, rejected simpler alternatives, single-agent baseline, multi-agent coordination contract where used, scoped permissions, HITL policy, simulation evidence, coordination-failure evals, latency/cost budget, observability traces, fallback or simpler-route option, rollback target, decision, and review timestamp.

## Design Commitments

- Select topology from workload evidence: task complexity, latency, cost, human involvement, and autonomy need.
- Start single-agent unless measured failures justify a more complex route.
- Use sequential and parallel workflow agents when orchestration is known; reserve model-orchestrated routing for dynamic tasks.
- Give every subagent a narrow context, narrow permission scope, explicit outputs, and eval coverage.
- Evaluate coordination and recovery, not only final content quality.
- Separate agent runtime, model runtime, and tool runtime in release records.
- Promote agentic topology changes only after an `agentic_architecture_release_gate` proves the route needs that degree of autonomy, preserves rejected simpler alternatives, and links runtime, permissions, HITL, simulation, observability, fallback, and rollback evidence.
