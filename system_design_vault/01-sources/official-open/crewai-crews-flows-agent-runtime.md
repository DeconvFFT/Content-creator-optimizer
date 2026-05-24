---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_source_note
rights_status: official_public
source_urls:
  - https://docs.crewai.com/en/concepts/crews
  - https://docs.crewai.com/concepts/tasks
  - https://docs.crewai.com/en/concepts/flows
  - https://docs.crewai.com/en/concepts/tools
  - https://docs.crewai.com/en/concepts/memory
  - https://docs.crewai.com/en/concepts/knowledge
  - https://docs.crewai.com/concepts/testing
  - https://docs.crewai.com/en/observability
  - https://docs.crewai.com/en/telemetry
---

# CrewAI Crews, Flows, And Agent Runtime

## Direct-Read Scope

This note is original synthesis from current official CrewAI documentation for crews, tasks, flows, tools, memory, knowledge, testing, built-in tracing, and telemetry. It stores no raw documentation text, code blocks, screenshots, copied examples, or long excerpts.

Current-doc check on 2026-05-18: current CrewAI docs list v1.14.x for crews/tracing pages while some concept pages still render v1.12.x, so Agent Studio should version-pin framework and doc/API assumptions. Crews now expose checkpointing, security config, streaming output, skills, tracing, before/after kickoff callbacks, planning, and `share_crew` in addition to agents, tasks, process, manager LLM, function-calling LLM, memory, cache, embedder, and rate limits. Tasks still separate expected output, context dependencies, async execution, human input, structured JSON/Pydantic outputs, output files, callbacks, guardrails, and guardrail retry limits. Tracing can expose agent decisions, task timelines, tool usage, LLM calls, performance, cost, errors, and exportable traces; telemetry warns that tool names and agent roles are collected and that `share_crew` expands data collection.

## Core Reading

CrewAI has two useful abstractions for Agent Studio:

- `Crew`: a collaborating group of role-specialized agents assigned tasks under a process;
- `Flow`: an event-driven workflow that coordinates functions, tasks, and crews with state.

The design lesson is that "multi-agent" and "workflow" are different control modes. Crews fit role/task collaboration; Flows fit explicit orchestration, routing, state, and integration. Agent Studio should preserve that distinction instead of representing every specialist collaboration as one generic agent graph.

## Crews And Tasks

Crews are built from agents, tasks, a process mode, memory, cache, embedder configuration, rate-limit settings, callbacks, tracing, skills, security config, and checkpointing. Tasks carry description, expected output, responsible agent, tool limits, guardrails, async execution, callbacks, and optional human input.

For Agent Studio, each role specialist should be more than a prompt:

- agent role, goal, backstory, model, tools, and delegation policy are route-release fields;
- task description and expected output are eval contract fields;
- sequential versus hierarchical process is a topology decision;
- manager-LLM use is a separate authority boundary;
- max-RPM and cache settings are runtime controls;
- guardrails and human input are task-level gates, not after-the-fact review notes.

This is useful for content production. A research crew, script crew, visual planning crew, and platform adaptation crew can share an operating pattern, but each task must still record its expected artifact, allowed tools, source scope, guardrails, and human approval needs.

## Flows

CrewAI Flows provide explicit start/listen/router-style event flow and state management. They can use unstructured state for small automations or structured state for validation and maintainability. Flows can chain multiple crews, branch conditionally, handle human feedback, broadcast events to multiple follow-up actions, run through the API or CLI, and persist memory across runs.

Agent Studio implication: when order and branching are known, use a Flow-like route before using a fully autonomous crew. A Flow can call crews as workers while keeping control, state, and terminal outputs explicit. This matches the product's need for reviewable pipelines: source intake, extraction, retrieval, drafting, critique, media planning, publish-readiness, and feedback update.

## Tools, Apps, Skills, MCP, And Knowledge

CrewAI separates tools from MCPs, apps, skills, and knowledge:

- tools are callable actions;
- MCPs expose remote tool servers;
- apps are platform integrations;
- skills are domain expertise or reusable procedural capability;
- knowledge is retrieved external information.

Agent Studio should keep the same separation. A source-backed drafting route should not treat a PDF knowledge source, a browser tool, a publishing app, and a writing skill as the same dependency. They differ in rights, side effects, freshness, eval, and security.

Knowledge sources exist at agent and crew levels. Crew-level knowledge is shared by all agents; agent-level knowledge is private/specialized. Knowledge storage collections are independent by level, and query rewriting turns task prompts into retrieval queries. Knowledge retrieval also emits events for monitoring.

For Agent Studio, this reinforces two rules:

- shared knowledge must be intentionally scoped, not inherited accidentally;
- retrieval query rewriting must be traceable, because a bad rewrite can cause a correct agent to answer from the wrong evidence.

## Memory

CrewAI's memory system is a unified memory API with LLM-assisted saving, automatic fact extraction, scope inference, categories, importance, adaptive-depth recall, and scoring that can combine semantic similarity, recency, and importance. Memory can be used standalone, with crews, with individual agents, or inside flows.

This is powerful but risky for Agent Studio. Automatic fact extraction and cross-run recall should not directly write canon or shared project policy. Memory needs:

- scope records;
- extraction policy;
- scoring weights and half-life;
- forget/delete support;
- evidence refs;
- review state for shared memories;
- conflict policy when multiple agents write related facts.

Private agent memory can help specialists improve, but shared content strategy, source rights, publishing policy, and architecture canon need human-reviewed promotion.

## Testing, Tracing, And Telemetry

CrewAI testing runs a crew repeatedly and produces task/crew performance metrics. For Agent Studio, that maps to repeated route trials over the same source/task set. One run is not evidence of route quality; repeated runs expose instability, tool-selection variance, and task-output variance.

CrewAI tracing exposes agent decisions, task timeline, tool usage, LLM calls, performance metrics, costs, errors, and exportable traces. Agent Studio should keep trace capture separate from anonymous product telemetry. Tracing can contain prompts, responses, tool outputs, and possibly private source material, so capture, export, redaction, and retention policies are release gates.

The telemetry docs also matter because they warn that tool names and agent roles may be collected and should not contain personal data. Agent Studio should treat agent names, tool names, task names, and role labels as metadata that can leave the local boundary when telemetry/tracing is enabled.

## Agent Studio Datastore Additions

- `crew_definition_record`: crew ID, agents, tasks, process mode, manager LLM, function-calling LLM, memory refs, cache policy, max RPM, tracing, skills, security config, checkpoint config, and owner.
- `crew_task_record`: task description ref, expected output ref, assigned agent, allowed tools, async flag, guardrail refs, human-input requirement, callback refs, output artifact refs, and status.
- `crew_process_decision`: sequential, hierarchical, or flow-controlled process with rejected alternatives, manager authority boundary, latency/cost impact, and eval evidence.
- `crew_agent_profile`: role, goal, backstory, model refs, tool refs, delegation policy, memory scope, knowledge scope, skills, max RPM, and trace policy.
- `flow_definition_record`: flow ID, start nodes, listeners, routers, state schema, called crews, terminal outputs, visualization ref, and owner.
- `flow_state_record`: state ID, structured/unstructured mode, schema ref, current values hash, state update refs, persistence policy, and created/updated times.
- `flow_event_record`: event source, listened method, branch/router decision, input/output refs, triggered methods, and timestamp.
- `agent_knowledge_scope`: agent-level or crew-level knowledge source refs, storage collection, embedder config, source rights, retrieval policy, and visibility.
- `knowledge_retrieval_event`: agent, task, original prompt hash, rewritten query hash, source collection, retrieved chunk refs, failure status, and trace refs.
- `memory_scoring_policy`: semantic/recency/importance weights, half-life, scope strategy, extraction model, forget policy, and review requirement.
- `crew_memory_fact`: extracted fact hash, scope, source task/run refs, importance, recency timestamp, retrieval count, conflict refs, and review state.
- `crew_guardrail_result`: task ref, guardrail policy, validation outcome, retry/edit/escalation action, and reviewer override.
- `crew_test_run`: crew version, iteration count, judge/model, task scores, crew score, execution time, variance, failed tasks, and promotion impact.
- `crew_trace_config`: tracing enabled, destination, captured surfaces, content policy, redaction policy, export policy, and retention.
- `agent_metadata_telemetry_policy`: allowed role/tool/task metadata, PII restriction, share settings, opt-out state, and compliance review.

## Design Commitments

- Use Flow-like deterministic orchestration when the route path is known; reserve Crew-style collaboration for specialist role/task work.
- Record crew process mode and manager authority as topology decisions.
- Treat task expected output as an eval contract.
- Keep tools, MCPs, apps, skills, knowledge, and memory as separate dependency classes.
- Trace retrieval query rewriting and knowledge retrieval events.
- Do not let automatic memory extraction promote shared canon without evidence and review.
- Run repeated crew tests before route promotion; track variance, not only average score.
- Keep tracing and telemetry metadata policies explicit because role/tool/task names can leak sensitive project information.

## Crew And Flow Runtime Release Gate

Promote CrewAI-style or equivalent crew/flow routes only after a `crew_flow_runtime_release_gate` is approved. The gate should bind route ID, framework version, selected control mode, rejected simpler workflow, crew definition, agent profiles, task contracts, process decision, manager authority boundary, flow definition, flow state schema, flow event/router contracts, checkpoint config, kickoff callbacks, planning policy, async task policy, tool/MCP/app/skill dependency snapshots, knowledge scopes, retrieval rewrite policy, memory scoring/extraction policy, shared-memory review policy, task guardrails and retry limits, human-input gates, structured output schemas, output artifact policy, tracing config, telemetry/share settings, metadata PII review, repeated test runs, variance/regression findings, security config, rate/cache policy, fallback route, and rollback target.

This gate is narrower than a generic agent-workflow gate. It exists because a crew route can change behavior through role labels, task expected-output text, manager selection, guardrail retry policy, knowledge scope, automatic memory extraction, or telemetry/share settings even when the visible product route remains unchanged.
