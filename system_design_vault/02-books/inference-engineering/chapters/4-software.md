---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Inference Engineering"
authors: "Philip Kiely"
chapter: "4"
chapter_title: "Software"
source_path: "/Users/saumyamehta/DS interview prep/books/Inference Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 4 - Software

## Reading Status

Direct source reading pass completed for chapter 4 from the local user-provided PDF extraction span. Promoted to `canon_ready` after official/open cross-check against Stanford CS336, NVIDIA Dynamo, TensorRT-LLM, vLLM, and production serving/runtime docs. This note is original synthesis only; it avoids raw text dumps, copied code, copied tables, copied figures, and long excerpts.

## Core Idea

Inference software is a layered stack. Hardware is slow to change, but inference software changes quickly as new models, kernels, engines, formats, and orchestration systems appear. Production teams therefore need both stable abstractions and enough low-level visibility to know what changed when performance or quality shifts.

For Agent Studio, serving software should be a versioned part of the route. A model served through vLLM, SGLang, TensorRT-LLM, TensorRT, ONNX Runtime, direct PyTorch, or a provider API is not the same operational artifact, even if the model weights are nominally identical.

## Software Abstraction Levels

The chapter organizes the stack from low to high abstraction:

- CUDA and kernels provide direct GPU control.
- Deep learning frameworks such as PyTorch describe tensor operations and model execution.
- Model formats such as safetensors and ONNX define how weights or execution graphs are serialized.
- Inference engines provide configurable production serving for common architectures.
- Distributed serving layers such as Dynamo coordinate cache reuse, disaggregation, and multi-node serving at scale.

Agent Studio implication: route records should store all relevant layers, not just model id. A production incident may come from a kernel, compiler, engine version, model format, Docker image, driver, or orchestration policy.

## CUDA, Kernels, And Fusion

CUDA is the foundation of NVIDIA GPU execution. Most teams do not write CUDA kernels, but kernel selection and kernel availability strongly affect inference performance. Common primitives such as matrix multiplication come from mature libraries; specialized inference kernels are needed for attention, sampling, low-precision operations, and architecture-specific model features.

Kernel fusion reduces unnecessary memory reads and writes by combining operations into one pass. This is especially important when memory bandwidth is the bottleneck, as in LLM decode.

Agent Studio implication: the serving profile should record whether a route uses generic kernels, engine-provided kernels, plugin kernels, or custom kernels. Kernel and GPU-generation compatibility should be part of deployment validation because kernels optimized for one architecture may underperform or fail on another.

## PyTorch And Compilation

PyTorch is the dominant framework for defining model computation. It can run inference directly and can compile model code for better performance through kernel selection and fusion. Compilation is useful but does not replace hand-optimized kernels for common LLM serving paths.

Agent Studio implication: direct PyTorch routes should be treated as flexible but higher-maintenance. They are appropriate for custom architectures or early modality work, but they need stronger benchmark and profiling evidence than a mature inference-engine route.

## Model File Formats

Safetensors stores model weights safely and efficiently without executable deserialization. ONNX stores weights with an execution graph and can be useful for portability and runtime execution. In LLM serving, many systems now use safetensors plus an inference engine rather than exporting a full graph.

Agent Studio implication: model artifact records should distinguish weight-only artifacts from executable graph artifacts. The artifact ledger should store format, sharding, checksum, architecture config, tokenizer/config files, and runtime compatibility.

## Inference Engines

The chapter compares vLLM, SGLang, and TensorRT-LLM as the major inference engines.

vLLM is broad, easy to adopt, and has strong model/hardware coverage. It is good for quickly standing up open models and multimodal routes when broad support matters.

SGLang combines a fast backend with a flexible frontend and has strong support for newer open-model architectures, large MoE serving, and image/video generation through diffusion-oriented extensions.

TensorRT-LLM is NVIDIA-focused, harder to tune, and often strongest for maximum performance on well-supported models and recent NVIDIA hardware. It exposes deep optimization controls and integrates naturally with NVIDIA's distributed serving stack.

Agent Studio implication: engine selection should be route-specific:

- use broad engines for rapid model onboarding and heterogeneous hardware;
- use SGLang-style flexibility for custom routing, MoE, and diffusion workloads;
- use TensorRT-LLM-style stacks when the model/hardware pair is well-supported and maximum performance justifies extra engineering.

## Distributed Serving Layer

Dynamo-style orchestration sits above engines and coordinates features such as KV-cache reuse, prefix-aware routing, prefill/decode disaggregation, multi-node serving, and SLA-aware scaling. It is most useful at high traffic, large model size, and complex serving topology.

Agent Studio implication: distributed serving orchestration should not be the default for every route. It should be introduced when traffic, model size, cache locality, or disaggregation value outweighs operational complexity. The datastore should preserve the triggering evidence.

## Benchmarking

Benchmarking is required to know whether optimization worked. Good benchmarks should resemble production traffic: sequence lengths, output lengths, concurrency, jitter, prompt contents, cache hit patterns, sampling settings, and reasoning/tool behavior. Shadow traffic is ideal when available.

Agent Studio implication:

- every optimization route change needs a baseline and an after-measurement;
- benchmark inputs should be linked to route eval slices, not generic toy prompts;
- performance and quality should be measured together because faster serving is not useful if model behavior regresses;
- benchmark configs should be immutable artifacts.

## Profiling

Benchmarking says what happened; profiling explains why. Profilers reveal time, memory, CPU/GPU coordination, kernel behavior, and interconnect bottlenecks. Most product teams will configure and benchmark engines more often than profile kernels, but profiling is essential for custom PyTorch, new modalities, framework work, and cutting-edge optimization.

Agent Studio implication: profiling artifacts should be attached to optimization investigations when benchmark deltas are unexplained. A route-change proposal should distinguish "measured improvement" from "diagnosed bottleneck."

## Datastore Requirements

Serving software records should include:

- `runtime_stack`: CUDA/driver, framework, inference engine, engine version, container image, compiler path, and plugin kernels.
- `model_artifact_format`: safetensors, ONNX, TensorRT engine, PyTorch checkpoint, tokenizer/config files, sharding, and checksums.
- `engine_config`: engine name, version, flags/config file, batching, cache, quantization, speculation, parallelism, disaggregation, and supported modality.
- `distributed_serving_config`: routing policy, KV routing, prefill/decode workers, multi-node strategy, SLA planner, and autoscaling hooks.
- `benchmark_run`: workload source, input/output length distribution, concurrency, jitter, cache behavior, route config, latency percentiles, throughput, goodput, cost, and quality deltas.
- `profile_artifact`: profiler tool, trace path, kernel hot spots, memory hot spots, interconnect bottlenecks, and remediation decision.

## Failure Modes

- Treating model weights as the only artifact when engine, container, driver, and kernel versions changed.
- Using broad inference engines for routes that require maximum performance without measuring the cost.
- Using highly specialized engines before model support and operational needs justify them.
- Assuming reference `transformers` or `diffusers` sample code is production serving code.
- Exporting to ONNX or TensorRT without checking unsupported operations and architecture-specific features.
- Benchmarking with unrealistic sequence lengths, concurrency, cache patterns, or sampling settings.
- Enabling multiple optimizations at once and losing causal understanding.
- Profiling kernels while the real bottleneck is queueing, routing, network, or client code.

## Agent Studio Design Implications

- Add serving software stack versioning to route releases.
- Require route-change proposals for inference engine changes, compiler changes, kernel/plugin changes, and container changes.
- Store benchmark inputs and configs as source-aware artifacts.
- Pair every performance report with quality-regression evidence.
- Use profiling selectively for custom serving, unexplained regressions, and new modalities.
- Keep high-scale orchestration optional until traffic and model characteristics justify it.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
