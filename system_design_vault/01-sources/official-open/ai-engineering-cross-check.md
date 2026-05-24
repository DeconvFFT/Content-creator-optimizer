---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
cross_checks:
  - source_title: "AI Engineering"
    chapters: "1-10"
sources:
  - https://developers.openai.com/api/docs/guides/evaluation-best-practices
  - https://developers.openai.com/api/docs/guides/agent-evals
  - https://developers.openai.com/api/docs/guides/prompt-engineering
  - https://developers.openai.com/api/docs/guides/model-optimization
  - https://developers.openai.com/api/docs/guides/fine-tuning-best-practices
  - https://developers.openai.com/api/docs/guides/supervised-fine-tuning
  - https://developers.openai.com/api/docs/guides/production-best-practices
  - https://developers.openai.com/api/docs/guides/latency-optimization
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview
  - https://platform.claude.com/docs/en/test-and-evaluate/develop-tests
  - https://platform.claude.com/docs/en/build-with-claude/prompt-caching
  - https://docs.cloud.google.com/architecture/deploy-operate-generative-ai-applications
  - https://docs.cloud.google.com/architecture/framework/perspectives/ai-ml/reliability
  - https://cs336.stanford.edu/
  - https://docs.vllm.ai/en/stable/features/quantization/
  - https://docs.vllm.ai/en/stable/features/multimodal_inputs/
  - https://docs.nvidia.com/tensorrt-llm/
---

# AI Engineering - Official Cross-Check

## Scope

This cross-check covers the full local `AI Engineering.pdf` chapter set. The chapter notes were created from direct local source reading. This note promotes them only where the book-level conclusions are reinforced by official provider documentation, official cloud architecture guidance, and Stanford course material. It is original synthesis only and does not store raw book text or long excerpts.

## Cross-Check Result

The official sources support the AI Engineering chapter set as canon-ready for Agent Studio architecture. The key convergence is that production AI systems are not just prompts around a model: they require explicit product objectives, model and route selection, eval datasets, prompt/version management, data governance, adaptation strategy, inference/runtime controls, monitoring, cost and latency budgets, safety controls, and feedback loops.

## Confirmation Matrix

| AI Engineering theme | Official/open-source confirmation | Agent Studio design implication |
|---|---|---|
| Product readiness starts with success criteria | Anthropic eval guidance starts from measurable success criteria; OpenAI eval guidance emphasizes task-specific evaluation before relying on outputs. | Intake records need objective, success metric, target threshold, risk class, and baseline before a workflow becomes production-eligible. |
| Foundation-model routes are not interchangeable | OpenAI model optimization, production, and latency docs distinguish model choice, customization, evaluation, and runtime constraints. | Route records need model/provider version, supported modalities, context policy, sampling settings, adaptation method, latency/cost envelope, and rollback evidence. |
| Evaluation is an architecture surface | OpenAI evals, agent evals, trace grading, and graders support dataset-backed and trace-backed evaluation rather than final-answer checks only. | Store eval datasets, cases, graders, trace graders, run results, and promotion gates as first-class artifacts. |
| Prompt engineering follows evals | Anthropic prompt engineering requires success criteria and empirical testing first; OpenAI prompt guidance and production docs reinforce iteration under tests. | Prompts should be versioned release artifacts with linked eval deltas, examples, schema expectations, and failure slices. |
| Structured behavior needs contracts | OpenAI docs separate structured outputs, function/tool use, graders, and agent workflow evaluation. | Agent Studio should validate schemas, tool arguments, handoff payloads, parser repair, retry budgets, and failure routing. |
| Fine-tuning is not the first response to failure | OpenAI model optimization and fine-tuning guidance place fine-tuning inside an optimization cycle with data quality and eval requirements. | Fine-tune proposals should prove that prompt, retrieval, tool, and eval fixes are insufficient and must include dataset provenance, split integrity, and rollback criteria. |
| Dataset work is governed production work | Google Cloud GenAI operations and reliability guidance treat deployment, monitoring, governance, and data lifecycle as operational concerns. | Dataset snapshots, processing runs, annotation guidelines, synthetic generation runs, and allowed-use policies belong in the same datastore as routes and evals. |
| Inference optimization affects behavior and product fit | OpenAI latency docs, vLLM quantization/multimodal docs, TensorRT-LLM, and Stanford CS336 reinforce latency, batching, cache, precision, hardware, and serving-stack constraints. | Serving profiles need TTFT, TPOT, queue time, cache policy, quantization, hardware/runtime, streaming support, cost, and quality regression gates. |
| Feedback closes the system loop | OpenAI agent eval guidance and cloud operations guidance converge on monitoring, feedback, and continuous improvement. | User corrections should flow into triage, source backlog, eval cases, dataset candidates, prompt/route issues, and release decisions rather than free-form comments only. |

## Canon Decisions

- AI Engineering chapters 1-10 are usable as canon design input for Agent Studio.
- Chapter 1 supports the product-intake and route-change decision model.
- Chapter 2 supports model registry, route metadata, sampling controls, hallucination/grounding evals, and structured-output contracts.
- Chapters 3-4 support eval-first development, task-specific metrics, trace grading, and promotion gates.
- Chapter 5 supports prompt versioning under empirical tests, not prompt folklore.
- Chapter 6 remains canon for RAG, retrieval, tools, agents, and traceable workflows.
- Chapter 7 supports fine-tuning only after dataset, eval, and baseline gates are in place.
- Chapter 8 supports governed dataset engineering, synthetic-data provenance, deduplication, and contamination controls.
- Chapter 9 supports route-level serving profiles, latency/cost decomposition, and runtime regression gates.
- Chapter 10 remains canon for AI engineering architecture, feedback loops, observability, and product operating model.

## Agent Studio Architecture Commitments

- Every workflow has a problem contract, route contract, eval contract, and feedback contract.
- Every model or provider route is versioned with adaptation method, sampling policy, context policy, runtime profile, and rollback evidence.
- Every prompt is released with linked eval deltas and trace evidence.
- Every dataset has source provenance, allowed use, processing lineage, split policy, and contamination checks.
- Every fine-tuning or distillation proposal requires baseline failure evidence and dataset readiness evidence.
- Every inference optimization requires quality, safety, structured-output, and grounding regression checks, not just latency wins.
- Every feedback event should be routable into eval, source, prompt, dataset, or product backlog.

## Remaining Refinement

Future official-source notes should deepen the Stanford CS336 and CS329S lecture coverage around eval design, data filtering, model adaptation, and production operations. That refinement should add detail, not block current canon use of the AI Engineering chapter notes.
