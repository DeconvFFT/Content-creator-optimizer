---
type: next-ingestion-queue
project: agent-studio-system-design
status: active
updated: 2026-05-21
manifest: next-ingestion-queue.json
---

# Next Ingestion Queue

## Purpose

`next-ingestion-queue.json` turns the current recommended next targets into machine-readable queue records. It is a control-plane queue, not a source note. Its job is to tell future ingestion agents what to recheck, what is blocked, what can be read now, and what must not be promoted without better evidence.

## Current Queue

| Priority | Queue item | Status | Allowed action |
|---:|---|---|---|
| 1 | Stanford CS336 Spring 2026 alignment refresh | `active_public_materials_increment_available` | Use current 2026 Lecture 15 and Lecture 16 as the live direct-read SFT/RLHF/DPO/RLVR anchor set, keep Lecture 17 blocked until the official current course page visibly exposes a public material link again, and spend no-delta cycles on compact maintenance only when they add genuinely new RL-systems evidence. Do not claim watched-video understanding from recording pointers or promote hidden/guessed artifacts. |
| 2 | Stanford CS25 May 21 Victoria Lin / Thinking Machines slot | `future_pending_public_materials` | Public title and abstract now exist; recheck after official materials or a public recording appears. |
| 3 | Stanford CS25 May 28 production inference recording/materials check | `future_pending_recording_materials` | Keep existing schedule-plus-primary-source note; recheck after lecture and recording delay. |
| 4 | Direct full-watch passes for selected public Stanford recordings | `eligible_but_not_required_for_existing_canon` | Watch official public video in full when video-specific nuance is needed; write compact original notes only. |
| 5 | Unresolved high-value local book gaps | `active_trigger_queue` | Use `unresolved-high-value-book-gaps.md` and its JSON manifest to select the smallest remaining local-book slice that can materially improve a live Agent Studio route or release gate. |
| 6 | Deferred local books | `deferred_until_gap_exists` | Promote only the smallest relevant slice if a concrete Agent Studio gap appears. |
| 7 | Weekly vault map, manifest, and safety audit | `active_recurring` | Run JSON, path, wiki-link, raw-payload, local-folder, and excluded-source checks after any source or manifest change. |

## Guardrails

- Queue membership is not canon evidence.
- Future-dated or gated material stays blocked until public official material exists.
- Public video URLs are navigation evidence until the videos are directly watched in full.
- Local deferred books should not be broadly summarized to create activity; use them only to answer concrete architecture gaps.
- Use `deferred-local-corpus-queue.json` before touching any deferred local file; it records per-file trigger and promotion policy.
- Maintenance audits should update counts in the audit notes and status summary.

## Latest Queue Evidence

- `queue.stanford_cs336_2026_alignment_refresh` was rechecked again on 2026-05-21 against the official CS336 course page. Queue-changing correction found: Lecture 16 still visibly exposes `lecture_16.pdf`, but the Lecture 17 row is currently schedule text only and the only Lecture 17 artifact in page source is a commented-out non-visible link. Keep Lecture 17 blocked until a visible official public material link reappears; use the live Lecture 16 + Assignment 5 anchor set for compact maintenance instead.
- `queue.stanford_cs336_2026_alignment_refresh` was rechecked again on 2026-05-20 late evening against the official CS336 course page. The visible official schedule still exposes a public Lecture 16 PDF link (`lecture_16.pdf`) for `Post-training - RLVR [Tatsu]`, but it does not currently expose a visible Lecture 17 material link. Treat the earlier same-day Lecture 17 visibility assumption as stale and keep Lecture 17 blocked until a visible official public link reappears.
- `queue.stanford_cs336_2026_alignment_refresh` was rechecked again on 2026-05-21 just after midnight against the official CS336 course page. No queue-changing delta: Lecture 16 still visibly exposes `lecture_16.pdf` and remains the live official RLVR anchor, while Lecture 17 still appears only as schedule text with no visible public material link. Keep Lecture 17 blocked until a visible official link reappears.
- `queue.cs25_may21_human_agency_slot` was rechecked on 2026-05-20 against the official CS25 V6 page and recordings page. The schedule now lists May 21 as `From Language Models to Native Multimodal Intelligence`, speaker Victoria Lin from Thinking Machines, and the official course row now includes a public abstract, but it still does not expose slides/materials and the recordings page still does not expose the slot as a selected public recording. Keep the item future-pending; do not create a direct source note from the title/abstract alone.
- `queue.cs25_may28_production_inference_recording_check` was rechecked on 2026-05-20 against the official CS25 V6 page and recordings page. The schedule still lists May 28 `Serving Transformers: Lessons from the Trenches of Production Inference`, speaker Charles Frye from Modal, with public description, but the recordings page still does not expose this slot as a selected public recording. Keep existing schedule-plus-primary-source coverage and recheck after May 28 plus the expected recording delay.
