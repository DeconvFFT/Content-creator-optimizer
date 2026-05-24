---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Prompt Engineering for LLMs"
authors: "John Berryman; Albert Ziegler"
chapter: "11"
chapter_title: "Looking Ahead"
source_path: "/Users/saumyamehta/DS interview prep/books/Prompt Engineering for LLMs- The Art and Science of Building.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 11 - Looking Ahead

## Reading Status

Direct source reading pass completed for chapter 11 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied code listings, copied figures, copied tables, and long excerpts.

## Core Idea

The chapter looks beyond text-only prompting toward multimodal inputs, stateful objects of discourse, better model intelligence, cheaper serving, longer context, and continuing architectural change. The durable lesson is not any single model feature but the need to design prompts and interfaces around how models actually consume context.

Agent Studio implication: the datastore and UI should assume capabilities will change. Routes, context strategies, model choices, artifact types, and eval gates must be versioned and replaceable.

## Multimodality

Multimodal systems can treat images and video frames as model inputs alongside text. The same context-selection discipline still applies: include relevant visual evidence, frame it with explanatory text, avoid irrelevant media, and prefer familiar visual/document formats the model can recognize.

Agent Studio implication: source records should support images, screenshots, frames, diagrams, generated assets, and visual QA artifacts. Retrieval should be able to attach both text snippets and visual references with purpose-specific captions.

## Stateful Objects Of Discourse

The chapter argues that many assistant interactions are really about a changing object: code, a diagram, a document, a plan, or another artifact. Chat transcripts alone are poor at this because they produce repeated versions instead of one evolving stateful object. Artifact-style UIs are a step toward working on the object directly.

Agent Studio implication: generated scripts, storyboards, reels, prompts, datasets, route manifests, diagrams, and source ledgers should be durable artifacts with versions, diffs, owners, and conversation links. The chat should discuss and modify the artifact rather than burying every version in messages.

## Multi-Artifact UX

Single-artifact UIs do not fully solve production work because real workflows involve several related objects. Users need shorthand names, direct editing, model awareness of user edits, and the ability to reason about multiple artifacts at once.

Agent Studio implication: the studio should expose named artifacts, artifact graph links, user edits, model edits, review comments, and dependency notifications. A task agent should know which artifact it owns and which upstream artifacts changed.

## Model Intelligence Trends

The chapter expects better benchmarks, stronger reasoning training, distillation, quantization, faster inference, lower cost, and larger context windows. It also warns that models will not be psychic: if needed information is absent from the prompt or tools, better intelligence will not reliably recover it.

Agent Studio implication: increasing model capability should reduce some constraints but not remove source grounding. Route promotion still needs source recall, context assembly, and eval evidence rather than trust in a newer model.

## Prompt Engineering Lessons

The closing lessons are that LLM interfaces still reduce to transcript-like completion and that prompt designers should empathize with model limitations. Prompts should use familiar motifs, remove distracting information, be understandable to humans, provide explicit task leadership, include needed information or tools, and permit useful intermediate reasoning where appropriate.

Agent Studio implication: generated prompts should be inspectable as documents. If a human cannot understand the rendered prompt and context, the system should not assume the model will behave predictably.

## Datastore Requirements

Agent Studio should store future-proofing records:

- `artifact_record`: type, owner task/agent, current version, prior versions, diff links, source links, and conversation anchors.
- `visual_source_record`: media type, capture method, rights status, caption, OCR/vision summary, and use constraint.
- `model_capability_record`: modalities, context length, tool support, structured-output support, latency, cost, eval evidence, and retirement plan.
- `artifact_dependency`: upstream/downstream links, change event, affected task agents, and revalidation status.
- `rendered_prompt_snapshot`: full prompt/context hash, human-readable rendering, included media pointers, and evaluator notes.

## Failure Modes

- Treating chat transcript history as a substitute for artifact state.
- Rewriting large artifacts repeatedly instead of applying trackable edits.
- Adding multimodal context without explaining why each image/frame matters.
- Assuming a smarter model can compensate for missing sources.
- Hardcoding current provider capabilities into the workflow design.
- Evaluating only text output while ignoring visual and artifact-state correctness.

## Agent Studio Design Implications

- Build around durable artifacts, not only messages.
- Support multimodal sources and visual QA as first-class records.
- Keep model capability assumptions in the route registry.
- Require rendered-prompt inspection for complex routes.
- Let users edit artifacts directly and feed those edits back into the next model context.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
