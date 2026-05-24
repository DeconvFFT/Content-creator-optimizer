---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Inference Engineering"
authors: "Philip Kiely"
chapter: "7"
chapter_title: "Production"
source_path: "/Users/saumyamehta/DS interview prep/books/Inference Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 7 - Production

## Reading Status

Direct source reading pass completed for chapter 7. Promoted to `canon_ready` after cross-check against Stanford CS336 and official serving/runtime docs. This note is original synthesis only and does not include raw book text or long excerpts.

## Core Idea

Fast single-instance inference is not the same as production inference. Production adds containerization, dependency stability, autoscaling, routing, queues, capacity management, reliability, compliance, deployment strategy, cost accounting, observability, and client-protocol design.

For Agent Studio, this means model serving must be treated as infrastructure, not a helper library. The agent runtime should expose the full path from client request to queue to route to model replica to stream/tool result, because production bottlenecks can appear at any layer.

## Containerization

Containers package the inference service, model-serving stack, dependencies, and configuration into repeatable deployment artifacts. Inference containers are especially fragile because they combine CUDA, drivers, deep learning frameworks, inference engines, Python packages, system packages, and model-specific code.

Agent Studio implication:

- Every dedicated model deployment should have an immutable image reference and dependency manifest.
- Use official vLLM/SGLang/TensorRT-LLM/NIM-style base images when they match the target model and GPU, instead of rebuilding the low-level stack casually.
- Keep images minimal because large images slow deployment and cold starts.
- Pin versions exactly for CUDA-related packages, torch, transformers/diffusers, inference engines, and system dependencies.
- Treat day-zero model support as unstable until rebuilt on stable dependency releases.

## NIMs And Opinionated Images

NVIDIA NIMs provide prebuilt containers for common model/GPU/configuration combinations. They are useful as production-ready services, references, or starting points. They trade control for convenience.

Agent Studio implication:

- Use opinionated model containers when speed to reliable deployment matters and the model/GPU pair is supported.
- Build custom containers when Agent Studio needs maximum control over engine config, custom kernels, LoRA handling, routing, observability, or unusual model architecture.

## Autoscaling

Autoscaling must keep enough replicas online to satisfy latency SLAs without paying for idle GPUs. Utilization-based scaling and traffic-based scaling capture different signals:

- Utilization shows what hardware is doing, but can lag traffic and hide shape differences.
- Traffic/request-based scaling can react to demand earlier, but must understand sequence length and cache-hit effects.

Agent Studio implication:

- Autoscaling decisions should use both traffic and utilization.
- Scaling policy should include min replicas, max replicas, autoscaling window, scale-down delay, and concurrency target.
- Per-agent serving profiles should declare whether latency, throughput, or cost dominates.

## Concurrency And Batching

Batch sizing trades latency for throughput. Continuous batching is the production default for modern LLM engines because it can swap requests at token boundaries and avoid static-batch wait times.

Agent Studio implication:

- Store batch-size and concurrency-target decisions with the serving profile.
- Test batch sizes under realistic sequence lengths and traffic shapes.
- Keep concurrency targets aligned with engine batch behavior; if every replica is saturated, scale up; if many replicas are serving partial load, scale down.
- Separate interactive agents from batch ingestion/eval jobs because they need different batching and queueing behavior.

## Cold Starts

Cold start time includes GPU procurement, image loading, model-weight loading, and engine startup/compilation. Slow cold starts force over-provisioning because scale-down becomes risky.

Agent Studio implication:

- Track cold start subcomponents separately.
- Minimize image size and load weights from high-bandwidth, physically close storage.
- Do not bake huge model weights into images by default; for large models, load weights separately from nearby storage.
- Cache built engines when using compilation-heavy stacks, but require exact environment compatibility.
- Quantized weights can reduce load time as well as runtime memory and bandwidth.

## Routing, Load Balancing, And Queues

Routing decides the best destination for a request; load balancing spreads traffic across viable destinations. Inference routing must account for more than replica count:

- sequence length;
- cache locality;
- LoRA adapter locality;
- model availability;
- replica load;
- queue state.

Queues are required when demand exceeds current capacity while autoscaling catches up. Priority queues can protect paid, enterprise, realtime, or human-facing traffic from background jobs.

Agent Studio implication:

- Routing should be cache-aware and adapter-aware, not round-robin only.
- Queue records should include workload class, tenant priority, timeout, estimated token size, route target, and retry/escalation behavior.
- New replicas should be visible to the queue immediately once healthy.

## Scale To Zero

Scale to zero is valuable for dev, bursty testing, scheduled batch systems, and low-frequency workloads where first-request latency is acceptable. It is not a good fit for latency-sensitive applications with unscheduled traffic unless cold starts are very fast.

Agent Studio implication:

- Use scale-to-zero for dev/test agents, scheduled ingestion, and offline eval jobs.
- Keep interactive production agents warm unless traffic is scheduled or the product can tolerate cold-start latency.
- If a supposedly production interactive agent depends on scale-to-zero for cost viability, it may not yet justify dedicated infrastructure.

## Independent Component Scaling

Compound AI systems often use multiple models and stages: VAD, ASR, embedding, retrieval, reranker, LLM, TTS, image model, guardrail, evaluator, etc. Each stage can need different hardware, batch behavior, and scaling policy.

Agent Studio implication:

- Scale pipeline stages independently.
- Keep related pipeline stages in the same cluster when latency matters.
- Surface per-component bottlenecks instead of reporting only end-to-end failure.
- Avoid overprovisioning the entire chain because one component needs a larger GPU.

## Multi-Cloud Capacity Management

Large-scale inference may need multi-region and multi-provider capacity for GPU availability, redundancy, user proximity, and compliance. A real multi-cloud design needs a global control plane and independent workload planes, not a set of manually managed silos.

Agent Studio implication:

- Separate global deployment/control decisions from workload-plane serving.
- Workload planes should keep serving if the control plane has issues.
- Store region/provider/compliance constraints on each tenant and agent.
- Use geo-aware routing when latency and data residency matter.

## GPU Procurement And Reliability

GPU supply is fragmented across hyperscalers, neoclouds, and resellers. Reserved, on-demand, and spot capacity have different cost and reliability profiles. Hardware failure is expected at scale, and GPU failure often means node-level remediation.

Agent Studio implication:

- Production serving plans should include capacity source and failover policy.
- Do not assume GPU nodes are stable just because the model is stable.
- Track node health, cordon suspect nodes, cycle pods proactively, and monitor provider incidents.
- For critical workloads, use active-active or active-passive failover across regions or providers.

## Security And Compliance

Inference security covers user data, model weights, and infrastructure access. The simplest data-retention security improvement is not storing inputs/outputs unless needed. When retention is necessary, it must be explicit and governed.

Agent Studio implication:

- Default to minimum necessary retention for prompts, outputs, traces, and model artifacts.
- Encrypt user data and model weights at rest and in transit.
- Use workload isolation, network controls, access controls, container scanning, and audit logs.
- Make provider/region choices compliance-aware before routing traffic.
- Treat fine-tuned and proprietary model weights as sensitive assets.

## Testing And Deployment

Production inference requires end-to-end testing, not only replica-level benchmarking. Useful methods include manual tests, load tests, and shadow traffic. Testing is expensive, so sampling and focused stress windows matter.

Zero-downtime deployment should avoid doubling GPU fleets unnecessarily. Canary deployments are usually more practical than blue-green for large inference workloads because they ramp traffic gradually without duplicating the entire fleet.

Agent Studio implication:

- Use canary rollouts for model-serving changes.
- Monitor latency, error codes, quality, queue depth, cost, and capacity during rollout.
- Ensure the canary deployment has enough warm replicas before receiving traffic.
- Roll back automatically on threshold breaches.
- Shadow traffic should respect privacy and data-use policy.

## Cost Estimation

Dedicated inference changes cost from simple per-token pricing to infrastructure total cost of ownership. Important variables include batch sizing, traffic utilization, input/output sequence length distributions, idle capacity, GPU source, and engineering time.

Agent Studio implication:

- Compare API and dedicated costs over at least a week of representative traffic.
- Track input and output token distributions separately.
- Include engineering and operational cost in dedicated-serving decisions.
- Report cost by agent, tenant, model, workload class, and route.

## Observability

Inference observability should include:

- request volume;
- input and output sequence sizes;
- response codes;
- TTFT, tokens/sec, end-to-end latency at P50/P90/P99;
- replica count and replicas starting;
- CPU, host memory, GPU, and GPU memory utilization;
- queue depth;
- server logs and audit logs.

These metrics are interdependent. A latency spike could be caused by request volume, long sequence lengths, cache misses, queueing, replica cold starts, hardware issues, or client overhead.

Agent Studio implication:

- Integrate inference telemetry with normal product observability.
- Link inference events to agent run traces.
- Keep audit logs for deployment changes, route changes, model version changes, and engine config changes.

## Client Code And Protocols

End-to-end latency includes client overhead. Session establishment can consume a meaningful fraction of a tight latency budget, so session reuse matters. Protocol choice also matters:

- HTTP streaming works for normal text chat.
- WebSockets fit unstructured bidirectional realtime streams like audio.
- gRPC fits schema-defined service-to-service streaming.
- Asynchronous jobs fit high-throughput, latency-insensitive workloads.

Agent Studio implication:

- Use async inference for batch ingestion, corpus embedding, and long eval jobs.
- Use streaming protocols for realtime voice/video agents.
- Reuse sessions in clients and SDK wrappers.
- Measure client-observed latency separately from server inference time.

## Failure Modes

- A fast model replica still fails production because autoscaling, queueing, or routing is weak.
- Dependency drift breaks previously working inference containers.
- Cold starts make scale-down unsafe and drive idle GPU cost.
- Load balancers ignore sequence length and send huge prompts to already stressed replicas.
- Queueing hides overload until latency SLOs are already missed.
- Scale-to-zero is applied to unscheduled interactive traffic.
- Pipeline stages scale together and waste GPU resources.
- Multi-cloud deployments become silos rather than a coordinated capacity system.
- Blue-green deployment doubles GPU cost unnecessarily.
- Cost estimation ignores engineering time and idle capacity.
- Client/protocol overhead dominates a tight latency budget.

## Agent Studio Design Decisions

- Add a dedicated-serving lifecycle: build image, benchmark, load test, canary, monitor, rollback.
- Store deployment artifacts: image digest, engine version, model version, quantization profile, GPU type, region, and autoscaling config.
- Add workload-class routing: interactive, realtime, background, eval, ingestion, and batch.
- Implement queue priority by tenant/workload class.
- Attach inference telemetry to every agent run trace.
- Require production-readiness checks for dedicated model deployments.
- Keep data-retention and compliance policy tied to the serving route.

## Follow-Ups

- Define Agent Studio model-deployment artifact schema.
- Define default canary gates for dedicated inference changes.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
