---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - "[[../../02-lectures/stanford/cs25-world-modeling-jepa]]"
  - "[[../../02-books/applied-ml-ai-engineers/applied-ml-engineering-patterns]]"
  - "[[../../02-books/probabilistic-ml-advanced/approximate-inference-shift-interpretability]]"
  - "[[../../02-books/hands-on-generative-ai/generative-media-pipelines]]"
  - "[[../../02-books/generative-deep-learning/generative-model-taxonomy-and-multimodal-controls]]"
  - "[[../../02-books/gans-in-action/gan-synthetic-media-controls]]"
  - https://cs231n.stanford.edu/2024/
  - https://cs231n.stanford.edu/2024/schedule.html
  - "[[../../02-lectures/stanford/cs231n-public-vision-notes]]"
  - "[[../../02-lectures/stanford/cs231n-vision-multimodal-source-map]]"
  - "[[../../02-lectures/stanford/cs231n-detection-segmentation-understanding]]"
  - "[[../../02-lectures/stanford/cs231n-self-supervised-visual-representations]]"
  - "[[../../02-lectures/stanford/cs231n-video-understanding]]"
  - "[[../../02-lectures/stanford/cs231n-3d-spatial-vision]]"
  - "[[../../02-lectures/stanford/cs231n-vision-language-grounding]]"
  - "[[../evaluation/prompt-workflow-eval-datasets]]"
  - "[[../security/genai-security-canon]]"
  - "[[../../01-sources/official-open/content-provenance-synthetic-media-disclosure]]"
  - "[[../../01-sources/official-open/provider-image-video-generation-runtime]]"
related:
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Visual And Multimodal QA Canon

## Scope

This canon note converts the public CS231N visual-system reading into Agent Studio product architecture. It is original synthesis only and does not store raw Stanford note text, slide text, or assignment material.

## Canon Decision

Agent Studio needs first-class visual and video records. A generated thumbnail, reel, carousel, storyboard frame, product image, or visual critique is not just text with an attached file. It has pixels, regions, objects, text, layout, temporal structure, source lineage, generation settings, approvals, and platform constraints.

The practical rule: every public-facing media artifact must be explainable from source IDs, prompt/artifact lineage, visual evidence, reviewer decisions, and publish destination.

Hands-On Generative AI adds the pipeline-level contract: generated media routes need model-card/license records, latent or pixel representation choices, scheduler/guidance/seed settings, adapter and control inputs, safety/watermark decisions, and rights/consent checks for reference media.

Generative Deep Learning adds the model-family and bridge-pattern contract: generated media routes should record whether they use diffusion, latent diffusion, autoregressive generation, GAN-style generation, VAE/autoencoder representations, music/audio event representations, or multimodal bridge patterns such as embedding priors, upsamplers, resamplers, and gated cross-attention. GANs in Action adds the critic/control layer: GAN routes need generator/discriminator evidence, mode-collapse checks, latent/conditioning controls, image-translation contracts, synthetic-data lineage, and adversarial-media evals. Visual QA should explicitly test attribute binding, rendered text, originality, and simulation transfer when a route uses generated media or learned world models.

Provider image/video generation docs add the hosted-runtime contract: provider media requests need parameter snapshots, input/reference/mask artifact refs, async operation state for video, output retrieval records, safety filter results, variant-set comparisons, and QA promotion gates before generated media becomes a publishable artifact.

Provider media route promotion needs a broader release gate than the per-asset QA gate. The release should prove provider/model and endpoint currency, request schema version, parameter snapshots, input rights/consent, privacy class, async lifecycle, polling/webhook policy, retrieval events, output hashes, safety filters, variants, visual/text QA, provenance/disclosure handoff, platform constraints, human approval, deprecation review, fallback, and rollback.

Applied ML/AI for Engineers adds the managed-vision contract: captioning, tagging, object detection, OCR, moderation, and face-related capabilities produce confidence-scored regions or category decisions that must be versioned, thresholded, and reviewed. Identity-sensitive features should be permission-gated separately from ordinary visual QA.

CS25 world-modeling adds the state-contract layer: visual and multimodal workflows need object relations, temporal state, and predicted consequences of edits. A visual route should know which region, frame, caption, source claim, and approval may change when an image or video artifact is edited.

CS231N detection and segmentation add the evidence-granularity layer: object boxes, masks, candidate sets, and visual explanations should be stored as first-class records before visual critique, editing, or publishing routes rely on them.

CS231N self-supervised learning adds the representation layer: media embeddings need objective provenance, positive/negative policy, robustness evals, cross-modal retrieval traces, and auditable refresh jobs before similarity search becomes product evidence.

CS231N video understanding adds the temporal layer: clip windows, action events, object tracks, modality traces, and temporal eval cases are required before a route claims continuity, action, pacing, subtitle alignment, or multimodal video quality.

CS231N 3D vision adds the spatial layer: representation family, camera view, reconstruction evidence, spatial consistency evals, and render lineage are required before a route treats product shots, scene edits, or generated views as stable spatial artifacts.

CS231N vision-language adds the grounding layer: captions, VQA answers, image-text retrieval, and visual claims should preserve task scope, visual evidence, source evidence, inference level, unsupported-claim flags, and reviewer outcome.

## Route Surfaces

| Surface | What can fail | Required evidence |
|---|---|---|
| Image retrieval | similar-looking but semantically wrong asset, duplicate, rights mismatch, stale source | media source record, embedding index, accepted/rejected candidates, rights filter |
| Visual critique | model flags or misses the wrong visual issue | region/frame evidence, critique rubric, reviewer override |
| Image generation | prompt drift, brand mismatch, unsafe content, bad text rendering, unsupported source claim | generation record, prompt/source refs, visual eval case, approval decision |
| Image editing | wrong object changed, crop damage, old artifact overwritten | artifact diff, edit mask/region, source image, version lineage |
| Video QA | continuity break, subtitle timing issue, unsupported visual claim, poor scene transition | shot list, frame samples, subtitle/audio refs, temporal trace |
| Publishing | unapproved public side effect or missing attribution/provenance | approval edge, content provenance record, destination record |
| Synthetic media disclosure | stripped credentials, unsupported watermark assumption, missing platform label, misleading realistic edit | C2PA manifest status, ingredient/action lineage, watermark detection event, disclosure requirement, provenance-loss event |

## Eval Cases

Visual QA evals should be stored as release assets and should include:

- object presence and count;
- spatial relation and layout;
- text legibility and typography;
- crop/aspect-ratio safety for target platform;
- brand/style fit;
- unsafe or misleading visual content;
- source-grounded visual claim support;
- temporal continuity for video;
- subtitle/audio/visual alignment;
- wrong-artifact and wrong-region edit prevention.
- distribution-shift slices for platform crop, visual style, language, image quality, camera/source domain, and reviewer-rubric changes.

These cases should inspect trace artifacts, not only final prose. A model saying "looks good" is not evidence that it checked the right regions or frames.

## Datastore Objects

The source and route ledger should add or strengthen:

| Object | Primary job | Key fields |
|---|---|---|
| `media_source_record` | Rights/provenance record for image or video sources | `media_source_id`, `source_id`, `path_or_url`, `media_type`, `rights_status`, `hash`, `dimensions`, `duration`, `format`, `allowed_use`, `created_at` |
| `visual_region` | Evidence region inside an image or frame | `region_id`, `artifact_id`, `frame_id`, `bbox`, `mask_ref`, `object_label`, `text_label`, `confidence`, `review_status` |
| `video_trace` | Temporal evidence for video workflows | `video_trace_id`, `artifact_id`, `shot_ids`, `frame_sample_ids`, `timestamp_ranges`, `subtitle_refs`, `audio_refs`, `transition_checks`, `continuity_flags` |
| `visual_eval_case` | Release-gate case for visual/media behavior | `visual_eval_case_id`, `route_id`, `artifact_refs`, `surface`, `expected_visual_behavior`, `forbidden_visual_behavior`, `region_assertions`, `temporal_assertions`, `grader_policy`, `risk_level` |
| `media_generation_record` | Generated-media lineage | `media_generation_id`, `route_id`, `prompt_variant_id`, `source_ids`, `model_provider`, `model`, `settings_hash`, `seed`, `edit_operations`, `output_artifact_id`, `approval_decision_id` |
| `provider_media_generation_operation` | Provider async image/video operation state | `operation_id`, `media_request_id`, `provider_operation_ref`, `status`, `poll_or_webhook_policy`, `started_at`, `completed_at`, `failed_at`, `cancelled_at`, `expires_at` |
| `media_output_asset_record` | Retrieved generated media artifact | `asset_id`, `media_request_id`, `operation_id`, `artifact_id`, `variant_set_id`, `media_type`, `dimensions`, `duration`, `format`, `content_hash`, `storage_ref`, `retrieval_status` |
| `media_generation_qa_gate` | Promotion gate from generated draft to public asset | `qa_gate_id`, `asset_id`, `visual_eval_refs`, `text_rendering_eval_refs`, `rights_or_consent_refs`, `provenance_refs`, `platform_constraint_refs`, `human_approval_ref`, `decision` |
| `provider_media_release_gate` | Route-level promotion gate for provider media generation | `gate_id`, `route_id`, `provider_model_refs`, `endpoint_refs`, `parameter_snapshot_refs`, `operation_lifecycle_refs`, `retrieval_event_refs`, `safety_filter_refs`, `variant_set_refs`, `qa_gate_refs`, `provenance_disclosure_refs`, `human_approval_ref`, `fallback_route_ref`, `rollback_target_ref`, `decision` |
| `publish_destination_record` | Public side-effect target | `destination_id`, `platform`, `account_scope`, `artifact_id`, `caption_artifact_id`, `approval_decision_id`, `published_at`, `rollback_or_delete_policy` |
| `media_pipeline_trace` | Full generation/edit pipeline lineage | `pipeline_trace_id`, `route_id`, `model_card_id`, `scheduler`, `guidance_scale`, `inference_steps`, `seed`, `precision`, `device`, `adapter_refs`, `control_refs`, `output_artifact_id` |
| `generation_control_record` | Explicit control input for media generation/editing | `control_id`, `route_id`, `control_type`, `source_artifact_id`, `mask_or_region_id`, `conditioning_scale`, `adapter_scale`, `composition_order`, `created_at` |
| `generative_model_profile` | Model-family contract for a generator or analyzer | `profile_id`, `model_ref`, `family`, `representation`, `objective`, `conditioning_policy`, `known_strengths`, `known_failure_modes`, `allowed_surfaces`, `status` |
| `diffusion_sampling_record` | Reproducibility and quality/latency contract for diffusion routes | `sampling_id`, `pipeline_trace_id`, `schedule`, `sampler`, `step_count`, `seed_policy`, `guidance_policy`, `denoiser_ref`, `latent_or_pixel_mode`, `ema_policy`, `eval_refs` |
| `gan_route_profile` | GAN-family generation route with generator, discriminator, latent source, conditioning policy, training/eval status, and allowed product surfaces | `gan_profile_id`, `route_id`, `generator_ref`, `discriminator_ref`, `latent_policy`, `conditioning_schema_ref`, `training_status`, `eval_refs`, `allowed_use`, `status` |
| `mode_collapse_signal` | Diversity and coverage warning for generated media | `collapse_signal_id`, `route_id`, `sample_window`, `diversity_metric`, `nearest_neighbor_summary`, `condition_coverage`, `seed_sensitivity`, `threshold`, `decision_status` |
| `conditional_generation_contract` | Expected control behavior for class, style, attribute, or domain-conditioned generation | `contract_id`, `route_id`, `condition_schema`, `allowed_values`, `attribute_binding_eval_refs`, `forbidden_attributes`, `rights_boundary`, `status` |
| `image_translation_contract` | Image-to-image transformation policy | `translation_contract_id`, `route_id`, `source_domain`, `target_domain`, `preserved_attributes`, `forbidden_changes`, `cycle_or_consistency_eval_refs`, `human_review_required` |
| `multimodal_bridge_record` | How media evidence enters a multimodal route | `bridge_id`, `route_id`, `bridge_type`, `text_encoder_ref`, `vision_or_audio_encoder_ref`, `resampler_or_prior_ref`, `cross_attention_policy`, `chunking_policy`, `known_failure_modes` |
| `upsampler_stage_record` | Super-resolution or decoder-stage lineage | `stage_id`, `pipeline_trace_id`, `stage_order`, `model_ref`, `scale_factor`, `input_artifact_id`, `output_artifact_id`, `artifact_risk_notes`, `eval_refs` |
| `attribute_binding_eval_case` | Eval for object-property binding failures | `case_id`, `route_id`, `prompt_or_input_ref`, `target_objects`, `target_attributes`, `forbidden_bindings`, `grader_policy`, `risk_level` |
| `text_rendering_eval_case` | Eval for generated or analyzed text inside media | `case_id`, `route_id`, `artifact_refs`, `required_text`, `legibility_threshold`, `semantic_correctness_policy`, `ocr_evidence_refs`, `grader_policy` |
| `media_adaptation_record` | Fine-tune or adapter lineage for media models | `adaptation_id`, `base_model_ref`, `adaptation_type`, `training_source_ids`, `rights_status`, `trigger_tokens`, `config`, `validation_prompt_refs`, `overfit_checks`, `status` |
| `model_card_record` | Model license/intended-use evidence | `model_card_id`, `model_ref`, `source_url`, `license`, `intended_use`, `limitations`, `dataset_disclosure`, `gated_access_terms`, `allowed_product_surfaces` |
| `media_watermark_record` | Generated-media provenance marker | `watermark_id`, `route_id`, `artifact_id`, `method`, `detectability`, `removal_risk`, `publication_requirement`, `created_at` |
| `c2pa_manifest_record` | Content credential state for final media | `manifest_id`, `artifact_id`, `credential_location`, `active_manifest_ref`, `signer_ref`, `claim_generator_ref`, `content_binding_type`, `validation_state`, `redaction_caveat` |
| `provenance_ingredient_edge` | Source-to-output media lineage edge | `edge_id`, `parent_artifact_id`, `ingredient_artifact_id`, `relationship`, `hash_or_binding_ref`, `rights_ref`, `consent_ref`, `transform_notes` |
| `watermark_detection_event` | Detector evidence for supported generated media | `event_id`, `artifact_id`, `watermark_family`, `detector_version`, `modality`, `confidence`, `region_or_time_range`, `supported_source_caveat`, `decision` |
| `platform_disclosure_requirement` | Platform-specific synthetic/altered media label decision | `requirement_id`, `artifact_id`, `platform`, `realism_flags`, `sensitivity_flags`, `required_label_field`, `reviewer_decision_ref`, `published_state_evidence` |
| `provenance_loss_event` | Credential or watermark loss after edit/export/transcode | `loss_event_id`, `artifact_id`, `operation_ref`, `lost_signal`, `cause`, `mitigation`, `review_status` |
| `content_provenance_release_gate` | Final-artifact promotion gate for generated media | `gate_id`, `route_id`, `artifact_revision_ref`, `source_ingredient_edge_refs`, `c2pa_or_missing_credential_refs`, `validation_event_refs`, `watermark_refs`, `disclosure_requirement_refs`, `provenance_loss_refs`, `rights_or_consent_refs`, `reviewer_approval_ref`, `fallback_or_non_publish_ref`, `rollback_policy_ref`, `decision` |
| `vision_api_result_record` | Managed vision/OCR/moderation output evidence | `result_id`, `provider`, `api_version`, `task`, `labels`, `tags`, `bounding_boxes`, `ocr_regions`, `category_scores`, `thresholds`, `source_artifact_id`, `review_status` |
| `responsible_ai_access_record` | Gate for identity-sensitive media capabilities | `access_id`, `feature`, `approval_policy`, `allowed_use`, `blocked_use`, `audit_requirement`, `escalation_owner`, `status` |
| `multimodal_state_record` | Current media/text workflow state | `state_id`, `artifact_id`, `regions`, `frames`, `ocr_spans`, `transcript_refs`, `mask_refs`, `transform_history`, `approval_refs` |
| `object_relation_record` | Relation between visual/text/workflow objects | `relation_id`, `from_object`, `to_object`, `relation_type`, `source_evidence`, `confidence`, `review_status` |
| `transition_eval_case` | Eval for media/workflow mutations | `case_id`, `initial_state`, `proposed_action`, `expected_state_delta`, `forbidden_side_effect`, `grader_policy` |
| `state_transition_release_gate` | Gate for media/workflow mutations requiring affected regions/frames/OCR/transcript/masks, invalidated approvals/evals, stale dependencies, transition evals, forbidden side effects, observed outcomes, rollback, and incident feedback. |
| `detection_result_record` | Region-level object evidence from a detector or multimodal model | `result_id`, `artifact_id`, `frame_id`, `model_ref`, `class_label`, `bbox`, `confidence`, `threshold_policy`, `postprocess_policy`, `review_status` |
| `segmentation_mask_record` | Mask-level evidence for object, region, or scene-part claims | `mask_id`, `artifact_id`, `frame_id`, `mask_ref`, `mask_type`, `class_or_instance_ref`, `source_model`, `confidence`, `edit_operation_refs`, `review_status` |
| `visual_candidate_set` | Object or region candidates before matching, suppression, or selection | `candidate_set_id`, `artifact_id`, `frame_id`, `candidate_refs`, `matching_or_suppression_policy`, `accepted_refs`, `rejected_refs`, `failure_notes` |
| `visual_explanation_record` | Reviewable evidence behind visual approval or rejection | `explanation_id`, `artifact_id`, `route_id`, `evidence_region_refs`, `method`, `decision_context`, `known_limitations`, `reviewer_outcome` |
| `region_evidence_release_gate` | Gate before boxes, masks, candidates, visual explanations, crop/edit decisions, moderation, or publishing checks become product evidence. |
| `media_embedding_profile` | Embedding route used for image/video retrieval | `profile_id`, `model_ref`, `architecture_family`, `training_objective`, `source_checkpoint`, `input_transform_policy`, `embedding_dimension`, `modality_scope`, `known_limitations`, `status` |
| `representation_eval_result` | Evidence that embeddings transfer to an Agent Studio task | `eval_id`, `profile_id`, `task_surface`, `dataset_ref`, `metric_set`, `hard_negative_policy`, `robustness_slices`, `compute_cost`, `decision_status` |
| `positive_negative_pair_record` | Pair evidence for contrastive media training or eval | `pair_id`, `anchor_ref`, `positive_ref`, `negative_ref`, `pair_source`, `augmentation_policy`, `semantic_relation`, `rights_relation`, `review_status` |
| `cross_modal_retrieval_trace` | Text-image or image-text retrieval evidence | `trace_id`, `query_ref`, `query_modality`, `target_modality`, `embedding_profile_id`, `candidate_refs`, `accepted_refs`, `rejected_refs`, `reranker_ref`, `failure_notes` |
| `embedding_refresh_job` | Auditable media embedding re-indexing run | `job_id`, `profile_id`, `source_snapshot_id`, `artifact_count`, `transform_version`, `index_version`, `started_at`, `finished_at`, `cost`, `failure_count` |
| `media_embedding_release_gate` | Gate before media embeddings or cross-modal retrieval affect product evidence, binding objective/checkpoint/transform provenance, rights filters, hard negatives, robustness slices, candidate traces, refresh lineage, fallback, and rollback. |
| `video_clip_window` | Temporal unit processed by a video route | `window_id`, `artifact_id`, `start_ms`, `end_ms`, `frame_rate`, `sampling_policy`, `stride_ms`, `overlap_policy`, `created_at` |
| `action_event_record` | Time-bounded action or event evidence | `event_id`, `artifact_id`, `window_id`, `label`, `confidence`, `actor_or_object_refs`, `evidence_frame_refs`, `motion_feature_ref`, `review_status` |
| `object_track_record` | Object or region continuity across frames | `track_id`, `artifact_id`, `object_ref`, `frame_region_refs`, `start_ms`, `end_ms`, `track_confidence`, `breakpoints`, `review_status` |
| `video_modality_trace` | Evidence bundle across frames, audio, subtitles, OCR, and transcript | `trace_id`, `artifact_id`, `clip_window_ids`, `frame_refs`, `audio_refs`, `subtitle_refs`, `ocr_refs`, `fusion_policy`, `disagreement_flags` |
| `temporal_eval_case` | Release-gate case for time-dependent video failures | `case_id`, `route_id`, `artifact_refs`, `timestamp_range`, `expected_temporal_behavior`, `forbidden_temporal_behavior`, `modality_assertions`, `grader_policy`, `risk_level` |
| `temporal_video_release_gate` | Gate before video routes claim action, continuity, pacing, subtitle alignment, multimodal agreement, generated-video quality, or publishing readiness. |
| `world_model_simulation_record` | Learned simulator evidence for media/workflow planning | `simulation_id`, `route_id`, `state_encoder_ref`, `transition_model_ref`, `controller_ref`, `temperature_or_uncertainty_policy`, `simulated_rollouts`, `real_eval_refs`, `status` |
| `simulation_exploit_check` | Test for policies exploiting model errors | `check_id`, `simulation_id`, `policy_ref`, `sim_score`, `real_score`, `gap_threshold`, `exploit_indicators`, `decision_status` |
| `music_generation_tokenization_record` | Representation contract for generated music/audio | `tokenization_id`, `route_id`, `representation_type`, `event_schema_or_codec_ref`, `temporal_resolution`, `control_attributes`, `duration_policy`, `eval_refs` |
| `audio_generation_eval_result` | Eval artifact for text-to-audio, music, or non-speech audio generation | `audio_eval_id`, `route_id`, `artifact_id`, `task_family`, `prompt_or_condition_ref`, `representation_ref`, `temporal_coherence`, `artifact_noise_flags`, `originality_refs`, `latency_tier`, `human_review_outcome` |
| `nearest_training_neighbor_check` | Originality and over-copying evidence | `check_id`, `artifact_id`, `source_scope`, `embedding_or_similarity_method`, `nearest_neighbor_refs`, `similarity_scores`, `policy_threshold`, `review_status` |
| `spatial_representation_record` | 3D representation used by a route or artifact | `spatial_id`, `artifact_id`, `representation_family`, `source_view_refs`, `model_or_checkpoint_ref`, `coordinate_frame`, `scale_policy`, `known_uncertainties`, `status` |
| `camera_view_record` | Viewpoint and rendering contract for spatial media | `view_id`, `spatial_id`, `camera_pose`, `field_of_view`, `projection_policy`, `crop_policy`, `platform_aspect_ratio`, `render_artifact_ref`, `created_at` |
| `reconstruction_evidence_record` | Evidence supporting a spatial or shape claim | `evidence_id`, `spatial_id`, `source_artifact_refs`, `mask_refs`, `depth_or_pose_refs`, `supported_regions`, `missing_view_assumptions`, `confidence`, `review_status` |
| `spatial_consistency_eval_case` | Eval for view, geometry, and scene consistency | `case_id`, `route_id`, `spatial_ref`, `view_refs`, `expected_consistency`, `forbidden_geometry`, `occlusion_or_scale_assertions`, `grader_policy`, `risk_level` |
| `render_lineage_record` | Lineage from spatial state to rendered media | `render_id`, `spatial_id`, `view_id`, `renderer_or_model`, `settings_hash`, `source_snapshot_id`, `output_artifact_id`, `approval_status`, `invalidated_by_refs` |
| `spatial_media_release_gate` | Gate before 3D/spatial reconstruction, generated views, camera paths, product shots, or spatial edit routes become product evidence. |
| `vision_language_task_record` | Task contract for captioning, VQA, alt text, or image-text retrieval | `task_id`, `route_id`, `task_type`, `input_artifact_refs`, `question_or_prompt_ref`, `expected_answer_type`, `allowed_inference_level`, `risk_level`, `status` |
| `visual_claim_record` | Source- and region-aware claim produced from visual evidence | `claim_id`, `artifact_id`, `claim_text_hash`, `claim_type`, `visible_evidence_refs`, `source_evidence_refs`, `inference_level`, `review_status` |
| `caption_artifact_record` | Generated or reviewed caption/alt-text artifact | `caption_id`, `artifact_id`, `model_ref`, `prompt_variant_id`, `visible_claim_refs`, `unsupported_claim_flags`, `accessibility_status`, `review_status` |
| `vqa_trace_record` | Question-scoped visual answer evidence | `vqa_id`, `task_id`, `question_ref`, `answer_hash`, `answer_type`, `evidence_region_refs`, `source_evidence_refs`, `confidence`, `reviewer_outcome` |
| `cross_modal_grounding_eval_case` | Eval for image-text grounding and retrieval failures | `case_id`, `route_id`, `input_refs`, `query_or_caption_ref`, `required_visual_evidence`, `required_source_evidence`, `forbidden_inference`, `grader_policy`, `risk_level` |
| `vision_language_grounding_release_gate` | Gate before captioning, VQA, alt text, image-text retrieval, OCR/question answering, or visual source-claim routes become product evidence. |

## Release Gates

A visual or multimodal route cannot be promoted unless:

- media source rights and allowed-use policy are attached;
- model card, license, and intended-use constraints are attached for the selected generator or adapter;
- generated media has lineage from source snapshot, prompt, model route, and output hash;
- generation/editing routes store scheduler, guidance, seed, control inputs, adapters, precision, and safety/watermark decisions;
- generated-media, editing, audio, adaptation, or local-media route behavior passes a `generative_media_pipeline_release_gate` proving model-card/license constraints, pipeline trace, controls/adapters, adaptation rights, audio representation and consent, local runtime feasibility, watermark/provenance, safety/rights review, fallback, and rollback;
- generated media routes store model family, representation path, bridge pattern, sampler/upscaler stages, and quality/latency sampling policy;
- generated audio and music routes retain route family, representation path, prompt or conditioning refs, temporal-coherence review, artifact/noise review, originality checks where publication or imitation risk matters, and human-review outcome before they are treated as publishable media evidence;
- generative model-family, bridge, diffusion, simulation, music/audio, or originality-sensitive routes pass a `generative_model_route_release_gate` proving model profile, representation path, sampler settings, bridge architecture, upsampler stages, public failure-mode evals, simulation transfer, originality checks, rights, fallback, and rollback;
- GAN-family, image-translation, synthetic-data, or adversarial-media routes pass a `gan_synthetic_media_release_gate` proving generator/critic profile, synthetic lineage, generator/discriminator eval, mode-collapse checks, latent control traces, conditional contracts, image-translation contracts, adversarial-media eval cases, rights review, fallback, and rollback;
- visual eval cases cover the route's public failure modes;
- visual eval cases include attribute binding, rendered text, originality, and multimodal alignment when those risks apply;
- managed vision/OCR/moderation calls store API version, confidence semantics, thresholds, regions, and reviewer decisions;
- identity-sensitive features are permission-gated and audited separately from general media analysis;
- video routes attach frame/shot/subtitle timing evidence;
- object-detection and segmentation routes retain candidate sets, boxes, masks, confidence, threshold policy, and matching or suppression policy;
- detection, segmentation, crop, edit, visual approval, and publish routes pass a region-evidence release gate before object or mask evidence can approve, reject, edit, crop, moderate, or publish an artifact;
- media embedding routes retain objective, transforms, checkpoint/source, hard-negative evals, robustness slices, index version, and refresh history;
- media embedding and cross-modal retrieval routes pass a media-embedding release gate before similarity scores become source, edit, duplicate, style, storyboard, or rights evidence;
- video routes retain clip-window policy, frame sampling, object tracks, action events, modality-fusion policy, and temporal eval coverage;
- video routes pass a temporal-video release gate before claiming action, continuity, pacing, subtitle alignment, audio/visual agreement, generated-video quality, or publishing readiness;
- learned-world or simulation routes prove simulated wins transfer to real workflow outcomes and do not exploit model errors;
- spatial routes retain representation family, source views, camera policy, reconstruction confidence, render lineage, and consistency eval coverage;
- 3D/spatial reconstruction, generated-view, camera-path, product-shot, and spatial-edit routes pass a spatial media release gate before they approve, reject, publish, or change product evidence;
- vision-language routes retain task type, prompt/question, evidence regions, source evidence, unsupported-claim flags, and cross-modal grounding eval coverage;
- captioning, VQA, alt-text, image-text retrieval, OCR/question answering, and visual source-claim routes pass a vision-language grounding release gate before they approve, reject, publish, or change source evidence;
- editing routes prove they changed the intended region or artifact;
- editing and generation routes predict which captions, approvals, evals, and source claims become stale;
- public publishing requires approval and content provenance;
- sensitive or brand-critical outputs have human review.

## Agent Studio Implications

- The UI should expose visual evidence alongside critique text: regions, frames, diffs, and source thumbnails.
- Retrieval should support text, image, and hybrid media search with accepted/rejected candidates.
- Route permissions should separate critique, generation, editing, and publishing.
- User reference images, styles, faces, and voice/media samples should be treated as high-sensitivity sources with explicit consent scope.
- Visual explanations should name their decision context: debugging, reviewer override, user recourse, safety inspection, or artifact critique.
- Visual failures should create eval cases just like text hallucinations or unsafe tool calls.
- The datastore should be ready for future 3D/spatial media, but image/video records are the immediate production need.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-whole-part-hierarchies]] - Stanford CS25, "Whole-Part Hierarchies in a Neural Network" ([YouTube](https://www.youtube.com/watch?v=CYaju6aCMoQ)).
- [[../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
