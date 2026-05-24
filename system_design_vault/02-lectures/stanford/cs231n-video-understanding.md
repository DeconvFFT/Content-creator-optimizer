---
type: official-course-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_stanford_schedule_plus_open_primary_papers
sources:
  - https://cs231n.stanford.edu/2025/schedule.html
  - https://cs231n.stanford.edu/slides/2025/lecture_10.pdf
  - https://cs231n.stanford.edu/2024/schedule.html
  - https://arxiv.org/abs/1406.2199
  - https://arxiv.org/abs/1412.0767
  - https://arxiv.org/abs/1705.07750
  - https://arxiv.org/abs/1711.11248
related:
  - "[[cs231n-detection-segmentation-understanding]]"
  - "[[cs231n-self-supervised-visual-representations]]"
  - "[[../../03-patterns/vision-multimodal/visual-multimodal-qa-canon]]"
---

# CS231N - Video Understanding

## Reading Scope

Canon-ready direct read of the official CS231N 2025 and 2024 schedule entries for video understanding, plus open primary papers for two-stream action recognition, C3D, I3D/Kinetics, and R(2+1)D spatiotemporal convolutions, rechecked on 2026-05-18. The 2025 schedule links a public Lecture 10 slide PDF, but the browser fetch did not expose readable PDF text in this pass; this note therefore does not claim a full slide extraction or lecture-video pass. It stores original synthesis only and no slide text, transcripts, or long excerpts.

## Why This Matters

Agent Studio is a content studio, so video is not just a stack of independent frames. Reels, shorts, demos, walkthroughs, and generated clips have temporal claims: actions unfold, edits change continuity, subtitles align or drift, and visual evidence can appear for only a few frames.

The CS231N video-understanding slice is useful because it separates spatial appearance, temporal motion, clip-level representation, and multimodal signals. That maps directly to Agent Studio's need for frame evidence, shot-level state, action/event records, and temporal eval cases.

## Spatial And Temporal Streams

The two-stream action-recognition line separates appearance from motion. A spatial stream sees what is in frames; a temporal stream models movement between frames. For Agent Studio, this distinction prevents a common product bug: approving a clip because individual frames look correct while the action, transition, or gesture is wrong.

Agent Studio implication:

- video QA should store both frame appearance evidence and motion/transition evidence;
- action or gesture claims need temporal windows, not single-frame screenshots;
- reviewer feedback should be attachable to a shot, timestamp range, object track, subtitle span, or transition.

## 3D Convolutions And Clip Windows

C3D and related 3D convolution approaches treat space and time jointly over clips. The product lesson is that windowing policy matters. Too short a clip misses context; too long a clip increases cost and can blur the event being evaluated.

Agent Studio implication:

- every video route should declare its clip-window policy: frame rate, window length, stride, overlap, and sampling strategy;
- evals should include failures for action missed due to poor sampling, transition cut too early, subtitle off by a short offset, and stale scene context;
- embedding and retrieval records for video should include clip boundaries, not only whole-file vectors.

## I3D, Kinetics, And Pretraining Transfer

I3D inflates successful image architectures into spatiotemporal models and uses a larger action dataset to improve transfer. The Agent Studio design takeaway is that video routes inherit both representation strengths and dataset assumptions. A model trained for action classification is not automatically a reliable judge for brand continuity, source grounding, text legibility, or social-platform pacing.

Agent Studio implication:

- model cards for video routes should include pretraining dataset, task family, modality inputs, and expected failure slices;
- transfer into Agent Studio requires route-specific evals for reels, slides, captions, faces/identity-sensitive content, and generated media artifacts;
- public-facing video decisions should require human review when the model's training task differs from the product decision.

## Factorized Spatiotemporal Models

R(2+1)D-style factorization separates spatial and temporal convolution. For system design, the important point is that temporal modeling is not a monolith: it can be represented through explicit streams, 3D kernels, factorized operations, recurrence, attention, or multimodal fusion. Route metadata must preserve which one is being used because each has different latency, memory, and failure behavior.

Agent Studio implication:

- video route registry entries need architecture family and temporal modeling strategy;
- capacity estimates must separate frame extraction cost, encoding cost, temporal aggregation cost, audio/subtitle processing, and reviewer rendering cost;
- fallback routes should be explicit: frame-only QA, sampled-frame QA, full temporal model, or human review.

## Multimodal Video Understanding Boundary

The CS231N schedules name multimodal video understanding, but this note does not claim a deep pass over a specific multimodal video lecture transcript. For Agent Studio, the immediate architecture implication is still clear: video QA should join frames, OCR/text overlays, audio, subtitles, transcript spans, and source claims into a single trace.

Agent Studio implication:

- store modality-specific evidence first, then fuse it;
- every fused video judgment should preserve which modalities contributed;
- disagreement between audio, captions, and visual evidence should create an eval case instead of being averaged away.

## Datastore Additions

| Object | Job | Minimum fields |
|---|---|---|
| `video_clip_window` | Defines the temporal unit processed by a video route | `window_id`, `artifact_id`, `start_ms`, `end_ms`, `frame_rate`, `sampling_policy`, `stride_ms`, `overlap_policy`, `created_at` |
| `action_event_record` | Time-bounded action or event evidence | `event_id`, `artifact_id`, `window_id`, `label`, `confidence`, `actor_or_object_refs`, `evidence_frame_refs`, `motion_feature_ref`, `review_status` |
| `object_track_record` | Object or region continuity across frames | `track_id`, `artifact_id`, `object_ref`, `frame_region_refs`, `start_ms`, `end_ms`, `track_confidence`, `breakpoints`, `review_status` |
| `video_modality_trace` | Evidence bundle across frames, audio, subtitles, OCR, and transcript | `trace_id`, `artifact_id`, `clip_window_ids`, `frame_refs`, `audio_refs`, `subtitle_refs`, `ocr_refs`, `fusion_policy`, `disagreement_flags` |
| `temporal_eval_case` | Release-gate case for time-dependent video failures | `case_id`, `route_id`, `artifact_refs`, `timestamp_range`, `expected_temporal_behavior`, `forbidden_temporal_behavior`, `modality_assertions`, `grader_policy`, `risk_level` |
| `temporal_video_release_gate` | Promotion gate before a route claims action, continuity, pacing, subtitle alignment, or multimodal video quality | `gate_id`, `route_id`, `video_clip_window_refs`, `action_event_refs`, `object_track_refs`, `video_modality_trace_refs`, `temporal_eval_case_refs`, `sampling_policy_ref`, `fusion_policy_ref`, `modality_disagreement_policy_ref`, `fallback_route_ref`, `rollback_target_ref`, `decision` |

## Agent Studio Design Implications

- Video QA needs timestamped evidence, not only final prose.
- Frame-only checks are useful fallbacks but should not be labeled as temporal understanding.
- Reels/shorts evals should include continuity, action timing, subtitle alignment, transition quality, visual-source grounding, and audio/visual disagreement.
- Video embedding and retrieval indexes should be clip-aware and refreshable by source snapshot.
- Public video publishing should require provenance, approval, and rollback metadata just like generated images and text artifacts.
- Promote video routes only after a `temporal_video_release_gate` proves clip windows, frame sampling, action/event evidence, object tracks, modality traces, temporal evals, disagreement handling, fallback, and rollback.

## Release Gate Contract

`temporal_video_release_gate` is required before Agent Studio promotes routes that claim action recognition, temporal continuity, pacing, transition quality, subtitle alignment, audio/visual agreement, storyboard continuity, generated-video quality, or public video publishing readiness.

The gate rejects promotion unless the release record binds:

- clip-window policy with start/end times, frame rate, stride, overlap, sampling policy, and source artifact snapshot;
- action/event records with timestamp range, actor/object refs, evidence frames, motion features, confidence policy, and review status;
- object-track records tying boxes, masks, regions, or entities across frames with breakpoints and track confidence;
- modality trace covering frames, audio, subtitles, OCR, transcript spans, source claims, fusion policy, and disagreement flags;
- temporal eval cases for missed actions, wrong transition, subtitle offset, stale scene context, audio/visual mismatch, flicker, continuity break, poor pacing, and unsupported visual claim;
- fallback route decision among frame-only QA, sampled-frame QA, full temporal model, or human review;
- provenance, approval, rollback target, and incident feedback path for public video or generated-video routes.
