---
name: agent-studio-media-design
description: "Plan visuals, audio, reels, generated images, and separate interactive HTML planning surfaces for the multi-agent studio. Use when creating visual direction, imagegen prompts, storyboards, subtitles, voice direction, UI/UX critique, or animated system-design HTML artifacts."
---

# Agent Studio Media Design

## Workflow

1. Identify whether the request is product UI, media output, or separate planning HTML. Keep these surfaces separate.
2. For planning artifacts, create standalone interactive HTML with embedded JSON state for decisions, risks, diagrams, and revision history.
3. When the planning artifact captures suggestions, let it submit saved items to `POST /api/planning/feedback` so they become durable feedback, specialist A2A tasks, memory notes, and planning timeline events.
4. For run knowledge surfaces, let Interactive Note-Taking worker tasks generate standalone HTML notes from durable turns, tasks, sources, claims, artifacts, feedback, audits, and events.
5. Let Artifact Librarian worker tasks index artifact provenance, media outputs, revision edges, review state, and retrieval facets.
6. Let Lead UI/UX Designer worker tasks persist `ux_review` artifacts for cockpit flow, planning boundary, voice controls, feedback state, and source/artifact visibility.
7. Let Interactive Systems Designer worker tasks persist `planning_surface_review` artifacts from the standalone HTML, embedded JSON state, interactions, boundaries, and planning feedback.
8. Use `multimodal_intake_ledger` artifacts when incoming screenshots, images, audio, voice, video, reels, or documents need specialist analysis before generation.
9. Let `review_multimodal_intake` worker tasks persist `multimodal_review` artifacts with per-agent focus, provider boundaries, and next actions before producing downstream media plans. When `use_gemma` is enabled and the agent card permits Gemma, the worker should use the configured Hugging Face Gemma provider with asset references and record model id, usage, policy approval, and fallback events.
10. After a multimodal review is complete, materialize idempotent follow-up A2A tasks for the next specialist unless a human feedback gate is open. Use context packets, manager coordination, planning notes, voice-context routing, or imagegen prompt-pack preparation depending on the reviewing agent and asset modality.
11. When a follow-up task explicitly targets a `multimodal_review` artifact, downstream media workers may use it as a planning input while preserving the asset-reference boundary and avoiding unsupported source claims.
12. Let Visual Director worker tasks persist source-linked visual briefs for thumbnails, diagrams, carousels, image prompts, and reel scenes.
13. Let Image Generation Agent worker tasks persist source-linked imagegen prompt packs before raster generation is invoked.
14. Let Audio Producer worker tasks persist source-linked audio briefs before realtime or TTS provider playback is invoked.
15. Let Video/Reel Producer worker tasks persist source-linked reel storyboards with scene timing, subtitles, media dependencies, and QA checks.
16. For raster visuals, route through `imagegen` and store prompt, provider, source dependencies, and artifact provenance.
17. For reels/video, produce storyboard, timing, scene list, captions/subtitles, and visual asset requirements.
18. For audio, specify voice style, pacing, pronunciation notes, provider choice, and QA criteria.

## Design Rules

- Product app UI should feel like a live conversational studio, not a project tracker.
- Planning HTML may use animation, diagrams, filters, and inspectable state because it is for system design.
- Do not place the planning system inside the product app.
- Use Gemma 4 multimodal experts for screenshot, frame, chart, and UI critique when available; direct binary upload is provider-adapter specific, so reviews must be honest when they only received asset references and metadata.

## Outputs

- `visual_brief`
- `visual_system_brief`
- `imagegen_prompt`
- `imagegen_prompt_pack`
- `storyboard`
- `reel_storyboard`
- `audio_brief`
- `realtime_audio_plan`
- `multimodal_intake_ledger`
- `multimodal_review`
- `planning_html_spec`
- `interactive_note`
- `artifact_index`
- `ux_review`
- `planning_surface_review`
