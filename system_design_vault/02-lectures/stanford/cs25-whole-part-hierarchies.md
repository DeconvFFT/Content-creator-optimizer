---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS25 Transformers United"
lecture_title: "Whole-Part Hierarchies in a Neural Network"
speaker: "Geoffrey Hinton"
source_status: official_public_video_pointer
updated: 2026-05-18
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://web.stanford.edu/class/cs25/recordings/
  - https://www.youtube.com/playlist?list=PLoROMvodv4rNiJRchCzutFw5ItR_Z27CM
  - https://arxiv.org/abs/2102.12627
related:
  - "[[../../03-patterns/transformer-systems/cs25-transformer-systems-canon]]"
  - "[[../../03-patterns/vision-multimodal/visual-multimodal-qa-canon]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# CS25 - Whole-Part Hierarchies

## Reading Status

Canon-ready source synthesis from the official Stanford CS25 recordings page entry for "Whole-Part Hierarchies in a Neural Network" by Geoffrey Hinton, rechecked on 2026-05-18, plus Hinton's open arXiv paper on representing part-whole hierarchies. The CS25 recordings page exposes the lecture as a public YouTube pointer, but this note does not claim a full video-watch pass, timestamp-level coverage, or transcript ingestion.

## Core Pattern

Whole-part hierarchy is a representation problem: the same fixed neural architecture must represent a different compositional structure for each input. In visual and multimodal products, that matters because evidence is rarely a single flat object. A product image has regions, objects, labels, relations, style constraints, edit masks, claims, and generated variants. A video has frames, shots, actions, objects, transitions, captions, and audio alignment.

Agent Studio should therefore avoid treating a media artifact as one embedding or one caption. It needs a part-whole evidence graph that can say which region, frame, object, claim, source, or edit belongs to which higher-level artifact.

## GLOM As Design Signal

Hinton's GLOM proposal is explicitly presented as an idea rather than a working production system. That boundary is useful. The Agent Studio takeaway is not to implement GLOM; it is to preserve compositional state so models, reviewers, and tools can reason about parts and wholes without losing provenance.

Useful translation:

- image or video artifact: the whole;
- regions, masks, frames, tracks, captions, claims, and source snippets: parts;
- relation edges: part-of, supports, contradicts, edited-from, generated-from, visible-in-frame, refers-to;
- reviewer/eval checks: evidence that the part-whole structure is valid enough to drive a decision.

## Interpretability Boundary

Part-whole representations can make model behavior more interpretable only if the product stores the structure explicitly. A hidden embedding or attention map is not enough for editorial QA. Agent Studio should expose user-facing or reviewer-facing evidence records: "this claim is supported by this region/source/frame" and "this edit changed these dependent parts."

For generated media, the same structure protects quality and rights. A generated variant should know which input asset, prompt, mask, region, voice, style reference, model, and safety decision contributed to it.

## Datastore Requirements

Add or strengthen:

| Object | Purpose |
|---|---|
| `part_whole_evidence_graph` | Graph connecting artifact wholes to regions, frames, tracks, source snippets, claims, prompts, edits, and approvals. |
| `media_part_record` | Region, mask, frame span, object track, caption segment, audio segment, or source snippet with provenance and coordinate/time metadata. |
| `composition_relation_record` | Typed edge such as part-of, supports, contradicts, generated-from, edited-from, visible-in-frame, or refers-to. |
| `hierarchical_consistency_eval` | Eval slice checking whether local parts and global artifact claims agree. |
| `part_whole_release_gate` | Promotion gate proving artifact decisions preserve part-whole evidence, provenance, evals, fallback, rollback, and human review. |

## Agent Studio Design Implications

- Media QA should store region/frame/track evidence rather than only whole-asset verdicts.
- Multimodal retrieval should return part-level evidence with whole-artifact context.
- Editing and generation routes should invalidate dependent claims, captions, approvals, and publish checks when a part changes.
- Reviewer UI should be able to traverse from artifact to part to source and back.
- Interpretability claims must be backed by explicit evidence graphs, not model-internal attention alone.
- Whole-artifact quality checks should include local-part consistency and cross-part contradiction checks.

## Failure Modes

- Flattening an artifact into one caption or embedding and losing which part supports which claim.
- Approving an edited asset without invalidating dependent captions, alt text, or source claims.
- Treating a model's internal representation as an audit trail.
- Running visual QA only at whole-image level when the failure is localized.
- Reusing a style/reference asset without preserving rights and provenance at the part level.

## Related Official Video Sources

This public Stanford Online video pointer is listed from the official CS25 recordings page and tracked in [[../../05-ingestion-runs/stanford-public-video-ingestion-status]]. It is a navigation source only until a direct full-watch pass is completed; no raw captions, transcripts, comments, or long excerpts are stored.

| Video | URL | Status |
|---|---|---|
| Stanford CS25: V2 I Represent part-whole hierarchies in a neural network, Geoff Hinton | https://www.youtube.com/watch?v=CYaju6aCMoQ | candidate; not watched in full |
