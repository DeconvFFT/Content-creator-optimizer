---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Inference Engineering"
authors: "Philip Kiely"
chapter: "1"
chapter_title: "Prerequisites"
source_path: "/Users/saumyamehta/DS interview prep/books/Inference Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 1 - Prerequisites

## Reading Status

Direct source reading pass completed for chapter 1. Promoted to `canon_ready` after cross-check against Stanford CS336 and official serving/runtime docs. This note is original synthesis only and does not include raw book text or long excerpts.

## Core Idea

Inference optimization is downstream of product constraints. The chapter argues that "best" cannot be defined globally: a system can optimize for latency, throughput, cost, reliability, quality, privacy, or operational flexibility, but real products choose tradeoffs based on model, interface, traffic, economics, and user expectations.

For Agent Studio, the implication is that every agent profile needs an inference contract before model-serving choices are made. Without an explicit latency budget, quality target, traffic pattern, and cost envelope, optimization work is mostly guesswork.

## Product Constraints Before Infrastructure

The chapter identifies several prerequisites for useful inference decisions:

- Model requirements: which model or model family must be served.
- Application interface: how inputs arrive and how outputs must be shaped.
- Latency budget: how quickly the product needs to respond end to end.
- Unit economics: acceptable cost per request, user, tenant, or month.
- Usage pattern: concurrency, traffic spikes, business-hours load, background jobs, and tenant distribution.

Agent Studio should capture these in the agent card and run profile:

- `model_requirement`: frontier API, open model, fine-tuned model, multimodal model, embedding model, or local/specialized model.
- `interface_type`: chat, tool call, background synthesis, voice, retrieval job, eval job, or batch processing.
- `latency_slo`: P50/P90/P95/P99 expectations and hard timeout.
- `cost_budget`: cost per run and monthly tenant budget.
- `traffic_shape`: interactive, bursty, scheduled batch, streaming, or long-running autonomous work.

## Shared Versus Dedicated Inference

The chapter separates shared inference from dedicated deployments:

- Shared inference fits early product work because it has low operational overhead, usage-based spend, and quick integration.
- Dedicated deployments become attractive when usage volume, custom models, latency/uptime requirements, or multi-step orchestration make shared APIs too expensive or too limiting.

This is not identical to open versus closed models. Open models can be served through shared endpoints, and closed providers can offer dedicated arrangements. The practical question is control: who controls latency, rate limits, uptime, model version, cost shape, and deployment topology.

Agent Studio design implication:

- Default to provider APIs for exploration and low-volume workflows.
- Use dedicated serving only when the agent has stable volume, special model requirements, strict latency/availability needs, compliance constraints, or enough orchestration overhead that colocated model serving matters.
- Track the business trigger for moving an agent from shared to dedicated inference. The move should not be aesthetic; it should be justified by observed cost, latency, reliability, customization, or compliance data.

## Application Categories And Inference Shape

Different AI-native applications impose different inference constraints:

- Agents: one user action can trigger many model calls, so orchestration overhead, tool latency, retries, and aggregate cost matter.
- Chat: user perception depends heavily on time to first token and streamed response smoothness.
- Voice: natural interaction requires tight end-to-end latency, not just fast model time.
- Media generation: quality/speed tradeoffs dominate; users may tolerate slower results for better artifacts.
- Search and document workflows: online query latency and offline corpus preparation are separate workloads.
- Recommendations and moderation: high request volume rewards throughput, predictability, and unit-cost discipline.
- Code completion: completion chunks must arrive at typing speed.

Agent Studio should not use one serving profile for every agent. A background source-ingestion scout, an interactive design assistant, a realtime voice agent, and a bulk eval runner should have different model routing, batching, timeout, streaming, and observability settings.

## Online Versus Offline Workloads

The chapter frames latency versus throughput as a core tradeoff:

- Online workloads optimize user-perceived latency because a user is waiting.
- Offline workloads optimize throughput because aggregate processing capacity matters more than one request feeling fast.
- The same model can have separate deployments for online and offline use when both workloads have meaningful volume.

Agent Studio implication:

- Split interactive agent serving from ingestion, embedding, eval, and backfill serving.
- Do not let batch ingestion jobs consume capacity needed by interactive agents unless the scheduler enforces priority and budgets.
- Maintain separate SLOs for interactive runs, background runs, and bulk corpus processing.

## Consumer, B2B, And Compliance Constraints

Consumer applications tend to be cost-sensitive and traffic-spiky. B2B systems tend to require stronger uptime, lower variance, and predictable performance, especially when embedded in revenue or operations workflows. Regulated domains add data sovereignty, privacy, and compliance constraints.

Agent Studio should treat tenant and deployment context as part of inference planning:

- Consumer-style public agents need marginal-cost controls and elasticity.
- Enterprise agents need predictable P90/P99 latency, availability, auditability, tenant isolation, and incident response.
- Regulated agents need explicit region, provider, data-retention, and privacy policies before model calls are allowed.

## Model Selection Is The Biggest Performance Lever

The chapter makes a practical point: model choice usually matters more than runtime tuning. Smaller models are faster and cheaper when they meet quality requirements. Larger frontier models remain necessary for some tasks, but they should not be the default for all traffic after the workload is understood.

Agent Studio implication:

- Use powerful models for discovery, hard tasks, and evaluator roles.
- Route narrow, stable, high-volume tasks to smaller models only after task-specific evals prove they are good enough.
- Prefer popular model architectures for dedicated serving because tooling support, inference-engine compatibility, and optimization maturity affect real production performance.
- Record why a model was selected: quality threshold, latency target, cost target, tooling support, modality need, or compliance constraint.

## Evals Before Optimization

High-confidence evaluation is a prerequisite for inference optimization because optimization can reduce model quality. Public benchmarks help shortlist models, but application-specific evals are necessary for final decisions.

Agent Studio implication:

- No model should be optimized, quantized, distilled, fine-tuned, or moved to dedicated serving without a task-specific baseline.
- Every optimization change should run against the same eval set that justified the current model.
- Public benchmarks can inform candidates, but Agent Studio should rely on product-specific evals for routing and deployment decisions.

## Fine-Tuning And Distillation

Fine-tuning can make a smaller model good enough for a narrow domain, which simplifies latency and cost targets. Distillation can transfer some behavior from a larger teacher to a smaller student, but it can also transfer teacher weaknesses and is less common in routine product work than fine-tuning.

Agent Studio implication:

- Fine-tuning is justified when the task is constrained, the eval suite is strong, and high-quality domain data exists.
- Distillation is worth considering when a large model's behavior is valuable but too expensive or slow, and when a smaller model architecture has strong serving support.
- Both require a quality baseline, regression tests, and post-change inference benchmarks.

## Latency And Throughput Metrics

The chapter distinguishes user-perceived latency from system throughput:

- TTFT: time before a streamed LLM response begins.
- Perceived TPS: token speed visible to one user after generation starts.
- Total TPS: aggregate service throughput.
- ITL: time between output tokens.
- Total response time: better metric when intermediate tokens are not useful, such as agent tool calls.

Agent Studio implication:

- Chat and cockpit interactions should track TTFT and perceived TPS.
- Tool calls and background jobs should track total response time.
- Batch ingestion and eval jobs should track total throughput and cost per item.
- Streaming quality should include gaps and stalls, not only average token rate.

## Percentiles And End-To-End Measurement

Mean latency hides user pain because inference latency has a long tail. P90, P95, and P99 matter because outliers damage trust. The chapter also distinguishes on-GPU inference time from end-to-end latency, which includes queueing, network, orchestration, retrieval, tools, and client overhead.

Agent Studio implication:

- Store P50/P90/P95/P99 metrics per model, provider, agent, route, tenant, and workload class.
- Separate `model_time`, `queue_time`, `retrieval_time`, `tool_time`, `orchestration_time`, `network_time`, and `client_observed_time`.
- When model time is fast but end-to-end latency is slow, optimize infrastructure, queueing, routing, retrieval, tools, or client code before touching the model.

## Failure Modes

- Optimizing a deployment before product requirements are known.
- Treating shared versus dedicated inference as a status choice instead of a business and control tradeoff.
- Using one deployment profile for both interactive and offline workloads.
- Measuring average latency and missing P95/P99 failures.
- Optimizing on-GPU time while the real bottleneck is queueing, orchestration, retrieval, networking, or client code.
- Switching to a smaller model without task-specific evals.
- Choosing a niche architecture with poor inference-engine support.
- Ignoring compliance constraints until after a deployment is designed.

## Agent Studio Design Decisions

- Add an `inference_contract` section to every agent card.
- Split interactive, background, eval, and ingestion workloads into separate serving profiles.
- Require model-selection rationale and task-specific eval baseline before production routing changes.
- Track both model-only and end-to-end metrics.
- Use latency percentiles rather than averages for SLOs.
- Treat dedicated serving as a measured transition triggered by scale, specialization, orchestration, compliance, or reliability needs.
- Record optimization attempts as experiment artifacts linked to eval results, cost metrics, and latency percentiles.

## Follow-Ups

- Define Agent Studio's first `inference_contract` schema.
- Decide which existing agents are interactive versus background workloads.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
