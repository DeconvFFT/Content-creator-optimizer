---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Prompt Engineering for LLMs"
authors: "John Berryman; Albert Ziegler"
chapter: "5"
chapter_title: "Prompt Content"
source_path: "/Users/saumyamehta/DS interview prep/books/Prompt Engineering for LLMs- The Art and Science of Building.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 5 - Prompt Content

## Reading Status

Direct source reading pass completed for chapter 5 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied code listings, copied figures, copied tables, and long excerpts.

## Core Idea

The chapter separates prompt content into static content and dynamic content. Static content defines the task, clarifies constraints, and gives examples. Dynamic content supplies request-specific context about the user, object, source material, or current state. Good prompt engineering starts by gathering more candidate content than will fit, then later scoring, filtering, and assembling it.

Agent Studio implication: prompt inputs should be modeled as typed content candidates with source, stability, latency, score, dependency, and trust metadata. The final prompt is an assembly result, not the source of truth.

## Static Content

Static content includes instructions, clarifications, policies, output expectations, and few-shot examples. Explicit instructions can work, especially in system messages for chat models, but examples often communicate format, style, threshold, and implicit scoring behavior more effectively.

Agent Studio implication: static prompt text should be versioned as a route artifact. Store purpose, expected behavior, affected output fields, and linked eval cases for each instruction block.

## Few-Shot Prompting

Few-shot examples teach the model patterns by demonstration. They are especially useful for output format, style, edge-case handling, and subjective thresholds. The chapter also stresses risks:

- examples consume context;
- examples bias the model toward their distribution;
- example order can imply accidental patterns;
- short examples may underrepresent the real task;
- overly similar examples can confuse long prompts.

Agent Studio implication: few-shot sets need their own evals. Store example source, selection policy, ordering policy, covered classes, edge cases, and measured bias.

## Dynamic Content

Dynamic content is gathered at request time or prepared ahead of time for a user/session/task. The chapter frames dynamic context by latency, preparability, comparability, proximity to the application, and stability over time.

Agent Studio implication: context sources should be selected by route latency tier. A realtime typing assistant cannot use the same retrieval and summarization path as an asynchronous report generator.

## Context Discovery

The chapter suggests two complementary discovery strategies: map what the model might need to know, and inventory what the application can actually obtain. Candidate sources include current app state, stored user profile, previous activity, public APIs, and user-permissioned systems.

Agent Studio implication: source planning should track not just relevance but access path, permission boundary, freshness, and whether the context can be precomputed.

## Retrieval

RAG retrieves relevant snippets from a large information space and injects them into the prompt. The chapter covers lexical retrieval, simple similarity methods, BM25-style weighting, neural retrieval with embeddings, snippet sizing, vector storage, and the tradeoff between semantic match and debuggability.

Agent Studio implication: retrieval routes need traceability. Store original query, rewritten query, retrieval method, score, snippet id, embedding model, index version, lexical fields, reranker result, and final inclusion decision.

## Chekhov Context Risk

The chapter warns that irrelevant retrieved context can be overinterpreted by the model because the model assumes included details matter. This is a core RAG risk: bad context can be worse than missing context.

Agent Studio implication: context precision matters as much as recall. Eval datasets need negative cases where irrelevant-but-plausible snippets are retrieved and should be ignored.

## Summarization

Summarization compresses large context by zooming out rather than searching in. The chapter covers hierarchical summarization, natural boundary splitting, summary-of-summary recursion, and the risk of compounding distortion. It also distinguishes general reusable summaries from task-specific summaries.

Agent Studio implication: summaries are derived artifacts with lineage. Store source span, summary prompt, model, target use case, abstraction level, and refresh trigger.

## Datastore Requirements

Agent Studio should store prompt-content records:

- `content_candidate`: source, static/dynamic type, stability, freshness, permission, latency tier, score, priority, dependencies, and trust level.
- `few_shot_set`: examples, selection rule, order rule, covered classes, edge cases, token cost, and eval result.
- `retrieval_candidate`: query, backend, index version, embedding model, lexical analyzer, score, rank, snippet id, and inclusion decision.
- `summary_artifact`: source span, summary level, summary prompt, model, use case, lossy-risk flag, and refresh policy.
- `context_precision_eval`: retrieved irrelevant snippets, model behavior, ignored/used judgment, and mitigation.

## Failure Modes

- Treating all context as equally useful.
- Adding examples that bias outputs toward accidental patterns.
- Retrieving semantically adjacent but task-irrelevant context.
- Using vector-only retrieval when lexical debuggability is required.
- Reusing a task-specific summary for a different task.
- Ignoring latency and permission costs of dynamic context.

## Agent Studio Design Implications

- Build context gathering as a scored candidate pipeline.
- Keep static instructions, few-shot examples, retrieved snippets, summaries, and user-provided content as separate artifact types.
- Add eval cases for context selection, not only final answer quality.
- Prefer hybrid retrieval when production debuggability matters.
- Treat summarization as a cacheable but lossy transformation with explicit lineage.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
