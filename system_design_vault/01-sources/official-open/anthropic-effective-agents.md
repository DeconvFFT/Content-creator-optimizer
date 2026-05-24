---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_url: https://www.anthropic.com/engineering/building-effective-agents
source_status: official_public
cross_checks:
  - ../../01-sources/official-open/openai-practical-agents
  - ../../01-sources/official-open/google-a2a-protocols
  - ../../01-sources/official-open/langchain-memory-and-persistence
  - ../../03-patterns/agent-systems/agent-route-architecture-canon
  - ../../03-patterns/agent-systems/long-running-agent-patterns
---

# Anthropic Building Effective Agents

## Direct-Read Scope

Read directly from Anthropic's official engineering article, published 2024-12-19 and checked 2026-05-18. This note captures original architecture synthesis only. It stores no raw article text or long excerpts.

## Core Architecture Read

Anthropic's central distinction is between agentic workflows and agents. Workflows use predefined code paths around LLM calls and tools. Agents let the model dynamically choose process and tool use over multiple steps. Agent Studio should make this distinction explicit in route metadata instead of treating every multi-step LLM path as an autonomous agent.

The article's strongest product rule is the simplicity ladder: start with the simplest useful design, then add agentic complexity only when eval evidence shows the simpler route is insufficient. That maps directly to Agent Studio route promotion: deterministic code, retrieval-augmented single calls, prompt chains, routers, parallel workers, orchestrator-worker graphs, evaluator loops, and autonomous agents should be separate topology choices with separate release gates.

## Pattern Fit Matrix

| Pattern | Use when | Agent Studio implication |
|---|---|---|
| Augmented LLM | One model call can solve the task with retrieval, tools, or memory exposed through clear interfaces. | Default route shape for many drafting, classification, and source-backed QA tasks. Require tool docs, retrieval snapshot, and memory scope policy before release. |
| Prompt chaining | The task decomposes into fixed ordered subtasks and intermediate checks can catch drift. | Store every step as a typed node with schema gates and trace-gradeable intermediate artifacts. |
| Routing | Inputs fall into reliably separable categories with distinct prompts, models, tools, or cost tiers. | Require a router eval set, confusion matrix, fallback route, and route-specific success contract. |
| Parallelization | Independent subtasks can run concurrently or multiple judgments improve confidence. | Record sectioning/voting policy, aggregation method, disagreement handling, and cost/latency impact. |
| Orchestrator-workers | The needed subtasks cannot be predicted in advance, but a central planner can delegate and synthesize. | Require task-decomposition evidence, worker contracts, bounded delegation depth, and synthesis trace. |
| Evaluator-optimizer | Clear criteria exist and iterative critique measurably improves the artifact. | Require loop stop policy, improvement metric, critique trace, and regression guard against polishing unsupported claims. |
| Autonomous agent | The task is open-ended, tool choice and recovery are needed, and the environment can provide ground truth. | Require sandbox tests, environmental feedback records, approval gates, tool permission scopes, and explicit stopping conditions. |

## Tool Interface Read

The appendix makes tool design a first-class agent-engineering surface. The agent-computer interface should be shaped as carefully as a human-computer interface: clear parameter names, examples, boundaries between similar tools, easy output formats, and tests that reveal model misuse. For Agent Studio, tool contracts are not just API schemas. They are promptable interfaces whose ergonomics affect correctness.

Important route consequence: framework abstraction is acceptable for velocity, but production review must still expose prompts, tool definitions, responses, state transitions, and failure traces. A route that cannot show why the model selected a tool or why a worker was delegated is not reviewable enough for canon or production use.

## Agent Studio Design Implications

- Add `workflow_pattern_fit` to route design: selected pattern, rejected simpler alternatives, task ambiguity, expected accuracy gain, and latency/cost burden.
- Add `agent_complexity_gate`: no route can move from workflow to autonomous agent without eval evidence that simpler designs fail on material slices.
- Add `tool_interface_test`: tool descriptions, examples, edge cases, parameter names, output format, misuse observations, and revisions.
- Add `orchestrator_delegation_trace`: planned subtasks, worker chosen, task contract, returned artifact, synthesis decision, and failure handling.
- Add `loop_stop_policy` for evaluator-optimizer and autonomous agents: maximum iterations, improvement threshold, budget, human-checkpoint triggers, and stop reason.
- Prefer single-agent and workflow routes until routing/eval traces show a real need for multi-agent topology.
- Store environmental feedback as first-class evidence: tool results, tests, retrieval outputs, execution outputs, user corrections, and reviewer decisions.

## Canon Decision

Agent Studio should not market complexity as architecture. The canonical release rule is: every agentic route must prove why its topology is needed, expose the interfaces the model sees, record the environmental feedback it used, and stop under explicit controls. This cross-checks cleanly with OpenAI practical agents, Google A2A task/artifact contracts, LangGraph checkpoints, AIMA task-environment contracts, and the existing route architecture canon.
