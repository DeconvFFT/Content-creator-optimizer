---
type: official-course-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
course: "Stanford CS329S Machine Learning Systems Design"
source_status: official_public_google_slides_html_view
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://stanford-cs329s.github.io/index.html
  - https://stanford-cs329s.github.io/syllabus.html
  - https://docs.google.com/presentation/d/1b-NLyZW2M8D7r_SXLlpLWnosgryMp7luXcn4d9KAn9M/htmlpresent
related:
  - "[[cs329s-ml-systems-design]]"
  - "[[../../01-sources/official-open/model-data-artifact-lineage-and-registries]]"
  - "[[../../01-sources/official-open/autoscaling-capacity-and-admission-control]]"
  - "[[../../01-sources/official-open/async-workflow-and-queue-reliability]]"
---

# CS329S ML Infrastructure And Platform

## Reading Scope

Canon-ready direct-read pass over the official Stanford CS329S course page, syllabus, and public Google Slides HTML view for Lecture 15, ML Infrastructure and Platform, rechecked from the public syllabus link on 2026-05-18. This note stores compact original synthesis only and does not copy slide text or long excerpts.

## Core Read

The lecture treats ML infrastructure as the shared facilities that keep ML systems developable, deployable, maintainable, and cost-aware. The important production lesson is that infrastructure is not one monolith. It includes storage and compute, development environments, containers, schedulers, orchestrators, workflow managers, model deployment, model stores, feature stores, and eventually a platform layer that standardizes common work across teams.

Agent Studio implication: the data store should represent platform boundaries explicitly. Source ingestion, evals, route releases, realtime serving, retrieval indexes, media generation, and long-running agents should not share one generic "job" abstraction.

## Infrastructure Layers

The lecture starts from the complexity of real ML systems: requests can pass through many components before a response. When something breaks, debugging depends on knowing which layer owns the failure. It then separates storage, compute, development environment, containers, resource management, workflow management, and platform components.

Agent Studio implications:

- separate durable source/artifact storage from execution metadata and from model/provider serving;
- record which layer owns each failure: source intake, extraction, retrieval, reranking, model call, tool call, workflow state, publish action, or UI projection;
- make platform layers observable enough that a reviewer can understand a failed run without reading logs from every subsystem.

## Compute And Cost

The compute layer is not just "has GPU." Useful records include memory, I/O bandwidth, operation speed, utilization, cost, workload fit, and whether the benchmark actually represents the route. The lecture's cloud discussion also frames cloud as variable-capacity convenience with real cost and lock-in tradeoffs.

Agent Studio implications:

- capacity estimates should track memory, I/O, GPU/CPU class, utilization, queue pressure, and cost per route class;
- cloud/provider use should be justified by workload shape, not chosen by default;
- local-first routes still need the same capacity records because laptop/local failures are production failures for this product.

## Development Environment And Dev/Prod Parity

The lecture emphasizes standardized dev environments, dependency versions, tools, hardware, containers, and the ability to bring development closer to production. For Agent Studio, this maps to reproducible ingestion and route testing.

Agent Studio implications:

- every ingestion or route release needs environment metadata: code version, dependency lock, tool versions, model/provider versions, hardware/runtime class, and secrets boundary;
- a route that works only in an interactive notebook is not production-ready;
- local reproduction should exist for failed source extraction, eval regression, route replay, and media generation where feasible.

## Schedulers, Orchestrators, And Workflow Managers

The lecture separates schedulers from orchestrators: schedulers decide when jobs run and handle dependencies, queues, quotas, and retries; orchestrators decide where containers/services run and manage instances, replication, and provisioning. Workflow managers encode data-science workflows as code or configuration and trade off flexibility, dynamic execution, boilerplate, and dev/prod parity.

Agent Studio implications:

- scheduled refreshes, batch ingestion, eval suites, and embedding rebuilds need scheduler contracts;
- realtime voice, source-ledger APIs, route-serving workers, and durable orchestrators need service-orchestration contracts;
- workflow definitions should be parameterized and reproducible, not copied into many static one-off jobs;
- queue priority, resource requirements, retry policy, and failure quarantine belong in route metadata.

## ML Platform Components

The platform section names common shared components: model deployment, model store, and feature store. The deeper point is platformization: after multiple teams rebuild the same deployment, registry, and feature-management tools, shared infrastructure becomes cheaper and safer than bespoke pipelines.

Agent Studio implications:

- define platform services for source registry, artifact registry, prompt/tool/agent registry, dataset/source snapshot versions, model/provider route registry, feature/index registry, eval registry, workflow registry, and trace store;
- keep the platform thin enough for one user/local-first development, but shape schemas so the same objects can scale to a team platform;
- platform objects should reduce duplication and failure surfaces, not add ceremony to one-off notes.

## Failure Modes

- Building one monolithic workflow that hides whether ingestion, evaluation, registration, serving, or publishing failed.
- Treating Kubernetes, Airflow, Argo, Kubeflow, or any platform as value by itself instead of matching the workload.
- Tracking model versions but not source snapshots, prompt/tool versions, index versions, and eval suites.
- Running notebook experiments whose environment cannot be reconstructed.
- Letting background jobs and realtime serving compete for the same unbounded resources.
- Measuring peak hardware capacity while ignoring I/O, utilization, queueing, and cost.

## Datastore Requirements

Add or strengthen:

| Object | Purpose |
|---|---|
| `platform_layer_record` | Maps source, storage, compute, workflow, serving, registry, eval, and UI layers to owners and failure surfaces. |
| `dev_environment_profile` | Reproducible dependency, tool, runtime, hardware, and secret-boundary profile. |
| `workflow_orchestration_profile` | Workflow manager, scheduler/orchestrator split, parameterization, retry, queue, and resource policy. |
| `compute_capacity_profile` | Memory, I/O bandwidth, accelerator/CPU class, utilization target, cost, and workload fit. |
| `ml_platform_component_record` | Shared model/source/prompt/index/eval/deployment platform component with owner, API, storage, and adoption status. |
| `platform_infrastructure_release_gate` | Promotion gate proving that platform and workflow changes are reproducible, observable, capacity-aware, and reversible before they carry production ingestion, eval, retrieval, serving, or publishing work. |

## Release Gate Contract

`platform_infrastructure_release_gate` is required before a workflow engine, scheduler, orchestrator, registry, model/source/prompt/index store, feature/signal store, deployment service, environment image, compute pool, or managed MLOps tool becomes a production dependency for Agent Studio.

The gate rejects promotion unless the release record binds:

- owned infrastructure layer and failure surface;
- development/execution environment profile with code, dependency, tool, runtime, hardware, and secret-boundary evidence;
- workflow contract that separates schedule triggers, dependency graph, parameterization, retry, queue, quota, and resource policy;
- service-orchestration contract for long-running services, replication, placement, and provisioning;
- compute/cost evidence for memory, I/O bandwidth, CPU/GPU or accelerator class, utilization target, benchmark representativeness, and workload fit;
- deployment mode and quality gate for online, batch, or mixed prediction/generation paths;
- registry lineage for model, source, prompt, index, eval, artifact, and workflow versions;
- monitoring, experimentation, and business-measurement hooks when the platform component can change route behavior or cost;
- tool-fit review covering cloud/provider compatibility, open-source versus managed posture, data-security requirements, lock-in/exit path, operational burden, fallback, and rollback.

## Canon Decision

Agent Studio should treat infrastructure as layered product design. The minimal durable data store needs registries, workflow metadata, environment profiles, capacity profiles, queue/orchestration contracts, platform-component ownership, monitoring/measurement hooks, tool-fit reviews, and rollback paths before autonomous ingestion, eval, retrieval, serving, or publishing routes can scale without becoming unreproducible notebook work.
