---
type: official-course-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_stanford_public_course_notes_and_schedule
sources:
  - https://cs231n.github.io/
  - https://cs231n.github.io/classification/
  - https://cs231n.github.io/linear-classify/
  - https://cs231n.github.io/convolutional-networks/
  - https://cs231n.github.io/understanding-cnn/
  - https://cs231n.github.io/attention/
  - https://cs231n.github.io/generative-models/
  - https://cs231n.stanford.edu/2024/
  - https://cs231n.stanford.edu/2024/schedule.html
  - https://cs231n.stanford.edu/2025/schedule.html
related:
  - "[[cs231n-vision-multimodal-source-map]]"
  - "[[cs231n-detection-segmentation-understanding]]"
  - "[[cs231n-self-supervised-visual-representations]]"
  - "[[cs231n-video-understanding]]"
  - "[[cs231n-3d-spatial-vision]]"
  - "[[cs231n-vision-language-grounding]]"
  - "[[../../03-patterns/vision-multimodal/visual-multimodal-qa-canon]]"
---

# CS231N Public Vision Notes

## Reading Scope

Direct-read pass over the public CS231N notes index, public notes for image classification, linear classifiers, convolutional networks, CNN visualization, attention, and generative modeling, plus the official 2024 and 2025 schedules. This note uses public official Stanford material only. It does not claim access to Canvas-gated lecture videos and stores no raw slide text, assignment solutions, or long excerpts.

## Core Thesis

CS231N is useful for Agent Studio because it treats vision as a full system: data representation, model architecture, train/test discipline, semantic embeddings, attention, dense prediction, video, generation, interpretability, and human-centered evaluation. For a content studio, this means visual QA cannot be a single image classifier bolted onto a text pipeline.

Agent Studio implication: visual and video routes need their own evidence model, traces, and eval cases.

## Visual Representation And Evaluation

The image-classification notes start from the mismatch between raw pixel arrays and visual meaning. Pixel distances can be cheap baselines, but they often overemphasize background, color, or low-level similarity rather than semantic identity. The same note emphasizes train/validation/test separation and tuning on validation rather than test data.

Agent Studio implication:

- media retrieval should not rely on raw-pixel or naive perceptual hashes for semantic decisions;
- visual eval sets need held-out examples by artifact type, platform, brand constraint, and failure slice;
- generated-asset QA should separate cheap sanity checks from semantic review.

## From Class Scores To Deployable Visual Models

The linear-classification notes introduce a key production tradeoff: nearest-neighbor methods are simple but store and compare against training data at inference time, while learned parametric models move work into training and make inference cheap. The same framing carries into Agent Studio media systems: a route can use retrieval-heavy similarity search, learned classifiers, or hybrid detectors depending on latency, update frequency, and evidence requirements.

Agent Studio implication:

- visual routes should declare whether they depend on indexed exemplars, learned classifiers, external vision APIs, or multimodal foundation models;
- route-change proposals should estimate retrieval latency, model latency, and update cost separately;
- quality regressions should be measured per visual slice, not only by aggregate accuracy.

## CNN Architecture Lessons

The convolutional-network notes explain why image-specific structure matters: local receptive fields, shared weights, spatial dimensions, pooling/downsampling, and layer patterns make visual inference more efficient and less overfit than dense connections over raw pixels. The practical lesson is not that Agent Studio must train CNNs; it is that visual representations encode spatial assumptions that text systems do not.

Agent Studio implication:

- visual QA objects need spatial fields: bounding boxes, masks, crops, layout regions, frame timestamps, and object relations;
- source records for images/videos should preserve resolution, aspect ratio, crop history, and transformations;
- eval cases should check object presence, object count, spatial relation, typography, crop safety, and platform aspect-ratio constraints.

## Interpretability And Failure Discovery

The CNN-visualization notes cover activation maps, filter inspection, maximally activating patches, embedding projections, and occlusion-style tests. The useful product principle is that a visual model's answer is insufficient without evidence about what part of the artifact drove it. Visual systems can be confidently wrong because of background cues, dead filters, adversarial perturbations, or shortcut correlations.

Agent Studio implication:

- visual QA traces should include evidence regions or frame samples, not only labels;
- reviewer UX should show what the model inspected when it rejects a generated asset;
- security and QA evals need cases for background-cue failures, occlusion, tiny text, near-duplicate layouts, and adversarial-looking artifacts.

## Attention And Multimodal Context

The attention notes bridge image captioning and general attention layers. A single global image vector is too compressed for detailed descriptions; attention lets a model condition each generated token or output element on different visual regions. This is directly relevant to storyboards, reels, thumbnails, and source-grounded alt text.

Agent Studio implication:

- captioning, storyboard critique, and video QA should preserve region/frame references for claims;
- multimodal model outputs should attach evidence spans to visual regions where possible;
- long visual artifacts need temporal and spatial attention traces rather than one coarse asset summary.

## Generative Visual Systems

The generative-modeling notes frame generation as learning a distribution and sampling from it, contrasting explicit likelihood approaches, latent-variable approaches, adversarial training, autoregressive generation, and later diffusion-style systems in the course schedule. The important Agent Studio lesson is that generation quality, controllability, diversity, inference cost, and evaluation evidence are separate axes.

Agent Studio implication:

- media-generation routes should record model/provider, prompt, source constraints, seed/settings when available, edit operations, and output hash;
- evals should test prompt adherence, visual fidelity, style/brand fit, unsafe content, text rendering, temporal consistency, and source-grounding;
- approval gates should be stronger for public media artifacts than for private drafts.

## Schedule Signals

The official 2024 and 2025 schedules show the course arc from image classification and CNNs through attention/transformers, detection/segmentation, video understanding, self-supervised learning, generative models, 3D vision, vision-language, robot learning, and human-centered AI. The 2024 schedule also makes lecture videos Canvas-gated, so public ingestion should rely on public notes/slides and not pretend to have video coverage.

The detection/segmentation follow-up note now covers the public Lecture 9 slide slice directly. Its key addition is that visual evidence should be object-, region-, and mask-addressable before Agent Studio trusts an edit, crop, safety rejection, or object-presence claim.

The self-supervised visual representations follow-up note now covers the public Lecture 12 slice directly. Its key addition is that media embeddings need objective provenance, hard-negative evals, cross-modal retrieval traces, and auditable refresh jobs before Agent Studio trusts visual similarity or image-text retrieval.

The video-understanding follow-up note now covers the official schedule signal plus primary open video-action papers. Its key addition is that video QA needs clip windows, action/event records, object tracks, modality traces, and temporal eval cases rather than frame-only captions.

The 3D/spatial follow-up note now covers the official schedule signal plus primary open spatial-representation papers. Its key addition is that spatial media needs representation family, camera-view records, reconstruction evidence, consistency evals, and render lineage rather than treating one rendered image as proof of a scene.

The vision-language follow-up note now covers the official schedule signal plus primary open captioning, VQA, region-attention, and CLIP-style grounding papers. Its key addition is that captions, answers, and cross-modal retrieval need question/prompt scope, visual evidence, source evidence, and unsupported-claim flags.

Agent Studio implication:

- create separate canon lanes for visual QA, video QA, multimodal retrieval, generation, and human-centered review;
- treat public schedules as coverage maps, not as lecture-comprehension artifacts;
- do not use gated course videos or protected assignment materials as evidence.

## Datastore Requirements

Add or strengthen these records for visual/multimodal routes:

- `media_source_record`: image/video identity, source rights, dimensions, duration, format, hash, transformations, and allowed use.
- `visual_region`: bounding box, mask, crop, detected object/text, confidence, source artifact, and reviewer status.
- `video_trace`: shot ID, frame sample IDs, timestamps, transcript/subtitle refs, transition decisions, and continuity checks.
- `visual_eval_case`: object presence, spatial relation, text legibility, brand/style fit, safety, crop/layout, temporal consistency, and grounding assertions.
- `media_generation_record`: prompt/artifact lineage, model/provider, settings, seed if available, source constraints, edit operations, output hash, approval, and destination.

## Agent Studio Design Implications

- Keep visual QA first-class instead of routing every media question through text-only evals.
- Preserve visual evidence regions and frame samples so reviewers can audit model judgments.
- Separate media retrieval, media generation, visual critique, and publishing into different route permissions.
- Use human review for brand-sensitive, safety-sensitive, or public-facing media even when automated visual checks pass.
