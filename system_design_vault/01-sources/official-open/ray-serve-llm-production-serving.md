---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_doc_page
rights_status: official_public
stores_raw_source_text: false
sources:
  - https://docs.ray.io/en/latest/serve/llm/index.html
  - https://docs.ray.io/en/latest/serve/production-guide/index.html
  - https://docs.ray.io/en/latest/serve/production-guide/kubernetes.html
  - https://docs.ray.io/en/latest/serve/autoscaling-guide.html
  - https://docs.ray.io/en/latest/serve/model-multiplexing.html
  - https://docs.ray.io/en/latest/serve/llm/architecture/core.html
  - https://docs.ray.io/en/latest/serve/llm/architecture/serving-patterns/index.html
---

# Ray Serve LLM Production Serving

## Direct-Read Scope

This note is compact original synthesis from current official Ray 2.55.1 documentation for Ray Serve LLM, Serve production deployment, Kubernetes RayService, autoscaling, model multiplexing, LLM core components, and serving patterns. It stores no raw doc text or copied examples.

## System Design Takeaways

Ray Serve LLM sits between low-level inference engines and product endpoints. Its useful abstraction is not "Ray runs a model"; it is a deployment surface where OpenAI-compatible requests, engine-specific runtime choices, placement, autoscaling, routing, observability, and Kubernetes lifecycle can be expressed together.

Current-doc check on 2026-05-18 confirms that this remains a release-sensitive platform boundary: Ray Serve LLM now explicitly emphasizes automatic scaling and load balancing, OpenAI-compatible API shape, Multi-LoRA over shared base models, engine-agnostic architecture for vLLM/SGLang-style runtimes, built-in metrics and dashboards, prefix-aware/session-aware/custom routing, multi-node deployments, prefill/decode disaggregation, data-parallel attention, and production Kubernetes deployment through KubeRay RayService.

For Agent Studio, the important design boundary is:

- the product route owns use case, latency/cost/quality gates, source policy, eval gates, and rollback;
- the serving platform owns replica placement, request routing, autoscaling, model/adaptor loading, endpoint health, and runtime metrics;
- the inference engine owns token generation mechanics such as batching, cache behavior, LoRA support, and parallelism.

Do not collapse these into one `provider` field. A route can expose an OpenAI-compatible API while running through Ray Serve, vLLM, SGLang, or another engine; the route evidence needs to preserve each layer.

## Serving Patterns

Ray's current LLM docs emphasize distributed LLM serving patterns: advanced parallelism, prefill/decode disaggregation, custom routing, multi-node deployment, OpenAI-compatible API shape, Multi-LoRA, built-in metrics, and engine-agnostic architecture.

Agent Studio should treat these as candidate topology choices. They are useful when the route has evidence that:

- traffic volume or model size needs multi-node serving;
- request distribution justifies application-level autoscaling rather than fixed capacity;
- source packs, sessions, or adapters create routing locality;
- LoRA/adapters or tenant-specific weights are sparse enough for multiplexing;
- prefill/decode separation improves the measured route workload.

The existence of a serving pattern is not a release argument. Promotion still needs workload-slice benchmarks, SLO evidence, quality regression checks, and fallback behavior.

## Autoscaling Controls

Ray Serve autoscaling is application-level scaling above Ray cluster scaling. The serving autoscaler reacts to request pressure by changing replica count, then the cluster layer adds or removes nodes when resources are insufficient.

Agent Studio implications:

- store Serve-level and cluster-level scaling decisions separately;
- record `target_ongoing_requests`, `max_ongoing_requests`, min/max replicas, delay/cooldown policy, and scale-to-zero policy as versioned route metadata;
- benchmark tail latency during upscale, not only steady-state throughput;
- treat manual replica updates and autoscaling as different release modes;
- attach resource placement evidence when GPU/CPU availability constrains the requested replica count.

Autoscaling defaults are not product policy. A route that silently inherits a high maximum replica count can violate cost boundaries; a manually configured autoscaler with an accidental low maximum can pretend to be elastic while never scaling.

## Multiplexing And Adapter Loading

Ray Serve model multiplexing routes traffic to replicas that already hold the requested model id, and evicts cached models when a replica exceeds its configured model capacity. Ray Serve LLM also applies this idea to LoRA adapter routing over a shared base model.

For Agent Studio, multiplexing is useful for sparse specialist routes, brand/user adapters, local domain adapters, or evaluation workers that share input shape. It needs explicit evidence:

- model or adapter id in the request contract;
- max models/adapters per replica;
- load latency and eviction policy;
- warm-cache versus cold-load latency;
- fallback behavior when the requested model id is missing;
- rights and approval status for each adapter or model variant;
- fairness policy so rare but urgent adapters are not permanently cold.

Never treat multiplexing as free personalization. It changes latency, memory pressure, cache behavior, and governance scope.

## Kubernetes And Production Lifecycle

The production guide prefers Kubernetes with KubeRay RayService for production because the custom resource binds the Ray cluster and Serve application lifecycle. That makes health, status, recovery, upgrades, and config-driven rollout part of the platform contract.

Agent Studio should keep:

- `serve_application_record` for Serve app identity, config version, import path, endpoint surface, and deployment graph;
- `rayservice_deployment_record` for Kubernetes namespace, RayService name, Ray cluster ref, Serve config, health/status, upgrade strategy, and rollback ref;
- `serve_deployment_record` for deployment name, resources, replicas/autoscaling, placement, runtime env, and status;
- `serve_multiplexing_record` for model/adapter id routing and eviction behavior;
- `serve_autoscaling_event` for app-level scaling decisions separate from cluster/node scaling.

These records let a route-change review distinguish product route approval from infrastructure rollout status.

## Agent Studio Design Implications

- Keep Ray Serve as an optional serving substrate, not a product architecture dependency.
- Model routes should record three layers: endpoint contract, serving deployment, and inference engine.
- OpenAI-compatible API shape does not mean provider-equivalent behavior; tokenizer, cache, streaming, tool, and error semantics still need smoke and regression tests.
- Multi-LoRA and model multiplexing require adapter provenance, adapter approval, load/eviction telemetry, and per-adapter eval slices.
- Application autoscaling must be tied to request pressure, SLOs, and cost ceilings, while cluster autoscaling must be tied to resource placement and node availability.
- Kubernetes RayService deployment is a release artifact with health, status, upgrade, and rollback state; it should not be hidden behind a plain endpoint URL.
- Production readiness for Ray Serve routes should require metrics proof, load-test slices, health checks, rollback path, and failure-mode evidence before traffic promotion.

## Datastore Objects Added

- `serve_application_record`
- `serve_deployment_record`
- `rayservice_deployment_record`
- `serve_autoscaling_event`
- `serve_multiplexing_record`
- `adapter_route_record`
- `serving_engine_contract`
- `serve_endpoint_smoke`
- `ray_serve_release_gate`

## Release Gate

Promote Ray Serve-backed routes only after a `ray_serve_release_gate` proves Serve application identity, deployment graph/config version, endpoint contract, RayService or VM deployment status, Serve and cluster autoscaling policies, resource/placement assumptions, model/adaptor multiplexing policy, adapter provenance and eval slices, serving-engine contract, OpenAI-compatible smoke tests, health/status evidence, load-test slices, metrics/observability wiring, upgrade strategy, fallback route, and rollback target.
