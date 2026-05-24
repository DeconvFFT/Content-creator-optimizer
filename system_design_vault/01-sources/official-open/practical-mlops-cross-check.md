---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
cross_checks:
  - source_title: "Practical MLOps"
    chapters: "1-12"
sources:
  - https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning
  - https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/machine-learning-lens.html
  - https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/design-principles.html
  - https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/best-practices-by-ml-lifecycle-phase.html
  - https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/monitoring.html
  - https://learn.microsoft.com/en-us/azure/machine-learning/concept-model-monitoring?view=azureml-api-2
  - https://learn.microsoft.com/en-us/azure/machine-learning/concept-endpoints
  - https://learn.microsoft.com/en-us/azure/machine-learning/how-to-use-mlflow-configure-tracking?tabs=cli%2Cmlflow&view=azureml-api-2
  - https://www.kubeflow.org/docs/components/pipelines/concepts/pipeline/
  - https://mlflow.org/docs/2.11.1/model-registry.html
  - https://opentelemetry.io/docs/specs/semconv/gen-ai/
---

# Practical MLOps - Official Cross-Check

## Scope

This note cross-checks the direct-read chapter notes for [[../../02-books/practical-mlops/chapters/1-introduction-to-mlops]] through [[../../02-books/practical-mlops/chapters/12-case-studies-and-design-patterns]].

It stores compact original synthesis only. It does not copy raw source text or long excerpts.

## Cross-Check Result

Status: `canon_ready`.

The official sources strongly support the book's production stance: ML systems are larger than model code; automation, monitoring, metadata, reproducibility, packaging, security, cost control, and feedback loops are part of the product. The source set also updates the book's cloud-service specifics: for Agent Studio, provider catalogs should be treated as examples of architectural patterns, not as frozen product recommendations.

## Confirmation Matrix

| Book theme | Official-source confirmation | Agent Studio implication |
|---|---|---|
| MLOps is DevOps plus data/model lifecycle discipline | Google Cloud defines MLOps as unifying ML development and operation with automation and monitoring across integration, testing, release, deployment, and infrastructure management. | Agent Studio needs CI/CD for prompts, retrievers, evaluators, source manifests, graph definitions, model routes, and note-promotion logic, not only application code. |
| ML systems are mostly surrounding infrastructure | Google Cloud's MLOps guidance emphasizes configuration, automation, data verification, resource management, model analysis, metadata, serving, and monitoring around model code. | Treat the system-design vault as an operational data product: source ledgers, extraction runs, indexes, evals, and artifacts need versions and owners. |
| Maturity grows from manual to automated pipelines | Google Cloud separates manual, pipeline automation, and CI/CD pipeline automation maturity levels. | Keep manual Obsidian synthesis for understanding, but production ingestion needs repeatable pipelines with validation, metadata, and promotion gates. |
| Ownership and reproducibility are core design principles | AWS ML Lens calls out ownership, protection, resiliency, reusability, reproducibility, automation, continuous improvement, resource optimization, and cost reduction. | Every Agent Studio artifact should name owner, source, build path, validation state, runtime target, rollback path, and cost/latency class. |
| Lifecycle best practices span business goal through monitoring | AWS ML Lens indexes best practices across business goal identification, ML problem framing, data processing, model development, deployment, and monitoring. | Agent Studio capability specs should include business/user objective, source/data profile, eval plan, deployment mode, monitoring plan, and feedback loop. |
| Monitoring is operational and model-specific | AWS monitoring guidance covers data quality, model quality, bias drift, feature-attribution drift, explainability, alerting, and retraining/update pipelines. Azure model monitoring covers production inference data, reference baselines, data drift, prediction drift, data quality, feature-attribution drift, model performance, alerts, and Event Grid actions. | Monitor source distribution, retrieval/citation quality, model output quality, drift in accepted edits, reviewer overrides, cost, latency, fallback rate, and publish outcomes. |
| Production endpoints need durable serving contracts | Azure endpoint docs distinguish stable endpoints from deployments, real-time from batch, routing among deployments, auth, network isolation, quota/cost behavior, and overcapacity handling. | Agent Studio should separate realtime studio APIs, batch ingestion jobs, offline eval jobs, and scheduled refresh endpoints with explicit auth, routing, cost, and queue behavior. |
| Registries and lineage matter | MLflow registry centers model lineage, versions, aliases, tags, annotations, and lifecycle management. Azure MLflow integration tracks run IDs and model metadata for traceability. | Use registry patterns for prompt bundles, tool schemas, source manifests, chunking profiles, embeddings, indexes, rerankers, evaluators, model routes, and generated note releases. |
| Pipelines should be explicit workflow graphs | Kubeflow Pipelines defines ML workflows as directed graphs of components with parameters, data flow, execution order, run history, and container execution. | Long-running Agent Studio ingestion should be graph-based: scan, verify, extract, chunk, embed, index, retrieve-test, synthesize, evaluate, review, and promote. |
| Interoperability is an exit and replay strategy | MLflow, Azure MLflow support, and Kubeflow reinforce portable artifacts, metadata, and execution definitions. | Do not trap the studio in one provider UI. Keep local replay, exportable artifacts, CLI/API triggers, and provider adapters. |
| Observability needs shared semantic conventions | OpenTelemetry GenAI conventions cover GenAI events, exceptions, metrics, model spans, agent spans, provider-specific systems, and MCP conventions. | Instrument model calls, tool calls, retrieval, handoffs, memory updates, MCP/tool boundaries, evals, and human approvals with consistent trace attributes. |
| Security is lifecycle-wide | AWS ML Lens includes privacy, license checks, least privilege, secure environments, data lineage, minimal retention, adversarial protection, endpoint access restriction, and anomalous human-access monitoring across lifecycle phases. | Apply least privilege and audit logs to local corpus access, source extraction, note promotion, provider credentials, tool execution, and stored traces. |
| Platform choice should match workload maturity | The book's AWS/Azure/GCP chapters are consistent with cloud docs: use simple managed/serverless/container services for narrow loops, and heavier ML platforms when lifecycle complexity justifies them. | Start Agent Studio with reproducible local/CLI plus managed services where useful; add Kubernetes or full ML platform patterns only when orchestration, scale, or team operations justify the burden. |

## Agent Studio Design Decisions Strengthened

- Treat the Obsidian vault as the human-readable layer over a stricter operational ledger, not as the only source of truth.
- Add artifact registries for source manifests, extraction outputs, chunking profiles, indexes, prompts, tool schemas, graph definitions, evaluator suites, and note releases.
- Build ingestion as an executable pipeline with component-level status, retry, validation, lineage, and promotion gates.
- Use monitoring signals that combine platform metrics, retrieval quality, source quality, output quality, user/reviewer behavior, and business outcomes.
- Keep cloud-provider usage pattern-based: serverless for narrow events, containers for portable workers, managed ML platforms for lifecycle-heavy workflows, Kubernetes for mature multi-service operations.
- Define a telemetry schema aligned with OpenTelemetry GenAI conventions, extended with source-ledger and content-studio fields.
- Require security controls for every lifecycle phase: provenance validation, least privilege, retention policy, encryption, secrets management, audit logs, and human-access anomaly checks.
- Prefer small automated quality improvements over broad manual ingestion pushes whose quality cannot be measured.

## Canon Status

Practical MLOps chapters 1-12 are canon-ready for Agent Studio system-design decisions. Cloud service names in the chapter notes should be interpreted as architectural examples that require current provider-doc verification before implementation.
