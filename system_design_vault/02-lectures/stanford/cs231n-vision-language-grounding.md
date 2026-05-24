---
type: official-course-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_stanford_schedule_plus_open_primary_papers_canon_ready
sources:
  - https://cs231n.stanford.edu/2025/schedule.html
  - https://cs231n.stanford.edu/slides/2025/lecture_16.pdf
  - https://cs231n.stanford.edu/2024/schedule.html
  - https://arxiv.org/abs/1411.4555
  - https://arxiv.org/abs/1505.00468
  - https://arxiv.org/abs/1707.07998
  - https://arxiv.org/abs/2103.00020
related:
  - "[[cs231n-self-supervised-visual-representations]]"
  - "[[cs231n-detection-segmentation-understanding]]"
  - "[[../../03-patterns/vision-multimodal/visual-multimodal-qa-canon]]"
  - "[[../../03-patterns/retrieval/reranking-search-kg-patterns]]"
---

# CS231N - Vision Language And Grounding

## Reading Scope

Canon-ready direct-read pass over the official CS231N 2025 schedule entry for Vision and Language, the official 2024 schedule cross-check, and primary open papers for image captioning, visual question answering, bottom-up/top-down attention for captioning and VQA, and CLIP-style language-supervised image-text representation learning. The source availability check was refreshed on 2026-05-18. The 2025 schedule links a public Lecture 16 slide PDF, but this pass records the link without claiming readable slide extraction or gated lecture-video ingestion. It stores original synthesis only and no slide text, transcripts, copied captions, or long excerpts.

## Why This Matters

Agent Studio will produce and critique media with language attached: prompts, captions, thumbnails, alt text, storyboard beats, subtitles, source claims, and reviewer comments. Vision-language systems are the bridge between visual evidence and natural-language decisions, but they are also a major hallucination surface. A fluent caption or answer can be unsupported by the image region, source record, or user intent.

The product rule: every vision-language output should be linked to visual evidence, source context, and the question or task that caused it.

## Captioning Is Not Grounding

Image captioning turns a visual artifact into language, but a caption can omit important details, overgeneralize, or mention plausible objects that are not actually present. For Agent Studio, captioning is useful as a draft, index signal, or accessibility aid, but it is not sufficient evidence for object presence, safety, rights, or publication decisions.

Agent Studio implication:

- store generated captions as artifacts with model, prompt, image/source, and review status;
- keep caption claims separate from verified visual claims;
- evaluate captions for supported content, missing critical details, unsafe omission, platform fit, and source claim leakage.

## VQA Requires Question-Scoped Evidence

Visual question answering is not generic image understanding. The answer depends on the question, the relevant region, the expected answer type, and the dataset or product context. For Agent Studio, this means a visual QA route must preserve the question and the evidence path, not only the final answer.

Agent Studio implication:

- store question, expected answer type, evidence regions, answer, confidence, and reviewer outcome together;
- create eval slices for yes/no questions, counting, spatial relations, OCR/text questions, temporal questions, and source-grounding questions;
- reject reuse of one VQA answer across different product decisions unless the evidence and question match.

## Region Attention And Fine-Grained Claims

Bottom-up/top-down attention connects detection-style region proposals with language generation or answering. The practical value is that language can be grounded in region candidates rather than a single global image embedding. This fits Agent Studio's existing detection and segmentation records: visual language should point to regions, masks, frames, or object tracks whenever possible.

Agent Studio implication:

- captioning and VQA traces should reference `detection_result_record`, `visual_region`, `segmentation_mask_record`, or `object_track_record` IDs;
- model explanations should identify which visual evidence was used, not only provide text rationales;
- evals should include wrong-region support and region-missing failure cases.

## CLIP-Style Image-Text Retrieval

CLIP-style representation learning enables text-to-image and image-to-text retrieval, zero-shot labeling, and broad cross-modal search. It is powerful infrastructure for Agent Studio asset search, but it should not be treated as proof. Text-image similarity can reflect dataset bias, prompt sensitivity, spurious correlations, or missing visual details.

Agent Studio implication:

- cross-modal retrieval traces should preserve the text query, image candidates, scores, accepted/rejected candidates, and reranker/reviewer decisions;
- prompt wording for retrieval should be versioned and evaluated because small prompt changes can change candidate ranking;
- public claims should require downstream verification against visual evidence and source records, not only CLIP similarity.

## Grounding And Source Claims

A content studio combines visual and textual sources. A thumbnail, reel frame, or visual explanation may refer to a paper, company logo, product UI, chart, or book claim. Vision-language grounding therefore has two axes: grounding in pixels and grounding in source records.

Agent Studio implication:

- a visual claim should link to both media evidence and source evidence when it says something factual;
- captions and alt text should separate visible facts from inferred interpretation;
- conflict between image evidence and source text should create a review item rather than being smoothed into a single answer.

## Datastore Additions

| Object | Job | Minimum fields |
|---|---|---|
| `vision_language_task_record` | Captures the task contract for captioning, VQA, alt text, or image-text retrieval | `task_id`, `route_id`, `task_type`, `input_artifact_refs`, `question_or_prompt_ref`, `expected_answer_type`, `allowed_inference_level`, `risk_level`, `status` |
| `visual_claim_record` | Source- and region-aware claim produced from visual evidence | `claim_id`, `artifact_id`, `claim_text_hash`, `claim_type`, `visible_evidence_refs`, `source_evidence_refs`, `inference_level`, `review_status` |
| `caption_artifact_record` | Generated or reviewed caption/alt-text artifact | `caption_id`, `artifact_id`, `model_ref`, `prompt_variant_id`, `visible_claim_refs`, `unsupported_claim_flags`, `accessibility_status`, `review_status` |
| `vqa_trace_record` | Question-scoped visual answer evidence | `vqa_id`, `task_id`, `question_ref`, `answer_hash`, `answer_type`, `evidence_region_refs`, `source_evidence_refs`, `confidence`, `reviewer_outcome` |
| `cross_modal_grounding_eval_case` | Eval for image-text grounding and retrieval failures | `case_id`, `route_id`, `input_refs`, `query_or_caption_ref`, `required_visual_evidence`, `required_source_evidence`, `forbidden_inference`, `grader_policy`, `risk_level` |
| `vision_language_grounding_release_gate` | Promotion gate before captioning, VQA, alt text, image-text retrieval, OCR/question answering, or visual source-claim routes can affect product evidence | `gate_id`, `route_id`, `candidate_release_id`, `vision_language_task_ref`, `input_artifact_refs`, `source_snapshot_ref`, `question_or_prompt_ref`, `expected_answer_type`, `allowed_inference_level`, `risk_level`, `visible_evidence_refs`, `region_or_mask_refs`, `frame_or_object_track_refs`, `visual_claim_refs`, `caption_artifact_refs`, `unsupported_claim_flags`, `vqa_trace_refs`, `cross_modal_retrieval_trace_refs`, `source_evidence_refs`, `forbidden_inference_policy_ref`, `cross_modal_grounding_eval_refs`, `fallback_route_ref`, `rollback_target_ref`, `decision`, `reviewed_at` |

## Release Gate Contract

A captioning, VQA, alt-text, image-text retrieval, OCR/text visual QA, or visual source-claim route cannot promote to product evidence unless the release binds:

- task type, prompt or question, expected answer type, allowed inference level, and risk level;
- input artifacts, source snapshot, and visual evidence refs for regions, masks, frames, or object tracks;
- visual claim records that separate directly visible facts, inferred interpretation, and source-backed factual claims;
- caption or alt-text artifacts with visible-claim refs, unsupported-claim flags, accessibility review, and reviewer outcome;
- VQA traces with question, answer type, evidence-region refs, source-evidence refs, confidence, and reviewer outcome;
- cross-modal retrieval traces with query, candidate set, accepted and rejected candidates, scores, reranker, and reviewer decisions;
- source-evidence refs whenever a visual output makes factual or source-backed claims;
- eval coverage for wrong-region support, unsupported captions, prompt-sensitive retrieval, OCR/text, counting, spatial relations, and image/source conflict;
- forbidden-inference policy, fallback route, rollback target, and incident feedback path.

## Agent Studio Design Implications

- Vision-language routes must preserve the question, prompt, evidence regions, and source context behind every answer.
- Captions are useful retrieval/accessibility artifacts, but unsupported caption claims need review before publication.
- Cross-modal retrieval should feed visual QA and source verification rather than bypassing them.
- Visual claims should distinguish directly visible facts, reasonable visual inferences, and source-backed factual claims.
- Multimodal evals should include wrong-region, unsupported-caption, prompt-sensitive retrieval, OCR/text, counting, spatial-relation, and source-conflict cases.
- Captioning, VQA, alt-text, image-text retrieval, OCR/question answering, and visual source-claim routes should pass a `vision_language_grounding_release_gate` before their outputs can approve, reject, publish, or change source evidence.
