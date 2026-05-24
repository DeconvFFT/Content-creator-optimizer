---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "LLM Engineer's Handbook"
authors: "Paul Iusztin; Maxime Labonne"
chapter: "7"
chapter_title: "Evaluating LLMs"
source_path: "/Users/saumyamehta/DS interview prep/books/LLM Engineers Handbook.pdf"
rights_status: user_provided_local
source_lines: "9668-10708"
updated: 2026-05-17
cross_check_note_path: "system_design_vault/01-sources/official-open/llm-engineers-handbook-cross-check.md"
---

# 7 - Evaluating LLMs

## Reading Status

Direct source reading and official cross-check completed for chapter 7. This note is original synthesis only and does not include raw book text or long excerpts.

## Core Idea

LLM evaluation is not one metric. The chapter distinguishes standalone model evaluation from system evaluation, especially RAG evaluation. General benchmarks help shortlist models, but task-specific and system-specific evals determine whether a model or pipeline is useful for the product.

For Agent Studio, this means evals must cover agents, retrieval, generation, style, factuality, grounding, latency, and user-visible workflow quality. The system should not rely on public leaderboards or model names as quality proof.

## Model Evaluation

Standalone model evaluation measures a model without prompt engineering, RAG, tools, or other pipeline components. It is useful for:

- selecting a base model;
- checking whether fine-tuning improved the intended behavior;
- detecting quality regressions from training or optimization;
- comparing candidate models before integration.

Agent Studio implication:

- Keep model evals separate from agent/system evals.
- Record whether an eval result applies to the raw model, prompt-wrapped model, RAG pipeline, or full agent workflow.

## How LLM Evaluation Differs From Classic ML

Classic ML evals often have objective numeric labels for classification, regression, or ranking. LLM outputs are open-ended and can span many tasks, so evaluation often needs qualitative judgment, task-specific rubrics, or LLM judges.

Agent Studio implication:

- Use exact metrics where outputs are structured.
- Use rubrics and judge models where outputs are open-ended.
- Always keep sample outputs and judge explanations for auditability.

## Benchmark Use

General-purpose benchmarks such as MMLU-style knowledge tests, instruction-following tests, conversation arenas, and agentic benchmarks are useful signals. They are not source-of-truth guarantees because public benchmarks can be saturated, gamed, contaminated, or biased toward verbose/confident outputs.

Agent Studio implication:

- Use public benchmarks to shortlist model families.
- Use domain/task evals to make production choices.
- Treat large benchmark jumps after fine-tuning as possible contamination unless explained.

## Domain And Task-Specific Evals

Domain evals should cover realistic capabilities inside the domain, often by combining several benchmarks. Task-specific evals are usually narrower and can sometimes use classic ML metrics:

- accuracy, precision, recall, and F1 for extraction/classification;
- ROUGE-like overlap metrics for summarization when references exist;
- multiple-choice question answering for constrained knowledge or reasoning;
- LLM-as-judge for open-ended generation and style.

Agent Studio implication:

- Build separate eval suites for retrieval notes, content generation, source-grounded answers, agent planning, tool use, and editorial quality.
- Prefer smaller high-quality task eval sets over large irrelevant benchmark scores.

## LLM-As-Judge

The chapter uses LLM-as-judge for open-ended outputs, with explicit scoring criteria, examples, structured JSON outputs, and short explanations. This is useful when human labels are expensive and outputs are not easily scored by exact match.

Known risks:

- judges can favor long, confident, polished answers;
- judges may lack domain expertise;
- scores can be inconsistent;
- style preferences can be mistaken for correctness.

Agent Studio implication:

- Judge prompts need criteria, scales, examples, and structured outputs.
- Store judge explanation alongside numeric score.
- Use multiple judges or complementary metrics for high-impact decisions.
- Separate factual accuracy from writing style, helpfulness, completeness, safety, and source grounding.

## RAG Evaluation

RAG evaluation must inspect the whole system, not only the model answer. The chapter highlights:

- retrieval accuracy: whether the system fetched relevant evidence;
- integration quality: whether retrieved context was actually used well;
- factuality and relevance: whether the final answer is grounded and answers the user.

Agent Studio implication:

- Evaluate retrieval before generation.
- Store retrieved documents, kept context, dropped context, and final citations for each eval case.
- Compare answers with and without retrieved context when testing integration.

## RAG Metrics And Frameworks

The chapter discusses Ragas and ARES:

- Ragas supports metrics-driven RAG evaluation with LLM-assisted metrics such as faithfulness, answer relevancy, context precision, and context recall, plus synthetic test generation and production monitoring hooks.
- ARES uses synthetic data generation, trained classifiers, and configurable evaluation stages for context relevance, answer faithfulness, and answer relevance.

Agent Studio implication:

- Use faithfulness to catch unsupported claims.
- Use answer relevancy to catch answers that are correct but off-task.
- Use context precision to check whether top-ranked context is useful.
- Use context recall to check whether necessary evidence is missing.
- Consider classifier-backed evals for stable high-volume checks and LLM judges for richer qualitative checks.

## Evaluation Pipeline Design

The chapter's example evaluation pipeline:

- generates answers from candidate models on a test split;
- saves generated answers as artifacts;
- evaluates each answer with a judge model;
- parses structured scores;
- stores both raw judge output and score columns;
- reviews qualitative examples and aggregate metrics.

Agent Studio implication:

- Every eval run should preserve prompts, inputs, outputs, judge outputs, parsed scores, model IDs, prompt versions, and dataset versions.
- Intermediate artifacts make evals recoverable when judge calls or generation fail.
- Manual review remains necessary even when aggregate scores look reasonable.

## Failure Modes

- Public leaderboard performance does not transfer to Agent Studio tasks.
- Evaluation is run only on final answers, hiding retrieval and tool failures.
- Judge model rewards verbosity instead of correctness.
- Judge prompt lacks criteria, examples, or structured output requirements.
- RAG eval ignores context recall and only checks final answer style.
- Fine-tuning improves style while damaging factuality.
- Eval data overlaps with training data.
- System-level changes are shipped without rerunning task-specific evals.

## Agent Studio Design Decisions

- Maintain separate eval suites for model, retrieval, RAG answer, agent trace, tool use, and production workflow.
- Store eval datasets as versioned artifacts with source provenance.
- Use public benchmarks only as coarse signals.
- Add RAG eval metrics to the retrieval-quality ledger.
- Use LLM judges with structured outputs and retained explanations.
- Include qualitative review samples in every eval report.
- Turn production failures and user corrections into future eval cases.

## Follow-Ups

- Define the first Agent Studio eval report schema.
- Decide which RAG metrics are mandatory for local-book notes versus web/docs notes.
- Canon cross-check: [[01-sources/official-open/llm-engineers-handbook-cross-check]]

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "How I Learned to Stop Worrying and Love the Transformer" ([YouTube](https://www.youtube.com/watch?v=1GbDTTK3aR4)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
