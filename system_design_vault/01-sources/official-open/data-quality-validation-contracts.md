---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://docs.greatexpectations.io/docs/core/define_expectations
  - https://docs.greatexpectations.io/docs/core/run_validations/create_a_validation_definition/
  - https://docs.greatexpectations.io/docs/reference/api/Checkpoint_class
  - https://docs.getdbt.com/docs/build/data-tests
  - https://docs.getdbt.com/reference/artifacts/run-results-json
  - https://www.tensorflow.org/tfx/data_validation/get_started/
  - https://tensorflow.github.io/tfx/guide/tfdv/
  - https://docs.soda.io/soda-documentation/soda-v3/overview-main
---

# Data Quality Validation Contracts

## Source Boundary

This note synthesizes official Great Expectations, dbt, TensorFlow Data Validation, and Soda documentation for data-quality assertions, validation runs, anomaly checks, and production gates. It applies those contracts to Agent Studio ingestion, retrieval, feature, eval, and route-release data. It does not store raw source text or copied validation examples.

The document layout/OCR runtime note adds a concrete extraction-quality surface for file ingestion: parser profile, page coverage, layout element coverage, table quality, OCR/image quality, and fallback decisions should be inputs to these validation contracts before any PDF, image, DOC, or DOCX source becomes retrieval evidence.

## Core Design Lessons

Validation logic needs its own durable identity. Current Great Expectations Core models expectations and expectation suites, then runs validation definitions and checkpoints that can trigger actions from validation results. dbt models data tests as SQL assertions that return failing records and emits run-result artifacts with executed-node status, timing, failures, and adapter metadata. TensorFlow Data Validation generates statistics, infers schemas, and validates data by comparing stats against expected schema/distribution constraints. Soda frames checks and contracts as executable data-quality scans. The shared pattern is clear: a data-quality rule is a versioned contract, not a comment beside a pipeline.

Validation should run at multiple boundaries. For Agent Studio, data checks belong before source ingestion, after extraction, after chunking, after embedding/index construction, before eval dataset promotion, before route-release promotion, and during production monitoring. A single final "eval score" is too late to catch malformed chunks, missing rights fields, stale embeddings, broken metadata filters, or leaked future labels.

Failed records are evidence. dbt can store failing rows for inspection; Great Expectations produces validation results and actions; TFDV reports anomalies and statistics. Agent Studio should preserve compact failure summaries, failure record refs or hashes, affected source/chunk/feature IDs, severity, owner, and release decision. The validation output should feed remediation, not disappear into logs.

Schema drift and semantic drift are different. A field can keep the same type while its values become invalid for a route. Agent Studio needs both structural checks, such as required fields and foreign keys, and semantic checks, such as accepted source status, rights labels, chunk token bounds, embedding dimension, timestamp freshness, graph edge type, and expected label distribution.

Validation severity should map to route policy. Some checks are hard blockers, such as missing source provenance or wrong embedding dimension. Others are warnings that trigger review, such as unusual topic distribution or unexpected chunk-count growth. The validation contract should state severity, allowed exceptions, owner, rollback/fallback behavior, and whether the result blocks ingestion, retrieval, route release, or publishing.

## Agent Studio Implications

Agent Studio should validate at least these data families:

- source records: provenance, rights status, owner, freshness, canonical URL/path, and disallowed-origin markers;
- extraction artifacts: text extraction success, OCR/layout caveats, page/section coverage, and table/image loss risk;
- chunks: section path, token bounds, overlap policy, chunk-context hash, sensitivity label, and source snapshot link;
- embeddings/indexes: model, dimension, vector type, distance metric, index release, and stale-source alignment;
- retrieval features: candidate IDs, score families, filter fields, graph refs, reranker traces, and rejected evidence;
- eval datasets: split policy, point-in-time features, expected labels, forbidden leakage, slice coverage, and grader refs;
- generated artifacts: source support, media rights, platform policy fields, approval status, and rollback record.

## Datastore Requirements

Agent Studio needs validation-shaped records for:

- data quality contract: subject family, assertion set, severity, owner, version, and blocking surface;
- validation run: contract, data snapshot, adapter, environment, started/finished time, and status;
- validation result: passed/failed/warned checks, metric values, thresholds, failure count, and severity;
- validation failure sample: affected record/chunk/feature ID, failure class, sample hash, remediation owner, and retention policy;
- anomaly report: schema drift, distribution drift, missingness, late data, duplicate keys, and unexpected category changes;
- data quality action: notify, quarantine, block route release, rebuild index, re-extract source, open review, or allow exception;
- exception waiver: check, scope, reason, expiry, approver, and follow-up requirement.

## Canon Cross-Check

- Document layout/OCR ingestion owns parser profile, page coverage, layout/table/OCR signals, and fallback decisions; this note owns whether those signals are promoted, blocked, quarantined, or waived by versioned quality contracts.
- Retrieval and reranking canon owns retrieval quality metrics and accepted/rejected evidence; this note owns structural and semantic checks that prevent malformed chunks, stale embeddings, broken filters, and missing source links from entering retrieval releases.
- Schema/API compatibility canon owns contract evolution and decoder compatibility; this note owns observed-data validity, distribution drift, failure samples, quality actions, and exception waivers.
- Feature-store parity canon owns online/offline feature definitions and point-in-time correctness; this note owns validation runs, anomaly reports, and release-blocking quality outcomes for feature views and materialization jobs.
- Production canon and HLD already require validation contracts before source snapshots, indexes, eval datasets, route releases, and publishable artifacts are trusted; this pass makes that requirement canon-ready and release-gated.

## Canon Decision

Agent Studio must treat data quality as release-managed infrastructure. No source snapshot, extracted artifact, chunk set, embedding/index release, feature view, eval dataset, route release, or publishable artifact should become production evidence without a `data_quality_release_gate` linking the relevant quality contracts, validation runs/results, failure samples, anomaly reports, quality actions, exception waivers, and owner decision.

## Operating Rule

No source snapshot, retrieval index, feature view, eval dataset, route release, or publishable artifact should become canon-ready solely because it exists. It needs the relevant validation contracts to pass, fail with an approved exception, or be explicitly marked unusable for production decisions.
