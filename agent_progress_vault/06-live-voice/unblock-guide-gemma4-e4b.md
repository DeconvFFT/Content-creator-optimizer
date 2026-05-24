---
type: superseded-unblock-guide
updated: 2026-05-23
superseded_by: OpenRouter LiveKit integration
---

# Superseded Gemma 4 E4B Live Voice Guide

This guide is no longer the active unblock path.

Current live dialogue direction:

- Reasoning: OpenRouter `deepseek/deepseek-v4-flash`
- Transport: LiveKit, local dev URL `ws://127.0.0.1:7880`
- Speech output: Kokoro
- Active setup fields: `OPENROUTER_API_KEY_FILE`, `OPENROUTER_LIVEKIT_URL`, `LIVEKIT_API_KEY_FILE`, and `LIVEKIT_API_SECRET_FILE`

Do not open new Hugging Face, Gamma, Gemma, or MLX setup tasks for the current realtime dialogue proof unless a later architecture decision explicitly reverses the OpenRouter default. The legacy native-audio lane may remain as historical reference or optional non-default research only.

Use [[openrouter-livekit-live-dialogue]] and [[status-snapshot-2026-05-23]] for current proof context. Provider-backed live voice is accepted for OpenRouter `deepseek/deepseek-v4-flash` + LiveKit + Kokoro; the remaining active blocker is `external-publication-proof` plus completion-status recheck, closure review, and release/CI closure.
