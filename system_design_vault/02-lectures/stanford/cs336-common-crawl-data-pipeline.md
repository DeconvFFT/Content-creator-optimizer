---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS336 Assignment 4: Data"
source_status: official_public
updated: 2026-05-18
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://cs336.stanford.edu/
  - https://github.com/stanford-cs336/assignment4-data
  - https://github.com/stanford-cs336/assignment4-data/blob/main/cs336_assignment4_data.pdf
  - https://raw.githubusercontent.com/stanford-cs336/assignment4-data/main/cs336_assignment4_data.pdf
  - [[cs336-data-and-alignment]]
  - [[../../01-sources/official-open/web-source-acquisition-and-crawl-governance]]
  - [[../../01-sources/official-open/data-quality-validation-contracts]]
  - [[../../01-sources/official-open/document-layout-ocr-ingestion-runtime]]
related:
  - [[../../03-patterns/system-design/production-agent-studio-canon]]
  - [[../../03-patterns/evaluation/eval-design-canon]]
  - [[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]
---

# CS336 - Common Crawl Data Pipeline

## Reading Status

Direct read of the official Spring 2026 CS336 Assignment 4 repository README and official assignment handout PDF. Current-source check on 2026-05-18 verified the live CS336 course page and public Stanford assignment repository/handout. The handout was temporarily downloaded to `/private/tmp` for text extraction; the vault stores only original synthesis and Agent Studio design implications.

This note complements [[cs336-data-and-alignment]]. The lecture note gives the conceptual frame for data sources, filtering, deduplication, mixing, and alignment data. This assignment handout makes the control plane concrete: raw web archives, extracted text, filters, deduplication, validation targets, tokenization, runtime, and training impact all become measurable pipeline artifacts.

## Core Synthesis

The assignment's central lesson is that "web data" is not a dataset. It is a chain of artifacts and decisions. Common Crawl begins as raw web archive records with URLs, HTTP metadata, crawl time, and page bytes. It can be projected into metadata records or extracted text records, but those projections are not neutral. The same page can look different as raw HTML, extracted text, filtered text, deduplicated text, tokenized IDs, and model-training examples.

For Agent Studio, this is directly relevant even though the product is not training a base model from scratch. The same failure modes appear when building a notes/retrieval store:

- HTML, PDF, DOCX, image, and video sources need source-type parsers with extraction-quality evidence.
- Filters must be auditable because they can remove useful minority-language, domain-specific, or high-risk examples.
- PII and harmful-content filters are necessary but can create false positives, false negatives, and unnatural training or retrieval artifacts.
- Quality classifiers are target-dependent: a page useful for one route can be junk for another.
- Deduplication reduces memorization and overweighting, but provenance must survive dedupe.
- Validation data can guide filtering, but direct leakage from validation into training or retrieval sets must be blocked.
- Pipeline runtime and scaling cost are part of the design, not operational trivia.

## Pipeline Stages For Agent Studio

| Stage | CS336 assignment signal | Agent Studio design implication |
|---|---|---|
| Raw crawl inspection | Look at WARC and WET records before implementing filters. | Every source adapter needs sample inspection records before it becomes trusted automation. |
| Format projection | WARC, WAT, and WET represent different views over the same crawl. | Store raw-source refs, metadata projections, extracted text artifacts, and note artifacts as separate object families. |
| Text extraction | HTML-to-text extraction handles encoding and visible-content noise. | Extraction jobs need parser version, encoding path, boilerplate risk, table/image/layout loss, and quality score. |
| Language filtering | Classifier predictions need confidence thresholds and manual checks. | Source language should be a scored field with false-negative review, not a binary assumption. |
| PII masking | Email, phone, and IP masking are useful but brittle. | PII masking needs match counts, false-positive samples, false-negative review, and downstream distortion notes. |
| Harm filtering | NSFW/toxicity classifiers require threshold validation. | Safety filters need category, threshold, language/domain caveat, skipped state, and reviewer calibration. |
| Rule quality filters | Simple length/symbol/word-shape rules remove obvious bad text. | Cheap deterministic filters should run before expensive judges, but their rejection reasons must be visible. |
| Quality classifier | Positive source choice defines what "quality" means. | Quality models need target-route, positive/negative source provenance, threshold, precision/recall, and slice caveats. |
| Exact dedupe | Repeated boilerplate lines can dominate web pages. | Deduplicate at line/chunk/document levels without erasing source provenance or agreement signals. |
| MinHash/LSH dedupe | Near-duplicate detection trades precision and recall. | Store normalization policy, n-gram size, hash count, bands, threshold, clusters, retained representative, and false-merge risk. |
| Final filtering | The assignment asks for kept/discarded proportions by filter. | Every ingestion run should emit stage counters and sample accepted/rejected examples. |
| Validation target | Filtering is optimized for a Paloma/C4 validation target. | Route-specific source stores need explicit eval targets and leakage checks. |
| Tokenization | Dataset becomes serialized token IDs with EOS policy. | Tokenization is a versioned transform: tokenizer, EOS policy, dtype, document boundary, and token count belong in the ledger. |
| Training impact | Same model/training setup isolates data-pipeline quality. | When evaluating ingestion changes, hold route/model settings fixed so data-pipeline effects are attributable. |

## Important Failure Modes

- **Extraction noise becomes learned style.** Navigation, footer, comments, menus, and malformed text can teach the system poor citation and writing behavior if accepted as source content.
- **Language filters create product blind spots.** A strict English threshold may improve an English benchmark while suppressing multilingual, code-mixed, or domain-specific material needed by a user.
- **PII filters distort facts.** Masking can protect privacy but also remove contact fields, IP examples, logs, or technical identifiers that a route legitimately needs.
- **Harm filters can remove safety evidence.** Filtering toxic or unsafe text can lower exposure risk, but the product still needs safe examples for detection, refusal, and moderation evals.
- **Quality labels inherit source bias.** Wikipedia-linked or Reddit-linked positives may favor one kind of web quality and down-rank useful niche documents.
- **Deduplication can erase authority.** If multiple official sources contain the same policy, the chunk body can be deduplicated, but the support count and source identities still matter.
- **Validation-guided filtering can leak.** Using validation examples to choose filters is different from copying validation text into train or retrieval stores. The latter should be a hard block.
- **Pipeline throughput hides route risk.** A fast filter pipeline is not good if it lacks counters, samples, reproducibility, and reviewable thresholds.

## Agent Studio Datastore Commitments

| Record | Purpose | Minimum fields |
|---|---|---|
| `crawl_projection_record` | Distinguish raw web archive, metadata, and extracted text views. | `projection_id`, `source_ref`, `projection_type`, `crawl_id`, `record_locator`, `url`, `http_metadata_ref`, `created_at`, `status` |
| `source_sample_inspection` | Human or agent inspection of raw/extracted source samples before automation is trusted. | `inspection_id`, `source_snapshot_ref`, `sample_method`, `sample_count`, `quality_findings`, `risk_findings`, `recommended_filter_changes`, `reviewer`, `created_at` |
| `language_filter_result` | Language classifier decision and calibration evidence. | `result_id`, `artifact_ref`, `model_ref`, `predicted_language`, `confidence`, `threshold`, `manual_label_ref`, `decision`, `created_at` |
| `pii_masking_event` | PII detection/masking action with distortion caveats. | `masking_event_id`, `artifact_ref`, `policy_ref`, `pii_types`, `match_counts`, `masked_artifact_ref`, `false_positive_sample_refs`, `false_negative_review_ref`, `created_at` |
| `content_filter_result` | Harm/safety classifier or rule result. | `filter_result_id`, `artifact_ref`, `category`, `model_or_rule_ref`, `score`, `threshold`, `decision`, `calibration_sample_ref`, `created_at` |
| `quality_filter_result` | Deterministic or classifier-based quality decision. | `quality_result_id`, `artifact_ref`, `filter_family`, `features_or_score_ref`, `threshold`, `decision`, `target_route_or_eval`, `rejection_reason`, `created_at` |
| `dedupe_cluster_record` | Exact or fuzzy duplicate cluster without losing source identities. | `cluster_id`, `method`, `normalization_policy`, `hash_or_signature_refs`, `candidate_refs`, `similarity_threshold`, `retained_ref`, `removed_refs`, `false_merge_review` |
| `filter_stage_counter` | Per-stage kept/rejected counts for an ingestion run. | `counter_id`, `run_id`, `stage_name`, `input_count`, `kept_count`, `rejected_count`, `modified_count`, `top_rejection_reasons`, `sample_refs` |
| `validation_leakage_check` | Evidence that eval/validation targets did not enter training/retrieval data. | `check_id`, `candidate_dataset_ref`, `validation_dataset_ref`, `method`, `overlap_count`, `blocked_refs`, `review_status`, `created_at` |
| `tokenization_artifact_record` | Versioned tokenized projection of text data. | `tokenization_id`, `source_dataset_ref`, `tokenizer_ref`, `eos_policy`, `dtype`, `document_boundary_policy`, `token_count`, `output_artifact_ref`, `created_at` |
| `pipeline_runtime_benchmark` | Runtime and scaling evidence for source processing. | `benchmark_id`, `run_id`, `input_size`, `worker_count`, `hardware_or_service_ref`, `elapsed_time`, `throughput`, `cost_estimate`, `bottleneck_notes` |
| `source_filter_pipeline_release_gate` | Promotion gate before a source-filtering, dedupe, tokenization, embedding, or eval-data pipeline affects retrieval, tuning, eval generation, or canon notes. | `gate_id`, `pipeline_release_id`, `candidate_source_snapshot_ref`, `crawl_projection_refs`, `source_sample_inspection_refs`, `language_filter_refs`, `pii_masking_refs`, `content_filter_refs`, `quality_filter_refs`, `dedupe_cluster_refs`, `filter_stage_counter_refs`, `validation_leakage_check_refs`, `tokenization_artifact_refs`, `embedding_artifact_refs`, `accepted_sample_refs`, `rejected_sample_refs`, `bias_false_negative_review_refs`, `pipeline_runtime_benchmark_refs`, `rollback_snapshot_ref`, `decision`, `reviewed_at` |

## Release Gate Contract

`source_filter_pipeline_release_gate` is required before a filtering, deduplication, tokenization, embedding, or eval-data-generation pipeline can affect retrieval results, source-backed answers, route tuning, eval generation, or canon notes.

The gate should reject promotion unless:

- raw/source projections, extracted text, tokenized artifacts, embedded artifacts, and note artifacts are separate records;
- sample inspections cover accepted and rejected examples before automation is trusted;
- language, PII, harm/safety, quality, and route-specific filters expose model/rule version, threshold, decision, and calibration sample;
- deterministic rule filters and learned quality classifiers record false-positive and false-negative caveats;
- exact and near-dedupe keep source-provenance edges, support counts, normalization policy, false-merge review, and retained/removed refs;
- every filter stage has input, kept, rejected, modified counts, top rejection reasons, and representative samples;
- validation and eval targets are protected by leakage checks before they influence filters, prompts, rerankers, or generated eval cases;
- tokenization and embedding projections record model/tokenizer identity, boundary policy, output counts, and compatibility assumptions;
- runtime and scaling benchmarks identify bottlenecks and costs for the input size the route will actually process;
- rollback can restore the prior source snapshot, filter policy, dedupe state, tokenized/embedded artifacts, and retrieval index.

## Design Implications

- Agent Studio should keep web/source ingestion as a typed pipeline, not a script that emits chunks. Each stage should produce records that can be inspected, compared, and rolled back.
- The system should preserve accepted and rejected examples. Rejected examples are needed to debug recall loss, filter bias, and over-aggressive safety or quality thresholds.
- A route-specific source store should declare its target eval. Optimizing for "C4-like language modeling" is different from optimizing for "official docs answerability" or "Agent Studio implementation design."
- Filtering should be staged from cheap to expensive: source eligibility, format parseability, language, PII/safety, quality rules, quality classifier, dedupe, route-specific eval.
- Dedupe needs at least three layers for this vault: exact file hash, normalized extraction hash, and near-duplicate chunk/document signature. Canonical chunk storage must still retain source provenance edges.
- Tokenization and embedding are both lossy projections. Treat them as versioned artifacts with model/tokenizer identity, boundary policy, output counts, and compatibility checks.

## Next Agent Studio Move

Add filter-stage counters and rejected-example sampling to future ingestion runs before adding more corpora. The datastore should be able to answer: which documents were discarded, by which filter, with what threshold, with what known false-positive risk, and how that affected retrieval/eval coverage. Production ingestion changes should pass `source_filter_pipeline_release_gate`.
