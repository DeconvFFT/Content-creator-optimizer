---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://stanford-cs329s.github.io/index.html
  - https://web.stanford.edu/class/cs224n/
  - https://web.stanford.edu/class/cs25/recordings/
  - https://web.stanford.edu/class/cs25/past/cs25-v3/index.html
  - https://www.youtube.com/watch?list=PLoROMvodv4rNiJRchCzutFw5ItR_Z27CM&v=wwQ1LQA3RCU
  - https://www.youtube.com/watch?index=44&list=PLoROMvodv4rNiJRchCzutFw5ItR_Z27CM&v=OyimE74UMF8
  - https://arxiv.org/abs/2201.11903
  - https://arxiv.org/abs/2206.07682
  - https://arxiv.org/abs/2210.11416
  - https://arxiv.org/abs/2102.12627
  - https://nanotron-ultrascale-playbook.static.hf.space/
  - https://github.com/huggingface/nanotron
  - https://ai-deeplang.github.io/large-language-models/lectures/
  - https://ai-deeplang.github.io/large-language-models/lectures/data/
  - https://ai-deeplang.github.io/large-language-models/lectures/legality/
  - https://ai-deeplang.github.io/large-language-models/lectures/modeling/
  - https://ai-deeplang.github.io/large-language-models/lectures/training/
  - https://ai-deeplang.github.io/large-language-models/lectures/selective-architectures/
  - https://ai-deeplang.github.io/large-language-models/lectures/adaptation/
  - https://ai-deeplang.github.io/large-language-models/lectures/environment/
  - https://cs336.stanford.edu/
  - https://cs336.stanford.edu/spring2025/index.html
  - https://github.com/stanford-cs336/assignment5-alignment
  - https://www.youtube.com/playlist?list=PLoROMvodv4rOY23Y0BoGoBGgQ1zmU_MT_
  - https://web.stanford.edu/class/cs349d/
  - https://web.stanford.edu/class/cs224g/
  - https://web.stanford.edu/class/cs224g/schedule.html
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%205%20-%20Context%20Engineering.pdf
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%206%20-%20More%20Context%20Engineering.pdf
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%207%20-%20Agent%20Orchestration%20%26%20Workflow%20Design.pdf
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%2015%20-%20Data%20Strategy%20and%20Memory%20Layer%20for%20AI%20Agents.pdf
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%2017%20-%20Workshop%20Building%20and%20Scaling%20Realtime%20Voice%20AI%20Apps.pdf
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%2018%20-%20Ethics%20and%20Guardrails.pdf
  - https://web.stanford.edu/class/cs25/
  - https://raw.githubusercontent.com/stanford-cs336/spring2025-lectures/main/lecture_13.py
  - https://raw.githubusercontent.com/stanford-cs336/spring2025-lectures/main/lecture_14.py
  - https://raw.githubusercontent.com/stanford-cs336/spring2025-lectures/main/lecture_17.py
  - https://cs231n.stanford.edu/2025/schedule.html
  - https://cs231n.stanford.edu/slides/2025/lecture_9.pdf
  - https://cs231n.stanford.edu/slides/2025/lecture_10.pdf
  - https://cs231n.stanford.edu/slides/2025/lecture_12.pdf
  - https://cs231n.stanford.edu/slides/2025/lecture_15.pdf
  - https://cs231n.stanford.edu/slides/2025/lecture_16.pdf
  - https://cs231n.github.io/assignments2025/assignment3/
  - https://cs231n.stanford.edu/slides/2024/lecture_18.pdf
  - https://cs231n.stanford.edu/2024/schedule.html
---

# Stanford Official Lecture Sources

Use official Stanford course pages, linked lecture materials, and official YouTube playlists/recordings as high-quality source material. Do not scrape third-party transcript sites as source truth. Do not download YouTube videos into the vault unless the user explicitly asks and rights allow it.

## Canon Scope

This note is the canon source map for official/open Stanford material already used in the vault. It is not a claim that every listed course video has been watched or transcribed. It distinguishes public lecture notes, public slides, public schedule entries, official recordings pages, official playlist pointers, gated Canvas recordings, and future/pending lecture slots.

The CS324 lecture index at `https://ai-deeplang.github.io/large-language-models/lectures/` was rechecked on 2026-05-18. It publicly lists lecture-note pages for introduction, capabilities, harms, data, security, legality, modeling, training, parallelism, scaling laws, selective architectures, adaptation, and environmental impact. The already-created CS324 note uses those public notes and does not claim Canvas-gated video ingestion.

## Included Courses

| Course | Why it matters for Agent Studio | Ingestion use |
|---|---|---|
| CS329S Machine Learning Systems Design | Direct match for production ML system design: objectives, architecture, data, infrastructure, deployment, monitoring, privacy, fairness, and security. | Use as the lecture backbone for Designing ML Systems notes and ML platform architecture implications. |
| CS224N NLP with Deep Learning | Gives the NLP/LLM substrate behind retrieval, generation, tokenization, model behavior, and project-based implementation. | Use lectures/slides to ground RAG, transformer, NLP, and evaluation notes. |
| CS224G Building and Scaling LLM Applications | Directly matches production LLM app design: context engineering, agent workflows, data/memory strategy, realtime voice, eval, observability, and guardrails. | Use public course page and public lecture PDFs to ground Agent Studio route assembly, memory, realtime, and safety design. Do not claim class recording ingestion because the course page says the class is not recorded. |
| CS25 Transformers United | High-signal guest lectures on transformers, retrieval-augmented language models, state-space tradeoffs, and generalist agents. | Use selected official recordings as deep-dive notes for modern model architecture and agent trends. |
| CS324 Large Language Models | Covers capabilities, data, security, legality, modeling, training, parallelism, scaling laws, adaptation, and environmental impact. | Use as the LLM policy/systems backbone, especially for risks and operational constraints. |
| CS336 Language Modeling from Scratch | Systems-heavy language-model course: tokenization, resource accounting, kernels, parallelism, inference, evaluation, data, and alignment. | Use for inference engineering, scaling, benchmarking, and from-scratch mental models. |
| CS349D AI Inference Infrastructure | Current Stanford inference-infrastructure seminar with visible public mini serving-engine milestones for parallelism, continuous batching, PagedAttention, context caching, chunked prefill, speculative decoding, hierarchical caching, and prefill/decode disaggregation. | Use as a source-map and curriculum signal for serving-feature compatibility, inference-phase metrics, and capacity planning. Do not claim detailed lecture, readings, or video ingestion from the sparse public page. |
| CS231n Deep Learning for Computer Vision | Vision/multimodal foundation with strong lecture slides and project practice. | Use for image/video/multimodal intake and model capability boundaries. |

## Agent Studio Design Implications

- Treat official lectures as durable learning sources, not just references. Each relevant lecture should create a compact note with: problem, system pattern, failure mode, implementation implication, and Agent Studio decision.
- Use CS329S and Designing Machine Learning Systems together for the ML product lifecycle: stakeholder objective, data source, labeling, features, model, evaluation, deployment, monitoring, and feedback loop.
- Use CS336 and Inference Engineering together for performance budgets: FLOPs, memory, kernels, parallelism, batching, serving, inference, and evaluation.
- Use CS224N, CS25, and local transformer books together for RAG and agent quality: tokenization, attention, prompting, retrieval augmentation, alignment, hallucination controls, and model limitations.
- Use CS324 for governance and safety: data provenance, security, legality, adaptation, environmental impact, and deployment risk.
- Store lecture-source provenance explicitly: schedule listing, public notes, public slides, public video, official playlist pointer, gated video, primary paper, or replacement official/open source.
- Keep video-worklist status separate from canon-source-map status so the vault does not pretend that a playlist pointer is equivalent to direct video understanding.

## Ingested Lecture Notes

- [[../../02-lectures/stanford/cs329s-ml-systems-design]] covers the official CS329S overview, syllabus, Lecture 1, Lecture 8, and Lecture 10 as a product/system-design cross-check for Building ML Powered Applications.
- CS336 official course page plus Lecture 2, Lecture 7, Lecture 10, and Lecture 12 source files were used in [[inference-engineering-cross-check]] to cross-check Inference Engineering chapters 1, 5, and 7.
- [[../../02-lectures/stanford/cs336-systems-inference-evaluation]] covers CS336 resource accounting, parallelism, inference, and evaluation from official course material and the official Stanford Online playlist pointer.
- [[../../02-lectures/stanford/cs336-data-and-alignment]] covers CS336 data source, filtering/deduplication, and alignment RL systems/mechanics from official course material. The 2026-05-18 availability check found the current alignment sequence listed, but current public lecture materials were not linked in visible official page content, so this note uses the Spring 2025 archive for alignment.
- [[../../02-lectures/stanford/cs336-common-crawl-data-pipeline]] covers the official Spring 2026 Assignment 4 repository and handout for Common Crawl WARC/WAT/WET projections, extraction loss, language/PII/harm/quality filters, exact and fuzzy deduplication, validation leakage, tokenization artifacts, and filter-runtime evidence.
- [[../../02-lectures/stanford/cs349d-ai-inference-infrastructure]] covers the official Stanford CS349D Spring 2026 course page as a sparse but high-value inference-infrastructure source map. It records the public mini serving-engine milestone ladder and does not claim detailed lecture slides, paper readings, recordings, or student-note ingestion.
- [[../../02-lectures/stanford/cs224g-building-scaling-llm-apps]] covers the official Stanford CS224G Winter 2026 course page, public schedule, and selected public lecture PDFs for context engineering, agent orchestration, data/memory strategy, product-embedded feedback, contributor-quality weighting, realtime voice, and guardrails. The course page says the class is not recorded or available via Zoom, so this note does not claim lecture-video or transcript ingestion.
- [[../../02-lectures/stanford/cs224r-reward-reasoning-world-models]] covers official CS224R Spring 2026 reward-learning, RL-for-LLM-reasoning, model-based RL, and multi-task/goal-conditioned RL slides for reward specification, test-time compute, world-model planning, and task conditioning. CS224R recordings remain Canvas-linked and are not claimed as ingested.
- [[../../02-lectures/stanford/cs234-policy-gradient-ppo]] covers official CS234 Winter 2026 Policy Gradient II public slides for baselines, advantage estimates, on-policy sample-efficiency limits, policy-space drift, adaptive KL penalties, PPO clipping, and PPO-style route-control records. No video or transcript ingestion is claimed.
- The CS336 Spring 2026 page lists Alignment - RLHF (DPO), Alignment - RL algorithms, and Alignment - RL systems for May 18, May 20, and May 27. As of the 2026-05-18 check, the public Assignment 5 repository still points to Spring 2025 handouts.
- [[../../05-ingestion-runs/stanford-current-availability-checks]] records current availability checks for CS336 alignment, CS25 selected-recording coverage, future/pending CS25 slots, and CS324 gated video status.
- [[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] covers the official CS25 Retrieval Augmented Language Models lecture listing and video pointer, grounded against the original RAG paper and Contextual AI production RAG materials. It does not use third-party transcript sites.
- [[../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] covers the official CS25 Generalist Agents in Open-Ended Worlds lecture listing and video pointer, grounded against MineDojo and Voyager primary materials.
- [[../../02-lectures/stanford/cs25-world-modeling-jepa]] covers the official CS25 V6 world-modeling lecture listing plus open primary papers for Causal-JEPA and LeWorldModel. The visible recordings page does not yet expose this lecture as a selected public recording in the page text as of this pass.
- [[../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] covers the official CS25 State Space Model and Transformer Tradeoffs lecture listing and video pointer, grounded against S4, H3, Mamba, Jamba, and Albert Gu's tradeoff essay.
- [[../../02-lectures/stanford/cs25-ultra-scale-training]] covers the official CS25 V6 Ultra-Scale training lecture listing, grounded against Hugging Face's official Ultra-Scale Playbook and Nanotron documentation. The visible CS25 recordings page does not yet expose this lecture as a selected public recording in the page text as of this pass.
- [[../../02-lectures/stanford/cs25-future-of-pretraining]] covers the official CS25 V6 future-of-pretraining lecture listing plus open primary papers on RAG-considerate pretraining, curriculum-guided layer scaling, and hallucination as reference-world error. The visible recordings page does not yet expose this lecture as a selected public recording in the page text as of this pass.
- [[../../02-lectures/stanford/cs25-production-inference]] covers the official CS25 V6 production-inference lecture listing plus current Modal docs for high-performance LLM inference, GPU selection, and TensorRT-LLM serving. The visible recordings page does not yet expose this lecture as a selected public recording in the page text as of this pass.
- [[../../02-lectures/stanford/cs25-lm-intuition-future-ai]] covers the official CS25 recordings page entry for Jason Wei and Hyung Won Chung's "Intuition on LMs, Shaping the Future of AI," grounded against open papers on chain-of-thought prompting, emergent abilities, and scaling instruction-finetuned language models. The public video pointer is recorded, but no transcript/timestamp coverage is claimed.
- [[../../02-lectures/stanford/cs25-whole-part-hierarchies]] covers the official CS25 recordings page entry for Geoffrey Hinton's "Whole-Part Hierarchies in a Neural Network," grounded against Hinton's open arXiv GLOM paper. The public video pointer is recorded, but no transcript/timestamp coverage is claimed.
- [[../../02-lectures/stanford/cs324-large-language-models]] covers the official CS324 public course page and lecture notes for LLM behavior, data, security availability, legality, tokenization/modeling, training, parallelism availability, selective architectures, adaptation, and environmental impact. The course page states recordings are available through Canvas, so private video recordings are not treated as public-ingested source coverage.
- [[../../02-lectures/stanford/cs231n-detection-segmentation-understanding]] covers public CS231N 2025 Lecture 9 slides and schedule-linked primary papers for detection, segmentation, visualization, and understanding. It strengthens object/region/mask evidence for visual QA and does not claim gated video coverage.
- [[../../02-lectures/stanford/cs231n-self-supervised-visual-representations]] covers public CS231N 2025 Lecture 12 slides, Assignment 3 source signals, and open primary papers for self-supervised and cross-modal visual representations. It strengthens media embedding, hard-negative eval, cross-modal retrieval, and embedding-refresh records without claiming gated video coverage.
- [[../../02-lectures/stanford/cs231n-video-understanding]] covers official CS231N video-understanding schedule signals and primary open papers for two-stream, C3D, I3D/Kinetics, and R(2+1)D video models. The Lecture 10 public slide link is recorded, but this pass does not claim full slide extraction or gated video coverage.
- [[../../02-lectures/stanford/cs231n-3d-spatial-vision]] covers official CS231N 3D Vision schedule signals and primary open PointNet, DeepSDF, Occupancy Networks, and NeRF papers. The public slide links are recorded, but this pass does not claim full slide extraction or gated video coverage.
- [[../../02-lectures/stanford/cs231n-vision-language-grounding]] covers official CS231N Vision and Language schedule signals and primary open papers for captioning, VQA, bottom-up/top-down region attention, and CLIP-style image-text representation. The public slide link is recorded, but this pass does not claim full slide extraction or gated video coverage.

## Ingestion Rule

For each lecture source, store only original compact notes and links to official course pages or YouTube links. Do not store full transcripts or generated transcript dumps in the vault.
