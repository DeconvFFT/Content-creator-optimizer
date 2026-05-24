---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Prompt Engineering for LLMs"
authors: "John Berryman; Albert Ziegler"
chapter: "2"
chapter_title: "Understanding LLMs"
source_path: "/Users/saumyamehta/DS interview prep/books/Prompt Engineering for LLMs- The Art and Science of Building.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 2 - Understanding LLMs

## Reading Status

Direct source reading pass completed for chapter 2 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied formulas, copied figures, copied tables, and long excerpts.

## Core Idea

The chapter gives the prompt engineer's mental model of LLM behavior: an LLM takes text in, emits text out, mimics training-document patterns, operates over tokens rather than human-visible words or letters, generates one token at a time, and sees information only in the left-to-right context available to it.

Agent Studio implication: route reliability improves when product design matches the model's mechanics instead of assuming human-style reading, pausing, checking, editing, or memory.

## Mimicry And Hallucination

The chapter explains that models learn to complete plausible documents rather than consult a truth oracle. Hallucination is a natural failure mode because plausible-looking continuation and true continuation are not the same thing. Prompts that assert false premises can induce the model to continue as if those premises were true.

Agent Studio implication: source-grounded routes need verification paths. The datastore should distinguish model-generated claims from retrieved evidence, tool results, and checked facts.

## Tokenization

LLMs see token sequences, not the exact units humans see. Tokenization affects spelling, typos, non-English text, code, rare names, length accounting, and apparent reasoning over characters. Counting tokens is also central to prompt packing and cost control.

Agent Studio implication: every route should store tokenizer, token counts, context budget, truncation strategy, and overflow behavior. User-facing "word" limits are not enough for prompt assembly.

## Autoregressive Generation

The model generates one token at a time and cannot revise previous tokens unless the application creates a new prompt. This explains why errors can compound and why explicit output formats, stop conditions, and parsers matter.

Agent Studio implication: structured output should be constrained, validated, and repaired outside the model loop. Long generations need stop rules, schema checks, and partial-output failure handling.

## Temperature And Sampling

Temperature controls how strongly the model follows the highest-probability token. Low temperature is better for correctness and repeatability; higher temperature can explore alternatives but increases instability. Very high temperature can create cascading nonsense because the model then mimics its own noisy output.

Agent Studio implication: sampling settings are route policy. Store temperature, top-p/top-k where available, candidate count, seed/retry policy, and use-case rationale. Do not reuse creative settings for factual extraction or compliance gates.

## Transformer Directionality

The chapter's transformer explanation emphasizes that information moves left-to-right and bottom-to-top through layers. The model cannot look ahead in the prompt; later instructions do not help earlier token representations. Generated intermediate text can become new context for later tokens, which is the basis of visible reasoning patterns.

Agent Studio implication: prompt order matters. Critical instructions, role, context boundaries, and task framing need deliberate placement and eval coverage.

## Human Capability Test

The chapter proposes a useful feasibility heuristic: ask whether a human expert with all relevant general knowledge could complete the prompt in one pass without backtracking, editing, or notes. If not, the LLM may need external tools, decomposition, retrieval, scratchpad/state, or deterministic code.

Agent Studio implication: task planning should classify whether a route is one-pass generation, retrieval-assisted generation, tool-assisted computation, multi-step workflow, or human-reviewed decision.

## Datastore Requirements

Agent Studio should store model-mechanics fields:

- `tokenization_policy`: tokenizer id, estimated tokens, actual tokens, context limit, truncation side, and overflow handling.
- `generation_policy`: temperature, stochasticity controls, max tokens, stop sequences, candidate count, and deterministic/retry expectations.
- `grounding_policy`: retrieved evidence, claim extraction, citation requirements, verification tools, and unsupported-claim handling.
- `prompt_order_policy`: system instructions, user input placement, context placement, output format placement, and injection boundaries.
- `task_feasibility_class`: one-pass, needs retrieval, needs tool, needs workflow, needs human review, or not suitable for model-only handling.

## Failure Modes

- Asking the model to count, verify, search, or edit as if it had human-style scratch space.
- Hiding critical instructions after long context and assuming they influence all prior text.
- Treating confident prose as evidence.
- Using high temperature for tasks that require reproducibility.
- Ignoring tokenizer behavior for names, code, multilingual text, or prompt budgets.
- Letting false prompt assumptions pass into generation without validation.

## Agent Studio Design Implications

- Grounded workflows must separate retrieved facts, generated reasoning, and final prose.
- Token and context accounting should be first-class telemetry.
- Factual routes should default to low stochasticity, explicit sources, and eval checks.
- Complex tasks should be decomposed into tool/workflow steps rather than forced into one prompt.
- Prompt templates should be tested for order sensitivity, not just wording.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
