---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Prompt Engineering for LLMs"
authors: "John Berryman; Albert Ziegler"
chapter: "6"
chapter_title: "Assembling the Prompt"
source_path: "/Users/saumyamehta/DS interview prep/books/Prompt Engineering for LLMs- The Art and Science of Building.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 6 - Assembling The Prompt

## Reading Status

Direct source reading pass completed for chapter 6 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied code listings, copied figures, copied tables, and long excerpts.

## Core Idea

The chapter turns gathered content into an ordered, budgeted prompt. Effective assembly needs introduction, context, refocus, transition, document format, snippet formatting, token accounting, importance scoring, dependencies, incompatibilities, and selection algorithms.

Agent Studio implication: prompt assembly is a deterministic service surface. It should be reproducible from route version, source candidates, scores, token budget, dependency graph, and tokenizer.

## Prompt Anatomy

The chapter recommends an introduction that orients the model early, context elements in a deliberate order, a refocus that returns attention to the task, and a transition that makes the desired completion begin naturally. Longer prompts need explicit refocus because key information in the middle can be underused.

Agent Studio implication: prompt templates should have named sections and section-level evals. Do not treat prompt order as incidental string concatenation.

## Document Format

The chapter compares advice conversations, analytic reports, and structured documents. Conversations fit interactive help and tool loops; reports fit analysis and conclusions; structured formats such as XML, YAML, or JSON make parsing and complex outputs easier.

Agent Studio implication: route records should include `document_archetype`. The choice affects prompt assembly, output parsing, injection defense, stop conditions, and eval design.

## Snippet Formatting

Snippets should be modular, natural, brief, and inert. Modularity lets snippets be included or removed. Naturalness keeps them aligned with the document format. Brevity preserves budget. Inertness reduces token-count surprises when snippets are concatenated.

Agent Studio implication: snippet artifacts need formatted text, source text hash, token count, formatting function version, and insertion constraints.

## Elastic Snippets

Some context can be represented at multiple levels of detail. The chapter describes elastic prompt elements that can shrink or expand based on available budget, and alternative incompatible snippets where only one representation should be selected.

Agent Studio implication: retrieval should not only produce fixed chunks. Store summary/full/linked variants and incompatibility groups so the assembler can choose the right representation.

## Prompt Element Relationships

Prompt elements have position, importance, and dependency. Position controls where the element belongs. Importance controls whether it survives token pressure. Dependencies express requirements and incompatibilities.

Agent Studio implication: prompt assembly should use a typed prompt-element graph, not a flat list. The graph should be inspectable in traces.

## Assembly Algorithms

The chapter frames prompt assembly as an optimization problem under token and dependency constraints. A minimal assembler can keep the most recent suffix. More mature routes may use additive greedy selection or subtractive pruning, depending on element interactions and latency needs.

Agent Studio implication: store the assembly algorithm and the rejected candidates. Debugging prompt quality requires seeing what did not fit and why.

## Datastore Requirements

Agent Studio should store prompt-assembly records:

- `prompt_template`: document archetype, named sections, introduction, refocus, transition, output boundary, and stop policy.
- `prompt_element`: position, priority, score, token count, source id, formatted text hash, dependencies, incompatibilities, and elastic variants.
- `assembly_run`: route version, tokenizer, max context, reserved completion tokens, selected elements, rejected elements, rejection reason, final prompt hash, and final section order.
- `snippet_formatter`: formatter version, input schema, output format, escaping policy, and inertness rule.
- `prompt_budget_decision`: hard context limit, soft budget, reserved output budget, overflow strategy, and latency tier.

## Failure Modes

- Appending context without a refocus or transition.
- Putting critical information in low-attention prompt regions.
- Counting tokens per snippet incorrectly because concatenation changes tokenization.
- Including two incompatible versions of the same evidence.
- Dropping required setup while keeping dependent details.
- Using a naive suffix assembler after the route becomes context-heavy.

## Agent Studio Design Implications

- Make prompt assembly traceable and replayable.
- Represent prompt elements with scores, priorities, positions, dependencies, and incompatibilities.
- Add token-budget simulations to route tests.
- Store rejected context so failures can be diagnosed.
- Treat output boundary and stop policy as part of the prompt template, not parser afterthoughts.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
