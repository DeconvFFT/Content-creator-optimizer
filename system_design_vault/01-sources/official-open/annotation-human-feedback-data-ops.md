---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://labelstud.io/guide/
  - https://labelstud.io/guide/project_settings
  - https://labelstud.io/guide/predictions
  - https://labelstud.io/guide/ml
  - https://labelstud.io/guide/storage
  - https://labelstud.io/guide/export
  - https://docs.argilla.io/latest/
  - https://docs.argilla.io/latest/how_to_guides/dataset/
  - https://docs.argilla.io/latest/how_to_guides/annotate/
  - https://docs.argilla.io/latest/how_to_guides/query/
  - https://docs.snorkel.ai/docs/25.4/user-guide/intro/what-is-snorkel-flow/
  - https://docs.snorkel.ai/docs/25.4/user-guide/intro/active-learning-weak-supervision
---

# Annotation And Human Feedback Data Ops

## Direct-Read Scope

This note synthesizes official Label Studio, Argilla, and Snorkel Flow documentation for annotation projects, task distribution, pre-annotations/suggestions, model-assisted labeling, external storage, exports, active learning, weak supervision, and SME feedback loops. It stores original Agent Studio implications only.

Current-doc check on 2026-05-18: Label Studio project settings still expose project identity, task sampling, labeling instructions, live predictions, connected models, training triggers, predictions, cloud storage, webhooks, and destructive project actions. Its storage and export docs keep source storage, target storage, raw annotation JSON, task files, regions, results, and export-format caveats explicit. Argilla still models datasets through guidelines, fields, questions, distribution policy, record status queues, metadata/suggestion/response filters, and draft/submitted/discarded states. Snorkel Flow still distinguishes active-learning expert selection from weak-supervision sources such as heuristics, crowds, and existing models.

## Core Takeaway

Human feedback is product data, not a comment field. Annotation projects need versioned task definitions, instructions, question schemas, examples, assignment policy, annotator roles, pre-annotation sources, model/backend versions, response state, export format, and downstream dataset promotion rules. Otherwise feedback cannot safely drive evals, route changes, preference tuning, retrieval audits, or source-quality improvements.

## Annotation Project Contract

An annotation task is a configured workflow:

- project/workspace identity and owner;
- input fields and media/source refs;
- question schema: label, multi-label, ranking, rating, span, text, or custom;
- guidelines and per-question instructions;
- required responses and task-distribution policy;
- metadata and vector fields used for filtering, similarity search, or sampling;
- pending/draft/submitted/discarded status;
- export format and downstream dataset target.

Agent Studio should treat the annotation schema as a release artifact. Changing a rubric, label set, rating scale, span boundary rule, or minimum-response count changes the meaning of every later metric and preference record.

## Pre-Annotation And Suggestions

Pre-annotations and suggestions accelerate review, but they also bias annotators and create hidden model influence. Store the suggestion source separately from the final human response:

- suggesting model/backend or labeling function;
- model version and prompt/schema if an LLM produced the suggestion;
- confidence or score if available;
- whether the suggestion was visible by default;
- whether the reviewer accepted, edited, rejected, or ignored it;
- final response and reviewer identity class.

For Agent Studio, this matters for source extraction audits, visual region labels, preference-pair creation, RAG relevance judgments, guardrail labels, and route-trace grading.

## Active Learning And Weak Supervision

Snorkel's data-development framing is useful because it separates three kinds of supervision:

- direct expert labels for ground truth and correction;
- weak labels from heuristics, rules, models, crowds, or LLM prompts;
- active-learning batches chosen because the model is uncertain or the slice is informative.

Agent Studio should not collapse these into one `label` table. A weak label, human correction, model suggestion, SME comment, and final promoted dataset example have different trust levels and reproducibility requirements.

## Source And Storage Boundaries

Labeling tools often connect to external storage and export annotation JSON or per-task files. Agent Studio should preserve object refs, not copy raw source bodies into notes. Annotation exports need hashes, source snapshot refs, storage policy, task IDs, and parser/export-version metadata so downstream evals and tuning datasets can be rebuilt.

## Agent Studio Design Implications

- Add `annotation_project`, `annotation_schema_version`, `annotation_task`, `annotation_response`, and `annotation_export_manifest` records.
- Add `preannotation_suggestion` records for ML backend predictions, LLM suggestions, labeling-function outputs, and imported predictions.
- Add `annotation_assignment_policy` and `annotator_profile` records so response counts, reviewer class, role, expertise, and conflict policy are explicit.
- Add `active_learning_batch` and `weak_label_source` records before using feedback for tuning or eval promotion.
- Keep annotation queues connected to trace/span feedback, but do not assume every annotation is an eval case until promotion status is recorded.
- Treat reviewer guidelines and label schemas as versioned release artifacts; stale or changed rubrics require separate assessment runs.

## Annotation Data Release Gate

Feedback should affect evals, tuning, source-quality filters, route releases, or retrieval/ranking policies only after an `annotation_data_release_gate` is approved. The gate should bind `route_id`, annotation project, schema version, guideline version, assignment policy, annotator profiles, task samples, pre-annotation suggestion lineage and visibility, active-learning batches, weak-label sources, export manifest, storage policy, disagreement review, draft/discard filters, dataset-promotion policy, selection-bias caveats, spot-review evidence, downstream-use policy, rollback or deprecation target, decision, and review time.

This gate makes the key product distinction durable: independent SME labels, model-assisted human edits, accepted suggestions, weak labels, active-learning samples, drafts, discarded responses, and promoted dataset examples are related but not interchangeable evidence.

## Agent Studio Failure Modes To Avoid

- Treating accepted model suggestions as independent human labels.
- Mixing ranking, rating, span, and free-text feedback in one untyped feedback table.
- Updating label schema without invalidating old metric comparisons.
- Training or tuning on unresolved drafts, discarded records, or unreviewed weak labels.
- Losing region/span IDs during export, making visual/document evidence unreplayable.
- Hiding annotator disagreement behind an averaged score.
- Using active-learning batches for unbiased assessment without marking the selection bias.
