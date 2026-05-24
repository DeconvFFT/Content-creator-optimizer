---
type: playlist-worklist
project: agent-studio-system-design
status: active
updated: 2026-05-19
sources:
  - https://web.stanford.edu/class/cs25/recordings/
  - https://web.stanford.edu/class/cs224n/
  - https://cs336.stanford.edu/
  - https://www.youtube.com/playlist?list=PLoROMvodv4rOY23Y0BoGoBGgQ1zmU_MT_
  - https://stanford-cs329s.github.io/index.html
  - https://ai-deeplang.github.io/large-language-models/lectures/
  - https://cs231n.stanford.edu/2024/schedule.html
---

# YouTube Playlist Worklist

Use official course pages as the source of truth for lecture video links. If YouTube playlists are saved in the browser/account, keep those playlists as navigation aids only; the canonical notes live in this vault.

## Playlist Buckets

| Playlist bucket | Source page | Note target | Purpose |
|---|---|---|---|
| Stanford CS25 Transformers United | https://web.stanford.edu/class/cs25/recordings/ | Separate notes under `02-lectures/stanford/cs25-*` plus `03-patterns/transformer-systems/cs25-transformer-systems-canon.md` | Transformers, state-space alternatives, LM capability behavior, retrieval-augmented language models, generalist agents, whole-part representations, scaling, pretraining, alignment, and production inference. |
| Stanford CS224N NLP with Deep Learning | https://web.stanford.edu/class/cs224n/ | `02-lectures/stanford/cs224n-nlp-with-deep-learning.md` | NLP/LLM foundations, transformers, RAG readings, projects, PyTorch implementation. |
| Stanford CS336 Language Modeling from Scratch | https://cs336.stanford.edu/ and https://www.youtube.com/playlist?list=PLoROMvodv4rOY23Y0BoGoBGgQ1zmU_MT_ | `02-lectures/stanford/cs336-systems-inference-evaluation.md` | Resource accounting, parallelism, inference, evaluation, data, alignment; official course page plus Stanford Online playlist pointer. |
| Stanford CS329S ML Systems Design | https://stanford-cs329s.github.io/index.html | `02-lectures/stanford/cs329s-ml-systems-design.md` | ML systems lifecycle, data, deployment, monitoring, privacy, fairness, security. |
| Stanford CS324 Large Language Models | https://ai-deeplang.github.io/large-language-models/lectures/ | `02-lectures/stanford/cs324-large-language-models.md` | LLM capabilities, harms, data, security, legality, modeling, training, scaling laws. |
| Stanford CS231n Deep Learning for Computer Vision | https://cs231n.stanford.edu/2024/schedule.html | `02-lectures/stanford/cs231n-computer-vision.md` | Vision/multimodal background for media intake and model capability boundaries. |

## Note Format

Each lecture note should stay compact:

- source link;
- lecture title;
- problem;
- key pattern;
- failure mode;
- Agent Studio implication;
- follow-up source links.

Do not store full transcripts.

## Current Note Status

- `02-lectures/stanford/cs25-transformer-foundations.md`: now includes a separate `Related Official Video Sources` section listing the CS25 Overview of Transformers, Introduction to Transformers, and Stop Worrying and Love the Transformer public Stanford Online video pointers. These are candidate video sources only; no full-watch notes are claimed.
- `02-lectures/stanford/cs25-state-space-transformer-tradeoffs.md`: now includes a separate `Related Official Video Sources` section for the public Stanford Online SSM/Transformer tradeoffs recording. Candidate only; not watched in full.
- `02-lectures/stanford/cs25-lm-intuition-future-ai.md`: now includes a separate `Related Official Video Sources` section for the public Stanford Online Jason Wei and Hyung Won Chung recording. Candidate only; not watched in full.
- `02-lectures/stanford/cs25-aligning-open-language-models.md`: now includes a separate `Related Official Video Sources` section for the public Stanford Online Nathan Lambert recording. Candidate only; not watched in full.
- `02-lectures/stanford/cs25-retrieval-augmented-language-models.md`: now includes a separate `Related Official Video Sources` section for the public Stanford Online Douwe Kiela RAG recording. The official public transcript was fetched directly on 2026-05-19 and used for a compact refresh; full-watch coverage is still not claimed.
- `02-lectures/stanford/cs25-generalist-agents-open-ended-worlds.md`: now includes a separate `Related Official Video Sources` section for the public Stanford Online Jim Fan recording. Candidate only; not watched in full.
- `02-lectures/stanford/cs25-whole-part-hierarchies.md`: now includes a separate `Related Official Video Sources` section for the public Stanford Online Geoffrey Hinton recording. Candidate only; not watched in full.
- `05-ingestion-runs/stanford-video-source-coverage-matrix.md`: added as the current audit matrix for public video, public notes/slides, schedule-only, and gated-recording distinctions across CS25, CS224N, CS336, CS329S, CS324, and CS231N. Use this before converting any playlist or course page into a video-level source note.
- `02-lectures/stanford/cs329s-ml-systems-design.md`: created from the official course site and public lecture notes for Lecture 1, Lecture 8, and Lecture 10. Public video availability for individual CS329S lectures was not required for this note; the official site and notes are the source of truth.
- `02-lectures/stanford/cs329s-ml-infrastructure-platform.md`: created from the official course page, syllabus, and public Google Slides HTML view for Lecture 15, ML Infrastructure and Platform. Public video coverage is not claimed.
- `02-lectures/stanford/cs224n-rag-agents-reasoning.md`: created from the official CS224N 2026 public course page and public RAG/agents plus reasoning slide PDFs, with the official public 2024 YouTube playlist recorded as the public video pointer. This note does not claim 2026 video/transcript ingestion because those videos remain enrolled-student gated.
- `02-lectures/stanford/cs336-systems-inference-evaluation.md`: created from the official CS336 Spring 2025 course page, official Stanford Online YouTube playlist pointer, and official lecture source files for resource accounting, parallelism, inference, and evaluation.
- `02-lectures/stanford/cs336-data-and-alignment.md`: created from official CS336 course pages and official Spring 2025 lecture source files for data sources, data filtering/deduplication, and alignment RL systems/mechanics. Refresh only after current 2026 alignment materials are publicly linked or otherwise published; the 2026-05-18 availability check is tracked in `05-ingestion-runs/stanford-current-availability-checks.md`.
- `02-lectures/stanford/cs25-transformer-foundations.md`: created from the official CS25 V6 page, public recordings page entries for Overview/Introduction/Stop Worrying and Love the Transformer, the original Transformer paper, and official Stanford CS224N transformer materials. No transcript or timestamp-level watch pass is stored.
- `02-lectures/stanford/cs25-state-space-transformer-tradeoffs.md`: created from the official CS25 V6 listing, the official recordings page, the official YouTube video pointer, and primary/open S4, H3, Mamba, Jamba, and Albert Gu tradeoff materials. The 2026-05-18 refresh confirmed the lecture is visibly listed on the public CS25 recordings page; no transcript or timestamp-level watch pass is stored.
- `02-lectures/stanford/cs25-lm-intuition-future-ai.md`: created from the official CS25 recordings page entry for Jason Wei and Hyung Won Chung's public recording pointer plus open primary papers on chain-of-thought prompting, emergent abilities, and instruction finetuning. No transcript or timestamp-level watch pass is stored.
- `02-lectures/stanford/cs25-whole-part-hierarchies.md`: created from the official CS25 recordings page entry for Geoffrey Hinton's public recording pointer plus the open GLOM paper. No transcript or timestamp-level watch pass is stored.
- `02-lectures/stanford/cs25-retrieval-augmented-language-models.md`: created from the official CS25 recordings page, official V3 schedule description, official YouTube playlist pointer, original RAG paper, and Contextual AI production RAG materials. Full video timestamp pass remains optional follow-up.
- `02-lectures/stanford/cs25-world-modeling-jepa.md`: created from the official CS25 V6 schedule entry, the official recordings page, and open primary papers for Causal-JEPA and LeWorldModel. No transcript or video download is stored; the visible recordings page does not yet list this lecture as a selected recording in page text.
- `02-lectures/stanford/cs25-ultra-scale-training.md`: created from the official CS25 V6 schedule entry, the official CS25 recordings page, Hugging Face Ultra-Scale Playbook, and Nanotron docs. No transcript or video download is stored; the visible recordings page does not yet list this lecture as a selected recording in page text.
- `02-lectures/stanford/cs25-future-of-pretraining.md`: created from the official CS25 V6 schedule entry, the official recordings page, and open primary papers on retrieval-aware pretraining, curriculum-guided layer scaling, and hallucination/reference-world framing. No transcript or video download is stored; the visible recordings page does not yet list this lecture as a selected recording in page text.
- `02-lectures/stanford/cs25-production-inference.md`: created from the official CS25 V6 schedule entry, the official recordings page, and current Modal docs for high-performance LLM inference, GPU selection, and TensorRT-LLM serving. No transcript or video download is stored; the visible recordings page does not yet list this lecture as a selected recording in page text.
- `02-lectures/stanford/cs324-large-language-models.md`: created from the official CS324 public course page and public lecture notes. The course page says recordings require Canvas access, so video coverage is marked as gated rather than ingested.
- `02-lectures/stanford/cs231n-detection-segmentation-understanding.md`: created from the official CS231N 2025 schedule, public Lecture 9 slides, the 2024 schedule cross-check, and schedule-linked primary/open papers. It covers detection/segmentation/visualization source material, not gated lecture-video ingestion.
- `02-lectures/stanford/cs231n-self-supervised-visual-representations.md`: created from the official CS231N 2025 schedule, public Lecture 12 slides, Assignment 3 page, and primary/open SimCLR, MoCo, CPC, DINO, MAE, and CLIP papers. It covers self-supervised/cross-modal representation source material, not gated lecture-video ingestion.
- `02-lectures/stanford/cs231n-video-understanding.md`: created from the official CS231N 2025/2024 schedule entries plus primary/open two-stream, C3D, I3D/Kinetics, and R(2+1)D papers. The Lecture 10 slide link is tracked, but this pass does not claim full slide extraction or gated lecture-video ingestion.
- `02-lectures/stanford/cs231n-3d-spatial-vision.md`: created from the official CS231N 2025/2024 schedule entries plus primary/open PointNet, DeepSDF, Occupancy Networks, and NeRF papers. The 3D Vision slide links are tracked, but this pass does not claim full slide extraction or gated lecture-video ingestion.
- `02-lectures/stanford/cs231n-vision-language-grounding.md`: created from the official CS231N 2025/2024 schedule entries plus primary/open image-captioning, VQA, region-attention, and CLIP papers. The Vision and Language slide link is tracked, but this pass does not claim full slide extraction or gated lecture-video ingestion.
- `05-ingestion-runs/stanford-current-availability-checks.md`: tracks CS336 current alignment availability, CS25 selected-recording coverage, future/pending CS25 slots, and CS324 gated-video status so worklist entries do not imply video ingestion.

## CS25 Public Video Inventory

This is the current official public video list mirrored from [[../../05-ingestion-runs/stanford-public-video-ingestion-status]]. These are links to official Stanford Online/CS25 public recordings and topic-note destinations only. Most remain `candidate; not watched in full`; `cs25-retrieval-augmented-language-models` is now official-transcript-backed but still not full-watch coverage.

| Topic note | Video | URL | Status |
|---|---|---|---|
| [[../../02-lectures/stanford/cs25-transformer-foundations]] | Stanford CS25: Transformers United V6 I Overview of Transformers | https://www.youtube.com/watch?v=bHSDPgZYie0 | candidate; not watched in full |
| [[../../02-lectures/stanford/cs25-transformer-foundations]] | Stanford CS25: V2 I Introduction to Transformers w/ Andrej Karpathy | https://www.youtube.com/watch?v=XfpMkf4rD6E | candidate; not watched in full |
| [[../../02-lectures/stanford/cs25-transformer-foundations]] | Stanford CS25: V3 I How I Learned to Stop Worrying and Love the Transformer | https://www.youtube.com/watch?v=1GbDTTK3aR4 | candidate; not watched in full |
| [[../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] | Stanford CS25: Transformers United V6 I On the Tradeoffs of State Space Models and Transformers | https://www.youtube.com/watch?v=OyimE74UMF8 | candidate; not watched in full |
| [[../../02-lectures/stanford/cs25-lm-intuition-future-ai]] | Stanford CS25: V4 I Jason Wei & Hyung Won Chung of OpenAI | https://www.youtube.com/watch?v=3gb-ZkVRemQ | candidate; not watched in full |
| [[../../02-lectures/stanford/cs25-aligning-open-language-models]] | Stanford CS25: V4 I Aligning Open Language Models | https://www.youtube.com/watch?v=AdLgPmcrXwQ | candidate; not watched in full |
| [[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] | Stanford CS25: V3 I Retrieval Augmented Language Models | https://www.youtube.com/watch?v=mE7IDf2SmJg | official transcript used on 2026-05-19; full watch not completed |
| [[../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] | Stanford CS25: V3 I Generalist Agents in Open-Ended Worlds | https://www.youtube.com/watch?v=wwQ1LQA3RCU | candidate; not watched in full |
| [[../../02-lectures/stanford/cs25-whole-part-hierarchies]] | Stanford CS25: V2 I Represent part-whole hierarchies in a neural network, Geoff Hinton | https://www.youtube.com/watch?v=CYaju6aCMoQ | candidate; not watched in full |
