---
type: official-open-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://mlflow.org/docs/latest/ml/tracking/
  - https://mlflow.org/docs/latest/ml/model-registry/
  - https://doc.dvc.org/example-scenarios/versioning-data-and-models
  - https://doc.dvc.org/example-scenarios/versioning-data-and-model-files/tutorial
  - https://www.kubeflow.org/docs/components/pipelines/concepts/metadata/
  - https://www.kubeflow.org/docs/components/pipelines/user-guides/data-handling/artifacts/
  - https://openlineage.io/docs/
  - https://openlineage.io/docs/spec/facets/
---

# Model Data Artifact Lineage And Registries

## Direct Read Scope

This pass uses current official/open documentation from MLflow, DVC, Kubeflow Pipelines, and OpenLineage. It focuses on experiment tracking, registries, data/model versioning, artifact metadata, and lineage. It does not store raw source text or long excerpts.

## Core Read

MLflow separates run metadata, artifacts, datasets, and registered model versions. The important design pattern is not "use MLflow exactly"; it is that every candidate model or AI component should be traceable back to the run, parameters, metrics, artifacts, data references, and validation status that produced it. Registry aliases and tags are deployment controls: a mutable alias such as champion is useful only if reassignment is auditable and backed by eval evidence.

DVC treats data, model files, code, and pipeline definitions as a linked version history. Agent Studio has the same problem for source snapshots, extracted text hashes, chunking configs, embeddings, vector indexes, graph communities, prompt bundles, eval datasets, model adapters, and generated artifacts. A route release is reproducible only when all of those inputs can be named together.

Kubeflow Pipelines metadata distinguishes executions from artifacts and records how artifacts flow between components. That separation maps directly to ingestion and content routes: a source scan, OCR pass, chunking job, embedding job, rerank eval, synthesis pass, and publishing step are executions; their inputs and outputs are artifacts with metadata and lineage edges.

OpenLineage provides a compact event model around jobs, runs, datasets, and extensible facets. The useful abstraction for Agent Studio is to emit lineage events whenever a route reads source data or writes derived artifacts, with custom facets for source rights, model route, prompt version, retrieval snapshot, eval result, human approval, and content sensitivity.

## Agent Studio Design Implications

- Treat prompts, tool schemas, agent graphs, retrieval indexes, source manifests, eval datasets, rerankers, model adapters, provider routes, and generated media as registry-managed artifacts, not loose files.
- Preserve run-to-artifact lineage for every ingestion and generation route: inputs, execution version, parameters, output hashes, metrics, reviewer state, and promotion decision.
- Store artifact content in the right backing store, but keep registry metadata and lineage in the durable Postgres plane.
- Use aliases only for stable deployment references such as `champion`, `candidate`, `rollback`, or `shadow`; never let an alias hide the immutable version that actually served a run.
- Version datasets and source snapshots together with the code/config that transformed them. A vector index without its source snapshot, chunker, embedding model, and filter policy is not reproducible.
- Emit lineage events for both ML-style runs and agent/content runs. Generated notes, scripts, reels, source ledgers, eval reports, and route releases all need traceable input/output edges.
- Keep registry records small and original. Do not store raw book text, full transcripts, or copied source content as registry metadata.

## Required Datastore Additions

| Object | Purpose |
|---|---|
| `registry_lineage_release_gate` | Promotion gate proving reusable/deployable assets can be reconstructed from immutable versions, producer runs, lineage events, validation state, and alias audits. |
| `artifact_registry_entry` | Canonical registry record for models, prompts, indexes, datasets, source snapshots, tools, eval suites, and generated artifacts. |
| `artifact_version_record` | Immutable version with hash, storage pointer, producer run, validation state, and rollback eligibility. |
| `experiment_run_record` | Run metadata for experiments, evals, ingestion jobs, tuning jobs, and route candidates. |
| `dataset_version_record` | Versioned source/dataset/snapshot bundle with rights, split policy, transform lineage, and contamination checks. |
| `prompt_registry_entry` | Versioned prompt or instruction bundle with route binding, eval coverage, and deprecation state. |
| `index_registry_entry` | Versioned vector/lexical/graph index with source snapshot, chunking policy, embedding model, and freshness status. |
| `lineage_event_record` | Job/run/dataset/artifact edge event for ingestion, eval, generation, publishing, and migration routes. |
| `registry_alias_record` | Mutable alias pointer with immutable target, owner, approval, and reassignment audit. |

## Canon Cross-Check

- Object/artifact storage owns binary durability, object versions/generations, retention, signed access, and restore posture; this note owns the registry identity, immutable version, producer run, validation state, and lineage edges that make stored objects meaningful.
- Data-quality canon owns validation contracts, failures, anomaly reports, and waivers; this note records validation state as release evidence but does not replace data-quality checks.
- Schema/API compatibility canon owns contract evolution; this note owns versioned artifact families and alias reassignment audit so consumers can identify exactly which version served a run.
- Feature flags and serving rollout notes own runtime traffic selection; this note owns the immutable release bundle behind aliases such as `candidate`, `champion`, `rollback`, and `shadow`.
- Production canon and HLD already require prompts, tools, agent graphs, model/provider routes, source snapshots, indexes, eval suites, generated media, and route releases to be reconstructible; this pass makes that requirement a release gate.

## Canon Decision

Agent Studio should use a registry-and-lineage layer for every deployable or reusable artifact. A route release is not valid unless a registry-lineage release gate proves that its model/provider, prompts, tools, agent graph, source snapshot, retrieval indexes, eval suite, generated artifacts, and approval state can be reconstructed from immutable artifact versions plus lineage events.
