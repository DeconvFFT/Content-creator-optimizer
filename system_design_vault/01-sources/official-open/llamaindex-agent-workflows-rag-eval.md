---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_source_note
rights_status: official_public
source_urls:
  - https://developers.llamaindex.ai/python/framework/
  - https://developers.llamaindex.ai/python/framework/getting_started/concepts/
  - https://developers.llamaindex.ai/python/llamaagents/workflows/
  - https://developers.llamaindex.ai/python/framework/understanding/agent/
  - https://developers.llamaindex.ai/python/framework/understanding/agent/state/
  - https://developers.llamaindex.ai/python/framework/understanding/agent/streaming/
  - https://developers.llamaindex.ai/python/framework/understanding/agent/human_in_the_loop/
  - https://developers.llamaindex.ai/python/framework/understanding/agent/multi_agent/
  - https://developers.llamaindex.ai/python/examples/workflow/checkpointing_workflows/
  - https://developers.llamaindex.ai/python/examples/workflow/corrective_rag_pack/
  - https://developers.llamaindex.ai/python/framework/understanding/tracing_and_debugging/tracing_and_debugging/
  - https://developers.llamaindex.ai/python/framework/understanding/evaluating/evaluating/
---

# LlamaIndex Agent Workflows, RAG, And Eval

## Direct-Read Scope

This note is original synthesis from official LlamaIndex developer documentation. It covers LlamaIndex framework overview, high-level concepts, Workflows, building agents, maintaining state, streaming output/events, human-in-the-loop tools, multi-agent patterns, workflow checkpointing, corrective RAG, tracing/debugging, and evaluation.

No raw source text, copied notebooks, long excerpts, or generated transcript material is stored here.

## Core Reading

LlamaIndex frames context augmentation as the product problem: private or domain-specific data sits behind files, databases, APIs, PDFs, and slides, and the application has to parse, index, retrieve, and expose only the right context to the LLM. For Agent Studio, this reinforces that source ingestion and route execution are the same product system. A content agent is only as reliable as the source objects, node/chunk records, retrieval policies, and source-rights records that feed its context.

LlamaIndex's agent definition is operational: an agent receives a message, uses history/tools/latest input to choose an action, invokes tools when needed, interprets tool outputs, loops until it stops, and returns a final output. This maps to Agent Studio's route model: each loop step needs action selection, tool call, tool result, continuation decision, and terminal result as durable records.

Workflows are event-driven rather than static DAGs. A workflow is built from steps that receive and emit typed events; `StartEvent` and `StopEvent` mark entry and exit; step input/output types can be inferred and validated. The design lesson is that Agent Studio should not overfit to a fixed graph UI. Production agent workflows need typed events, branches, loops, parallel execution, checkpoint state, and event streams.

## Agent Studio Implications

Event-driven workflows fit Agent Studio's long-running content production better than prompt chains. Research, outline, draft, media generation, review, safety scan, approval, schedule, publish, and rollback can all be represented as events. The UI can still show a graph, but the datastore should preserve the event log because loops, branches, and human waits are first-class behavior.

LlamaIndex state handling separates a workflow run from the `Context` that can persist across runs. Context can be serialized and later restored; tools can read or write shared state through the workflow context. Agent Studio should copy the useful part but add stricter governance: context state is not automatically long-term memory. State writes need scope, actor, reason, TTL or retention policy, conflict handling, and replay impact.

Streaming output is not just token streaming. LlamaIndex emits events such as agent stream deltas, agent input, agent output, tool calls, and tool-call results. Agent Studio should preserve stream events as transient UI/trace events until a terminal artifact is produced and approved. A partial draft, partial citation, or partial tool result should not become a canonical note or publishable artifact.

Human-in-the-loop support uses input-required and human-response events. The important design pattern is a wait point with a unique waiter ID, explicit required response type, and stream-visible waiting state. Agent Studio approval gates should use this pattern for dangerous tools, publishing, source-rights overrides, memory promotion, route changes, and external writes.

Multi-agent patterns are explicitly tradeoffs:

- `AgentWorkflow` gives built-in handoff behavior with low code burden.
- Orchestrator-as-agent exposes subagents as tools and gives the orchestrator more explicit selection responsibility.
- Custom planners make the plan explicit and let deterministic code invoke agents in a controlled order.

Agent Studio should store which pattern is used and why. Default handoff heuristics are convenient but risky for high-stakes publishing or source-governance routes. Custom planners or explicit orchestrator routes are better when the product needs explainable ordering, bounded authority, or deterministic review gates.

Checkpointing stores the last completed step, input event, output event, and context-state snapshot. This is directly relevant for long-running Agent Studio work. A resumed workflow should know which step completed, which event caused it, what state existed then, and which queued events remain. Checkpoints should be tied to route version, source snapshot, tool versions, and approval state.

Corrective RAG is a useful production pattern: retrieve candidates, evaluate relevance, extract relevant text, transform the query or fall back to web search when candidates are weak, then synthesize. Agent Studio should treat retrieval quality as a workflow decision, not a hidden retriever setting. Relevance results, transformed queries, fallback searches, accepted/rejected nodes, and synthesis context should be persisted.

Tracing/debugging and evaluation are separate but connected. LlamaIndex exposes logging/callbacks/observability for prompts, LLM outputs, embeddings, indexing/querying traces, and component behavior. It also distinguishes response evaluation, such as faithfulness to context, from retrieval evaluation, such as hit rate and MRR against expected node IDs. Agent Studio should keep both trace observability and eval records: traces explain what happened; evals decide whether a route is good enough.

## Current-Source Cross-Check

Current LlamaIndex framework docs still position context augmentation, ingestion, indexing, querying, storage, agents, tracing, and evaluation as separate application surfaces. That supports Agent Studio's split between source ledgers, index releases, route execution, observability, and eval records.

Current LlamaAgents workflow docs still use typed events with explicit workflow entry and exit events. The important production rule is unchanged: a user-facing graph can be a projection, but the durable route state should be an ordered typed event log with versioned step contracts.

Current agent docs still support stateful agents, streaming events, HITL, and multi-agent patterns. Agent Studio should record whether the route uses default handoff, orchestrator-as-agent, or custom planner control, and should not treat streamed deltas or tool events as approved artifacts.

Current checkpointing, corrective RAG, tracing/debugging, and evaluation docs still support release gates for resumability and source-grounded quality: checkpoint state must carry completed step/input/output/context, corrective RAG must preserve relevance decisions and fallback branches, and response faithfulness plus retrieval relevance should both block promotion when source-backed behavior is weak.

## Datastore Additions

- `workflow_event_record`: typed workflow event with event class, payload/artifact refs, producer step, consumer step, run ID, ordering key, and trace refs.
- `workflow_step_record`: step definition with accepted input event types, emitted output event types, timeout, retry policy, side-effect class, and validation state.
- `workflow_context_snapshot`: serialized context state for a run/checkpoint with serializer, schema version, state hash, sensitivity labels, and restore status.
- `workflow_checkpoint_record`: completed step, input event ref, output event ref, context snapshot ref, route version, source snapshot, tool snapshot, and resume eligibility.
- `agent_event_stream_record`: streaming event for agent input, delta, output, tool call, tool result, waiting state, or terminal artifact.
- `human_wait_event`: waiter ID, requested response type, required actor, prompt/artifact refs, approval policy, timeout, and current wait state.
- `human_response_event`: waiter ID, actor, decision, modified payload refs, rationale, timestamp, and resume event ref.
- `multi_agent_pattern_decision`: selected AgentWorkflow/orchestrator/custom-planner pattern, rejected patterns, control rationale, authority boundary, and eval evidence.
- `agent_handoff_policy`: allowed source agent, target agent, handoff conditions, return-to-user option, failure policy, and trace requirements.
- `corrective_rag_step`: retrieval event, relevance eval refs, query transform refs, fallback search refs, accepted node refs, rejected node refs, and synthesis context refs.
- `retrieval_relevance_eval`: candidate node, query, expected node IDs where available, relevance decision, metric family, evaluator, and release-blocking status.
- `response_faithfulness_eval`: response artifact, source context refs, query, evaluator, passing state, hallucination or unsupported-claim refs, and remediation action.
- `workflow_trace_callback_record`: callback/observability handler, event categories captured, timing/count metrics, redaction policy, and backend/export destination.
- `agent_workflow_release_gate`: promotion gate for event-driven agent/RAG workflows, binding workflow step contracts, event schemas, context snapshots, checkpoint/resume evidence, HITL wait/response states, multi-agent pattern decision, corrective RAG branches, trace callbacks, retrieval relevance evals, response faithfulness evals, side-effect policy, and rollback condition.

## Design Commitments

- This note is canon-ready for Agent Studio event-driven agent and RAG workflow architecture.
- Agent Studio should represent workflows as typed events plus user-facing graph projections, not only as static DAG edges.
- Context state should be serializable and restorable, but promoted memory requires separate governance.
- Stream events are trace/UI data until terminal artifact validation and approval.
- Human wait/response events should be first-class route states for approvals and dangerous actions.
- Multi-agent routes should record whether they use default handoff, orchestrator-as-tool, or custom planner control.
- Corrective RAG should persist relevance judgments, query rewrites, fallback searches, rejected evidence, and final synthesis context.
- Response faithfulness and retrieval quality evals should both be required for source-backed content routes.
