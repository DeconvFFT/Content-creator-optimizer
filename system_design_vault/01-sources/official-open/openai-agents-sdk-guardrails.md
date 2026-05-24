---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_doc_page
rights_status: official_public
stores_raw_source_text: false
sources:
  - https://openai.github.io/openai-agents-python/guardrails/
  - https://openai.github.io/openai-agents-python/ref/guardrail/
  - https://openai.github.io/openai-agents-python/ref/tool_guardrails/
  - https://developers.openai.com/api/docs/guides/agent-builder-safety
---

# OpenAI Agents SDK Guardrails

## Direct-Read Scope

This note is compact original synthesis from current official OpenAI Agents SDK guardrails documentation, guardrail API references, tool-guardrail references, and OpenAI agent safety guidance. It stores no copied code blocks, raw documentation text, or long excerpts.

Current-source check: the Agents SDK guardrails docs still distinguish agent-level input/output guardrails from function-tool guardrails, the API reference still exposes `run_in_parallel` for input guardrails, and Agent Builder safety guidance still treats tool approvals, input guardrails, trace graders, and structured data flow as complementary controls.

## System Design Takeaways

OpenAI's guardrail model makes one point very clear for Agent Studio: guardrails are route-stage controls, not a generic "safety layer" that magically covers every agent step.

Agent Studio should model guardrails by execution boundary:

- input guardrails for first-user-input checks;
- output guardrails for final-answer checks;
- tool input guardrails before specific function-tool calls;
- tool output guardrails after specific function-tool calls;
- human approval edges for privileged MCP/tool operations;
- trace graders and evals for regression evidence.

This matters because a multi-agent workflow can delegate, hand off, call tools, use hosted tools, and produce intermediate artifacts before the final response. A guardrail attached to the first or last agent does not prove that every intermediate tool call or specialist action was protected.

## Workflow Boundaries

Input guardrails run at the beginning of a chain and output guardrails run at the final output boundary. Tool guardrails run around custom function-tool invocations and are the right control when the route needs per-tool checks in a manager/specialist workflow.

Agent Studio should therefore store a `guardrail_scope` for each guardrail:

- route-level first input;
- final output;
- specific function tool;
- specific artifact transition;
- external side-effect edge;
- publishing edge;
- human approval edge.

The control should state what it can see, what it cannot see, and whether it protects the step before a side effect occurs.

## Execution Mode And Side Effects

Input guardrails can run in parallel with agent execution or block before the agent starts. Parallel mode reduces latency but may still allow model tokens or tool work to begin before a failing guardrail cancels the run. Blocking mode is safer for cost control and side-effect prevention.

Agent Studio implication: `run_in_parallel` is not an implementation detail. It should be a release-gated route setting. Routes that can call publishing, deletion, file write, browser/computer, email, payment, credential, or external mutation tools should prefer blocking checks or human approval before the side effect path.

## Tripwires And Recovery

Guardrails signal failure through tripwires. For Agent Studio, a tripwire should not disappear into an exception log. It should become structured product evidence:

- which guardrail ran;
- input/output/tool surface checked;
- whether execution was blocked, replaced, rejected, or halted;
- user-visible status;
- retry/resume policy;
- reviewer escalation state;
- trace and eval linkage.

For tool guardrails, the behavior can allow execution, reject content while continuing with a model-visible message, or halt execution by raising an exception. That distinction belongs in the trace because each behavior creates a different user experience and recovery path.

## Agent Safety Guidance

The OpenAI agent safety guidance reinforces that guardrails are only one layer. The larger system should avoid putting untrusted variables into higher-priority instructions, use structured outputs to constrain data flow, keep tool approvals on for MCP operations, use guardrails for user input sanitation, and run trace graders/evals to inspect decisions, tool calls, and reasoning steps.

Agent Studio should treat untrusted text, uploaded documents, retrieved chunks, browsed pages, social content, and tool outputs as data. They can inform the route only after extraction, validation, and trust-boundary labeling. They cannot rewrite developer instructions, route policy, source rights, approval rules, or tool permissions.

## Canon Cross-Check

The security canon already treats prompt injection, private data leakage, tool misuse, and privileged instruction flow as route-architecture risks. This note narrows that into guardrail placement evidence: each route must say which boundary is covered, which boundary is not covered, and whether a side-effect can happen before the guardrail finishes.

The eval canon owns trace grading and failure-slice regression evidence; this note owns the guardrail execution records, tripwire events, and recovery actions that trace graders should inspect.

The privacy note owns redaction, retention, provider data boundaries, and human-access audit; this note owns the pre-context and pre-tool guardrail checks that prevent sensitive material from entering privileged instructions, unsafe tool arguments, model-visible tool output, or publishable artifacts.

The tool/MCP/computer-use notes own executable capability exposure. Guardrails do not replace tool permissions, sandbox policies, or user approvals. Hosted tools, built-in execution tools, handoffs, and MCP operations need explicit caveats because function-tool guardrails do not automatically cover all of them.

## Agent Studio Design Implications

- Add route-level `guardrail_policy_record` objects that specify boundary, execution mode, model/tool dependencies, failure behavior, and evidence requirements.
- Add `guardrail_execution_record` to the run trace for every guardrail attempt, including skipped/not-applicable states.
- Add `tripwire_event` as a first-class event with user-visible status, halt/reject/replace behavior, escalation state, and eval linkage.
- Separate agent-level guardrails from tool-level guardrails in the route graph.
- Require blocking guardrails or human approval before irreversible external side effects.
- Use structured outputs between graph nodes so untrusted content cannot travel as freeform instructions.
- Treat hosted tools, MCP tools, browser/computer actions, and handoffs as separate trust surfaces; do not assume function-tool guardrails cover them.
- Grade traces for guardrail placement, not just final output refusal.
- Promote guardrail changes only after a guardrail release gate proves boundary coverage, execution mode, side-effect ordering, hosted-tool caveats, tripwire/recovery behavior, eval coverage, and approval fallback.

## Datastore Objects Added

- `guardrail_policy_record`
- `guardrail_execution_record`
- `tool_guardrail_policy`
- `tripwire_event`
- `guardrail_recovery_action`
- `untrusted_variable_flow_check`
- `guardrail_release_gate`
