---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Prompt Engineering for LLMs"
authors: "John Berryman; Albert Ziegler"
chapter: "4"
chapter_title: "Designing LLM Applications"
source_path: "/Users/saumyamehta/DS interview prep/books/Prompt Engineering for LLMs- The Art and Science of Building.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 4 - Designing LLM Applications

## Reading Status

Direct source reading pass completed for chapter 4 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied code listings, copied figures, copied tables, and long excerpts.

## Core Idea

The chapter defines an LLM application as a loop between the user's problem domain and the model's text domain. The application gathers the user problem, transforms it into a prompt or transcript, runs the model, then transforms the completion back into user-facing information or action. Complex products add persistent state, external context, reasoning decomposition, tools, and evaluation loops.

Agent Studio implication: system design should focus on the loop, not only the model call. The high-value datastore records are the state, context, prompt assembly, tool execution, parsing, eval, and feedback artifacts around each call.

## User Problem Complexity

The chapter classifies user problems by medium, abstraction, required context, and statefulness. A proofreading task is simple; IT support and travel planning require voice/text conversion, documentation search, API access, multi-turn memory, preferences, and real-world constraints.

Agent Studio implication: intake should classify task complexity before choosing a route. The same model can support multiple tasks, but each task has a different context, state, and tool profile.

## Prompt Construction Criteria

The chapter gives four criteria for model-domain transformation:

- the prompt should resemble familiar documents or transcripts;
- it should contain the information needed for the problem;
- it should condition a useful completion rather than more wandering text;
- it should have a natural or enforced stopping point.

Agent Studio implication: prompt templates need evidence for document pattern, source completeness, output usefulness, and stop/parse behavior.

## Context Gathering And Snippetizing

The chapter decomposes context work into source gathering, snippet extraction, scoring/prioritization, and prompt assembly. It notes that long context windows reduce but do not remove the need to select and organize relevant information; irrelevant context can still degrade completion quality.

Agent Studio implication: retrieval traces should show why each snippet was selected, how it was scored, what priority tier it belonged to, and whether it fit the token budget.

## State Management

Simple feedforward routes hold no memory. Chat and long-running workflows need state across turns, but state cannot be naively stuffed into every prompt forever. The application must decide what to keep, truncate, summarize, or retrieve.

Agent Studio implication: conversation memory needs a policy: raw history, summarized history, durable user facts, task checkpoints, and forgotten/expired content should be stored separately.

## External Context And RAG

RAG fills knowledge gaps by injecting information unavailable to the model during training. The chapter compares direct search from user text, model-generated search queries, and tool-mediated search decisions. It also emphasizes that classic keyword search can be easier to debug than vector-only retrieval.

Agent Studio implication: support hybrid retrieval. Store query source, query rewrite, retrieval backend, vector/text/graph hits, reranker output, and final context inclusion.

## Reasoning And Tools

For deeper tasks, the prompt engineer must decompose work and elicit intermediate reasoning or stepwise structure. Tools extend the loop by allowing the model to request searches, lookups, calculations, or external actions, with the application executing the request and injecting the result.

Agent Studio implication: tool loops need checkpoints and side-effect controls. Read-only tools and write/action tools should have different approval and audit rules.

## Evaluation

The chapter separates offline evaluation before shipping from online evaluation after exposure to users. Offline evaluation should exercise as much of the real application as possible, not just isolated prompt text. Online evaluation needs explicit feedback and implicit telemetry tied to actual product outcomes.

Agent Studio implication: eval runs should cover context gathering, prompt assembly, model generation, parsing, tools, and user-facing outcome. Telemetry should track outcome metrics, not only thumbs-up/down.

## Datastore Requirements

Agent Studio should store loop-level records:

- `task_intake`: user problem, medium, abstraction level, context needs, statefulness, tool needs, and risk class.
- `context_trace`: source queries, snippets, scores, priorities, truncation decisions, and final inclusion.
- `prompt_assembly`: boilerplate/template version, ordered segments, token accounting, stop policy, and final prompt hash.
- `state_policy`: raw turns, summaries, durable memories, task checkpoints, retention, and redaction.
- `tool_loop`: tool catalog, calls, results, retries, approvals, side effects, and errors.
- `offline_eval_run`: full pipeline coverage, cases, expected behavior, graders, metrics, and failure clusters.
- `online_telemetry`: explicit feedback, implicit outcome metrics, correction events, abandonment, edit distance, and downstream success.

## Failure Modes

- Testing only prompt wording while production failures come from retrieval or parsing.
- Adding too much context and reducing answer quality.
- Losing earlier critical conversation state through naive truncation.
- Letting the model decide tool use without tool result validation or side-effect controls.
- Treating user feedback buttons as the only online quality signal.
- Shipping without a natural stop condition or parseable output boundary.

## Agent Studio Design Implications

- Build the datastore around the full application loop.
- Make prompt assembly reproducible from source snapshots and route versions.
- Treat retrieval and snippet ranking as evalable components.
- Store state in typed layers rather than one undifferentiated transcript blob.
- Require offline evals that exercise the same retrieval, tool, and parsing paths used in production.
- Tie online telemetry to product outcomes that matter for the user, not only model aesthetics.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
