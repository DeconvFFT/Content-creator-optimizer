---
type: question-backlog
project: agent-studio-system-design
status: backlog_ready
updated: 2026-05-18
source:
  source_id: local_books.llm_questions
  title: LLM Questions
  local_path: "/Users/saumyamehta/DS interview prep/books/LLM Questions.pdf"
  source_class: local_book_pdf
  rights_status: user_private_notes
  provenance_status: user_provided_local
related:
  - "[[../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../03-patterns/evaluation/prompt-workflow-eval-datasets]]"
  - "[[../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# LLM Questions Eval Backlog

## Reading Status

Direct local-PDF read of the 50-question interview handout. This note uses the file only as a coverage checklist for Agent Studio eval and review backlog design. It does not treat the handout's answers as factual canon, does not copy the question list, and does not store raw text or long excerpts.

## Safe Use Boundary

Use this source to ask: "Which LLM concepts should Agent Studio be able to explain, evaluate, or route around?"

Do not use it to answer technical questions without cross-checking against canon sources such as AI Engineering, Build a Large Language Model From Scratch, CS224N, CS336, Inference Engineering, LLM Engineers Handbook, Prompt Engineering for LLMs, and official provider docs.

## Coverage Clusters

The handout maps into these backlog clusters:

| Cluster | Concepts to test against canon |
|---|---|
| Tokenization and context | tokenizer choice, subword/OOV behavior, context-window limits, positional encoding, token-cost inflation |
| Transformer mechanics | attention, multi-head attention, scaled dot product, encoder/decoder roles, residual/normalization stability |
| Generation controls | greedy decoding, beam search, top-k/top-p sampling, temperature, output diversity/coherence tradeoffs |
| Training objectives | autoregressive modeling, masked modeling, cross-entropy, KL divergence, SFT/fine-tuning boundaries |
| Adaptation and compression | LoRA, QLoRA, PEFT, catastrophic forgetting, distillation, hyperparameter decisions |
| RAG and structured knowledge | retrieval, ranking, generation, knowledge graphs, grounding and hallucination reduction |
| Multimodal and foundation models | language, vision, generative, and multimodal model families; modality-specific evidence contracts |
| Deployment risk | resource intensity, privacy, bias, interpretability, incorrect output handling, production monitoring |

## Agent Studio Backlog Items

| Backlog item | Route or eval implication |
|---|---|
| `llm_concept_explainer_eval` | Route should explain core concepts from canon notes with citations and without overclaiming. |
| `tokenization_cost_probe` | Eval should compare token counts and truncation risk across representative source snippets, prompts, and languages. |
| `context_window_boundary_case` | Eval should test long-context summarization, source omission, and stale memory behavior near context limits. |
| `decoding_policy_comparison` | Serving profile should record when temperature, top-p, beam search, or deterministic decoding is allowed. |
| `adaptation_method_triage` | Capacity decision should choose prompt/RAG/PEFT/SFT/distillation based on measured failure, data, and serving constraints. |
| `rag_kg_grounding_probe` | Retrieval eval should test whether structured entity relations improve source support rather than adding unsupported graph claims. |
| `multimodal_route_readiness_probe` | Visual/multimodal routes should prove evidence-region and modality-bridge coverage before claiming image/video understanding. |
| `deployment_risk_review_case` | Release gates should check privacy, bias, interpretability, compute cost, and fallback behavior before product use. |

## Datastore Implications

Add or preserve:

| Object | Purpose |
|---|---|
| `question_backlog_item` | Non-canon question or concept coverage item with source, cluster, priority, and target eval surface. |
| `concept_coverage_record` | Links a concept to canon notes, eval cases, and unresolved gaps. |
| `learning_eval_case` | Tests whether an explainer route can answer a concept question from approved sources. |
| `answer_canon_check` | Records whether a generated answer is supported by canon notes rather than a private checklist. |

## Promotion Rule

A backlog item can become a canon eval only after:

- the concept is cross-checked against at least one canon source;
- expected behavior is written as an eval case rather than a copied interview answer;
- the eval requires source attribution or an explicit "not enough evidence" response;
- the question is tagged by route surface, failure mode, and product risk.

## Agent Studio Design Implications

- The UI should separate "source canon" from "coverage questions" so private notes do not become factual evidence.
- Question backlogs are useful for finding weak coverage in eval suites, onboarding docs, and route explainability.
- Concept explainers should cite the vault's canon notes, not this handout.
- Interview-style questions can seed regression tests for hallucinated simplifications, outdated model comparisons, and unsupported deployment advice.
