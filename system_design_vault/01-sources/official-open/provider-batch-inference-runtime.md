---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_public
provenance_status: official_provider_batch_docs_direct_read
sources:
  - https://developers.openai.com/api/docs/guides/batch
  - https://platform.claude.com/docs/en/build-with-claude/batch-processing
  - https://ai.google.dev/gemini-api/docs/batch-api
  - https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/batch-prediction-gemini
---

# Provider Batch Inference Runtime

## Scope

Direct-read synthesis from current official OpenAI Batch API, Anthropic Message Batches, Gemini API Batch, and Vertex/Gemini batch inference docs. This note captures Agent Studio batch-runtime and datastore implications. It stores no copied request examples, raw output files, code blocks, or long excerpts.

Current-doc check on 2026-05-18 found the official provider docs still aligned with this note. OpenAI Batch still requires caller-owned `custom_id` mapping, endpoint-specific JSONL input, completion windows, output/error file retrieval, and order-independent result processing. Anthropic Message Batches still expose bounded request/file limits, 24-hour processing expiry, 29-day result availability, result types for succeeded/errored/canceled/expired work, cancel behavior, and order-independent `custom_id` matching. Gemini Batch still supports inline and JSONL/file-backed jobs, generation/embedding/image surfaces, and cancel/delete behavior. Vertex Gemini batch inference still uses Cloud Storage or BigQuery inputs, supports regional or global endpoints with data-residency caveats, queues jobs before execution, cancels incomplete work after processing limits, and documents current system limits.

## Core Pattern

Provider batch inference is not just a cheaper model call. It is a different runtime class with delayed completion, provider-side input/output storage, batch-specific quotas, per-request result matching, partial failures, cancellation/deletion behavior, and different retention posture.

Agent Studio should treat provider batch as a governed workload lane for noninteractive work:

- eval sweeps;
- source classification;
- embedding or enrichment backfills;
- moderation sweeps;
- image/video generation batches where supported;
- offline judging and artifact QA;
- dataset labeling or extraction jobs with bounded freshness needs.

Interactive drafting, realtime voice, approval-gated publishing, and user-visible recovery should not silently fall back to provider batch unless the UI and route state make the delay explicit.

## Cross-Provider Runtime Contract

The providers converge on a durable job model:

- submit many requests as an inline list or JSONL/file-backed input;
- each request carries a stable caller key such as `custom_id` or request key;
- provider validates and processes asynchronously;
- poll or list batch status;
- retrieve result files or inline results after completion;
- handle per-request success, validation error, provider error, cancel, expiry, or missing result;
- cancel/delete where supported;
- respect provider retention and result-availability windows.

The durable Agent Studio requirement is per-request identity. Batch results may not arrive in input order, and partial completion is normal enough to model. Every row needs a stable `batch_item_id`, source/eval/artifact ref, provider request key, expected output contract, retry policy, and terminal outcome.

## Provider-Specific Design Signals

OpenAI Batch uses uploaded JSONL files with an endpoint-specific request body and a completion window. The supported endpoints include text, embeddings, moderation, image, and video surfaces. OpenAI's batch guide frames this as lower-cost, higher-headroom asynchronous processing with status polling and result retrieval. For Agent Studio, endpoint, model, input file, output file, error file, completion window, and `custom_id` mapping are release evidence.

Anthropic Message Batches process Messages API requests independently, support vision/tool/system/multi-turn/beta-feature requests, return request-count summaries, can be canceled, and expose result types for succeeded, errored, canceled, and expired items. The docs also make retention explicit: batch processing stores request/response data for a bounded period and can be deleted after processing. For Agent Studio, batch retention and ZDR eligibility are route-policy fields, not implementation notes.

Gemini API Batch supports inline requests for smaller jobs and input-file JSONL for larger jobs, with separate paths for generation, embeddings, and image generation. Job results can be inline or file-backed; jobs can be canceled or deleted. The docs currently show an active incident notice on the public batch page, which reinforces that batch lanes need provider-health and retry/backoff policy.

Vertex/Gemini batch inference supports large asynchronous processing through Cloud Storage or BigQuery, with regional/global endpoint and data-residency caveats. It exposes queue-time and request-limit constraints, plus a note that Vertex AI documentation has moved under Gemini Enterprise Agent Platform. For Agent Studio, cloud batch input/output location, region, data-residency posture, queue expiry, and storage IAM policy must be explicit.

## Agent Studio Design Implications

- Batch is a release class: `realtime`, `interactive`, `background`, `provider_batch`, and `offline_backfill` need different SLOs, cost policies, retry policies, user visibility, and retention.
- Batch input files are source artifacts. Store their hashes, schema version, endpoint, model, route release, source snapshot, eval dataset, and redaction policy.
- Batch output files are result artifacts. Store output hash, error-file hash, provider status, item-count summary, retention expiry, and deletion event.
- Match results by caller key, not row order.
- Separate validation errors from retryable provider errors and expired/canceled work.
- Do not mix privacy classes, route releases, or output schemas in one batch unless the provider and internal result parser can preserve boundaries.
- Large batch jobs need admission control so they do not starve foreground routes or consume shared provider quota unexpectedly.
- For evals and source enrichment, batch results should feed trace/eval/source records only after schema validation and spot review.
- Result retention windows need local capture policy: what is stored as metadata, what is stored as artifact, what is redacted, and when provider-side results are deleted.

## Datastore Additions

| Object | Purpose | Key fields |
|---|---|---|
| `provider_batch_job` | Provider-side asynchronous batch job | `batch_job_id`, `provider`, `endpoint`, `model_ref`, `route_release_id`, `input_artifact_ref`, `output_artifact_ref`, `error_artifact_ref`, `completion_window`, `status`, `created_at`, `ended_at`, `expires_at`, `cancelled_at`, `deleted_at` |
| `provider_batch_item` | One request inside a provider batch | `batch_item_id`, `batch_job_id`, `custom_key`, `source_or_eval_ref`, `request_hash`, `expected_output_schema_ref`, `result_status`, `result_ref`, `error_type`, `retry_decision`, `created_at` |
| `batch_input_manifest` | Internal manifest for JSONL/inline batch inputs | `manifest_id`, `route_release_id`, `item_count`, `endpoint`, `model_ref`, `schema_version`, `privacy_class`, `source_snapshot_refs`, `eval_dataset_ref`, `hash`, `validation_status` |
| `batch_result_manifest` | Parsed result summary after provider completion | `result_manifest_id`, `batch_job_id`, `succeeded_count`, `errored_count`, `expired_count`, `canceled_count`, `missing_key_count`, `unexpected_schema_count`, `parser_version`, `review_status` |
| `batch_retention_policy` | Provider/local retention and deletion contract | `policy_id`, `provider`, `route_id`, `provider_storage_duration`, `local_artifact_policy`, `redaction_policy`, `delete_after_retrieval`, `zdr_or_data_boundary_review`, `status` |
| `batch_admission_record` | Capacity and quota admission decision for a batch | `admission_id`, `batch_job_id`, `workload_class`, `priority`, `provider_quota_bucket`, `max_staleness`, `cost_budget_ref`, `foreground_impact_review`, `decision` |
| `batch_reconciliation_run` | Maps provider results back to local records | `reconciliation_id`, `batch_job_id`, `result_manifest_id`, `matched_count`, `unmatched_count`, `retry_batch_refs`, `downstream_records_written`, `completed_at` |
| `provider_batch_release_gate` | Promotion gate for provider-batch lanes | `gate_id`, `route_id`, `provider_refs`, `endpoint_refs`, `batch_input_manifest_ref`, `provider_batch_job_refs`, `item_identity_policy_ref`, `privacy_segmentation_ref`, `retention_policy_ref`, `admission_record_ref`, `quota_budget_ref`, `provider_health_ref`, `result_manifest_ref`, `reconciliation_run_ref`, `partial_failure_policy_ref`, `schema_validation_refs`, `spot_review_refs`, `downstream_write_policy_ref`, `fallback_or_foreground_policy_ref`, `rollback_target_ref`, `decision`, `reviewed_at` |

## Release Gates

Do not promote a provider-batch route when:

- item IDs are not stable and unique;
- input/output artifacts lack hashes and schema versions;
- privacy class, route release, or model configuration is mixed without explicit segmentation;
- result matching depends on input order;
- partial failures are not reconciled into retry, quarantine, or human review;
- provider retention/deletion policy is not recorded;
- batch cost/quota admission can affect foreground routes;
- provider health/incidents are ignored for time-sensitive backfills;
- batch outputs can update evals, source records, embeddings, or published artifacts without validation.
- provider-batch release gates lack item identity, input/output hashes, privacy segmentation, retention/deletion policy, admission/quota review, provider-health review, result reconciliation, partial-failure handling, schema validation, spot review, downstream write policy, fallback, and rollback evidence.

## Agent Studio Decision

Use provider batch inference for large noninteractive jobs, but keep it outside the foreground agent loop. Batch jobs should produce governed artifacts and reconciliation records before they alter source ledgers, eval datasets, embeddings, route scores, or publishable media. The product can use provider discounts and higher throughput, but only with explicit identity, retention, quota, partial-failure, and validation controls.

Promote provider-batch lanes only after a `provider_batch_release_gate` proves the route can submit, monitor, retrieve, reconcile, validate, retry, quarantine, and delete batch work without losing per-item identity or starving foreground routes.
