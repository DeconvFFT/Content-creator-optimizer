---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS25 Transformers United V6"
lecture_title: "Distinct Modes of Generalization from Parameters and Context, and Paths to Bridge the Gap"
speaker: "Andrew Lampinen, Anthropic"
source_status: official_public
updated: 2026-05-18
sources:
  - https://web.stanford.edu/class/cs25/
  - https://arxiv.org/abs/2505.00661
  - https://arxiv.org/abs/2210.05675
  - https://lampinen.github.io/index.html
related:
  - "[[cs25-retrieval-augmented-language-models]]"
  - "[[../../03-patterns/transformer-systems/cs25-transformer-systems-canon]]"
  - "[[../../04-agent-studio-implications/Capacity Estimation - Adaptation and Serving Decisions]]"
  - "[[../../03-patterns/retrieval/reranking-search-kg-patterns]]"
---

# CS25 - Parameters And Context Generalization

## Reading Status

Canon-ready direct read of the official Stanford CS25 V6 listing for the May 7 talk, the arXiv record for the 2025 controlled study on in-context learning versus finetuning, the earlier arXiv paper on context versus weights, and Lampinen's public research page, rechecked on 2026-05-18. This note does not claim video-level coverage and stores no raw paper text, slide text, or long excerpts.

## Why This Matters

Agent Studio constantly has to decide where knowledge should live:

- in model weights through fine-tuning;
- in retrieved context from the source ledger;
- in prompts and examples;
- in agent memory or skills;
- in eval data and route policies.

The CS25 lecture slice matters because it warns that these storage locations do not generalize the same way. A fact learned in weights is not automatically equivalent to the same fact presented in context. The right design question is not "can we teach the model?" but "what kind of reuse and generalization do we need?"

## Core Finding

The 2025 controlled study reports that finetuned models can show narrow generalization over learned factual information, while in-context learning can support different and sometimes more flexible deductive behavior. The earlier context-versus-weights paper frames the same split as different inductive biases: models may generalize differently depending on whether information is stored in parameters or supplied at inference time.

Agent Studio implication: a source-grounded product should not fine-tune volatile knowledge, provenance-sensitive facts, or route-specific source claims just because the model can memorize them. Retrieval and context assembly preserve inspectability, updateability, and citation behavior.

## Memory Placement Rules

| Need | Preferred placement | Reason |
|---|---|---|
| Fresh facts, official docs, policy, source-backed claims | Source ledger + retrieval/context | Must be updateable and citeable. |
| Stable task behavior, formatting, domain procedure | Prompt, tool schema, examples, skills | Behavior can change without retraining. |
| Repeated latent reasoning pattern with enough examples | Adapter/SFT candidate | Only after evals show retrieval/prompt/tool fixes fail. |
| Preference/style tradeoff | Preference pairs or rubric tuning | Should not be mixed with factual updates. |
| High-risk decisions | External evidence + human gate | Model memory is not authority. |

## Bridging The Gap

The CS25 listing says the talk covers data augmentation, retrieval, and RL as possible bridges between parameter learning and context learning. For Agent Studio, these are three different product levers:

- data augmentation: create eval and training examples that expose the generalization requirement, not just surface style;
- retrieval: keep episodic/source evidence available when flexible reuse and citations matter;
- RL/preference optimization: tune behavior only against explicit reward or preference signals, with regression checks against grounding.

Agent Studio implication: adaptation proposals should state which gap they target. "The model forgot" suggests retrieval or source freshness. "The model cannot use the right evidence" suggests context assembly, reranking, or reasoning traces. "The model repeatedly chooses the wrong behavior even with correct evidence" is a stronger adaptation candidate.

## Failure Modes

- Fine-tuning can make a route look better on seen examples while still failing reversals, deductions, or unseen compositions.
- Long context can hide weak retrieval if source recall and citation validity are not measured.
- RAG can fail if context is retrieved but not used, or if relevant evidence is drowned by irrelevant chunks.
- Preference tuning can improve style while damaging grounding if reward signals do not inspect evidence.
- A route can pass aggregate evals while failing the exact generalization slice that motivated the change.

## Agent Studio Design Implications

Add or strengthen these fields in route and adaptation records:

- `knowledge_memory_choice`: weights, retrieved context, prompt examples, graph memory, skill memory, or human policy;
- `generalization_requirement`: reversal, deduction, composition, extrapolation, source recall, style transfer, or workflow recovery;
- `context_vs_weight_rationale`: why the chosen memory location is appropriate;
- `latent_generalization_eval_id`: eval slice proving the behavior generalizes beyond seen examples;
- `retrieval_as_memory_required`: whether source-grounded evidence must remain external and citeable.

The practical release rule: do not approve model adaptation unless the proposal identifies the required generalization type and proves that lighter source/context/tool repairs are insufficient.

## Release Gate Contract

`knowledge_allocation_release_gate` is required before Agent Studio moves knowledge or behavior between model weights, retrieved context, graph memory, prompt examples, skills, tools, human policy, preference data, or fine-tuned/adapted route state.

The gate rejects promotion unless the release record binds:

- knowledge subject, freshness requirement, source-rights status, citation requirement, and volatility;
- chosen memory location: weights, retrieval/index, graph memory, prompt examples, skill memory, tool/policy surface, human policy, or hybrid;
- generalization requirement: reversal, deduction, composition, extrapolation, source recall, style transfer, workflow recovery, or stable format behavior;
- context-versus-weight rationale explaining why the chosen memory location fits the required generalization and auditability;
- lighter interventions tried before adaptation: source refresh, retrieval/reranking, context assembly, prompt/tool/schema repair, eval correction, or human-policy change;
- latent generalization evals that go beyond seen examples and include counterexamples, reversals, compositions, and hard source-recall slices where relevant;
- retrieval-as-memory requirement for claims that must remain updateable, inspectable, rights-aware, and citeable;
- adaptation proposal, capacity estimate, serving impact, regression checks for grounding/source diversity/safety/style/latency/cost, fallback, rollback, and human approval.
