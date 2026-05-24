---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Prompt Engineering for LLMs"
authors: "John Berryman; Albert Ziegler"
chapter: "9"
chapter_title: "LLM Workflows"
source_path: "/Users/saumyamehta/DS interview prep/books/Prompt Engineering for LLMs- The Art and Science of Building.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 9 - LLM Workflows

## Reading Status

Direct source reading pass completed for chapter 9 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied code listings, copied figures, copied tables, and long excerpts.

## Core Idea

Workflows trade generality for strength. A conversational agent can handle broad, short, user-corrected interactions; a workflow decomposes a larger goal into well-defined tasks, schemas, dependencies, evaluators, and retries so the system can complete complex work with less improvisation.

Agent Studio implication: the content studio should default to explicit workflows for production publishing work and reserve open-ended agent orchestration for cases where flexibility is worth the reliability cost.

## When Chat Is Not Enough

The chapter's Shopify plug-in example shows why a single conversational agent degrades on multi-step business work: it chooses naive searches, produces shallow outputs, struggles with many work items, and gives developers few precise failure boundaries. More prompt detail and more tools can make the agent narrower, but also more distracted.

Agent Studio implication: long-running reel/article/carousel production should be decomposed into tasks such as source selection, claim extraction, outline, script, visual plan, asset generation, editorial QA, policy review, platform formatting, and publishing approval.

## Basic Workflow Construction

The workflow build sequence is goal definition, task specification, task implementation, workflow integration, and optimization. Each task needs explicit inputs, outputs, schemas, and success criteria. Tasks can be LLM-based, traditional code, classic ML, or human review.

Agent Studio implication: each production route should have a workflow manifest that defines task contracts and artifacts. A task without an input/output contract should not be part of the canon workflow.

## Task Implementation Patterns

The chapter distinguishes prompt-template tasks from tool/structured-output tasks. Prompt templates are useful for generated prose bounded by clear context and boundaries. Tool-based approaches are better when the route needs structured extraction from free text. Smaller schemas usually work better than large nested objects.

Agent Studio implication: prefer structured-output extraction for claims, citations, entities, scenes, objections, and QA findings. Use prose generation tasks only after upstream tasks have produced clean structured context.

## Sophisticated Task Control

Tasks can improve through planning, tool-disabled reasoning turns, self-correction, external analyzers, LLM-as-judge review, user-proxy/expert-agent conversations, or model choice by difficulty. The chapter repeatedly warns that LLMs are expensive, slow, nondeterministic, and less dependable than conventional code when code is enough.

Agent Studio implication: route plans should include a "non-LLM first" check. Use deterministic code for crawling, formatting, storage, validation, dedupe, scheduling, and schema checks; reserve model calls for semantic judgment, synthesis, and creative transformation.

## Workflow Topologies

Pipelines are simple but can hide missing dependencies. DAGs allow multiple downstream consumers and make task readiness easy to reason about. Cyclic graphs support repair loops but require storing original inputs, carrying failure metadata, capping attempts, and preventing endless cycling.

Agent Studio implication: content workflows should be DAG-first with local retry loops inside individual tasks. Promote cycles to workflow level only when failure information genuinely needs to revisit earlier semantic decisions.

## Batch Versus Streaming

Batch workflows process a finite set of work items and are simpler to operate. Streaming workflows process work as it arrives and fit low-latency or continuous ingestion, but they introduce more operational complexity.

Agent Studio implication: book/source ingestion can be batch; trend monitoring, inbox ingestion, social feedback, and publishing analytics should be streaming or scheduled incremental pipelines.

## Advanced Agentic Workflows

Advanced workflows let an LLM choose routes, delegate to task agents, create task-specific agents, maintain a prioritized work list, or coordinate role-based agents. These systems are more flexible but less stable and harder to debug. Stateful task agents can own assets and respond to dependency changes.

Agent Studio implication: use role agents as bounded workers with finish tools and asset ownership, not as unconstrained chat participants. Each agent should produce a specific artifact and hand it back through a typed interface.

## Optimization And Evaluation

Workflow quality improves by collecting task examples, building offline harnesses, comparing prompt changes, adding corrective feedback, and recording real production input/output data. Task-level evaluation should start before the full workflow exists because it localizes failures.

Agent Studio implication: every task needs examples, eval data, latency/cost telemetry, and artifact diffs. Workflow promotion should require both task-level and end-to-end eval gates.

## Datastore Requirements

Agent Studio should store workflow records:

- `workflow_manifest`: goal, topology, task list, dependency graph, input/output contracts, and release version.
- `task_contract`: input schema, output schema, prompt/tool policy, model route, validator, retry policy, and human-review policy.
- `work_item`: current task, upstream artifacts, attempt count, failure metadata, and state transition history.
- `task_run`: rendered prompt hash, model/tool calls, output artifact, parser result, cost, latency, and eval score.
- `workflow_eval`: task-level tests, end-to-end tests, acceptance metrics, failure buckets, and rollout decision.

## Failure Modes

- Using a general chat agent for many-item, many-step production work.
- Passing hidden dependencies through unrelated tasks instead of explicit DAG edges.
- Letting cyclic graphs retry forever.
- Asking an LLM to do mechanical work that deterministic code can do better.
- Creating agents that chat indefinitely because they lack a finish contract.
- Optimizing the whole workflow without isolating failing tasks.

## Agent Studio Design Implications

- Build production content generation as typed DAGs with bounded LLM tasks.
- Keep repair loops local unless workflow-level recursion is clearly needed.
- Store artifacts and task contracts as durable state, not ephemeral prompt glue.
- Evaluate tasks before composing them into larger flows.
- Use advanced multi-agent delegation only behind typed finish tools and traceable ownership.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
