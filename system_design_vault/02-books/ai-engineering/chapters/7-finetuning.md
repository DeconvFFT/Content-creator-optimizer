---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "AI Engineering"
authors: "Chip Huyen"
chapter: "7"
chapter_title: "Finetuning"
source_path: "/Users/saumyamehta/DS interview prep/books/AI Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 7 - Finetuning

## Reading Status

Direct source reading pass completed for chapter 7 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied formulas, copied tables, copied figures, and long excerpts.

## Core Idea

Finetuning changes model weights; prompt engineering, RAG, and agents change model inputs and tool access. Because weight-changing adaptation raises data, training, memory, serving, evaluation, and maintenance costs, it should be selected only after the failure mode justifies it. The chapter's practical rule is simple: use RAG for missing or changing facts, and use finetuning for behavior, form, style, specialized syntax, and instruction-following gaps.

For Agent Studio, finetuning should be a governed route type, not a casual optimization. A fine-tuned model route needs its own dataset lineage, training config, adapter/base-model relationship, evaluation proof, serving profile, rollback plan, and refresh policy.

## When To Finetune

Finetuning is useful when a base model has relevant latent capability but does not express it reliably for the task. It can improve domain behavior, structured-output reliability, safety behavior, style, and task-specific instruction following. It is especially plausible when the model repeatedly produces factually correct but operationally unusable outputs, such as wrong format, wrong level of detail, wrong tone, or weak adherence to a specialized syntax.

Reasons to avoid or delay finetuning:

- prompt and context experiments have not been systematic;
- failure is caused by missing, stale, or private information;
- eval criteria and datasets are weak;
- high-quality training data is unavailable;
- the model must handle many diverse tasks and could regress on some of them;
- serving a custom model would add operational burden;
- new base models may improve faster than the fine-tuned model can be maintained.

Agent Studio implication: route-change proposals should require a failure-mode diagnosis before allowing finetuning. If the failure is information-based, try retrieval and source quality first. If the failure is behavior-based, consider fine-tuning only after prompt and structured-output controls are measured.

## RAG Versus Finetuning

RAG supplies information at inference time. Finetuning alters behavior learned into weights. The chapter frames this as facts versus form.

Use RAG when:

- the answer depends on private, fresh, or long-tail knowledge;
- source citation and auditability matter;
- source data changes often;
- the route should explain where the answer came from;
- the same base behavior can work with better evidence.

Use finetuning when:

- the model sees the right information but answers in the wrong format or style;
- the task uses a domain-specific language, schema, or syntax;
- the model repeatedly ignores stable instructions;
- a smaller model must imitate a stronger model for cost or latency reasons;
- many examples would otherwise need to be included in every prompt.

Agent Studio implication: capacity estimation should compare prompt, retrieval, reranking, graph traversal, constrained decoding, fine-tuning, distillation, and serving changes as separate levers. Finetuning should not be the default answer to retrieval or data-quality failures.

## Memory And Serving Constraints

Finetuning is memory-intensive because training requires more than loading weights. It also needs activations, gradients, and optimizer state. The number of trainable parameters and numerical precision directly affect feasibility. Inference can often run in lower precision, but training is more sensitive and may require mixed precision, quantization-aware choices, or memory-saving techniques.

Agent Studio implication:

- Fine-tuned routes need a serving profile: base model size, precision, adapter type, max context, expected batch size, memory footprint, latency, and cost.
- Training proposals need a training profile: trainable parameter count, optimizer, precision, batch size, gradient accumulation, epochs, checkpointing, and hardware target.
- Long-context fine-tuning should not be assumed to improve all context use; it can create short-context regressions and needs separate evals.

## PEFT, LoRA, And Adapter Serving

Parameter-efficient finetuning reduces memory pressure by training only a small set of parameters. LoRA is especially useful because adapters are modular: a base model can be shared while multiple adapters specialize behavior for tasks, customers, or routes.

Design consequences:

- Adapter-based routes should store base model id and adapter id separately.
- Multi-adapter serving can reduce storage and switching cost, but may add runtime overhead depending on whether adapters are merged or applied dynamically.
- LoRA rank, target modules, alpha/scaling, precision, and quantization settings are part of the route's reproducibility contract.
- QLoRA-style quantized approaches make fine-tuning more accessible but add quantization/dequantization tradeoffs that should be measured.

Agent Studio implication: the model registry should support base-model records, adapter records, merged-model records, and route bindings. A route should say whether it serves a merged full model or dynamically loads adapters.

## Model Merging

Model merging combines multiple models or adapters into one artifact. It can support multi-task adaptation, on-device deployment, federated learning, model upscaling, or combining specialized skills. The chapter covers summing, spherical interpolation, task-vector pruning, layer stacking, and concatenation. These methods are promising but more experimental than ordinary route changes.

Agent Studio implication:

- Merged models need stronger provenance and eval evidence because behavior can change in non-obvious ways.
- A merged route should store constituent models, merge method, weights/factors, pruning method, layer map, post-merge training, and task coverage.
- Model merging should be evaluated on every source task and on interference/regression slices.
- Adapter merging may be attractive for multi-agent systems, but serving separate adapters can be safer when tasks need independent rollback.

## Finetuning Development Path

The chapter recommends treating fine-tuning as an experiment sequence, not one big run.

Practical path:

- prove feasibility with the strongest affordable model;
- test fine-tuning code with a cheap model;
- test data quality with a middle model;
- use loss curves and validation performance to detect data or hyperparameter problems;
- map price/performance across candidate models;
- decide whether to serve via API, managed fine-tuning, self-hosting, adapters, or merged artifacts.

Agent Studio implication: fine-tuning runs should be tracked like ingestion and eval runs. Failed training runs are useful evidence when they explain data quality, loss behavior, overfitting, or serving infeasibility.

## Datastore Requirements

Fine-tuned routes need these records:

- `training_dataset`: source records, rights, filters, annotation guideline, synthetic-data flags, and split definitions.
- `finetune_run`: base model, method, framework/API, trainable parameter count, precision, optimizer, learning rate, batch size, epochs, prompt loss weight, hardware, checkpoints, and run status.
- `adapter_artifact`: base model dependency, LoRA/PEFT method, target modules, rank, scaling, precision, quantization, checksum, and storage path.
- `merged_model_artifact`: constituent models/adapters, merge method, weights, pruning/stacking details, post-merge training, and compatibility.
- `adaptation_eval`: before/after eval results, slice regressions, task improvements, cost/latency change, and safety changes.
- `serving_binding`: route id, base model id, adapter id or merged model id, load strategy, memory estimate, latency envelope, and rollback target.

## Failure Modes

- Fine-tuning because prompting was tried casually rather than systematically.
- Fine-tuning for missing facts that should be retrieved.
- Improving one task while regressing other supported tasks.
- Training on low-quality or misaligned examples and worsening hallucination or safety.
- Selecting a base model without checking license, serving support, and data-lineage constraints.
- Treating LoRA adapters as interchangeable without recording base-model compatibility.
- Serving many full fine-tuned models when adapter serving would be cheaper.
- Merging models without evaluating task interference.
- Ignoring training memory, activation memory, optimizer state, and precision constraints.
- Failing to budget ongoing maintenance as base models, data, and eval requirements change.

## Agent Studio Design Implications

- The adaptation decision ladder should be: prompt, examples, retrieval, reranking/graph/context engineering, structured-output controls, fine-tuning, distillation, model merging, and custom serving.
- Fine-tuning should require an eval contract and data-readiness check before training begins.
- The route registry should distinguish managed API fine-tunes, self-hosted full fine-tunes, adapters, quantized adapters, merged adapters, and merged full models.
- The datastore should retain before/after evals and slice regressions, not only the final fine-tuned artifact.
- Multi-agent specialization should usually start with route/tool/prompt separation; adapter specialization becomes attractive only when repeated behavior failures justify weight-level adaptation.
- Fine-tuned models should have explicit refresh triggers: new base model, new source data, recurring failure slice, cost change, safety incident, or serving bottleneck.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
