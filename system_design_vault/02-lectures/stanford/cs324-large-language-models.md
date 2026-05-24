---
type: lecture-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_id: stanford.cs324.large_language_models
source_title: "Stanford CS324: Understanding and Developing Large Language Models"
source_status: official_public_course_notes
official_sources:
  - https://ai-deeplang.github.io/large-language-models/
  - https://ai-deeplang.github.io/large-language-models/lectures/
  - https://ai-deeplang.github.io/large-language-models/lectures/introduction/
  - https://ai-deeplang.github.io/large-language-models/lectures/data/
  - https://ai-deeplang.github.io/large-language-models/lectures/security/
  - https://ai-deeplang.github.io/large-language-models/lectures/legality/
  - https://ai-deeplang.github.io/large-language-models/lectures/modeling/
  - https://ai-deeplang.github.io/large-language-models/lectures/training/
  - https://ai-deeplang.github.io/large-language-models/lectures/parallelism/
  - https://ai-deeplang.github.io/large-language-models/lectures/selective-architectures/
  - https://ai-deeplang.github.io/large-language-models/lectures/adaptation/
  - https://ai-deeplang.github.io/large-language-models/lectures/environment/
related:
  - "[[../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../03-patterns/security/genai-security-canon]]"
  - "[[../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../04-agent-studio-implications/Capacity Estimation - Adaptation and Serving Decisions]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# CS324 Large Language Models

## Reading Status

Direct-read pass covered Stanford CS324's official course home page, lecture index, and representative public lecture notes for introduction, data, security availability, legality, modeling/tokenization, training, parallelism availability, selective architectures, adaptation, and environmental impact. Current-source check on 2026-05-18 verified the public course page, lecture index, and Canvas-gated recording boundary. The public course page says recordings require Canvas access, so this note uses official public course notes and marks private video access as out of scope unless the user provides access.

This is compact original synthesis for Agent Studio. It stores no raw lecture text, copied slides, full transcripts, or long excerpts.

## Why This Matters

CS324 is useful because it treats LLMs as a full lifecycle object: behavior, data, legal and security constraints, model architecture, training, scaling, adaptation, and environmental cost. That is the right frame for Agent Studio. A production content-studio agent is not just a prompt around an API. It is a route with data provenance, model behavior assumptions, adaptation decisions, rights constraints, deployment surfaces, evals, and lifecycle cost.

## Course Boundary And Source Policy

The course home page states that lectures are based on public lecture notes, while Zoom recordings are available through Stanford Canvas. Agent Studio ingestion should therefore treat the public notes as the canonical open source and avoid private recordings unless the user explicitly provides access.

For video-source planning, this creates a useful rule: if official video is gated, record the gating and use public official notes rather than third-party transcript mirrors.

## LLM Behavior Before Internals

CS324 starts from the outside: inspect what LLMs do before assuming how they work. This matters for Agent Studio because route design should separate observed behavior from mechanism. A model can appear capable on a task due to pretraining distribution, prompt format, retrieval support, benchmark leakage, tool scaffolding, or actual generalization. Those are different explanations and require different evals.

Agent Studio implication: every model route needs both behavior evidence and mechanism assumptions. The eval record should say whether a success was black-box behavior, source-grounded behavior, tool-assisted behavior, or adaptation/training evidence.

## Data Provenance, Representation, And Contamination

The data lecture is directly relevant to source-ledger design. Large language models are trained on broad raw text, often from the web, where population, language, domain, geography, time, and platform representation are uneven. Dataset documentation should track included and excluded data, provenance, social bias, machine/human authorship, demographic coverage, and contamination risks.

For Agent Studio:

- source records must include provenance, rights, authorship class, and intended use;
- evaluation records must track whether eval material could have leaked into training, retrieval indexes, or prompt examples;
- data filters are not neutral and can remove important groups, dialects, or topics;
- OCR and machine-translated sources need quality flags because systematic extraction errors can become model behavior;
- dataset documentation is part of model and route governance, not optional metadata.

## Legal And Rights-Aware AI Systems

The legality lecture reinforces that LLM development and deployment intersect copyright, licensing, privacy, terms of service, downstream harmful use, and high-stakes domain regulation. The practical vault rule is the same rule the user already set: do not ingest shadow-library sources, do not store raw copyrighted book text, and do not replace source material with long summaries.

Agent Studio needs rights checks at multiple lifecycle stages:

- collection and ingestion of sources;
- extraction and embedding;
- adaptation or fine-tuning;
- generation using source-grounded context;
- publication or external sharing.

Facts, ideas, and short original synthesis can be used differently from copied expression, but terms of service and privacy obligations can still constrain use. The datastore should preserve source license, allowed use, blocked use, consent scope, and publication policy separately.

## Tokenization And Context Economics

The modeling notes make tokenization a systems variable. Tokenizers change sequence length, multilingual support, byte/Unicode behavior, context capacity, and effective cost. A different tokenizer can make the same source cheaper, longer, or more fragmented.

Agent Studio implications:

- store tokenizer profile per model/provider;
- measure token inflation on local source types: PDFs, code, transcripts, Markdown, OCR, tables, social posts, and multilingual content;
- treat context-window capacity as tokenizer-dependent, not a universal character count;
- include tokenizer changes in route-change proposals because they can affect retrieval, cost, truncation, and eval comparability.

## Training Objectives And Model Families

The training notes distinguish decoder-only, encoder-only, and encoder-decoder objectives. Agent Studio should keep this distinction alive even when using hosted models:

- decoder-only routes fit generation, dialogue, planning, and continuation;
- encoder-only routes remain useful for classifiers, embeddings, and rerankers;
- encoder-decoder routes can be appropriate for structured transformation, summarization, translation, or constrained transduction.

Do not reduce everything to "an LLM call." The route registry should model objective family, input/output shape, and whether the route is generative, scoring, embedding, retrieval, or transformation oriented.

## Parallelism And Scaling Constraints

The public parallelism page points to whiteboard/slides and supporting discussions rather than full public lecture notes. The durable systems implication is still clear: large-model training and serving are bounded by model size, memory placement, GPU communication, pipeline scheduling, and cluster topology. This aligns with the CS336 and inference notes already in the vault.

Agent Studio should not trigger self-hosting, finetuning, or distillation work without capacity estimates. For each proposal, record memory, communication risk, latency target, fallback route, and whether a hosted API or retrieval/prompt change is simpler.

## Selective Architectures: MoE And Retrieval

The selective-architectures note frames two ways to avoid using all model capacity for every input:

- mixture-of-experts activates a subset of parameters per input;
- retrieval activates a subset of external data per input.

For Agent Studio, this is a useful mental model. Expert routing, retrieval routing, graph traversal, and tool selection are all selective computation. The system should store which experts, documents, graph communities, tools, or model routes were selected, why they were selected, what was rejected, and how much capacity was used.

Retrieval is not only a way to improve factuality; it is a capacity-allocation and provenance mechanism.

## Adaptation Ladder

The adaptation note gives a clean ladder:

- probing/prediction heads inspect or reuse representations with limited trainable parameters;
- full fine-tuning changes all model parameters and usually needs more storage and risk controls;
- instruction tuning and preference-based alignment shift behavior toward helpful, honest, harmless outputs;
- lightweight tuning methods such as prompt tuning, prefix tuning, and adapters trade expressivity against storage and operational cost.

Agent Studio should make adaptation a proposal, not an impulse. Before adapting a model, the route should show a failure slice, simpler interventions tried, expected benefit, data requirements, rights status of training examples, eval gates, rollback path, and serving impact.

## Security, Privacy, And Extraction

The public security page points to slides and highlights training-data extraction as required reading. Combined with the data and legality lectures, the architecture implication is straightforward: memorization, extraction, private-data leakage, and unauthorized source exposure are route-level risks.

Agent Studio should treat uploaded PDFs, private notes, local book material, browser pages, transcripts, and retrieval chunks as untrusted or rights-constrained inputs until source policy says otherwise. Source-grounded generation should store compact references and hashes, not raw source text in ordinary traces.

## Environmental And Cost Accounting

The environmental-impact note frames model training and use as lifecycle-cost questions with uncertain but material emissions, hardware, data-center, and amortization effects. Agent Studio does not need perfect carbon accounting to benefit from the principle: expensive route changes should carry cost and lifecycle awareness.

Practical implications:

- prefer retrieval, prompt, tool, and eval fixes before new training;
- use smaller or specialized models when they satisfy the success contract;
- store cost and latency alongside quality, not after quality;
- include self-hosted hardware and managed-provider calls in capacity estimates;
- track route-level utilization so unused expensive capacity can be retired.

## Failure Modes

- A public course note is treated as video coverage even though recordings are Canvas-gated.
- A route passes an eval because benchmark items were present in training, retrieval, or prompt examples.
- Tokenization changes silently alter truncation, cost, and multilingual coverage.
- Data filters remove sensitive or underrepresented populations and are later mistaken for neutral cleaning.
- A model is fine-tuned when retrieval, prompt design, classifier heads, or adapters would have been safer.
- A generated artifact copies protected expression instead of synthesizing ideas with source attribution.
- A self-hosting proposal ignores memory placement, communication, and utilization.
- Environmental and cost costs are hidden behind quality gains without a product tradeoff decision.

## Agent Studio Design Rules

1. Separate observed model behavior, source/retrieval support, tool scaffolding, and adaptation evidence.
2. Treat source provenance, rights, dataset documentation, and contamination checks as required route evidence.
3. Make tokenizer profiles and token-inflation measurements part of route capacity planning.
4. Keep model objective family visible: decoder-only, encoder-only, encoder-decoder, embedding, reranker, classifier, and retrieval route.
5. Use selective computation deliberately: route to experts, retrieval stores, graph communities, or tools with accepted/rejected evidence.
6. Require an adaptation proposal before finetuning, adapters, prompt tuning, distillation, or self-hosting.
7. Store legal/privacy/ToS constraints separately from technical source quality.
8. Attach cost, latency, utilization, and lifecycle impact to major capacity decisions.

## Datastore Implications

Add or strengthen these records:

- `dataset_documentation_record`: source scope, included/excluded data, authorship class, demographic/language/domain coverage, contamination risks, known filters, and documentation owner.
- `training_contamination_check`: eval/source artifact, possible training/retrieval/prompt overlap, check method, contamination class, and mitigation.
- `rights_policy_record`: source license, terms, consent scope, allowed uses, blocked uses, publication policy, and review status.
- `tokenizer_profile`: tokenizer source, vocabulary/encoding, language coverage, token inflation, byte/Unicode behavior, and compatible routes.
- `model_objective_record`: model family, objective, route role, input/output shape, and task fit.
- `selective_computation_trace`: selected experts/documents/tools/graph communities, rejected candidates, selection policy, capacity used, and quality evidence.
- `adaptation_proposal`: failure slice, adaptation type, simpler interventions tried, data requirements, rights status, eval gates, serving impact, and rollback.
- `capacity_estimate`: model size, memory, communication risk, runtime plan, cost estimate, latency target, utilization expectation, and fallback.
- `lifecycle_cost_record`: training/adaptation/serving energy or cost proxy, provider or hardware assumptions, utilization, amortization caveat, and review cadence.
- `model_adaptation_lifecycle_release_gate`: promotion gate before finetuning, adapters, prompt/prefix tuning, distillation, self-hosting, or other model-capacity changes affect production routes.

## Release Gate Contract

`model_adaptation_lifecycle_release_gate` is required before Agent Studio changes model weights, trains adapters, adds prompt/prefix tuning, distills a route, self-hosts a model, or treats a new model objective family as production behavior.

The gate should reject promotion unless:

- the route has observed behavior evidence and clearly separated mechanism assumptions;
- dataset/source documentation covers provenance, included/excluded data, authorship class, known filters, demographic/language/domain coverage, and contamination risk;
- rights policy records confirm ingestion, embedding, adaptation, generation, and publication uses are allowed for the affected source material;
- training contamination checks cover eval, retrieval, prompt-example, generated-data, and previous route-tuning overlap;
- tokenizer profiles and tokenization evals show token inflation, truncation, multilingual/Unicode behavior, context capacity, and cost impact on the route's source mix;
- model objective family and route role are explicit: generation, scoring, embedding, reranking, classification, structured transformation, or retrieval support;
- selective computation traces show selected and rejected experts, documents, graph communities, tools, or model routes when routing capacity is part of the design;
- simpler interventions were tried or rejected with evidence before adaptation: retrieval, prompt/template repair, tool/schema repair, classifier/reranker support, or test-time compute;
- capacity estimates include memory, communication risk, runtime plan, latency, utilization, cost, and fallback path;
- lifecycle cost records include adaptation/serving cost proxy, hardware or provider assumptions, utilization, amortization caveat, and review cadence;
- rollback can restore the prior model/provider/route, tokenizer, retrieval/source snapshot, eval suite, and serving profile.
