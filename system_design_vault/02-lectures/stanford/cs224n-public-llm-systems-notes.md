---
type: official-course-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
source_status: official_stanford_public_course_page_slides_notes_and_playlist_pointer
sources:
  - https://web.stanford.edu/class/cs224n
  - https://web.stanford.edu/class/cs224n/
  - https://www.youtube.com/playlist?list=PLoROMvodv4rOaMFbaqxPDoLWjDaRAdP9D
  - https://web.stanford.edu/class/cs224n/readings/cs224n_winter2023_lecture1_notes_draft.pdf
  - https://web.stanford.edu/class/cs224n/readings/cs224n-2019-notes02-wordvecs2.pdf
  - https://web.stanford.edu/class/cs224n/readings/cs224n-self-attention-transformers-2023_draft.pdf
  - https://web.stanford.edu/class/cs224n/slides_w26/cs224n-2026-lecture07-pretraining.pdf
  - https://web.stanford.edu/class/cs224n/slides_w26/cs224n-2026-lecture08-posttraining.pdf
  - https://web.stanford.edu/class/cs224n/slides_w26/cs224n-2026-lecture09-peft.pdf
  - https://web.stanford.edu/class/cs224n/slides_w26/cs224n-2026-lecture10-rag-agents.pdf
  - https://web.stanford.edu/class/cs224n/slides_w26/cs224n-2026-lecture12-reasoning-part1.pdf
  - https://web.stanford.edu/class/cs224n/slides_w26/cs224n-2026-lecture13-reasoning-part2.pdf
  - https://web.stanford.edu/class/cs224n/slides_w26/cs224n-2026-lecture14-guest-julie-tokenization-multilinguality.pdf
  - https://web.stanford.edu/class/cs224n/slides_w26/cs224n-2026-lecture16-impact-on-humanity.pdf
related:
  - "[[cs224n-nlp-llm-systems-source-map]]"
  - "[[../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
---

# CS224N Public LLM Systems Notes

## Reading Scope

Direct-read pass over the current public CS224N Winter 2026 course page, public lecture notes for word vectors and transformers, public 2026 slides for pretraining, post-training, PEFT, agents/RAG, reasoning, tokenization/multilinguality, and broader impacts, plus the official public Spring 2024 YouTube playlist pointer. This note does not claim 2026 video coverage because the course page says those videos require enrolled-student access.

This note stores compact original synthesis only. It does not store raw slide text, assignment solutions, or long excerpts.

## Core Thesis

CS224N is the vault's strongest Stanford source family for the language side of Agent Studio. It connects representation learning, transformers, pretraining, alignment, efficient adaptation, RAG, agents, benchmarking, reasoning, tokenization, multilinguality, and social risk into one progression.

Agent Studio implication: language routes should be designed as systems with representation, data, adaptation, tool, eval, decoding, and governance choices, not as isolated prompts.

## Representation And Retrieval

The word-vector notes start from the representation problem: symbols need computational forms, and one-hot identity alone cannot express similarity, relatedness, or context. Distributional learning makes meaning operational by learning from context. The course also emphasizes that language systems are deployed in settings where failures are opaque and socially consequential.

Agent Studio implication:

- retrieval and reranking should expose the representation used, not just a final answer;
- embedding quality should be evaluated on source recall, entity recall, semantic near-misses, and bias/fairness slices;
- source-grounded routes should preserve provenance because question answering and summarization are dual-use systems.

## Transformers And Pretraining

The transformer notes and pretraining slides make two production points. First, attention is the routing primitive that lets models condition on different context positions instead of compressing everything into one fixed representation. Second, pretraining changed NLP by moving most parameters into large self-supervised initialization, with different architecture families supporting different use cases: decoders for generation, encoders for bidirectional representation, and encoder-decoders for conditional generation.

Agent Studio implication:

- route selection should distinguish decoder generation, embedding/encoder retrieval, and encoder-decoder transformation jobs;
- context packing is an architectural decision because attention cost, context position, and source ordering affect behavior;
- pretraining data provenance matters even when the model is used only through an API.

## Post-Training And Preferences

The post-training and PEFT slides frame the gap between language modeling and assisting users. Instruction tuning, RLHF-style preference optimization, DPO-style preference learning, and human/AI feedback are adaptation tools with real data and governance costs. The PEFT slides reinforce that adaptation is a ladder: prompting, LoRA/adapters, distillation, pruning, and other parameter-efficient methods trade capacity, cost, deployability, and risk.

Agent Studio implication:

- preference pairs should store chosen and rejected artifacts, rubric, evaluator type, source evidence, and candidate order;
- route-change proposals should justify why prompt/RAG/tool changes are insufficient before fine-tuning or PEFT;
- adaptation decisions need data provenance and eval gates, not only a training script.

## Agents, Tool Use, And RAG

The RAG/agents lecture explicitly combines question answering, retrieval, planning, memory, tool use, and agent data/evaluation. That matches Agent Studio's core production concern: an agent is not a chat prompt; it is a routed workflow that has memory, external tools, retrieval evidence, and eval data.

Agent Studio implication:

- agent routes need tool contracts, memory policy, retrieval traces, planner traces, and approval edges;
- RAG routes need accepted/rejected evidence, authorization filters, chunk/source IDs, and source freshness;
- tool-use and RAG evals should inspect traces rather than only final answers.

## Benchmarking And Evaluation

The course schedule places benchmarking/evaluation after agents and before reasoning, which is the right order for production systems: once routes can retrieve, call tools, and plan, model benchmarks alone are too weak. The Agent Studio equivalent is route-specific eval suites with workflow traces, source grounding, approval checks, and regression budgets.

Agent Studio implication:

- benchmark results should be stored as context, not as release approval by themselves;
- eval datasets should map to real route surfaces: retrieval, tool choice, reasoning, citation, safety, latency, and cost;
- every route promotion should compare baseline and candidate behavior on fixed cases.

## Reasoning And Decoding

The reasoning slides separate decoding behavior from model capability. Greedy, beam, sampling, speculative decoding, long-context extension, on/off-policy distillation, and inference-time scaling all affect output quality, loops, latency, and cost. The notes also surface looping as a live failure mode in reasoning models, not an old solved issue.

Agent Studio implication:

- reasoning routes need loop detectors, retry budgets, trace-grade checks, and cost ceilings;
- decoding settings are release metadata, not incidental provider parameters;
- speculative decoding or draft/target setups should be treated as serving-profile changes with eval comparison.

## Tokenization And Multilinguality

The tokenization/multilinguality lecture shows that text segmentation is not a neutral preprocessing detail. Word, character, byte, and subword choices affect spelling, rare words, glitch tokens, multilingual fairness, cost, and cross-lingual transfer.

Agent Studio implication:

- tokenization profiles should be recorded for model/provider routes, especially for multilingual social content;
- capacity estimates should account for language-specific token inflation and latency;
- eval suites need multilingual slices for source retrieval, generation quality, safety, and cost.

## Broader Impacts

The course includes risks and social impacts as part of the main sequence. For Agent Studio, this means source-grounded content generation, summarization, surveillance-like analysis, multilingual coverage, and public publishing all need explicit policy and review boundaries.

Agent Studio implication:

- routes that summarize people, communities, or sensitive topics should carry risk labels and reviewer gates;
- public publishing should require provenance and approval;
- bias, dialect, and underrepresented-language failures should create eval cases, not just warnings.

## Datastore Requirements

Add or strengthen:

- `tokenizer_profile`: model/provider tokenizer, language coverage, token inflation estimates, known failure modes, and route compatibility.
- `adaptation_candidate`: prompt/RAG/tool/PEFT/fine-tune/distillation option, justification, data requirement, eval gate, and rollback plan.
- `reasoning_trace`: decoding settings, test-time compute budget, loop detector, verifier calls, accepted/rejected reasoning artifacts, and final answer trace.
- `benchmark_context`: external benchmark or course benchmark used only as contextual evidence, with limitations and route relevance.
- `language_coverage_slice`: language, dialect/locale, tokenizer cost, source availability, evaluator coverage, and known risks.

## Agent Studio Design Implications

- Treat CS224N as the canonical Stanford language-system source family, separate from CS231N visual systems and CS336 infrastructure systems.
- Keep model benchmarks subordinate to route evals.
- Store decoding, tokenization, and adaptation choices as release metadata.
- Make multilingual and broader-impact slices first-class eval coverage for any public content route.
- Keep public YouTube playlist/video notes separate from this schedule/slide synthesis until direct video watching notes are created.

## Related Official Video Sources

The official CS224N page routes public video viewers to the Spring 2024 playlist, while the current 2026 videos are gated. These entries are topic navigation pointers only; no individual video has been watched in full for this note.

| Video source | URL | Relevant topics | Status |
|---|---|---|---|
| CS224N Spring 2024 public YouTube playlist | https://www.youtube.com/playlist?list=PLoROMvodv4rOaMFbaqxPDoLWjDaRAdP9D | word vectors, neural NLP foundations, transformers, pretraining, post-training, adaptation, benchmarking, reasoning, tokenization, multilinguality, impacts | playlist candidate; individual videos not watched in full |
| CS224N Winter 2026 Canvas/Panopto recordings | Official course page only; enrolled-student access boundary | current-offering lecture videos | gated; not ingested |
