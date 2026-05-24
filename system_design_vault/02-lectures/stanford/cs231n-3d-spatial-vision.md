---
type: official-course-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_stanford_schedule_plus_open_primary_papers_canon_ready
sources:
  - https://cs231n.stanford.edu/2025/schedule.html
  - https://cs231n.stanford.edu/slides/2025/lecture_15.pdf
  - https://cs231n.stanford.edu/2024/schedule.html
  - https://cs231n.stanford.edu/slides/2024/lecture_18.pdf
  - https://arxiv.org/abs/1612.00593
  - https://arxiv.org/abs/1901.05103
  - https://arxiv.org/abs/1812.03828
  - https://arxiv.org/abs/2003.08934
related:
  - "[[cs231n-detection-segmentation-understanding]]"
  - "[[cs231n-video-understanding]]"
  - "[[../../03-patterns/vision-multimodal/visual-multimodal-qa-canon]]"
---

# CS231N - 3D And Spatial Vision

## Reading Scope

Canon-ready direct-read pass over the official CS231N 2025 and 2024 schedule entries for 3D Vision, plus primary open papers for PointNet, DeepSDF, Occupancy Networks, and NeRF. The source availability check was refreshed on 2026-05-18. The official schedules list 3D shape representations, shape reconstruction, and neural implicit representations, and link public slide PDFs; this pass records those slide links but does not claim readable slide extraction or lecture-video ingestion. It stores original synthesis only and no slide text, transcripts, or long excerpts.

## Why This Matters

Agent Studio's visual system should be ready for product shots, scene consistency, storyboard space, object relations, and generated-media edits that imply geometry. Even if the first product version handles only 2D images and videos, many user-facing content decisions are spatial: object pose, viewpoint, occlusion, depth, camera path, layout, and whether an edit respects the scene.

The 3D vision slice adds a spatial-state layer to the existing visual QA layer. The core design move is to separate 2D evidence, 3D hypotheses, and generated view/render artifacts so the system does not treat one rendered image as proof of a stable scene.

## Shape Representations

Point clouds, meshes, voxels, signed distance functions, occupancy fields, and radiance fields encode different tradeoffs. PointNet is useful as a minimal mental model because unordered point sets require permutation-invariant processing; DeepSDF and Occupancy Networks move shape into continuous implicit functions; NeRF-style representations model view-dependent appearance and scene radiance.

Agent Studio implication:

- spatial routes must record representation family instead of storing a generic "3D asset" label;
- retrieval and eval should distinguish object identity, surface geometry, occupancy, appearance, and render view;
- an artifact generated from a spatial representation needs both scene/state provenance and rendered-output provenance.

## Reconstruction And Partial Evidence

3D reconstruction often starts from partial, noisy, or view-limited observations. A single image or short clip may be enough to hypothesize a shape, but not enough to prove back-side geometry, scale, or real-world dimensions. Product workflows should therefore treat reconstructed geometry as an uncertain state estimate.

Agent Studio implication:

- store reconstruction confidence and missing-view assumptions;
- mark which views, frames, depth cues, or masks support a spatial claim;
- eval cases should include occlusion, mirror/glossy surfaces, scale ambiguity, inconsistent multi-view evidence, and impossible geometry.

## Neural Implicit Representations

DeepSDF, Occupancy Networks, and NeRF all push geometry or appearance into learned continuous functions. The product advantage is compactness and flexible rendering; the product risk is hidden state. A generated view can look plausible while encoding incorrect geometry, missing source evidence, or unstable behavior under camera movement.

Agent Studio implication:

- generated spatial media should keep the implicit model/checkpoint, camera parameters, render settings, and source views as lineage;
- visual QA should evaluate consistency across multiple views, not only a single rendered frame;
- edits to a spatial scene should invalidate dependent renders, captions, approvals, and source claims.

## Viewpoint And Camera Policy

For Agent Studio, camera path and viewpoint are product controls. Thumbnails, product demos, explainer reels, and storyboard frames all depend on where the camera is and what it can see. Spatial understanding therefore needs camera records and view contracts, not only image artifacts.

Agent Studio implication:

- store camera pose, field of view, projection/crop policy, and target platform aspect ratio;
- create eval cases for wrong viewpoint, occluded object, inconsistent scale, camera jump, and visually plausible but source-unsupported view;
- attach reviewer feedback to a view or camera path, not only to the final exported image.

## Datastore Additions

| Object | Job | Minimum fields |
|---|---|---|
| `spatial_representation_record` | Records the 3D representation used by a route or artifact | `spatial_id`, `artifact_id`, `representation_family`, `source_view_refs`, `model_or_checkpoint_ref`, `coordinate_frame`, `scale_policy`, `known_uncertainties`, `status` |
| `camera_view_record` | Viewpoint and rendering contract for spatial media | `view_id`, `spatial_id`, `camera_pose`, `field_of_view`, `projection_policy`, `crop_policy`, `platform_aspect_ratio`, `render_artifact_ref`, `created_at` |
| `reconstruction_evidence_record` | Evidence supporting a spatial or shape claim | `evidence_id`, `spatial_id`, `source_artifact_refs`, `mask_refs`, `depth_or_pose_refs`, `supported_regions`, `missing_view_assumptions`, `confidence`, `review_status` |
| `spatial_consistency_eval_case` | Eval for view, geometry, and scene consistency | `case_id`, `route_id`, `spatial_ref`, `view_refs`, `expected_consistency`, `forbidden_geometry`, `occlusion_or_scale_assertions`, `grader_policy`, `risk_level` |
| `render_lineage_record` | Lineage from spatial state to rendered media | `render_id`, `spatial_id`, `view_id`, `renderer_or_model`, `settings_hash`, `source_snapshot_id`, `output_artifact_id`, `approval_status`, `invalidated_by_refs` |
| `spatial_media_release_gate` | Promotion gate before 3D/spatial reconstruction, generated views, camera paths, product shots, or spatial edit routes affect product evidence | `gate_id`, `route_id`, `candidate_release_id`, `spatial_representation_refs`, `source_view_refs`, `source_snapshot_ref`, `camera_view_refs`, `reconstruction_evidence_refs`, `render_lineage_refs`, `coordinate_frame`, `scale_policy`, `missing_view_assumptions`, `known_uncertainties`, `geometry_claim_refs`, `view_claim_refs`, `occlusion_policy_ref`, `spatial_consistency_eval_refs`, `viewpoint_eval_refs`, `scale_ambiguity_eval_refs`, `impossible_geometry_eval_refs`, `staleness_invalidation_refs`, `fallback_route_ref`, `rollback_target_ref`, `incident_feedback_path_ref`, `decision`, `reviewed_at` |

## Release Gate Contract

A 3D/spatial route cannot promote reconstructed geometry, generated views, camera paths, spatial edits, product shots, or scene-consistency claims to product evidence unless the release binds:

- representation family, model or checkpoint, coordinate frame, scale policy, and known uncertainties;
- source views, masks, depth or pose cues, source snapshot, and missing-view assumptions;
- camera pose, field of view, projection/crop policy, platform aspect ratio, and render lineage for each generated view;
- reconstruction evidence records that distinguish observed regions from inferred or unsupported geometry;
- geometry and view claims with evidence refs, confidence, review status, and explicit source-support boundaries;
- eval cases for wrong viewpoint, occlusion, scale ambiguity, inconsistent multi-view evidence, impossible geometry, and plausible-but-source-unsupported renders;
- staleness propagation to dependent renders, captions, approvals, source claims, and spatial QA results when a representation, camera, source view, or render setting changes;
- fallback route, rollback target, reviewer decision, and incident feedback path.

## Agent Studio Design Implications

- Treat 3D and spatial media as stateful artifacts, not only rendered images.
- Generated views need camera, source-view, and render lineage before public approval.
- Scene edits should propagate staleness to renders, captions, subtitles, approvals, and eval results.
- 2D visual QA can inspect rendered frames, but spatial QA must also check geometry, view consistency, and missing evidence.
- Future 3D routes should be gated behind explicit evals because plausible spatial output can hide unsupported geometry.
- 3D reconstruction, generated-view, camera-path, spatial-edit, product-shot, and scene-consistency routes should pass a `spatial_media_release_gate` before their outputs can approve, reject, publish, or change product evidence.
