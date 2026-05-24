---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_openai_docs
sources:
  - https://developers.openai.com/api/docs/guides/evaluation-best-practices
  - https://developers.openai.com/api/docs/guides/evals
  - https://developers.openai.com/api/docs/guides/agent-evals
  - https://developers.openai.com/api/docs/guides/trace-grading
  - https://developers.openai.com/api/docs/guides/graders
  - https://developers.openai.com/api/docs/guides/agent-builder-safety
---

# OpenAI Evals And Agent Evals

## Reading Scope

This note covers OpenAI's official evaluation best-practices, programmatic evals, agent workflow evals, trace grading, graders, and agent safety guidance. It is original synthesis only; it does not store raw docs text or code examples. Current-source check: the OpenAI API docs now expose evals as a first-class navigation surface alongside production, safety, model optimization, and Agents SDK workflow evaluation.

## Core Thesis

Evaluation is not an after-the-fact QA task. For production agents, evals are part of the system architecture: they define what good behavior means, preserve representative cases, make nondeterministic behavior measurable, and gate changes to models, prompts, routing, retrieval, tools, guardrails, and handoffs.

For Agent Studio, this means every autonomous workflow needs a versioned eval suite before it can become a production profile.

## Evaluation Surfaces

OpenAI separates several related surfaces:

- general eval design for production AI behavior;
- datasets for rapid iteration on prompts and expected behavior;
- programmatic eval runs for repeatability and scale;
- graders for automated scoring;
- trace grading for agent workflow behavior;
- safety guidance that treats trace graders and evals as part of risk reduction.

Agent Studio should mirror that separation. A single "quality score" would hide too much. The platform needs distinct eval suites for source retrieval, answer grounding, editorial quality, tool use, handoffs, safety, latency, and cost.

## Eval-Driven Development

The OpenAI guidance treats evals as a continuous process. The practical loop is:

1. define the objective;
2. collect representative and adversarial cases;
3. define metrics and thresholds;
4. run and compare evals;
5. grow the dataset from logs, failures, and human feedback.

Agent Studio should use this as a release discipline. A prompt, agent graph, tool schema, retrieval index, or provider route should not be promoted unless it has a baseline, a candidate result, and a decision record explaining the delta.

## Architecture-Specific Evals

Different architectures introduce different failure modes.

| Architecture | What to evaluate in Agent Studio |
|---|---|
| Single-turn model call | instruction following, output schema, factuality, style, refusal policy |
| Workflow | per-step correctness, routing, data passed between steps, final assembly |
| Single agent | tool choice, tool arguments, recovery from tool errors, guardrail behavior |
| Multi-agent | handoff boundaries, loop prevention, state preservation, conflicting instructions |

The most important design consequence is that evals must inspect intermediate behavior. Final-answer grading is necessary, but insufficient for agents.

## Trace Grading

Trace grading assigns structured labels or scores to the run trace: model calls, tool calls, decisions, guardrails, handoffs, and final output. This is the right debugging surface while behavior is still changing because it can answer questions that final-output evals cannot:

- Did the agent choose the right tool?
- Did it pass the correct arguments?
- Did it hand off to the right specialist?
- Did a guardrail trigger for the right reason?
- Did a prompt or route change improve the workflow or only change the wording?

Agent Studio should store traces as evaluable artifacts, not only as logs. Each trace should be replay-addressable by run ID, workflow version, source manifest, prompt version, model/provider version, tool schema version, retrieval index version, and grader version.

## Graders

OpenAI graders cover exact/string checks, text similarity, model-based scoring, code execution, and combinations. The useful abstraction is not the specific grader type; it is the explicit contract between an eval item, a generated sample, and a scoring rule.

Agent Studio grader types should include:

- deterministic checks for schemas, citations, required fields, and tool arguments;
- retrieval checks for context precision, context recall, source freshness, and claim coverage;
- rubric graders for editorial judgment, reasoning quality, and grounding;
- safety graders for jailbreak susceptibility, unsafe tool use, over-refusal, and policy misses;
- cost and latency checks for route eligibility.

Model graders need calibration against human review. Pairwise or pass/fail framing should be preferred when it is sufficient, because open-ended scoring can drift.

## Dataset Design

Useful eval datasets should come from mixed sources:

- production logs and observed failures;
- expert-authored cases;
- edge cases and adversarial examples;
- user corrections and reviewer overrides;
- synthetic examples only when they are reviewed or constrained by realistic distributions.

The dataset should identify which architecture surface it tests. A retrieval eval item, a tool-call eval item, and a final-answer eval item should not share the same schema unless they actually measure the same behavior.

## Edge Cases To Preserve

Agent Studio should explicitly track:

- short or ambiguous user requests;
- multilingual or non-text input where applicable;
- long context and long-running conversations;
- conflicting user and system/developer instructions;
- ambiguous tool-return fields;
- multiple tool calls;
- multiple handoffs and handoff loops;
- format requests that conflict with safety or source-grounding requirements;
- jailbreak attempts and indirect prompt injection through retrieved material.

These should become named eval slices so regressions can be diagnosed by failure class rather than only by aggregate score.

## Agent Safety Implications

OpenAI's agent safety guidance combines several controls: stronger instruction-following models, tool approvals, guardrails, structured outputs, trace graders, evals, and isolation of untrusted input. The important systems lesson is that no single control is sufficient.

Agent Studio should require human approval for write actions and high-risk tool use, keep untrusted retrieved text out of control instructions, extract structured fields before tool calls where possible, and use trace graders to detect unsafe autonomy patterns.

## Canon Cross-Check

Production canon already requires route releases, eval suites, source snapshots, rollback plans, and trace inspection. This note makes that requirement concrete: every production route needs an eval release gate that binds success contract, dataset version, grader version, trace coverage, baseline/candidate comparison, failure slices, calibration state, and human-review override policy.

Retrieval and reranking notes own candidate recall, ranking metrics, and source-grounding checks; this note owns the release decision that says those measurements are sufficient for a route change.

Observability notes own traces, spans, and annotation loops; this note owns which trace fields must become graded evidence before agent topology, tool schemas, handoffs, guardrails, or publishing authority change.

Safety and privacy notes own trust boundaries, approvals, redaction, and provider data boundaries; this note owns the eval cases that prove those controls are still effective after a model, prompt, tool, retrieval, or route change.

## Agent Studio Data Model Implications

Minimum durable entities:

- `eval_dataset`: purpose, owner, source provenance, architecture surface, slice tags;
- `eval_case`: input, expected behavior, references, risk tags, production-origin metadata;
- `grader`: type, rubric, threshold, calibration status, model/runtime version if applicable;
- `trace_grader`: grader attached to trace spans, tool calls, handoffs, or guardrail events;
- `eval_run`: workflow/model/prompt/tool/retrieval versions, dataset version, results, cost, latency;
- `eval_result`: score, pass/fail, grader explanation, failing span, linked trace, reviewer override;
- `eval_slice`: named failure or behavior class such as grounding, source coverage, tool use, handoff, jailbreak, over-refusal, latency, or cost;
- `grader_calibration_record`: human-review sample, agreement signal, drift caveat, reviewer override policy, and recalibration cadence;
- `eval_release_gate`: required suites, trace coverage, baseline/candidate comparison, threshold decisions, failure-slice regressions, calibration state, reviewer, and rollback condition before a variant can ship.

## Release Gates

Every candidate change should declare which eval suites are required:

| Change type | Required gate |
|---|---|
| prompt edit | prompt dataset, output schema checks, representative workflow traces |
| model/provider route | task evals, safety evals, latency/cost thresholds, regression comparison |
| retrieval/index change | context precision/recall, source coverage, citation accuracy, freshness |
| tool schema change | tool-choice accuracy, argument precision, failure recovery, approval policy |
| agent graph/handoff change | trace grading, loop detection, state preservation, specialist routing |
| guardrail change | jailbreak, over-refusal, unsafe pass-through, false-positive review |

## Design Commitments

- Build evals before broad autonomy.
- Treat traces as first-class eval inputs.
- Keep retrieval, tool use, final output, and safety as separate eval surfaces.
- Version every eval artifact and every artifact being evaluated.
- Convert production failures into eval cases.
- Calibrate model graders against human review.
- Use eval deltas as promotion evidence, not aggregate vibes.

## Follow-Ups

- Define the first Agent Studio `eval_run` schema in the LLD.
- Add named eval slices for retrieval grounding, tool use, handoffs, and safety.
- Decide which eval suites are required before enabling autonomous publishing profiles.
