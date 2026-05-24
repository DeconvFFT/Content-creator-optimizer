---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Inference Engineering"
authors: "Philip Kiely"
chapter: "3"
chapter_title: "Hardware"
source_path: "/Users/saumyamehta/DS interview prep/books/Inference Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 3 - Hardware

## Reading Status

Direct source reading pass completed for chapter 3 from the local user-provided PDF extraction span. Promoted to `canon_ready` after official/open cross-check against Stanford CS336, NVIDIA Dynamo, TensorRT-LLM, vLLM, and production serving/runtime docs. This note is original synthesis only; it avoids raw text dumps, copied hardware tables, copied figures, and long excerpts.

## Core Idea

Inference hardware decisions are workload decisions. The right accelerator depends on whether the route is compute-bound, memory-bandwidth-bound, memory-capacity-bound, interconnect-bound, power-constrained, or latency-sensitive at the edge.

For Agent Studio, hardware should not be a hidden deployment detail. The platform should know which routes can run on provider APIs, dedicated cloud GPUs, fractional GPUs, multi-GPU nodes, multi-region capacity pools, or local devices, and should store why that placement is appropriate.

## Accelerator Categories

The chapter centers datacenter GPUs because large-scale generative AI inference usually needs high bandwidth, standardized clusters, and fast interconnects. It distinguishes datacenter GPUs from workstation and personal GPUs, then distinguishes cloud, on-premise, and air-gapped deployment modes.

Agent Studio implication:

- exploration and normal SaaS operation should default to cloud/provider capacity;
- enterprise/private routes may need region, tenant, or air-gapped deployment metadata;
- local inference can be useful for privacy, latency, and cost, but only for small enough workloads and supported devices.

## GPU Architecture Mental Model

GPUs are throughput machines. CPUs excel at complex sequential work; GPUs excel at running the same simple operation across many data elements. That fits AI inference because the hot path is dominated by vector and matrix operations.

The chapter highlights three compute units:

- CUDA cores for scalar operations;
- Tensor cores for vector and matrix operations;
- special-function units for mathematical functions used inside operations such as softmax.

For inference planning, Tensor Core capability is the relevant compute signal, but only when compared at the same precision and sparsity assumptions. Sparse peak numbers are not the default dense inference reality.

Agent Studio implication: serving profiles should store the precision and dense/sparse assumptions used for capacity estimates. A route should not compare accelerators from headline peak numbers without matching precision and workload.

## Compute Versus Memory

VRAM capacity determines whether model weights plus KV cache and runtime headroom fit. VRAM bandwidth determines how quickly data can feed the GPU. LLM decode is often bandwidth-limited at low to medium batch sizes, while LLM prefill and image/video generation are usually compute-limited.

The chapter's practical rule is that model weights should fit with meaningful headroom for KV cache and request variability. Long context, higher batch sizes, video, and multimodal inputs increase the headroom requirement.

Agent Studio implication:

- every self-hosted route needs a memory budget: weights, adapters, KV cache, batch headroom, and runtime overhead;
- every capacity estimate should label the expected bottleneck;
- long-context routes should not be approved from weight-fit alone.

## Hardware Generations

The chapter explains NVIDIA generations as architecture families that add compute, memory bandwidth, precision support, and inference-specific features over time. Hopper is mature and broadly supported; Blackwell adds newer low-precision and memory features; upcoming architectures in the source are positioned around even higher bandwidth and prefill-focused compute.

Agent Studio implication: hardware generation affects software support. The newest accelerator may have better theoretical performance but weaker kernel maturity, availability, or integration. The route record should include not only GPU type but also runtime/framework support maturity and benchmark evidence.

## CPU-GPU Memory Path

GPU inference still depends on host CPU, host memory, disk, networking, and CPU-GPU transfer. High-bandwidth CPU-GPU interconnects matter when serving uses CPU memory for offloaded LoRA weights, cache tiers, or other state that must move quickly to the GPU.

Agent Studio implication: instance records should include CPU, host memory, storage, network, CPU-GPU interconnect, and GPU-GPU interconnect. "GPU type" alone is too weak to explain tail latency or OOM failures.

## Instances And Interconnect

Cloud allocation happens at the instance level. An instance includes GPUs, CPUs, host memory, storage, networking, and interconnect. Multi-GPU serving depends on the bandwidth and topology between GPUs and, for multi-node serving, between nodes.

The chapter emphasizes that intra-node GPU interconnect is much faster than node-to-node networking. Tensor parallelism, pipeline parallelism, expert parallelism, and disaggregation all depend on this topology.

Agent Studio implication:

- model placement should know whether a route fits on one GPU, one multi-GPU node, or multiple nodes;
- multi-node inference should require explicit evidence because slower interconnects can dominate latency;
- placement records should store topology, not just GPU count.

## Multi-Instance GPUs

MIG-style partitioning lets large GPUs serve smaller models more efficiently by slicing compute and memory into fractional instances. This is useful when a model is too small to utilize a full high-end GPU but still benefits from modern architecture and isolation.

Agent Studio implication: small embedding, classification, TTS, moderation, or narrow agent routes may belong on fractional GPU profiles rather than full accelerators. The scheduler should support fractional capacity records and avoid wasting full GPUs on tiny steady workloads.

## Non-NVIDIA Accelerators

The chapter surveys alternative datacenter accelerators and groups their potential advantages around memory bandwidth, power efficiency, and platform integration. The main challenge for alternatives is not just chip performance; it is rebuilding the software ecosystem that NVIDIA has through CUDA, kernels, inference engines, and broad availability.

Agent Studio implication: non-NVIDIA providers should be evaluated as serving stacks, not just chips. Records should include supported models, runtime maturity, framework compatibility, kernel support, operational tooling, regional availability, and portability risk.

## Local Inference

Local inference removes network latency, improves privacy, reduces developer-side serving cost, and keeps the product usable during connectivity issues. Its weaknesses are limited hardware, thermal constraints, fragmented support, battery life, and device variability.

Desktop inference can run larger open models on enthusiast or professional hardware, especially with aggressive quantization or unified memory. Mobile inference is better suited to small models, transcription, speech synthesis, translation, and other constrained tasks.

Agent Studio implication:

- local routes should have a capability handshake before execution;
- the platform should know which tasks can fall back to local models and which require cloud;
- user device class, battery state, privacy mode, and offline state should influence routing;
- local outputs still need eval, guardrail, and provenance records.

## Datastore Requirements

Hardware-aware serving records should include:

- `accelerator_profile`: vendor, architecture generation, SKU, memory, bandwidth, precision support, dense/sparse assumptions, and power class.
- `instance_profile`: cloud/provider, region, GPU count, CPU, host memory, storage, network, CPU-GPU interconnect, GPU-GPU interconnect, and node-to-node interconnect.
- `placement_constraint`: one GPU, fractional GPU, one node, multi-node, local desktop, mobile, air-gapped, or provider-managed.
- `memory_budget`: weights, adapters, KV cache, batch headroom, context headroom, media latent-state headroom, and expected OOM risk.
- `bottleneck_claim`: compute-bound, bandwidth-bound, capacity-bound, interconnect-bound, queue-bound, or unknown.
- `local_capability_profile`: device class, supported runtimes, max model size, thermal/battery constraints, privacy mode, and fallback route.
- `hardware_benchmark`: workload sample, model, precision, engine, batch/concurrency, TTFT, TPOT, throughput, goodput, cost, and quality regression link.

## Failure Modes

- Selecting hardware from peak FLOPS while the workload is memory-bandwidth-bound.
- Loading weights with no room left for KV cache, adapters, or long-context batches.
- Treating all GPUs with the same SKU as equivalent across providers and instance types.
- Ignoring interconnect and then blaming the model when multi-GPU serving is slow.
- Using full high-end GPUs for tiny steady workloads that fit fractional instances.
- Moving to non-NVIDIA accelerators without checking software/runtime maturity.
- Assuming local inference works for median users because it works on an enthusiast machine.
- Ignoring thermal and battery costs for mobile routes.

## Agent Studio Design Implications

- Add hardware and instance profiles to the route registry for all self-hosted and local routes.
- Capacity estimation should begin with bottleneck classification and memory budget, not only request count.
- Keep provider-managed routes separate from hardware-owned routes; they need different observability and failure evidence.
- Support fractional GPU serving for small steady models.
- Treat local inference as a privacy/latency/cost route with capability checks, not a universal replacement for cloud serving.
- Require hardware benchmark evidence before changing accelerator family, precision, topology, or provider.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
