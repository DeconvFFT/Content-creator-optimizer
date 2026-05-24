---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://cloud.google.com/vertex-ai/docs/featurestore/latest/overview
  - https://docs.feast.dev/
  - https://docs.aws.amazon.com/sagemaker/latest/dg/feature-store.html
  - https://docs.aws.amazon.com/sagemaker/latest/dg/feature-store-concepts.html
---

# Feature Store And Online/Offline Parity

## Source Boundary

This note synthesizes current official Google Vertex AI Feature Store, Feast, and Amazon SageMaker Feature Store docs. It covers reusable feature definitions and train/serve parity patterns that apply to Agent Studio source, route, retrieval, feedback, and eval signals. It stores no raw docs text or long excerpts.

Current-doc check on 2026-05-18: Vertex AI Feature Store currently centers on BigQuery-backed feature groups, online store instances, feature views, periodic refresh/materialization, historical serving, feature monitoring, embeddings support, and metadata catalog integration. Feast still presents a feature store as an operational system with offline stores for historical training extraction and online stores plus a feature server for low-latency production serving. SageMaker Feature Store still distinguishes feature groups, feature definitions, records, record identifiers, event time, online low-latency latest-record lookup, streaming/batch ingestion, and append-only offline history in S3.

## Core Design Lessons

Feature stores exist because feature logic becomes product behavior. A feature is not just a column; it has an entity key, schema, transformation, event time, freshness expectation, offline history, online serving path, owner, and quality contract. Agent Studio has the same problem with source quality scores, retrieval features, user feedback signals, route health signals, artifact revision features, and eval slice definitions.

Online and offline stores solve different jobs. Offline stores preserve historical values for training, backtests, audits, and point-in-time joins. Online stores serve recent values at low latency for inference or route decisions. Agent Studio should not compute a route decision one way during offline eval and another way during a live run. The feature definition and transformation release should be shared, with separate materialization records for offline and online views.

Point-in-time correctness is a release gate. Training and evaluation should only use feature values available at the event time being simulated. If a retrieval route uses future feedback, later source status, or post-publication labels to train a ranking policy, the offline result is contaminated. Agent Studio needs point-in-time join records for retrieval evals, ranking evals, route selection, and user-feedback learning.

Freshness and materialization are route-specific. A source-rights label, embedding freshness timestamp, index health signal, user preference, draft acceptance rate, and platform quota signal have different staleness tolerances. Feature stores make materialization and serving freshness explicit; Agent Studio should copy that discipline for source/retrieval/routing features.

Schema and ownership matter more than the storage brand. Vertex, Feast, and SageMaker use different terms, but they converge on versioned feature definitions, entities, feature groups or views, offline/online storage, metadata, ingestion or materialization jobs, and serving APIs. Agent Studio should keep provider/platform choice behind a feature registry contract.

Monitoring should attach to signals, not only models. Feature drift, missing values, late arrivals, schema changes, and stale online values can break routing before model metrics move. Agent Studio should monitor source features, route features, retrieval features, eval features, and feedback features as first-class production objects.

## Agent Studio Implications

Treat every reusable route signal as a governed feature:

- source authority, rights, freshness, and extraction quality;
- chunk context quality and embedding/index freshness;
- retrieval candidate scores, graph authority priors, reranker movement, and false-negative labels;
- user feedback, artifact revision burden, acceptance signals, and delayed outcomes;
- provider latency, cost, quota, safety tripwires, and degradation state;
- publishing platform readiness, compliance, and rollback signals.

Do not hide these signals inside ad hoc Python functions or prompt templates. A route release should know the feature definitions it reads, their materialization jobs, online/offline serving state, freshness SLA, point-in-time join policy, privacy class, and monitoring status.

## Datastore Requirements

Agent Studio needs feature-store-shaped records for:

- feature entity: stable entity key, namespace, privacy class, and owner;
- feature view definition: feature names, schema, transformation, source refs, event timestamp, TTL, and status;
- feature materialization job: source snapshot, destination, window, row count, late-data handling, and freshness result;
- online feature serving record: online store, key, latest timestamp, latency, stale/missing behavior, and fallback;
- offline feature snapshot: point-in-time join policy, training/eval dataset ref, leakage checks, and reproducibility hash;
- feature quality monitor: missingness, drift, freshness, schema violations, late arrivals, and alert policy;
- feature consumer record: route, eval, model, retriever, reranker, or agent that depends on the feature view;
- feature deprecation record: old feature, replacement, consumers, migration window, and compatibility check.

## Feature Parity Release Gate

`feature_parity_release_gate` is the promotion gate for any route, eval, retriever, reranker, agent scheduler, memory policy, feedback learner, or publishing workflow that reads reusable feature/signal definitions. It prevents a route from passing offline evals with one signal path and serving users with a different live signal path.

Required evidence:

- `gate_id`, `route_id`, `release_ref`, `feature_view_refs`, `feature_entity_refs`, `feature_consumer_refs`, and `owner_refs`;
- `source_snapshot_refs`, `transformation_version_refs`, `schema_ref`, `event_timestamp_policy`, `ttl_policy`, and `privacy_class`;
- `offline_store_ref`, `online_store_ref`, `materialization_job_refs`, `latest_online_timestamp_refs`, `historical_snapshot_refs`, and `point_in_time_join_refs`;
- `leakage_check_refs` proving training, eval, and route-selection data did not use future source status, future feedback, post-publication labels, or post-release quality signals;
- `freshness_sla`, `freshness_monitor_refs`, `missingness_monitor_refs`, `drift_monitor_refs`, `schema_violation_refs`, and `late_data_policy_ref`;
- `serving_latency_refs`, `stale_or_missing_policy`, `fallback_feature_refs`, `fallback_route_behavior`, and `online_lookup_error_budget_ref`;
- `authorized_discovery_refs`, `metadata_catalog_refs`, `access_policy_refs`, and `retention_policy_refs`;
- `offline_online_parity_check_refs`, `sampled_live_lookup_refs`, `affected_consumer_refs`, `deprecation_or_migration_refs`, `decision`, `reviewer`, and `reviewed_at`.

Do not promote a feature-consuming route when:

- the offline eval feature path and online serving feature path are implemented by separate, unversioned logic;
- event-time semantics are missing or cannot prove point-in-time joins;
- the online store serves only latest values but the route assumes historical state;
- materialization freshness is below the route's decision tolerance;
- missing, stale, late, or schema-violating feature values lack fallback behavior;
- feature access or discovery is available to unauthorized consumers;
- a feature definition changed without validating affected evals, retrievers, models, prompts, tools, and publishing gates.

## Operating Rule

Feature parity is not only for traditional ML models. For Agent Studio, source retrieval, routing, agent scheduling, eval selection, memory promotion, and publishing gates all consume features. If offline evaluation and online execution do not read the same governed signal definitions, the product will ship routes that looked correct only in the lab.
