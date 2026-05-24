---
type: video-source-coverage-matrix
project: agent-studio-system-design
status: active
updated: 2026-05-18
sources:
  - https://web.stanford.edu/class/cs25/
  - https://web.stanford.edu/class/cs25/recordings/
  - https://web.stanford.edu/class/cs224n/
  - https://cs336.stanford.edu/
  - https://stanford-cs329s.github.io/index.html
  - https://ai-deeplang.github.io/large-language-models/lectures/
  - https://cs231n.stanford.edu/2024/schedule.html
---

# Stanford Video Source Coverage Matrix

## Purpose

This matrix separates official public video links, public lecture notes/slides, schedule-only source signals, and gated recordings. It prevents Agent Studio from treating "lecture listed" as "video understood" and gives ingestion agents a stable checklist for future video-source passes.

It stores no video transcripts, timestamp dumps, raw slide text, copied lecture text, or protected course material.

## Coverage Matrix

| Course/source | Official evidence checked on 2026-05-18 | Public video status | Public non-video status | Current vault action |
|---|---|---|---|---|
| CS25 Transformers United V6 | Official course page and recordings page. | Selected public YouTube recordings visible for overview, SSM/Transformer tradeoffs, introduction/Transformer foundations, LM intuition/future AI, Transformer foundations, open-model alignment, RAG, generalist agents, and whole-part hierarchies. New recordings are described as expected one to two weeks after each lecture. | Current V6 schedule lists slide links and descriptions for several talks, including world modeling, ultra-scale training, future of pretraining, parameter/context generalization, collaborative AI agents, and production inference. | Keep selected-recording notes mapped, but do not claim timestamp/transcript coverage. Keep schedule-plus-primary-source notes separate from video-ingested notes. |
| CS25 May 21 Victoria Lin slot | Official CS25 V6 schedule. | No public recording yet. | Public title is now `From Language Models to Native Multimodal Intelligence` with speaker listed as Victoria Lin, Thinking Machines, but no slides/materials are exposed on the row yet. | Keep `future_pending_public_materials`; do not create direct source note from title visibility alone. |
| CS25 May 28 production inference slot | Official CS25 V6 schedule. | Future-dated relative to this check; no public recording yet. | Public schedule gives title, speaker, and description for production inference. | Existing note may use schedule plus Modal/TensorRT-LLM style official sources, but no video ingestion is claimed. Recheck after May 28 plus recording delay. |
| CS224N Winter 2026 | Official CS224N 2026 page. | Current lecture videos are Canvas/Panopto for enrolled students and not publicly viewable; the page points public viewers to the free Spring 2024 YouTube playlist. | Current slides, notes, assignments, readings, and schedule are public course artifacts. | Use public 2026 slides/notes for current course synthesis; use 2024 playlist only as public video pointer; no 2026 video claim. |
| CS336 Spring 2026 | Official CS336 Spring 2026 page. | No public video source is exposed on the current page. | Lecture material links are public through Lecture 15; Lecture 16/17 alignment material links are absent. | Keep current 2026 data/system notes and current Lecture 15 mid/post-training note; keep Lecture 16/17 refresh pending until official public materials appear. |
| CS336 Spring 2025 archive / Stanford Online playlist | Official CS336 previous offering and Stanford Online YouTube playlist pointer recorded in existing notes. | Public playlist pointer is usable for navigation, but no transcript/timestamp pass is claimed. | Official lecture source files and slides support direct-reading notes. | Continue using archive materials for systems/inference/eval and alignment archive cross-checks, with clear year labels. |
| CS329S ML Systems Design | Official CS329S page. | The page says lectures are recorded for enrolled/SCPD students; public availability is uncertain. A demo-day recording exists but is not a lecture substitute. | Public slides, intensive notes, assignments, and project materials are source truth. | Keep CS329S notes as public notes/slides synthesis; do not claim lecture-video ingestion. |
| CS324 Large Language Models | Official public lecture-note site. | No public video is used in the vault; existing status treats recordings as gated. | Public lecture notes cover introduction, capabilities, harms, data, security, legality, modeling, training, parallelism, scaling laws, selective architectures, adaptation, and environmental impact. | Keep CS324 as public lecture-note coverage; no Canvas/video claim. |
| CS231N 2024/2025 computer vision | Official CS231N schedules and notes. | Lecture-video links point to Canvas for enrolled students. Individual schedule readings may link public third-party videos, but those are not course lecture recordings. | Public course notes, slides, schedule links, readings, and papers are usable. | Keep visual/multimodal notes as public slides/notes/paper synthesis; do not claim gated lecture-video ingestion. |

## Ingestion Rules

Detailed selected-recording metadata is tracked in `05-ingestion-runs/stanford-public-video-ingestion-status.json` and summarized in [[stanford-public-video-ingestion-status]]. That ledger is the source of truth for `public_recording_visible` versus `video_watch_ingested` on the nine currently visible CS25 public recordings.

- A public YouTube URL is a navigation source until the video is watched directly in full.
- A public course schedule can support a source-map or availability note, but it cannot support a video-understanding claim by itself.
- Gated recordings stay out of the vault unless access and allowed use are explicitly provided.
- Public slides, lecture notes, paper links, and official docs can support compact original synthesis when directly read.
- Public video notes should include: official page URL, video URL, lecture title, watched status, concepts understood from the viewing pass, Agent Studio implication, gaps, and no transcript dump.
- Future-dated lectures should remain in `future_source_watch` status until official public materials or recordings appear.

## Agent Studio Implications

Add or preserve these datastore distinctions:

| Datastore distinction | Why it matters |
|---|---|
| `public_recording_visible` versus `video_ingested` | Prevents a playlist link from being treated as source understanding. |
| `public_notes_available` versus `recording_gated` | Lets agents use public notes while blocking protected video claims. |
| `schedule_only` versus `direct_read_note_created` | Keeps future or sparse listings from becoming shallow canon. |
| `recording_delay_window` | CS25 states new recordings are uploaded after a delay, so rechecks need calendar logic. |
| `public_archive_year` | Public videos may belong to older offerings while current slides/notes belong to a newer offering. |

The implementation rule for Agent Studio is simple: source routes should attach evidence type to every claim. A claim from public notes, public video, public slides, official docs, schedule listing, or gated-but-not-ingested material carries different confidence and replay behavior.
