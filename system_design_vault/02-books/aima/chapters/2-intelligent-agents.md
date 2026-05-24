---
type: book-chapter-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source:
  local_path: /Users/saumyamehta/DS interview prep/books/Artificial Intelligence. A modern approach (Stuart Russell  Peter Norvig).pdf
  title: "Artificial Intelligence: A Modern Approach"
  authors: "Stuart Russell, Peter Norvig"
chapter:
  number: 2
  title: "Intelligent Agents"
extraction:
  method: pdftotext
  physical_pages: "36-62"
  pdf_pages: "49-75"
  temp_extract: "/private/tmp/aima_ch2_intelligent_agents.txt"
stores_raw_source_text: false
related:
  - "[[../agent-planning-foundations]]"
  - "[[../../../03-patterns/agent-systems/agent-route-architecture-canon]]"
  - "[[../../../03-patterns/agent-systems/long-running-agent-patterns]]"
  - "[[../../../03-patterns/system-design/production-agent-studio-canon]]"
  - "[[../../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Chapter 2 - Intelligent Agents

## Reading Scope

This is a direct-read chapter synthesis from the local user-provided Artificial Intelligence: A Modern Approach PDF. It covers Chapter 2 only: agents and environments, percept sequences, agent functions versus agent programs, performance measures, rationality, task-environment specification, environment dimensions, agent program structures, learning-agent components, and state representation choices.

This note stores compact original synthesis and Agent Studio implications only. It does not store copied chapter text, tables, figures, algorithms, or long excerpts.

## Why This Chapter Matters

Agent Studio should not call every LLM/tool loop an agent. Chapter 2 makes the abstraction stricter: an agent is a policy over percept history, prior knowledge, and available actions inside a task environment. The useful design move is to define the environment and performance measure before choosing a model, tool graph, memory policy, or autonomy level.

The product rule: a route can claim agentic behavior only after it declares what it can observe, what it can change, what success means, what it already knows, and which environment uncertainties change the correct action.

## Agent Boundary

The chapter separates the external agent function from the concrete agent program. For Agent Studio, the external function is the behavior contract: given observed user input, source state, memory, tool results, reviewer feedback, and run history, what action should the route take? The program is only the implementation: prompts, model calls, workflow nodes, retrieval, tools, and persistence.

Agent Studio implications:

- route records should describe the behavior policy independently from the current implementation;
- model/provider swaps should not silently change the route's action boundary;
- tool outputs, file contents, browser observations, reviewer comments, and publish-state events are percepts;
- file writes, memory writes, tool calls, notifications, posts, and external API calls are actuators with side-effect classes.

## Performance Measure Risk

The chapter's rational-agent frame treats behavior as good when it improves the intended environment outcome, not when it follows a locally attractive behavior rule. That is the core reward-hacking warning for Agent Studio. A route optimized for speed, engagement, acceptance by an automated judge, or volume of generated assets can degrade source fidelity, rights discipline, reviewer trust, or rollback quality.

Agent Studio implications:

- every autonomous route needs a `route_success_contract` and a performance-measure review;
- route evals should include blocked tradeoffs such as fast-but-ungrounded, engaging-but-unsafe, complete-but-uncited, cheap-but-rework-heavy, and autonomous-but-unreviewable;
- performance measures should score environment state after action, not just the action string or model output;
- unknown or contested objectives should become human-review or preference-learning boundaries rather than hidden prompt assumptions.

## Rationality Contract

Rational action depends on four inputs: the performance measure, prior environment knowledge, available actions, and percept history. This maps directly to route release evidence.

Required release evidence:

- performance measure and forbidden shortcuts;
- prior knowledge and source assumptions;
- available actions and side-effect limits;
- percept/event history used by the route;
- expected outcome and why alternatives were rejected.

This turns "the model decided" into an auditable route-policy execution record.

## Task Environment Classification

The chapter's PEAS-style task environment specification is the most important reusable artifact for Agent Studio. Each route should define performance measure, environment, actuators, and sensors, then classify the environment before selecting orchestration.

Relevant classifications:

- fully versus partially observable: most source, browser, reviewer, and publishing workflows are partially observable;
- single-agent versus multiagent: specialist routes become multiagent when agents have different tools, prompts, memories, metrics, or information;
- deterministic versus stochastic: extraction, retrieval, model generation, web state, and external APIs are rarely deterministic in practice;
- episodic versus sequential: ingestion, revision, publishing, memory, and eval loops are sequential because one action changes future options;
- static versus dynamic: docs, queues, user feedback, provider limits, and social-platform state can change while a run is active;
- discrete versus continuous: route state often mixes discrete workflow status with continuous scores, latencies, costs, confidence, and reviewer ratings;
- known versus unknown: official docs, third-party APIs, and GUI surfaces can be only partially known until observed.

Agent Studio should use this classification to decide whether the right implementation is deterministic code, a fixed workflow, retrieval, bounded planning, model-mediated repair, multi-agent delegation, or human approval.

## Agent Program Families

The chapter distinguishes simple reflex, model-based reflex, goal-based, utility-based, and learning agents. These are useful as route maturity levels.

Agent Studio interpretation:

- simple reflex: safe for low-risk routing rules and formatting transforms;
- model-based reflex: required when current observation is insufficient and route state must remember source, user, or tool history;
- goal-based: appropriate when the route must plan toward a declared artifact or state;
- utility-based: required when the route trades off quality, latency, cost, rights, confidence, reviewer burden, and risk;
- learning agent: appropriate only when feedback modifies future behavior under governance, eval, rollback, and drift checks.

The route should state which family it is using. A utility-based or learning route needs stronger eval and governance than a reflex route.

## Learning Agent Components

The chapter's learning-agent split maps well to production feedback loops:

- performance element: the route behavior that acts now;
- learning element: the update process that changes future behavior;
- critic: evaluator or reviewer signal about behavior quality;
- problem generator: exploration source that proposes useful trials.

Agent Studio implication: feedback must not directly mutate production behavior without provenance, scope, evaluation, and rollback. Human edits, grader scores, trace feedback, failed tool calls, and post-publication outcomes should flow through governed feedback records before becoming route policy changes.

## Representation Choices

Chapter 2 closes by separating atomic, factored, and structured state representations. Agent Studio needs all three:

- atomic state for simple queue status or route phase;
- factored state for route variables such as source freshness, rights status, reviewer state, latency, cost, and confidence;
- structured state for sources, claims, citations, assets, agents, tools, tasks, approvals, posts, and relationships.

The design implication is that a single "run status" field is too weak for serious agents. Agent Studio needs structured route state, but it should still project atomic and factored views for scheduling, dashboards, eval slices, and release gates.

## Datastore Objects Reinforced By This Chapter

| Object | Role |
|---|---|
| `task_environment_contract` | Declares performance measure, environment, sensors/percepts, actuators/tools, and environment dimensions before route design. |
| `agent_architecture_record` | Separates model, memory, tool contracts, sensor channels, actuator channels, state policy, and approval boundary. |
| `route_success_contract` | Captures desired environment outcome, not just desired model output. |
| `route_policy_execution_record` | Stores percept/history inputs, selected action, rejected alternatives, expected outcome, and realized outcome. |
| `performance_measure_review` | Reviews metric shortcuts, reward-hacking risk, and objective uncertainty before route promotion. |
| `feedback_capture_event` | Captures reviewer, evaluator, user, or environment feedback before it changes route behavior. |
| `learning_update_record` | Versioned behavior update from feedback with provenance, scope, eval, rollback, and approval. |
| `agent_environment_planning_release_gate` | Ensures environment classification, performance measure, agent architecture, side-effect policy, evals, human boundary, fallback, and rollback are reviewed before agentic promotion. |

## Agent Studio Design Implications

- Start route design with the task environment, not prompt wording.
- Treat sensors and actuators as first-class contracts; tool permissions are actuator scope.
- Store performance measures and known forbidden shortcuts beside the route.
- Classify partial observability, stochasticity, dynamics, and multiagent character before allowing autonomy.
- Match route architecture to environment complexity; avoid utility-based or learning routes when a reflex rule or deterministic workflow is enough.
- Keep feedback ingestion separate from behavior mutation through explicit critic, learning-update, eval, and rollback records.
- Represent route state structurally, while maintaining simpler projections for scheduling and monitoring.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
