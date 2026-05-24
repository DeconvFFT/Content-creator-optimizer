---
type: official-course-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_stanford_public_slides_assignment_and_open_primary_papers
sources:
  - https://cs231n.stanford.edu/2025/schedule.html
  - https://cs231n.stanford.edu/slides/2025/lecture_12.pdf
  - https://cs231n.github.io/assignments2025/assignment3/
  - https://arxiv.org/abs/2002.05709
  - https://arxiv.org/abs/1911.05722
  - https://arxiv.org/abs/1807.03748
  - https://arxiv.org/abs/2104.14294
  - https://arxiv.org/abs/2111.06377
  - https://arxiv.org/abs/2103.00020
related:
  - "[[cs231n-public-vision-notes]]"
  - "[[cs231n-detection-segmentation-understanding]]"
  - "[[../../03-patterns/vision-multimodal/visual-multimodal-qa-canon]]"
  - "[[../../03-patterns/retrieval/reranking-search-kg-patterns]]"
---

# CS231N - Self-Supervised Visual Representations

## Reading Scope

Canon-ready direct read of the official CS231N 2025 schedule entry, public Lecture 12 slide deck on self-supervised learning, and the public Assignment 3 page that names transformer captioning, self-supervised image classification, diffusion, CLIP, and DINO as implementation targets, rechecked on 2026-05-18. This note cross-checks the lecture arc against primary open papers for SimCLR, MoCo, CPC, DINO, MAE, and CLIP. It stores original synthesis only and does not store slide text, notebook code, assignment solutions, video transcripts, or long excerpts.

## Why This Matters

Agent Studio needs media retrieval and visual QA that work when human labels are sparse. Self-supervised visual representation learning is the systems answer: use structure inside images, augmentations, temporal continuity, or image-text pairs to build embeddings that transfer to downstream tasks.

The design lesson is not "train a self-supervised model now." It is that every media embedding route needs an objective, augmentation policy, evaluation protocol, and downstream task contract. Otherwise visual similarity search will look plausible while retrieving the wrong objects, styles, rights category, or edit references.

## Pretext Tasks And Downstream Utility

The lecture starts from the label bottleneck: large-scale supervised training needs many labeled examples, while self-supervised methods generate learning targets from the data itself. Rotation prediction, inpainting, patch rearrangement, colorization, and video color propagation force encoders to learn structure that can transfer to classification, detection, segmentation, or tracking.

Agent Studio implication:

- treat "embedding model" as a learned representation with an objective, not as a generic vectorizer;
- record the pretext or pretraining objective that produced a media embedding route;
- evaluate embeddings on the actual downstream workflow: asset retrieval, object-region recall, style matching, edit-reference matching, visual duplicate detection, or storyboard continuity.

## Evaluation Protocol For Representations

The lecture separates pretext-task performance from representation quality. A representation can be good for downstream work even if the pretext task itself is not the product task. It also highlights linear evaluation, clustering, transfer, robustness, generalization, and compute cost.

Agent Studio implication:

- media embedding releases need held-out retrieval and downstream evals, not only nearest-neighbor demos;
- track robustness slices for crop, color, compression, platform aspect ratio, screenshot quality, typography, and generated-versus-real images;
- store compute and memory profile for embedding refresh jobs because media corpora can be expensive to re-index.

## Contrastive Learning As Retrieval Infrastructure

Contrastive learning reframes representation learning as matching positives against negatives. SimCLR depends heavily on augmentation and large batches; MoCo uses a momentum-updated encoder and a queue so negative sample count can be decoupled from mini-batch size; CPC extends contrastive prediction to ordered or temporal signals.

Agent Studio implication:

- retrieval quality depends on how positives and negatives were defined during training or adaptation;
- contrastive media evals should include hard negatives: same style but wrong object, same object but wrong rights, same text overlay but wrong visual, and same scene but wrong timestamp;
- video and storyboard routes should use temporal positives and negatives, not only image-level similarity.

## DINO, MAE, And Attention-Like Evidence

DINO-style self-distillation and masked autoencoding show that useful visual structure can emerge without manual labels. For Agent Studio, the important idea is that representation learning can produce object- or region-sensitive behavior that supports downstream retrieval, localization, and review, but only if the route stores enough evidence to audit what the representation is doing.

Agent Studio implication:

- store embedding provenance with architecture family, objective, checkpoint/source, input transforms, and known limitations;
- connect media embeddings to visual regions or masks when they are used for object-level claims;
- do not treat a high-similarity vector match as source-grounded evidence unless it links back to a visible artifact, region, frame, or approved source.

## CLIP And Image-Text Alignment Boundary

The public Assignment 3 page names CLIP and DINO as representation methods students implement. CLIP matters for Agent Studio because it aligns text and image embeddings, making text-to-image retrieval and image-to-text search possible. This note uses the assignment page and primary CLIP paper as source signals, but it does not claim a full CLIP lecture-video pass.

Agent Studio implication:

- cross-modal retrieval should store both the text query and image evidence that produced a match;
- image-text embeddings need bias, spurious-correlation, and prompt-sensitivity evals;
- visual claims generated from CLIP-style retrieval still need downstream verification before public use.

## Datastore Additions

| Object | Job | Minimum fields |
|---|---|---|
| `media_embedding_profile` | Defines the embedding route used for image/video retrieval | `profile_id`, `model_ref`, `architecture_family`, `training_objective`, `source_checkpoint`, `input_transform_policy`, `embedding_dimension`, `modality_scope`, `known_limitations`, `status` |
| `representation_eval_result` | Measures whether embeddings transfer to Agent Studio tasks | `eval_id`, `profile_id`, `task_surface`, `dataset_ref`, `metric_set`, `hard_negative_policy`, `robustness_slices`, `compute_cost`, `decision_status` |
| `positive_negative_pair_record` | Training/eval pair evidence for contrastive media routes | `pair_id`, `anchor_ref`, `positive_ref`, `negative_ref`, `pair_source`, `augmentation_policy`, `semantic_relation`, `rights_relation`, `review_status` |
| `cross_modal_retrieval_trace` | Text-image or image-text retrieval evidence | `trace_id`, `query_ref`, `query_modality`, `target_modality`, `embedding_profile_id`, `candidate_refs`, `accepted_refs`, `rejected_refs`, `reranker_ref`, `failure_notes` |
| `embedding_refresh_job` | Auditable re-indexing run for media embeddings | `job_id`, `profile_id`, `source_snapshot_id`, `artifact_count`, `transform_version`, `index_version`, `started_at`, `finished_at`, `cost`, `failure_count` |
| `media_embedding_release_gate` | Promotion gate before a media embedding, self-supervised, or cross-modal retrieval route affects product evidence | `gate_id`, `route_id`, `media_embedding_profile_ref`, `source_snapshot_ref`, `positive_negative_pair_refs`, `hard_negative_policy_ref`, `representation_eval_refs`, `cross_modal_retrieval_trace_refs`, `robustness_slice_refs`, `rights_filter_ref`, `embedding_refresh_job_ref`, `accepted_rejected_candidate_policy_ref`, `fallback_route_ref`, `rollback_target_ref`, `decision` |

## Agent Studio Design Implications

- Use self-supervised and cross-modal representations as retrieval infrastructure, not as unreviewed truth.
- Every media embedding route needs an eval contract with hard negatives and robustness slices.
- Visual similarity search should expose accepted and rejected candidates so reviewers can correct the embedding space.
- Cross-modal retrieval should feed source-grounded visual QA, not bypass it.
- Media embedding refreshes are data migrations: they need source snapshots, index versions, eval deltas, rollback, and stale-reference handling.
- Promote media embedding or cross-modal retrieval changes only after a `media_embedding_release_gate` proves objective provenance, transform/checkpoint identity, hard-negative coverage, robustness slices, rights filtering, candidate traceability, refresh job lineage, fallback, and rollback.

## Release Gate Contract

`media_embedding_release_gate` is required before Agent Studio promotes image/video embeddings, self-supervised visual representations, CLIP/DINO-style cross-modal retrieval, visual duplicate detection, style matching, storyboard-continuity search, or media embedding refresh jobs into production evidence.

The gate rejects promotion unless the release record binds:

- embedding profile with architecture family, training objective, checkpoint/source, transform policy, dimension, modality scope, and known limitations;
- source snapshot, rights filter, privacy/sensitivity class, and blocked-use policy for every indexed media collection;
- positive/negative pair policy, hard-negative set, augmentation policy, semantic relation, and rights relation used for evals or adaptation;
- representation eval results on Agent Studio task surfaces: asset retrieval, object/region recall, style match, edit-reference match, visual duplicate detection, storyboard continuity, and cross-modal search;
- robustness slices for crop, color, compression, screenshot quality, platform aspect ratio, generated-versus-real media, typography, text overlays, and temporal sampling where relevant;
- cross-modal retrieval traces preserving text/image query, candidate refs, accepted and rejected candidates, reranker refs, and failure notes;
- embedding refresh job lineage with source snapshot, transform version, index version, artifact count, failure count, cost, eval delta, stale-reference handling, fallback route, and rollback target.
