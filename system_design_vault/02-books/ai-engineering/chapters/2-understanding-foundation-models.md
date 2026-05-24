---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "AI Engineering"
authors: "Chip Huyen"
chapter: "2"
chapter_title: "Understanding Foundation Models"
source_path: "/Users/saumyamehta/DS interview prep/books/AI Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 2 - Understanding Foundation Models

## Reading Status

Direct source reading pass completed for chapter 2 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied tables, copied figures, and long excerpts.

## Core Idea

Application teams do not need to train foundation models to build useful products, but they do need enough model literacy to choose, route, constrain, evaluate, and operate them. Chapter 2 frames model behavior as the result of five practical design surfaces: training data, architecture, scale, post-training, and sampling.

For Agent Studio, the main lesson is that a "model" is not a single interchangeable capability. A production route should record what the model is likely good at, what it was not trained or aligned to do, what sampling settings and structured-output controls are used, and what failure modes must be evaluated before promotion.

## Training Data Fit

Training data determines capability boundaries. General-purpose models inherit the distribution, quality problems, language skew, domain gaps, and synthetic-content contamination of their training sources. This matters even when a model scores well on broad benchmarks, because a product workflow may depend on a low-resource language, proprietary domain, uncommon format, or regulated source type that was weakly represented in pre-training.

Design implications:

- Treat language, domain, modality, and format fit as route metadata, not as informal model-selection notes.
- Maintain eval slices for low-resource languages, domain-specific terminology, entity-heavy prompts, and source-sensitive tasks.
- Prefer retrieval, domain-specific context, or smaller specialized models when the required facts or formats are unlikely to be present in a general model's training mix.
- Track data provenance and freshness for source corpora because proprietary, licensed, and user-owned data can be a practical moat.
- Do not assume translation-to-English is a free fix for multilingual workflows; it can lose social, cultural, and factual signals while increasing token cost.

Agent Studio implication: the source ledger should expose coverage gaps by language, domain, modality, and freshness so routing can explain why a model was paired with retrieval, graph context, or human review.

## Architecture Literacy

The transformer remains the dominant architecture because attention lets models condition generation on many previous tokens while parallelizing input processing. The practical runtime distinction is between prefill, where input tokens can be processed in parallel, and decode, where output tokens are generated sequentially. This distinction explains why long prompts, long outputs, and high concurrency stress serving systems differently.

Chapter 2 also highlights that context length is not just a product feature. Key-value cache size, memory pressure, attention cost, and hardware utilization shape whether a long-context route is actually economical. Non-transformer and hybrid architectures such as state-space and Mamba-style systems matter because they target long-sequence efficiency, but changing architecture does not remove the need for evaluation, routing, context design, and monitoring.

Agent Studio implication: capacity estimates should separate input-context cost, output-generation cost, KV-cache pressure, batchability, and maximum useful context. A larger context window should trigger retrieval and summarization evals rather than automatically replacing them.

## Scale Economics

Model scale is not only parameter count. Useful scale judgment needs at least three numbers:

- parameters as a rough proxy for learning capacity and memory footprint;
- training tokens as a proxy for what the model could learn from;
- training compute as a proxy for cost and optimization difficulty.

Sparse models and mixture-of-experts complicate naive parameter-count comparisons because total parameters can differ from active parameters per token. A smaller newer model can also outperform an older larger model because data quality, training recipe, post-training, and inference optimization change quickly.

The scaling-law discussion is useful for product architecture even if Agent Studio is not training frontier models. It reinforces that better model quality is expensive, marginal quality gains can cost disproportionately more, and inference demand should influence model choice. A route that is technically strongest on one eval can still be wrong if latency, cost per useful outcome, or deployment complexity makes it unusable.

Agent Studio implication: model-selection records should compare quality, latency, cost, memory footprint, context needs, tool/retrieval dependence, and expected request volume together. Benchmark score alone is insufficient evidence for a route change.

## Post-Training And Alignment

Pre-training makes a model broadly capable, but not necessarily conversational, safe, obedient, or aligned with product policy. Supervised fine-tuning teaches response behavior through demonstrations. Preference fine-tuning teaches ranking or policy preferences through comparison-style signals, reward models, RLHF, DPO, or related approaches.

This chapter is careful about the limits of "human preference." Preference data reflects labeler demographics, task design, policy choices, and disagreement. Alignment can improve helpfulness or acceptability while still creating blind spots, refusals, political/cultural skew, or hallucination side effects.

Agent Studio implication:

- Store policy and preference assumptions alongside model routes.
- Keep refusal, safety, tone, and helpfulness evals separate from factuality and task-completion evals.
- Treat reward-model or judge-model outputs as fallible artifacts with provenance, model version, prompt version, and calibration checks.
- When collecting user feedback, separate "I prefer this" from "this is factually correct" and "this followed policy."

## Sampling And Test-Time Compute

Sampling turns model logits into outputs, which makes behavior probabilistic. Temperature, top-k, top-p, stopping conditions, seeds, and logprobs shape creativity, consistency, cost, and format reliability. Test-time compute improves outcomes by generating multiple candidates and selecting among them, but it increases cost and can expose verifier weaknesses if selection is poorly designed.

Design implications:

- Route registry entries should store sampling parameters, stop conditions, max output limits, and whether outputs are selected from multiple candidates.
- Deterministic-looking settings reduce variation but do not prove full determinism across providers, hardware, model versions, or prompt perturbations.
- Best-of-N, self-consistency, reward-model selection, and verifier-based selection should be reserved for workflows where quality gains justify extra latency and spend.
- If multiple candidates are generated, the datastore should retain candidate metadata, selection reason, scorer version, and rejected-candidate signals where privacy and cost permit.

Agent Studio implication: evals should test both single-run quality and stability under repeated runs or small prompt variations. The cockpit should show when a response came from direct generation versus candidate selection.

## Structured Outputs

Structured output is a production contract, not a cosmetic formatting preference. It matters when the task itself produces machine-readable artifacts, such as SQL, regex, classifications, or API arguments, and when downstream tools need parseable output.

Chapter 2 gives a useful control ladder:

- prompt for the desired shape;
- validate and repair with post-processing;
- spend extra model calls for judge/corrector loops;
- use constrained sampling where supported;
- fine-tune or add task-specific heads when reliability requirements justify deeper adaptation.

Each layer trades reliability against latency, cost, implementation complexity, and portability. JSON mode alone does not guarantee schema correctness, semantic correctness, or non-truncated output.

Agent Studio implication: tool calls and workflow handoffs need explicit schemas, parser/validator versions, repair policy, retry budget, and failure routing. A route should not be considered production-ready just because the model usually emits valid JSON.

## Inconsistency And Hallucination

Probabilistic generation creates two major production risks: inconsistency and hallucination. Inconsistency appears both when identical prompts produce different outputs and when tiny prompt changes produce materially different outputs. Hallucination is harder because it can arise from self-reinforcing generated context, weak source grounding, mismatched supervision, and the model's inability to reliably separate known facts from plausible completions.

Mitigations are layered, not absolute:

- cache stable answers where appropriate;
- lock sampling settings and seeds where available;
- design prompts and memory to reduce unnecessary variance;
- reduce unsupported claims through retrieval and source-required generation;
- ask for concise answers when factual risk rises with output length;
- use verification, citation checks, judge models, and human escalation for high-risk outputs;
- evaluate hallucination separately from helpfulness or style.

Agent Studio implication: grounding and citation validity need their own eval gates. Retrieval traces should distinguish retrieved evidence, accepted evidence, cited evidence, and unsupported claims in the final answer.

## Failure Modes

- Choosing a model because of a broad benchmark score while ignoring domain, language, or format mismatch.
- Treating long context as a substitute for retrieval quality and source selection.
- Comparing dense and sparse models by total parameter count without active-parameter, memory, and serving-cost context.
- Assuming post-training policy reflects universal human preference.
- Letting judge or reward models silently define product policy without audit.
- Using high-temperature or broad sampling in workflows that need repeatability.
- Relying on JSON mode or prompt wording as the only structured-output safeguard.
- Running best-of-N without measuring verifier errors, latency, and cost per accepted answer.
- Measuring final answer quality without separately measuring stability, grounding, and schema validity.
- Assuming hallucination can be eliminated by one technique rather than managed through layered controls.

## Agent Studio Design Implications

- Model registry entries should include architecture family, context limits, supported modalities, known data-fit gaps, post-training/alignment notes, structured-output support, and serving profile.
- Route-change proposals should justify model swaps with eval evidence for domain fit, language fit, structured-output reliability, hallucination rate, latency, cost, and stability.
- Retrieval and graph context should be treated as capability patches for training-data gaps, not just answer-quality enhancements.
- Evaluation datasets should include repeated-run tests, prompt-perturbation tests, multilingual/domain slices, schema-validity tests, and unsupported-claim checks.
- The source ledger should connect model limitations to source strategy: when the model may not know, the route should retrieve, ask a tool, defer, or escalate.
- Capacity estimation should separate prefill cost, decode cost, KV-cache pressure, long-context cost, and candidate-selection overhead.
- Preference feedback should be typed: factual correction, policy concern, usefulness preference, formatting failure, citation failure, or routing failure.
- Tool execution needs schema validation and repair gates before side effects happen.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "How I Learned to Stop Worrying and Love the Transformer" ([YouTube](https://www.youtube.com/watch?v=1GbDTTK3aR4)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
