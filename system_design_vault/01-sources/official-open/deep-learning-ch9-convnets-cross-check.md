---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-20
cross_checks:
  - source_title: "Deep Learning (Goodfellow, Bengio, Courville)"
    scope: "Chapter 9 convolutional networks core mechanics"
anchor_note: "02-books/deep-learning-book/chapters/9-convolutional-networks-core-mechanics.md"
sources:
  - https://www.deeplearningbook.org/contents/convnets.html
  - https://pytorch.org/docs/2.12/generated/torch.nn.Conv2d.html
  - https://www.tensorflow.org/api_docs/python/tf/keras/layers/Conv2D
  - https://papers.nips.cc/paper_files/paper/2012/hash/c399862d3b9d6b76c8436e924a68c45b-Abstract.html
  - https://openaccess.thecvf.com/content_cvpr_2015/html/Long_Fully_Convolutional_Networks_2015_CVPR_paper.html
  - https://arxiv.org/abs/1511.07122
related:
  - "[[../../02-books/deep-learning-book/generalization-optimization-sequence-systems]]"
  - "[[../../02-books/deep-learning-book/chapters/9-convolutional-networks-core-mechanics]]"
  - "[[../../02-books/applied-ml-ai-engineers/chapters/ch10-image-classification-with-cnns]]"
---

# Deep Learning Chapter 9 Convnets - Official Cross-Check

## Scope

This cross-check hardens the new Deep Learning Chapter 9 note with canonical open sources for convolution semantics, padding/stride/channel controls, dense-output follow-through, and receptive-field expansion without early resolution collapse.

## Cross-Check Result

The chapter note is strongly supported. The main reinforcement is that convolution is best understood as an architectural contract among locality, shared detectors, equivariant feature maps, and selective invariance. The corroborating sources also sharpen a practical point the original chapter only hints at: modern implementation quality depends on explicit kernel/stride/padding/dilation/groups semantics and on knowing when dense spatial outputs must survive deeper into the stack.

## Confirmation Matrix

| Chapter 9 theme | Official/open confirmation | Agent Studio implication |
|---|---|---|
| Sparse local interactions and parameter sharing are the central CNN bias | The Deep Learning web-book chapter explicitly centers convnets on sparse interactions, parameter sharing, translation equivariance, and pooling as a strong prior. | Spatial routes should justify locality and shared-detector assumptions rather than importing CNNs by habit. |
| Convolution behavior is operationally defined by kernel, stride, padding, dilation, and groups | Official PyTorch `Conv2d` and TensorFlow `Conv2D` docs make these parameters the actual implementation contract. | Route records need explicit convolution configuration, not only a vague "CNN backbone" label. |
| Zero padding is architecture control, not cosmetic sizing | The book and framework docs both show padding determines output geometry and border behavior; without it, depth rapidly collapses spatial extent. | Border-sensitive OCR/layout tasks should record padding choice and any edge underrepresentation risk. |
| Shared local detectors can scale to strong image classification | AlexNet is the canonical proof that stacked convolution, nonlinearity, and pooling can turn shared local filters into strong large-scale recognition systems. | For image classification routes, shared-local feature hierarchies remain a sound baseline before heavier multimodal architectures are introduced. |
| Fully convolutional stacks can preserve spatial output semantics | FCN shows that replacing terminal dense classification logic with fully convolutional prediction preserves location-aware outputs for segmentation-style tasks. | Detection, segmentation, grounding, and page-region routes should delay flattening and preserve dense maps longer. |
| Dilated convolution grows receptive field without immediate downsampling | Yu & Koltun show dilated convolution expands context while retaining resolution for dense prediction. | Dense-output routes should consider dilation when they need wider context without losing coordinate fidelity. |

## Canon Decisions

- The chapter note remains `canon_ready`.
- Add `spatial_topology_record`, `feature_invariance_policy`, `downsampling_record`, and `structured_output_readiness_record` as first-class evidence for perception and layout routes.
- Treat `groups`, padding mode, and dilation as reviewable deployment semantics rather than hidden framework defaults.
- Preserve spatial maps longer when the route produces boxes, masks, grounded spans, or region-aware moderation decisions.

## New Agent Studio Design Rules

1. **A CNN backbone is not enough metadata.** Record the spatial contract: what is shared, what is pooled, and what resolution survives.
2. **Pooling and stride are governance choices.** They decide whether the system is optimized for invariance or localization.
3. **Grouped or depthwise connectivity needs explicit justification.** Use it for efficiency only when quality and spatial precision remain acceptable.
4. **Dense-output routes need map-preservation evidence.** Fully convolutional or dilation-style design should be preferred over early flattening when exact region semantics matter.

## Remaining Refinement

- The chapter note now covers the reusable convnet prior cleanly, but a future targeted pass could deepen the later structured-output section if a specific segmentation or dense-layout route needs closer book-level grounding.
- If a future route depends on modern backbone comparison, the next corroboration tier should add current official docs for feature pyramids, segmentation heads, and document-AI layout models.