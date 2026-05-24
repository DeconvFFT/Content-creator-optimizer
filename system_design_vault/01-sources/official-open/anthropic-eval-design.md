---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
source_status: official_anthropic_claude_docs
sources:
  - https://platform.claude.com/docs/en/test-and-evaluate/define-success
  - https://platform.claude.com/docs/en/test-and-evaluate/develop-tests
  - https://platform.claude.com/docs/en/test-and-evaluate/eval-tool
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview
---

# Anthropic Eval Design

## Reading Scope

Direct-read pass over Anthropic's current Claude docs for defining success criteria, building evaluations, using the Console Evaluation Tool, and prompt-engineering prerequisites. This note stores compact original synthesis only; it does not store raw doc text or long excerpts.

## Core Thesis

Anthropic frames prompt engineering as an empirical loop: define success criteria, build evaluations that mirror the real task, test prompt variants, then refine. Prompt work should not start until the team knows what good behavior means and has a way to measure it.

Agent Studio implication: every production route should begin with a route-specific success contract and eval dataset, not a prompt draft. Prompt changes, model swaps, retrieval changes, and workflow changes should be measured against that contract.

## Success Criteria

Good success criteria are specific, measurable, achievable, and relevant to the use case. Anthropic's criteria families include task fidelity, consistency, relevance/coherence, tone/style, privacy preservation, context utilization, latency, and price.

Agent Studio implication: route records should not contain a vague `quality` field. They should carry explicit objective metrics and qualitative rubrics by surface: source grounding, script usefulness, visual fidelity, platform fit, safety, latency, and cost.

## Multidimensional Evaluation

Most serious use cases need several success criteria at once. A route can improve style while harming citation accuracy, or improve answer quality while increasing latency and cost.

Agent Studio implication: promotion gates should be multidimensional. Do not ship a variant because the aggregate judge score improved if source recall, unsupported-claim rate, policy intervention rate, or token cost regressed beyond threshold.

## Eval Design Principles

Anthropic prioritizes task-specific evals, edge cases, and automation when possible. The docs explicitly prefer scalable automated evaluation where the grading signal is reliable enough, even if individual cases have slightly lower signal than hand grading.

Agent Studio implication: create broad regression suites from real content workflows and observed failures. Use deterministic checks for schema/citation/tool behavior, model judges for nuanced editorial criteria, and human review only where automation is not trustworthy.

## Grading Ladder

The Anthropic docs rank grading methods by speed, reliability, and scalability: code-based grading first when possible, human grading when necessary, and LLM-based grading when it is flexible enough and validated.

Agent Studio implication: each eval case should specify `grader_policy`: exact match, schema validation, code/functional check, retrieval/citation check, LLM rubric, human review, or mixed. Model judges should be calibrated before becoming release gates.

## LLM-Based Rubrics

Anthropic recommends detailed, clear, empirical rubrics for LLM grading. Rubrics should ask for constrained outputs such as pass/fail or ordinal scores rather than vague qualitative commentary. Reasoning can improve judge quality, but the stored eval result should preserve the score and concise rationale rather than unnecessary chain-of-thought.

Agent Studio implication: model-judge graders should store aspect definitions, anchors, judge model/version, prompt version, threshold, calibration notes, failing span, and reviewer override. Do not store hidden reasoning as source truth.

## Console Evaluation Tool

The Claude Console Evaluation Tool supports prompt variables, generated prompts, generated test cases, CSV/imported test cases, side-by-side comparison, quality grading, prompt versioning, and re-running suites after prompt edits.

Agent Studio implication: the local vault should mirror those primitives even if Agent Studio is provider-neutral: prompt templates with variables, eval-case tables, prompt variant comparisons, version history, and repeatable runs.

## Prompt Engineering Boundary

Anthropic's prompt-engineering overview states that prompt engineering is only appropriate for success criteria controllable by the prompt. Latency or cost, for example, may be better solved by changing the model or architecture.

Agent Studio implication: route-change proposals should classify the failure cause before editing prompts. Some failures require retrieval changes, schema changes, model routing, cache strategy, workflow topology, or human approval rather than prompt text.

## Datastore Requirements

Agent Studio should store eval-design records:

- `route_success_contract`: objective, task distribution, required quality dimensions, thresholds, and business/user relevance.
- `eval_case_table`: variables, input artifacts, expected behavior, edge-case tags, grader policy, and risk level.
- `prompt_variant`: prompt template, variables, model/provider, version, and reason for change.
- `eval_comparison`: baseline route, candidate route, per-metric deltas, regression flags, and ship/no-ship decision.
- `grader_rubric`: criterion, scale, anchors, judge prompt, judge model, calibration evidence, and override policy.
- `eval_generation_record`: generated test cases, seed examples, reviewer edits, and synthetic-data caveats.

## Agent Studio Design Implications

- Start each new content workflow with success criteria and eval cases before optimizing prompts.
- Keep eval surfaces separate: prompt unit, retrieval grounding, tool call, workflow trace, artifact state, safety, latency, and cost.
- Use broad automated suites for routine regression and focused human review for high-risk qualitative decisions.
- Make prompt variables explicit and versioned so prompt variants can be compared cleanly.
- Convert observed user corrections, policy failures, and citation errors into new eval cases.
- Treat cost and latency as first-class success criteria, not incidental telemetry.

## Canon Promotion

Promoted after cross-checking against OpenAI evals, Prompt Engineering for LLMs chapter 10, prompt/workflow eval templates, and production route-change templates. Durable decisions were extracted into [[../../03-patterns/evaluation/eval-design-canon]].

## Follow-Ups

- Keep model-judge rubrics calibrated against human review before using them as release gates.
- Convert new production failures and reviewer overrides into eval cases tied to route success contracts.
