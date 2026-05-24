---
name: agent-studio-content-production
description: "Produce source-backed social content packs for the multi-agent studio. Use when turning grounded briefs into ELI5 reels, Instagram posts, carousel copy, LinkedIn posts, YouTube Shorts scripts, or detailed-plus-ELI5 Substack drafts."
---

# Agent Studio Content Production

## Workflow

1. Start from a grounded brief, `data_brief`, and source ledger. Do not draft factual claims that lack source support.
2. Choose the content format: ELI5 short-form, platform post, carousel, reel script, or Substack article.
3. Draft in channel-native language:
   - Reels and posts: simple, concrete, vivid, and ELI5.
   - Substack: detailed argument with ELI5 explanation blocks and deeper technical sections.
4. Use `POST /api/runs/{run_id}/distribution-package`, or let the Platform Optimization, Influencer Strategy, or Outreach worker task invoke the same workflow, when current source-backed drafts need hooks, captions, hashtags, keywords, CTAs, and outreach angles.
5. Every first-draft artifact must carry source citations, claim trace, prompt input, model/provider provenance, and an initial guardrail review decision before it can be revised or packaged.
6. ELI5 and Substack worker passes must create versioned source-backed artifacts from current leaf drafts and emit `content_writer_artifacts_created`.
7. Send scripts through the Script Doctor for hook, pacing, retention, and spoken clarity; Script Doctor passes must create a versioned reel script and emit `script_doctor_artifacts_created`.
8. Send final drafts and distribution packages to the Editor-in-Chief, Claim Verification Agent, Guardrails Agent, and Influencer Strategy Agent before approval.
9. Editor-in-Chief and Critic/Reviewer worker passes must persist reviewer decisions directly on the current leaf artifacts and emit `editorial_review_completed`.

## Required Content Pack Fields

- `hook`
- `audience`
- `platform`
- `draft`
- `source_ids`
- `claim_ids`
- `source_citations`
- `claim_trace`
- `prompt_input`
- `model_provider`
- `model_id`
- `data_brief`
- `revision_history`
- `reviewer_decisions`
- `distribution_package` when platform-ready variants are requested

## Style Rules

- Prefer real-world examples over abstract explanation.
- Make technical topics understandable without removing important caveats.
- Keep unsupported claims out of final drafts.
- Treat distribution packages as publishable artifacts: they still need claim ids, source ids, guardrail audit, and human approval.
- Preserve user feedback as revision history, not hidden prompt context.
