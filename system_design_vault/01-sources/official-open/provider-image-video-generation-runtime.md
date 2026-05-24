---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_public
provenance_status: official_provider_media_generation_docs_direct_read
sources:
  - https://developers.openai.com/api/docs/guides/image-generation
  - https://developers.openai.com/api/docs/guides/video-generation
  - https://ai.google.dev/gemini-api/docs/image-generation
  - https://docs.cloud.google.com/vertex-ai/generative-ai/docs/image/generate-images
  - https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/overview
  - https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/projects.locations.endpoints/predict
---

# Provider Image And Video Generation Runtime

## Scope

Direct-read synthesis from current official OpenAI image generation and Sora video generation docs, Google Gemini image generation docs, and Google Vertex AI Imagen/Veo docs. This note captures Agent Studio runtime and datastore implications for provider-hosted image and video generation. It stores no copied prompts, code samples, generated media, raw request bodies, or long excerpts.

Current-doc check on 2026-05-18 found the official provider docs still aligned with this note. OpenAI image generation still exposes generation/edit flows with output controls such as size, quality, format, compression, and background policy. OpenAI Sora video generation still requires job lifecycle tracking, polling or webhooks, terminal status handling, and binary content retrieval. Gemini image generation still documents SynthID watermarking and batch image generation. Vertex Imagen still exposes model/version choice, safety/person-generation settings, and parameterized image generation. Vertex Veo still documents resolution, aspect-ratio, duration, audio/dialogue, image-reference, extend/insert/remove modes, location, and responsible-AI guidance.

## Core Pattern

Provider media generation is not just another model-completion route. It creates durable public-facing artifacts with dimensions, duration, edit inputs, safety filters, provider storage behavior, watermark/provenance expectations, and QA obligations.

Agent Studio should model image and video generation as an artifact pipeline:

- source and prompt assembly;
- input media/reference validation;
- provider request and parameter snapshot;
- asynchronous operation tracking where required;
- output retrieval and artifact storage;
- safety, rights, provenance, and visual QA gates;
- human approval before publishing or reuse.

The product should never treat generated media as text response with a URL. The output is a versioned artifact with lineage, reproducibility limits, platform constraints, and disclosure requirements.

## Runtime Surfaces

Image routes include text-to-image, image editing, multi-image or reference-guided editing, masks/inpainting where supported, output format selection, quality/speed selection, compression, dimensions/aspect ratio, background or transparency options, and provider-side safety behavior.

Video routes add longer-running job semantics. Sora and Veo-style flows require operation IDs, status polling or webhooks, video content retrieval, prompt/reference media lineage, duration, aspect ratio, resolution, audio support where available, extension/edit variants, and provider storage/retrieval windows.

Google's current public docs split image behavior between Gemini native image generation and Vertex AI Imagen. Gemini image generation emphasizes conversational generation/editing, model choice, batch image generation support, and SynthID watermarking. Vertex Imagen docs also expose image-generation endpoints, deprecation/migration pressure for older Imagen endpoints, and parameterized generation/editing behavior. Vertex Veo docs expose text-to-video, first-frame image-to-video, first-and-last-frame video, ingredients/reference images, extension, insertion/removal workflows, supported resolution/aspect/duration families, region selection, and responsible-AI guidance. The Vertex REST predict reference is the common model-dependent prediction envelope for Imagen and Veo.

OpenAI's image docs expose generation and editing flows with configurable output controls such as size, quality, format, compression, and background behavior. OpenAI's video docs expose a video job lifecycle with status events and content retrieval once complete. For Agent Studio, those are datastore boundaries: media generation requests, operations, generated asset records, and retrieval events should be separate records.

## Agent Studio Design Implications

- Media generation is a side-effecting artifact route, not a pure answer route.
- Store prompt/input references and hashes; avoid storing sensitive raw prompts, uploaded images, or video bytes in notes or logs.
- Record provider/model, route release, endpoint, requested media kind, generation/edit surface, parameter snapshot, input artifact refs, mask or reference refs, output artifact refs, safety decision, and approval state.
- Treat provider-generated URLs and job IDs as transient integration state. Durable product state is the local artifact record, hash, provenance record, and QA result.
- Separate draft generation from publishable asset promotion. Drafts can be cheap/fast; published assets need visual QA, rights/consent checks, disclosure policy, and human approval.
- Image variants need set-level comparison records so reviewers can explain why one output was accepted.
- Video jobs need operation tracking, polling/webhook events, retrieval records, timeout/cancel handling, and asset-expiration policy.
- Media generation must feed content provenance, watermark/disclosure, visual-region QA, OCR/text-rendering evals, and platform crop/duration checks before public use.
- Provider endpoint deprecations and model migrations are release risks. Route cards need current supported model/endpoint evidence and sunset review dates.
- Batch image/video generation belongs in the provider batch lane only when item identity, privacy class, and result reconciliation are explicit.

## Datastore Additions

| Object | Purpose | Key fields |
|---|---|---|
| `provider_media_generation_request` | One submitted media generation or edit request | `media_request_id`, `route_release_id`, `provider`, `endpoint`, `model_ref`, `media_kind`, `surface`, `prompt_ref_hash`, `input_artifact_refs`, `reference_artifact_refs`, `mask_refs`, `requested_parameter_snapshot_id`, `privacy_class`, `created_at` |
| `media_generation_parameter_snapshot` | Reproducible provider parameter envelope without raw media | `parameter_snapshot_id`, `provider`, `model_ref`, `size_or_aspect_ratio`, `resolution`, `duration`, `quality_or_speed`, `format`, `compression`, `background_policy`, `seed_policy`, `safety_setting_refs`, `raw_request_schema_version`, `settings_hash` |
| `provider_media_generation_operation` | Async provider operation or job lifecycle | `operation_id`, `media_request_id`, `provider_operation_ref`, `status`, `poll_or_webhook_policy`, `started_at`, `completed_at`, `failed_at`, `cancelled_at`, `expires_at`, `provider_status_payload_hash` |
| `media_output_asset_record` | Generated image or video artifact after retrieval/storage | `asset_id`, `media_request_id`, `operation_id`, `artifact_id`, `variant_set_id`, `media_type`, `dimensions`, `duration`, `format`, `content_hash`, `storage_ref`, `retrieval_status`, `created_at` |
| `media_safety_filter_result` | Provider or internal safety decision for media generation | `filter_result_id`, `media_request_id`, `asset_id`, `provider`, `filter_family`, `blocked_or_allowed`, `risk_tags`, `review_required`, `override_ref`, `created_at` |
| `media_generation_variant_set` | Candidate set for comparing generated alternatives | `variant_set_id`, `media_request_id`, `variant_asset_refs`, `selection_policy`, `accepted_asset_ref`, `rejected_asset_refs`, `reviewer_rationale_ref`, `created_at` |
| `media_generation_retrieval_event` | Retrieval/download/transcode event for generated output | `retrieval_event_id`, `operation_id`, `provider_content_ref`, `retrieved_artifact_ref`, `bytes_hash`, `content_type`, `retrieved_at`, `expiration_observed`, `failure_reason` |
| `media_generation_qa_gate` | Promotion gate from generated draft to publishable asset | `qa_gate_id`, `asset_id`, `visual_eval_refs`, `text_rendering_eval_refs`, `rights_or_consent_refs`, `provenance_refs`, `platform_constraint_refs`, `human_approval_ref`, `decision`, `decided_at` |
| `provider_media_release_gate` | Route promotion gate for provider image/video generation | `gate_id`, `route_id`, `provider_model_refs`, `endpoint_refs`, `request_schema_version_refs`, `parameter_snapshot_refs`, `input_rights_consent_refs`, `privacy_class_ref`, `operation_lifecycle_refs`, `poll_webhook_policy_ref`, `retrieval_event_refs`, `output_asset_refs`, `safety_filter_refs`, `variant_set_refs`, `visual_eval_refs`, `text_rendering_eval_refs`, `provenance_disclosure_refs`, `platform_constraint_refs`, `human_approval_ref`, `deprecation_review_ref`, `fallback_route_ref`, `rollback_target_ref`, `decision`, `reviewed_at` |

## Release Gates

Do not promote a media-generation route when:

- input media rights, consent, or privacy class is unknown;
- prompts, references, masks, and output assets are not linked by artifact refs and hashes;
- provider operation state can be lost after async completion;
- generated URLs are used as durable state instead of retrieved artifact records;
- provider safety blocks or warnings are not stored;
- endpoint/model deprecation has no route-card review;
- visual QA ignores crop, text rendering, attribute binding, temporal continuity, or platform destination;
- content provenance, watermark/disclosure, and human approval are skipped for public-facing realistic media;
- batch media generation lacks item-level identity and reconciliation.
- provider-media release gates lack model/endpoint currency, request schema version, parameter snapshots, operation lifecycle, retrieved artifact hashes, safety result, visual/text QA, provenance/disclosure handoff, platform constraints, approval, fallback, and rollback evidence.

## Agent Studio Decision

Treat provider image and video generation as a governed media artifact subsystem. The route can call OpenAI, Gemini, Imagen, or Veo providers, but the durable product contract is local: request record, parameter snapshot, operation lifecycle, retrieved artifact, safety result, provenance/disclosure evidence, visual QA, and human approval before publication.

Promote provider media-generation routes only after a `provider_media_release_gate` proves the exact route can create, retrieve, store, review, and roll back generated media without relying on transient provider URLs, uncaptured job state, unsupported model parameters, missing safety output, or unapproved publishable artifacts.
