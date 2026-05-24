---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "AI Engineering"
authors: "Chip Huyen"
chapter: "5"
chapter_title: "Prompt Engineering"
source_path: "/Users/saumyamehta/DS interview prep/books/AI Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 5 - Prompt Engineering

## Reading Status

Direct source reading pass completed for chapter 5 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied prompts, copied tables, copied figures, and long excerpts.

## Core Idea

Prompt engineering is the first adaptation layer for foundation-model applications. It is cheap compared with fine-tuning, but it is still engineering work: prompts need experiments, versioning, evaluation, dependency tracking, cost accounting, and security review. Prompting is also not enough by itself for production systems because prompts interact with context construction, model templates, structured-output controls, tool permissions, and adversarial inputs.

For Agent Studio, prompts should be treated as versioned route artifacts. A prompt change can alter model behavior as much as a code or model change, so it needs the same release discipline: diff, eval, rollout, rollback, and owner.

## Prompt Anatomy

A useful prompt can contain task description, examples, task input, role/persona, output format, constraints, and context. The chapter distinguishes prompt from context: prompt is the full model input, while context is the information the model needs to perform the task.

Agent Studio implication: prompt records should separate reusable instruction text from query-specific context. This makes it possible to version instructions while snapshotting retrieved evidence, user input, examples, and tool outputs separately.

## In-Context Learning

In-context learning lets a model infer desired behavior from examples in the prompt without changing weights. Few-shot examples are helpful when the desired behavior, domain API, output style, or edge-case policy is not obvious from instruction alone. More examples can improve behavior but consume context, raise cost, and increase latency.

Design implications:

- Store few-shot examples as curated artifacts, not hidden strings inside code.
- Track which examples were used for which route run.
- Evaluate whether examples improve the actual task rather than assuming they help.
- Prefer compact examples when they preserve quality because token budget is production budget.
- Revisit examples when model versions change; stronger models may need fewer examples, while domain-specific workflows may still need them.

## System Prompts, Chat Templates, And Context Efficiency

System prompts and user prompts are eventually combined into a model-specific final input. Different models use different chat templates, and template mismatches can cause silent behavior regressions. The chapter also stresses that longer context windows do not mean every token is equally useful; models can be weaker at using information in the middle of long prompts.

Agent Studio implication:

- Route registry entries should store model chat template version or provider message protocol.
- Prompt rendering should be inspectable before execution.
- Context-position evals should test whether critical evidence is usable when placed early, middle, and late.
- Long-context routes still need retrieval/reranking discipline, summarization, and source selection.
- Provider/model swaps should rerun prompt-template and context-efficiency evals.

## Prompting Practices

The durable practices are straightforward but need operational discipline:

- write explicit instructions;
- define role/persona when it changes judgment or tone;
- provide examples to reduce ambiguity;
- specify output format and parser expectations;
- include sufficient context or tools to gather it;
- decompose complex workflows into simpler prompts;
- use reasoning or self-critique only where the quality gain justifies cost and latency;
- iterate prompts with stable evaluation data;
- evaluate the prompt inside the full system, not as an isolated string.

Prompt decomposition is especially important for Agent Studio. It turns one opaque instruction into a chain of inspectable steps, such as intent classification, retrieval query creation, source filtering, draft generation, critique, repair, and final response. This improves monitoring and debugging, but it also increases orchestration complexity, cost, and latency.

Agent Studio implication: each prompt step should have input/output schemas, evals, cost traces, and failure routing. Prompt chains are workflows, not just text.

## Prompt Tools And Automation

Prompt optimization tools can search, mutate, critique, and evaluate prompts automatically. They are useful when paired with a trustworthy evaluation set, but they can create hidden API calls, hidden prompt templates, tool-specific assumptions, and silent template errors.

Agent Studio implication:

- Any prompt tool output should be stored as a generated artifact with provenance.
- Hidden model calls should be counted in route cost.
- Tool-generated prompts should be inspected and evaluated before promotion.
- Prompt optimization should optimize against Agent Studio eval slices, not only a small generic validation set.

## Prompt Catalog

The chapter recommends separating prompts from code and adding metadata. A serious prompt catalog should support search, reuse, versioning, model compatibility, application ownership, expected schemas, sampling settings, and dependency tracking.

Agent Studio prompt records should include:

- prompt id and semantic version;
- route or agent owner;
- intended model/provider family;
- system/user/developer/tool message segments;
- expected input schema;
- expected output schema;
- sampling defaults;
- few-shot example set;
- context requirements;
- safety restrictions;
- eval contract;
- dependent agents/routes;
- rollback target.

## Defensive Prompt Engineering

Prompt attacks exploit the same instruction-following ability that makes foundation models useful. Chapter 5 covers prompt extraction, jailbreaking, prompt injection, indirect prompt injection through tools or retrieved content, and information extraction from context or training data. Prompt-level defenses help, but the chapter is clear that security must also be handled at model and system levels.

Agent Studio controls:

- Assume system prompts and hidden context can leak; do not put secrets in prompts.
- Treat retrieved text, web pages, emails, documents, and tool outputs as untrusted input.
- Separate instruction channels from data channels where the model/provider supports it.
- Require approval for impactful tool calls and database mutations.
- Run generated code only in isolated environments.
- Add input and output guardrails for PII, unsafe content, policy violations, and suspicious patterns.
- Track violation rate and false-refusal rate together.
- Maintain adversarial eval sets for known attacks and new red-team findings.

## Security Architecture Implications

Prompt-level wording is not a sufficient security boundary. Agent Studio needs defense in depth:

- model-level: choose models that respect instruction hierarchy and tool-output priority boundaries where possible;
- prompt-level: explicit policies, out-of-scope behavior, refusal behavior, and context-only constraints;
- system-level: permissioned tools, human approval, sandboxing, input/output filtering, anomaly detection, rate limits, and audit logs.

The platform should distinguish read-only tools from side-effecting tools. Retrieval and summarization can be automated more freely; file writes, publishing, email sending, database mutations, and external API writes need stronger approval and replay records.

## Failure Modes

- Treating prompt changes as informal tweaks rather than route changes.
- Burying prompts in code where they cannot be reviewed, searched, versioned, or rolled back independently.
- Using the wrong chat template for a model and misdiagnosing the failure as model weakness.
- Adding examples that improve a small demo but degrade production slices.
- Building one giant prompt that hides which substep failed.
- Using reasoning/self-critique everywhere and ignoring added latency and cost.
- Trusting prompt optimization tools without inspecting generated prompts and hidden calls.
- Putting secrets or private policy text in prompts and assuming users cannot extract them.
- Letting retrieved or tool-provided text issue instructions to the model.
- Measuring only jailbreak violation rate and ignoring false refusals.

## Agent Studio Design Implications

- Prompt artifacts should be part of the same source/route ledger as models, retrieval configs, judge prompts, and guardrails.
- Prompt releases need diffs, eval gates, canary rollout, rollback target, and owner approval.
- Prompt chains should be represented as graph nodes with typed inputs, typed outputs, and per-node traces.
- Context construction should be separate from prompt instructions so source evidence can be audited independently.
- Every side-effecting tool call should include the prompt version, context snapshot, tool parameters, approval state, and result.
- Prompt-security evals should include direct jailbreaks, indirect prompt injection through retrieved content, prompt extraction attempts, PII extraction attempts, and out-of-scope requests.
- The cockpit should show final rendered prompts for debugging where policy allows, with secrets redacted and context provenance preserved.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
