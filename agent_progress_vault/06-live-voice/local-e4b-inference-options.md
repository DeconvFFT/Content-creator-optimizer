---
type: local-inference
updated: 2026-05-23
---

# Local E4B Inference Options (Mac / Apple Silicon)

> Superseded for the current live-dialogue default. As of 2026-05-23, Agent Studio uses OpenRouter `deepseek/deepseek-v4-flash` for text-turn reasoning, LiveKit for transport, and Kokoro for spoken output. Do not reopen MLX, Hugging Face, Gamma/Gemma, or `GEMMA4_MULTIMODAL_ENDPOINT_URL` setup for the current provider-backed live dialogue proof unless a future decision explicitly reactivates native Gemma audio.

Your machine: **arm64** (Apple Silicon). For the historical native-Gemma audio experiment, the recommended local stack was **MLX**, not vLLM/SGLang on GPU.

## Current Default

Use `[[openrouter-livekit-live-dialogue]]` and `[[status-snapshot-2026-05-23]]` for current live-dialogue work. The accepted proof gap is the same-run OpenRouter + LiveKit + Kokoro timing/proof record, not local E4B inference.

## What the Superseded Native-Gemma Path Expected

For legacy/native-audio background only, `GEMMA4_MULTIMODAL_ENDPOINT_URL` had to be a full HTTP(S) URL. The voice agent **POSTed** JSON with:

- `Authorization: Bearer <HF_TOKEN>`
- `Accept: text/event-stream`
- `messages` + optional `audio_base64` PCM attachments
- SSE response in OpenAI `chat.completion.chunk` shape

See `src/all_about_llms/voice_agent/adapters.py` → `_stream_gemma_chat_deltas`.

**Legacy implication:** Raw `mlx_vlm.server` OpenAI API may not accept our audio message shape. Use the **local proxy** only when intentionally testing the superseded native-Gemma path.

## Comparison

| Backend | Mac? | E4B audio | Fits app format? | Verdict |
|---------|------|-----------|------------------|---------|
| **MLX + mlx-vlm** | Yes | Yes (model supports audio) | Via **proxy** | **Recommended** |
| **vLLM** | No (CUDA) | — | — | Skip on Mac |
| **SGLang** | Limited | — | — | Skip on Mac |
| **vllm-mlx** | Yes | Claims audio in chat | Untested with our payload | Try later |
| **HF Inference Endpoint** | Cloud | Yes | If OpenAI-compatible | Production path |

## Model IDs

| Name | Hugging Face / MLX |
|------|---------------------|
| E4B edge (your choice) | `google/gemma-4-e4b-it` or `mlx-community/gemma-4-e4b-it-4bit` |
| E2B smaller | `mlx-community/gemma-4-e2b-it-4bit` (~5 GB) |

"EB4" in your notes = **E4B** in this codebase (`google/gemma-4-e4b-it`).

## Disk / RAM

- 4-bit E4B MLX: ~5–8 GB download, ~8–16 GB RAM at inference
- First run downloads from Hugging Face (needs network + HF token in env for gated models)
