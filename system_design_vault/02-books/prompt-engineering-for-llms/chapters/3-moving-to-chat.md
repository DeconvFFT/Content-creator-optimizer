---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Prompt Engineering for LLMs"
authors: "John Berryman; Albert Ziegler"
chapter: "3"
chapter_title: "Moving to Chat"
source_path: "/Users/saumyamehta/DS interview prep/books/Prompt Engineering for LLMs- The Art and Science of Building.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 3 - Moving To Chat

## Reading Status

Direct source reading pass completed for chapter 3 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied code listings, copied figures, copied tables, and long excerpts.

## Core Idea

The chapter explains how the industry moved from raw completion models to chat models. Chat behavior is still document completion, but the document is a structured conversation transcript shaped by supervised fine-tuning, preference/reward modeling, RLHF-style alignment, API role separation, and tool-call conventions.

Agent Studio implication: a chat route is not "just a prompt." It is a transcript compiler with roles, hidden application messages, user messages, tool results, state, model settings, and injection boundaries.

## RLHF And Alignment

The chapter describes the alignment pipeline as base model, supervised fine-tuned assistant model, reward model, and reinforcement-style optimization against human preferences. The target behaviors are helpfulness, honesty, and harmlessness, but alignment can also impose taxes: over-refusal, blandness, lost task capability, or policy-shaped behavior that conflicts with a narrow product need.

Agent Studio implication: route evals should test both capability and alignment side effects. A model that is safer or chattier can still regress a product workflow.

## Chat Models As Transcript Completion

Chat APIs provide roles such as system, user, assistant, and tool/function. The model is trained to complete the next assistant message in a structured transcript. The visible user conversation and the model-facing transcript are not identical because the application may inject hidden instructions, context, examples, or tool outputs.

Agent Studio implication: store the model-facing transcript separately from the human-visible conversation. Bugs and prompt-injection risks often live in the hidden assembly layer.

## System Message Boundary

The chapter warns against placing user-controlled content in privileged instruction space. User text, retrieved documents, and tool outputs can contain adversarial instructions; placing them into system-level instructions defeats role separation.

Agent Studio implication: context records need prompt-location policy. Retrieved material should be quoted or sandboxed as data, not promoted into authority.

## Completion vs Chat Tradeoffs

Completion interfaces can be cleaner for tight formats where the completion begins exactly where the desired artifact begins. Chat interfaces are easier for assistant behavior but can add extra commentary or alignment behavior. Tool APIs extend the transcript pattern with machine-readable tool requests and tool results.

Agent Studio implication: route selection should compare completion-style, chat-style, structured-output, tool-call, and workflow interfaces. The interface is part of the route contract.

## API Parameters

The chapter highlights generation controls such as max tokens, stop sequences, logprobs, multiple completions, streaming, and temperature. These parameters are part of prompt engineering because they shape output quality, determinism, latency, and parseability.

Agent Studio implication: model settings belong in route versioning and eval diffs. A prompt change without settings lineage is not reproducible.

## Prompt Engineering As Playwriting

The chapter's playwriting metaphor is useful: the prompt engineer is the lead writer of a script containing roles, hidden exposition, user-supplied lines, model-authored lines, and external API-authored content. The application controls what the model sees and what the end user sees.

Agent Studio implication: model traces should attribute every transcript segment to its author: user, application, retrieval source, tool, model, or policy wrapper.

## Datastore Requirements

Agent Studio should store chat-route records:

- `chat_transcript`: role, author, visibility, trust level, source id, content hash, and injection boundary for each segment.
- `system_instruction_version`: role description, tool policy, safety policy, output format, and allowed user/context interpolation fields.
- `alignment_eval`: helpfulness, honesty, harmlessness, refusal behavior, over-compliance, jailbreak resistance, and task-specific capability retention.
- `chat_generation_settings`: model, temperature, max tokens, stop strings, streaming mode, logprobs availability, candidate count, and retry policy.
- `tool_transcript_segment`: tool definition, call arguments, execution result, error, side-effect class, and user approval state.

## Failure Modes

- Injecting user or retrieved content into system instructions.
- Evaluating only the visible chat and ignoring hidden transcript assembly.
- Choosing chat when a completion or structured-output route would be easier to parse.
- Allowing alignment behavior to silently change product task success.
- Letting model-generated tool calls execute without schema validation and side-effect policy.
- Losing reproducibility by not recording model settings and stop conditions.

## Agent Studio Design Implications

- Separate human-visible conversation, model-facing transcript, and execution trace.
- Enforce privileged-role boundaries for system/developer instructions.
- Treat chat format and tool API format as release artifacts.
- Include alignment-regression tests in route promotion.
- Store transcript attribution so failures can be traced to prompt template, user input, retrieval, tool result, or model behavior.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
