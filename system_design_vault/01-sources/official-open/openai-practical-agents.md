---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
source_status: official_openai_pdf_and_docs
sources:
  - https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
  - https://developers.openai.com/api/docs/guides/agents
  - https://developers.openai.com/api/docs/guides/agent-builder
  - https://developers.openai.com/api/docs/guides/agent-builder-safety
  - https://developers.openai.com/api/docs/guides/agent-evals
  - https://developers.openai.com/api/docs/guides/trace-grading
  - https://developers.openai.com/api/docs/guides/evaluation-best-practices
---

# OpenAI Practical Agents, AgentKit, and Agent Builder

## Reading Scope

Direct-read pass over OpenAI's official practical agents PDF and current AgentKit / Agent Builder / safety / agent-eval docs. This replaces the previous shallow note for this source. It stores compact original synthesis only and does not store raw PDF or documentation text.

## Core Thesis

OpenAI's current guidance separates three layers that Agent Studio should also keep distinct:

- product-level agent design: when an agent is warranted, how tools/instructions/orchestration should be shaped, and where guardrails belong;
- SDK/runtime ownership: code-first orchestration, tool execution, approvals, state, observability, and continuation behavior;
- hosted workflow path: Agent Builder for visual workflow assembly, typed node edges, versioned publishing, ChatKit deployment, trace inspection, and grader-backed evaluation.

Agent Studio implication: do not treat "agent" as a prompt template. The datastore needs route definitions, typed tool contracts, run loops, versioned workflow snapshots, trace records, grader results, guardrail events, and human approval state.

## When To Build An Agent

The practical guide frames agents as appropriate when workflows require judgment, exception handling, unstructured-data interpretation, or rule sets that are too costly to maintain deterministically. It also warns that deterministic automation may be enough when the workflow is clear and stable.

Agent Studio implication: new agent routes need an `agent_justification` field. The default should be deterministic workflow, retrieval, or prompt-only automation unless the source evidence shows ambiguity, tool choice, multi-step recovery, or unstructured context handling.

## Agent Design Components

The practical guide reduces agent design to model, tools, and instructions. The current Agents SDK docs add the ownership boundary: use the SDK when the application owns orchestration, tool execution, approvals, state, storage, and product integration.

Agent Studio implication: each route should store:

- model/provider choices and fallback policy;
- tool schema, tool risk class, owner, version, and approval mode;
- instructions and policy variables as versioned artifacts;
- run-loop exit conditions, turn limits, error stops, and handoff stops;
- storage strategy for conversation state, artifacts, and trace events.

## Single Agent Before Multi-Agent

OpenAI's practical guide recommends maximizing a single agent first because multi-agent systems add coordination overhead. Splitting becomes useful when instructions become too conditional, tool surfaces overlap, or tool selection fails even after better names, parameters, and descriptions.

Agent Studio implication: multi-agent topology should be an evaluated escalation, not the default architecture. Route-change proposals should require evidence of prompt/tool overload before splitting a route into specialist agents.

## Orchestration Patterns

The practical guide distinguishes a manager pattern, where a central agent calls specialist agents as tools, from decentralized handoffs, where peer agents transfer execution. The current Agent Builder docs express workflows as typed node graphs with configured inputs and outputs, preview/debug runs, publishable versions, and deployment through ChatKit or exported SDK code.

Agent Studio implication: graph records need both edge type and control semantics:

- `tool_call_edge` for manager-as-orchestrator delegation;
- `handoff_edge` for transferring control to another specialist;
- `typed_data_edge` for validated node-to-node payloads;
- `approval_edge` for user or reviewer confirmation before sensitive actions;
- `terminal_edge` for final artifact, stop, failure, or escalation.

## Safety Requirements

OpenAI's Agent Builder safety docs treat prompt injection and private-data leakage as core risks. Important mitigations include keeping untrusted variables out of developer messages, constraining node boundaries with structured outputs, documenting desired policies with examples, using stronger models for higher-risk workflows, keeping tool approvals on, using guardrails for user inputs, and running trace graders/evals.

Agent Studio implication: untrusted source text, social comments, scraped webpages, user uploads, and retrieved snippets must enter as user/context data with typed extraction, not privileged instructions. The datastore should record where each field came from and whether it crossed a trust boundary.

## Evaluation And Trace Grading

OpenAI's current agent-eval guidance points teams to traces, graders, datasets, and eval runs. Trace grading is especially important because it evaluates an end-to-end record of decisions, model calls, tool calls, guardrails, handoffs, and reasoning steps rather than only final output text.

Agent Studio implication: evals need multiple surfaces:

- final artifact quality;
- tool selection and tool argument precision;
- handoff accuracy;
- policy and instruction adherence;
- source-grounding and citation behavior;
- guardrail intervention correctness;
- cost, latency, and route stability;
- trace-level regression against previous route versions.

## Practical Datastore Requirements

- `agent_route`: goal, agent justification, deterministic alternative considered, owner, status, and risk tier.
- `workflow_version`: graph snapshot, node versions, edge types, prompt versions, tool versions, model/provider settings, and publish metadata.
- `tool_contract`: schema, description, parameters, examples, risk class, approval requirement, and test coverage.
- `instruction_artifact`: base instructions, policy variables, source-derived routines, edge cases, and version history.
- `run_trace`: model calls, tool calls, handoffs, guardrail checks, approvals, outputs, errors, and stop reason.
- `trace_grade`: grader version, rubric, target trace span, score/label, rationale summary, and regression flag.
- `eval_dataset`: production examples, expert examples, adversarial cases, expected outputs or rubrics, and route coverage tags.
- `trust_boundary_event`: untrusted input source, extraction schema, sanitizer/guardrail result, and downstream fields populated.

## Agent Studio Design Implications

- Preserve a code-first runtime path even if a visual workflow editor is added later.
- Make workflow versions first-class; a route is not just the latest prompt.
- Keep typed node inputs/outputs in the graph schema so downstream nodes cannot receive arbitrary text where structured fields are expected.
- Treat human approvals as product state, not just UI interruptions.
- Require trace coverage before promoting route changes that affect tools, handoffs, guardrails, or model/provider choices.
- Use eval failures to decide whether to adjust prompts, improve tools, add guardrails, split agents, or change models.
- Store old platform URLs as aliases, but prefer current `developers.openai.com` canonical docs in new notes and manifests.

## Canon Promotion

Promoted after cross-check against Anthropic eval design, AWS GenAI security and observability, the route-change template, and the datastore schema. Durable decisions were extracted into [[../../03-patterns/agent-systems/agent-route-architecture-canon]].

## Follow-Ups

- Direct-read OpenAI Agents SDK orchestration, guardrails, results/state, and observability pages for implementation-level detail.
- Keep legacy `platform.openai.com` Agent Builder and eval URLs as aliases, but prefer current `developers.openai.com` canonical URLs in new notes.
