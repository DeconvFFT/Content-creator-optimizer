---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - [[../../01-sources/official-open/openai-responses-state-tools]]
  - [[../../01-sources/official-open/openai-apps-sdk-chatgpt-apps]]
  - [[../../01-sources/official-open/openai-agent-builder-chatkit-product-integration]]
  - [[../../02-books/aima/agent-planning-foundations]]
  - [[../../01-sources/official-open/anthropic-effective-agents]]
  - [[../../01-sources/official-open/google-a2a-protocols]]
  - [[../../01-sources/official-open/langchain-memory-and-persistence]]
  - [[../../01-sources/official-open/langsmith-agent-server-deployment-runtime]]
  - [[../../01-sources/official-open/crewai-crews-flows-agent-runtime]]
  - [[../../01-sources/official-open/opentelemetry-genai-observability]]
  - [[../../01-sources/official-open/huggingface-smolagents-agent-patterns]]
  - [[../../01-sources/official-open/llamaindex-agent-workflows-rag-eval]]
  - [[../../01-sources/official-open/microsoft-agent-framework-autogen]]
  - https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
---

# Long-Running Agent Patterns

## Pattern Summary

Use simple deterministic workflows where the path is known. Use autonomous agent loops only where the task needs tool choice, iterative search, or recovery from ambiguity.

Agent Studio should therefore use a durable orchestrator, not a hidden swarm:

- explicit A2A-style agent cards,
- typed task messages and artifacts,
- run checkpoints,
- memory scope policies,
- event logs,
- external-event wakeups,
- deterministic gates before expensive model work,
- human feedback gates for ambiguity, high-risk outputs, and policy memory.

## Topology Ladder

Long-running behavior is not automatically autonomous behavior. Route design should climb this ladder only when direct eval or trace evidence justifies the next step:

1. augmented single-call route;
2. prompt-chain workflow;
3. router workflow;
4. parallel sectioning or voting workflow;
5. orchestrator-worker workflow;
6. evaluator-optimizer loop;
7. autonomous agent loop with environmental feedback and stop conditions.

Every climb adds state, latency, cost, and failure surface. The route ledger should keep the rejected simpler alternative and the eval slice that made the extra topology necessary.

## Design Rules

- Every agent has an agent card with capabilities, inputs, outputs, models, tools, handoff rules, and guardrails.
- Remote or specialist agents are invoked through card/skill selection, not hardcoded prompt routing.
- Every agent has a task-environment contract before it gets autonomy: performance measure, observed inputs, allowed actions, environment dynamics, known/unknown assumptions, and risk class.
- Handoffs create durable tasks, typed messages, typed artifact parts, stream events, and terminal states.
- A run is resumable from event log, checkpoint/session state, source ledger, artifacts, and pending external events.
- Checkpoint state is not long-term memory. Route state, user memory, project memory, organization policy, procedural skills, and Obsidian planning notes are separate surfaces.
- Critical routes choose synchronous persistence before continuing after side effects; low-risk drafting routes can use asynchronous persistence for throughput.
- Long-running work is decomposed into auditable state transitions with idempotency keys for retryable operations.
- Human interrupts are typed route states with payload, decision, reviewer, checkpoint, and resume command.
- Abstract plans, contingencies, and replanning events are stored separately so reviewers can see when a run changed course and why.
- Agentic route promotion requires an environment/planning release gate before autonomy replaces deterministic workflow, fixed retrieval, or human-reviewed routing.
- Information gathering is logged with the uncertainty it is intended to resolve; browsing, retrieval, extraction, or user interruption should have a decision impact.
- Tool interfaces are tested as model-facing products: descriptions, examples, parameter names, output formats, and edge cases should be revised when traces show misuse.
- Orchestrator-worker routes log delegated task contracts and synthesis decisions; evaluator-optimizer routes log critique criteria, improvement deltas, and stop reasons.
- Agent/workflow/tool/model spans are separate observability objects; a successful high-level agent invocation is not enough evidence unless child model, retrieval, tool, checkpoint, and handoff spans explain what happened.
- Background agents can continue independent research, but their outputs must become notes, artifacts, or source-ledger records before influencing the product.
- Background memory consolidation must preserve evidence refs, rejected memories, conflicts, and schedule. It should not silently rewrite shared memory.
- Human feedback is a gate, not a chat aside.
- Push-style task updates are preferable to polling when a route is waiting on long-running generation, external review, or provider work.
- Provider background mode should be treated as a durable lifecycle with queued, in-progress, terminal, polling, cancellation, retention, and ZDR-compatibility fields.
- Provider streaming should produce typed event records. Partial deltas are UI/trace events, not final approved artifacts.
- Smolagents' one-step execution and HITL planning examples add a practical boundary: each model step should be independently replayable, and plan review should pause the route without discarding prior memory. Agent Studio should persist the plan, the human modification or cancel decision, the memory mutation, and the resume event as first-class trace records.
- LlamaIndex workflow events add the durable execution model: a route should persist typed start, step, stream, tool, wait, response, checkpoint, and stop events. Checkpoints need the completed step, input/output events, context snapshot, route version, source snapshot, and tool snapshot so resume behavior is explainable.
- Microsoft Agent Framework adds the production session boundary: chat history, session state, context providers, and audit stores are separate surfaces. A long-running route should record which provider loads messages, which provider injects context, which provider stores audit context, and how duplicate replay is prevented.
- LangSmith Agent Server adds the deployed-runtime boundary: graph blueprint, assistant configuration, thread state, run execution, task queue, stream subscription, interrupt, cron job, webhook, and protocol endpoint are separate runtime objects. Agent Studio should support join/rejoin streaming, thread-level timelines, typed HITL resumptions, scheduled background runs, and double-texting policy before claiming robust long-running behavior.
- CrewAI adds the crew-versus-flow boundary: use flows for explicit stateful orchestration and crews for role/task collaboration. A long-running content route should not use an autonomous crew when a deterministic flow with crew worker calls gives clearer state, replay, guardrail, and human-review behavior.
- ChatGPT app routes add a host/UI boundary: backend business state, message-scoped widget state, cross-session preferences, model-visible structured content, and widget-only metadata have different owners and lifetimes. A long-running route exposed as an app should persist bridge events, state snapshots, file authorizations, and discovery eval outcomes rather than relying on iframe state as durable workflow memory.
- ChatKit routes add a product-session boundary: the workflow version, product user identity, session issuance, widget state, action payloads, hidden context items, and streamed thread items must be replayable separately. Widget actions are not casual UI events; they are untrusted client-originated triggers that can create side effects or run inference.

## Agent Studio Implications

- Product app: voice/text studio with run activity, sources, artifacts, feedback, and voice settings.
- Planning workspace: Obsidian notes and optional viewers.
- Orchestration: LangGraph-style checkpoints plus Postgres event tables.
- Inter-agent protocol: local A2A card/task/artifact shape now, real A2A-compatible surface later.
- Resume model: persisted checkpoints, session state, interrupt records, and explicit external-event or human-resume request records.
- Memory model: default to user-scoped writable memory, read-only organization policy, and reviewed shared/canon writes.

## Failure Modes

- Too many agents doing the same task.
- Escalating to an autonomous loop when prompt chaining, routing, or parallel sectioning would have been enough.
- Tool schemas that validate technically but confuse the model at runtime.
- Handoffs without durable state.
- Agent cards fetched once and then trusted forever.
- Model-generated decisions without source evidence.
- Memory applied as policy without confirmation.
- Shared writable memory that lets one user or compromised source influence another route.
- Realtime voice session treated as a backend reasoning model.
- Resume implemented as a chat summary instead of durable state, events, and typed pending work.
- Provider-side response state treated as the only replay mechanism.
- Streaming deltas persisted as final artifacts without terminal completion and approval state.
- Trace export without anonymization/redaction for uploaded sources, local books, private user data, or tool outputs.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
