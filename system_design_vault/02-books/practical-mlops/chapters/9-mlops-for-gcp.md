---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Practical MLOps"
authors: "Noah Gift; Alfredo Deza"
chapter: "9"
chapter_title: "MLOps for GCP"
source_path: "/Users/saumyamehta/DS interview prep/books/Practical MLOps_ Operationalizing Machine Learning Models.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# Practical MLOps - Chapter 9: MLOps for GCP

## Source Reading Scope

Direct-read extraction span: `/tmp/practical_mlops_text.txt` lines 10065-10929.

This note is original synthesis only. It does not preserve raw source text.

## Core Takeaways

The GCP chapter frames Google Cloud around strong open and managed infrastructure patterns: Kubernetes, TensorFlow, BigQuery, Cloud Functions, Cloud Run, Cloud Build, and Vertex AI.

Service choice should reflect workload maturity. A "light" MLOps path can use App Engine, Cloud Functions, Cloud Run, AI APIs, and Cloud Build to deploy quickly. A "heavy" path can use Vertex AI-style lifecycle services for datasets, models, feature stores, explainability, endpoints, and monitoring.

Kubernetes is powerful but carries operational weight. It is useful where autoscaling, service discovery, health management, secrets/configuration, and Kubeflow-style workflows matter. Cloud Run or another CaaS path is often better for simpler containerized services.

BigQuery is a data-centric MLOps pattern: the data lake/warehouse can become the center of analytics, feature preparation, model training, and business reporting. That is especially relevant when the system's advantage is grounded in large, queryable datasets.

The chapter's project checklist is portable: source code in GitHub, continuous deployment, cloud-hosted data, served predictions, monitoring, REST/JSON interface, separate environments, correct datastore, least privilege, and encryption in transit.

## Agent Studio Design Implications

- Keep two deployment tracks: light paths for fast ingestion/enrichment services, heavy lifecycle paths for production indexes, evaluator suites, and model/prompt release management.
- Use data-warehouse or lake patterns for large corpus metadata, source provenance, extracted-section inventories, embedding stats, and evaluation outcomes.
- Prefer Cloud-Run-like services for simple stateless agent utilities before reaching for Kubernetes.
- Use Kubernetes only when multi-service orchestration, autoscaling, custom runtimes, or organization-wide platform conventions justify it.
- Design every production-facing agent service around REST/JSON or similarly explicit contracts, with monitoring and separate environments.
- Track cost and machine shape as design inputs; specialized hardware and large accelerators should be justified by workload characteristics.

## Portable GCP Patterns

| GCP Pattern | Agent Studio Equivalent |
|---|---|
| BigQuery-centered workflows | corpus metadata warehouse and evaluation analytics |
| Cloud Functions | event-driven source and pipeline triggers |
| Cloud Run | stateless extraction, validation, retrieval, and eval services |
| GKE/Kubeflow | complex platform orchestration when simple services are insufficient |
| Vertex AI | managed lifecycle for datasets, models, endpoints, feature stores, and monitoring |

## Failure Modes To Guard Against

- Choosing Kubernetes when a managed container service is enough.
- Treating provider-native ML platforms as magic while skipping source control and CI/CD.
- Ignoring cost class when selecting compute for batch, training, or inference.
- Building a data store that cannot be queried for lineage, quality, and evaluation analytics.
- Shipping one environment only, with no dev/prod separation or deployment checklist.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
