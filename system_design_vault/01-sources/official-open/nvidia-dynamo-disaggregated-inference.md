---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_public
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://docs.nvidia.com/dynamo/latest/getting-started/introduction
  - https://docs.dynamo.nvidia.com/dynamo/design-docs/disaggregated-serving
  - https://docs.nvidia.com/dynamo/latest/components/router
  - https://docs.nvidia.com/dynamo/latest/components/planner
  - https://docs.nvidia.com/dynamo/backends/tensor-rt-llm
related:
  - "[[../../03-patterns/inference/realtime-and-inference-patterns]]"
  - "[[../../04-agent-studio-implications/Capacity Estimation - Adaptation and Serving Decisions]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
  - "[[baseten-inference-engineering]]"
  - "[[inference-engineering-cross-check]]"
---

# NVIDIA Dynamo - Disaggregated Inference And KV-Aware Serving

## Reading Scope

Direct-read pass over official NVIDIA Dynamo documentation for the current introduction, disaggregated serving design, KV router, Planner autoscaling, and TensorRT-LLM backend support. Current-source check on 2026-05-18 confirmed Dynamo 1.1.1 still frames itself as a distributed layer above inference engines, with disaggregated serving, KV cache-aware routing, KV cache offloading, Planner SLA/load scaling, topology-aware deployment, fault tolerance, observability, and TensorRT-LLM support. This note stores compact original synthesis only. It does not copy diagrams, command recipes, or long documentation excerpts.

## Core Pattern

Dynamo treats LLM serving as a distributed systems problem around inference engines. The engine still owns model execution, but the serving layer owns scheduling, routing, KV-cache placement, data transfer, autoscaling, topology, fault tolerance, and observability.

The main design lesson for Agent Studio: serving optimization should not be represented as a single `runtime = vLLM/TensorRT/Ray` field. Production inference needs a route-level serving topology:

- whether prefill and decode are aggregated or disaggregated;
- whether requests are routed by KV overlap, queue pressure, device capacity, or simple load balance;
- where KV cache lives across GPU, CPU, SSD, or remote tiers;
- how prefill/decode workers scale against TTFT and inter-token latency targets;
- how topology and gang scheduling constrain placement;
- how in-flight work is migrated, canceled, rejected, or retried.

## Disaggregated Prefill And Decode

Long prompts and generation have different bottlenecks. Prefill is prompt/context heavy; decode is ongoing token-generation heavy and memory-sensitive. Disaggregating them lets a serving stack allocate different hardware, tensor parallelism, replica counts, and queues to each phase.

For Agent Studio, this matters most for:

- book-heavy source reading and long-context synthesis;
- retrieval-augmented drafts with large context packs;
- multi-turn agent sessions with repeated source context;
- eval and critique jobs that share prefixes or source snapshots;
- realtime-adjacent routes where a long prefill must not block interactive decode.

The route contract should separately measure prefill, decode, queue, transfer, cold-start, and end-to-end latency. A single latency average can hide the exact bottleneck that disaggregation is meant to fix.

## KV Cache As A Routable Resource

Dynamo's KV-aware routing reframes cache as route state, not an invisible runtime optimization. A router can select workers using overlap between the incoming request and existing cache, active block pressure, load, and queue policy. That can reduce redundant prefill work and improve TTFT for repeated or shared-context workloads.

Agent Studio should treat KV/prefix cache decisions as first-class release metadata:

- cache key or overlap policy;
- accepted context reuse boundaries;
- source snapshot or conversation state tied to cache;
- cache hit/miss and eviction signals;
- fallback behavior when KV events are unavailable;
- fairness policy so cache-friendly work does not starve urgent non-cacheable work.

Cache-aware routing is especially relevant for Obsidian/book ingestion, RAG over stable source packs, repeated eval cases, and agent review loops over the same artifact bundle.

Current Dynamo router docs add production constraints that Agent Studio should preserve: KV routing depends on dynamic endpoint discovery and tokenized model inputs; workers report cache events, but the router can fall back to approximate routing when events are unavailable; queue policy can optimize tail TTFT, average TTFT, or comparison/debug ordering; and priority hints can influence backpressure handling. These are release parameters, not hidden runtime flags.

## Autoscaling For LLM Workloads

Traditional autoscaling based only on request count or CPU does not match LLM inference because request cost depends heavily on input length, output length, cache state, batching, and prefill/decode split.

Agent Studio needs two capacity views:

- planned capacity from predeployment profiling or benchmark data, used as the lower bound for stable service;
- reactive capacity from online forward-pass, queue, cache, and latency signals, used for bursts and distribution shifts.

Autoscaling decisions should be auditable. A route release should record why a serving lane scaled prefill, decode, or both; what TTFT/TPOT/SLA targets were used; what scale-down policy does to in-flight work; and which workload class is allowed to be shed or deferred.

Dynamo's current Planner docs make the failure mode concrete: LLM autoscaling cannot be inferred from CPU/request rate alone, because sequence length, prefill/decode phase behavior, GPU startup cost, TTFT, ITL/TPOT, and KV pressure drive real user latency. Planner also documents that aggressive scale-down can terminate in-flight work, including decode work waiting on KV transfer from a removed prefill worker. Agent Studio should therefore treat minimum endpoint floors, scale-down sensitivity, observation/no-op mode, and per-lane replica decisions as release-gated safety settings.

## Fault And Overload Behavior

Disaggregated inference creates new failure modes. A failed prefill worker can strand decode work waiting for KV transfer. A scale-down can terminate in-flight requests. A router with stale cache state can misroute. A cache layer can improve TTFT for one workload while increasing tail latency or unfairness for another.

Agent Studio serving routes should therefore define:

- request cancellation and migration policy;
- rejection/load-shedding thresholds;
- user-visible retry or degraded-mode behavior;
- in-flight request preservation expectations;
- worker drain and scale-down sensitivity;
- router state persistence and recovery;
- per-lane fairness and priority rules.

TensorRT-LLM integration is useful but not a blanket capability claim. Current Dynamo docs list disaggregated serving, KV-aware routing, SLA-based Planner, KVBM, request cancellation, multimodal/video-diffusion support, speculative decoding, and attention data parallelism, while also identifying feature gaps such as conditional disaggregation and load-based Planner support. Agent Studio should keep backend feature support as versioned evidence so a route cannot assume that all engines support the same disaggregation, routing, cancellation, multimodal, and autoscaling semantics.

## Canon Cross-Check

This note is now canon-ready because it cross-checks cleanly against the existing inference-engineering cross-check, CS25 production inference note, CS349D inference-infrastructure source map, autoscaling/admission canon, Netflix overload canon, and datastore schema. The shared conclusion is consistent: advanced serving features are production architecture, not performance garnish.

Dynamo owns the most concrete evidence for the disaggregated serving plane: prefill/decode topology, KV transfer metadata, router state, dynamic endpoint discovery, KV event fallback, backend capability differences, SLA/load autoscaling, and in-flight scale-down failure modes. CS25 and CS349D own the broader workload-profile and serving-engine ladder. Autoscaling/admission and Netflix shedding own quota, criticality, and overload behavior. The datastore owns durable release evidence.

## Datastore Requirements

Add or strengthen:

| Object | Purpose |
|---|---|
| `inference_topology_record` | Aggregated, disaggregated, multimodal EPD, or mixed serving topology with worker roles and placement constraints. |
| `prefill_decode_lane_record` | Separate prefill/decode lane capacity, queue, replica, tensor-parallelism, and scale policy. |
| `kv_cache_policy_record` | Cache key, overlap policy, memory tier, eviction policy, accepted reuse boundary, and privacy/source constraints. |
| `kv_routing_decision` | Per-request routing evidence: overlap score, active blocks, queue pressure, selected worker, fallback mode, and fairness class. |
| `cache_transfer_trace` | KV transfer metadata and timing between prefill and decode workers without storing prompt or cache contents. |
| `llm_autoscaling_decision` | Planner decision for prefill/decode workers with TTFT, TPOT, traffic, queue, cache, and replica evidence. |
| `inference_fault_event` | Worker failure, request migration, cancellation, rejection, scale-down failure, or router-state recovery event. |
| `serving_topology_benchmark` | Workload-specific comparison of aggregated versus disaggregated or cache-aware configurations. |
| `serving_topology_release_gate` | Promotion decision for disaggregated/KV-aware serving, including workload fit, backend feature support, dynamic discovery, KV event/fallback mode, queue policy, scale-down safety, benchmark evidence, overload behavior, and rollback. |

## Canon Decision

Agent Studio should treat advanced serving techniques as governed route changes. Disaggregated serving, KV-aware routing, KV offload, and SLA-based autoscaling are powerful only when the workload has measured prefill/decode/cache behavior and the release records quality, latency, cost, fairness, overload, backend capability, scale-down safety, and rollback evidence.

Production rule: a route may not promote disaggregated or KV-aware serving solely because an engine supports it. Promotion requires a workload-specific serving topology release gate proving measured prefill/decode pressure, cache-reuse boundaries, backend feature support, dynamic endpoint/router state assumptions, KV event fallback behavior, scale-down protection for in-flight requests, queue/priority policy, overload semantics, benchmark deltas, eval/quality regression status, and a fallback topology.
