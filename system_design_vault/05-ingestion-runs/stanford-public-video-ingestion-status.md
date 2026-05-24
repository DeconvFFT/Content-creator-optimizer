---
type: public-video-ingestion-status
project: agent-studio-system-design
status: active
updated: 2026-05-19
manifest: stanford-public-video-ingestion-status.json
sources:
  - https://web.stanford.edu/class/cs25/recordings/
  - https://www.youtube.com/playlist?list=PLoROMvodv4rNiJRchCzutFw5ItR_Z27CM
---

# Stanford Public Video Ingestion Status

## Purpose

This ledger tracks official public Stanford video candidates separately from lecture notes. It records which CS25 selected recordings are visible on the official Stanford recordings page, which official YouTube video metadata was checked, and whether a direct full-watch pass has actually happened.

It is a control-plane record, not a source-understanding note. It stores no downloaded videos, raw captions, transcripts, timestamp dumps, or long excerpts.

## Current Boundary

The official CS25 recordings page was refreshed on 2026-05-19. Nine selected public recordings are visible and each YouTube page exposes Stanford Online metadata. The current pass still does not promote any selected recording to watched-video coverage because transcript, caption, comment, and metadata review are not substitutes for directly watching the full video.

One exception now matters for source provenance: the official public YouTube transcript for `Retrieval Augmented Language Models` was fetched directly on 2026-05-19 and used to refresh `02-lectures/stanford/cs25-retrieval-augmented-language-models.md`. That note remains transcript-backed rather than watched-video coverage.

The linked canon notes remain valid as source-aware synthesis from official pages, schedules, primary/open materials, and now one official transcript-backed refresh. They should not be described as full-watch video notes unless a direct full viewing pass actually happens.

## Current Records

| Recording | Speaker/source | Linked note | Public recording visible | Full video watched |
|---|---|---|---:|---:|
| Stanford CS25: V6 Overview of Transformers | Instructors | `02-lectures/stanford/cs25-transformer-foundations.md` | yes | no |
| On the Tradeoffs of State Space Models and Transformers | Albert Gu, CMU and Cartesia AI | `02-lectures/stanford/cs25-state-space-transformer-tradeoffs.md` | yes | no |
| Introduction to Transformers | Instructors and Andrej Karpathy | `02-lectures/stanford/cs25-transformer-foundations.md` | yes | no |
| Intuition on LMs, Shaping the Future of AI | Jason Wei and Hyung Won Chung | `02-lectures/stanford/cs25-lm-intuition-future-ai.md` | yes | no |
| Stop Worrying and Love the Transformer | Ashish Vaswani | `02-lectures/stanford/cs25-transformer-foundations.md` | yes | no |
| Aligning Open Language Models | Nathan Lambert | `02-lectures/stanford/cs25-aligning-open-language-models.md` | yes | no |
| Retrieval Augmented Language Models | Douwe Kiela, Contextual AI | `02-lectures/stanford/cs25-retrieval-augmented-language-models.md` | yes | no; official transcript used |
| Generalist Agents in Open-Ended Worlds | Jim Fan, NVIDIA AI | `02-lectures/stanford/cs25-generalist-agents-open-ended-worlds.md` | yes | no |
| Whole-Part Hierarchies in a Neural Network | Geoffrey Hinton | `02-lectures/stanford/cs25-whole-part-hierarchies.md` | yes | no |

## Video Lists By Topic Note

These are official public video pointers already represented as separate sections inside the linked topic notes. They are playlist/navigation candidates only until a direct full-watch pass creates compact original video notes.

| Topic note | Official video candidates |
|---|---|
| `02-lectures/stanford/cs25-transformer-foundations.md` | Overview of Transformers; Introduction to Transformers; Stop Worrying and Love the Transformer |
| `02-lectures/stanford/cs25-state-space-transformer-tradeoffs.md` | On the Tradeoffs of State Space Models and Transformers |
| `02-lectures/stanford/cs25-lm-intuition-future-ai.md` | Intuition on LMs, Shaping the Future of AI |
| `02-lectures/stanford/cs25-aligning-open-language-models.md` | Aligning Open Language Models |
| `02-lectures/stanford/cs25-retrieval-augmented-language-models.md` | Retrieval Augmented Language Models |
| `02-lectures/stanford/cs25-generalist-agents-open-ended-worlds.md` | Generalist Agents in Open-Ended Worlds |
| `02-lectures/stanford/cs25-whole-part-hierarchies.md` | Whole-Part Hierarchies in a Neural Network |

## Promotion Rule

Promote an individual video to watched-video coverage only when this is true:

- the official public video is directly watched in full and compact original notes are written from the watched content.

Official lecture slides, notes, captions, transcripts, comments, and metadata may support source discovery or cross-checks, but they do not promote a record to watched-video coverage.

## Agent Studio Implications

- The datastore needs a separate video availability record from a video understanding record.
- Playlist and recording-page links are useful for routing, but cannot be watched-video route evidence until the video is directly watched in full.
- Video notes should carry `public_recording_visible`, `video_watch_ingested`, `raw_transcript_stored`, `caption_track_count`, source URL, linked note path, checked date, watch status, and remaining visual/audio gaps.
- Captions and transcripts are useful accessibility and verification metadata, but they do not replace full viewing.
- Public video ingestion should remain compact: concepts, failure modes, Agent Studio design implications, and open gaps only.
