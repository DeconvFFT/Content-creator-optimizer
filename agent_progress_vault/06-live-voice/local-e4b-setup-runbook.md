---
type: runbook
updated: 2026-05-23
---

# Legacy Local E4B Setup Runbook (MLX + Proxy)

> Superseded for current work: do not use this Hugging Face/Gemma/Gamma/MLX path as the realtime default. The active live-dialogue setup is OpenRouter DeepSeek V4 Flash + LiveKit + Kokoro; see [[openrouter-livekit-live-dialogue]] and [[local-livekit-setup]].

## Why a proxy?

Agent Studio sends **audio PCM as base64** in a custom streaming payload. `mlx_vlm.server` speaks OpenAI `/v1/chat/completions` for text/image. The repo proxy adapts audio turns to MLX-VLM.

## Prerequisites

- Apple Silicon Mac
- HF token in `.secrets/hf_token` (already done)
- LiveKit + Postgres running (see [[local-livekit-setup]])
- `uv` installed

## Step 1 — Install MLX-VLM (one time, ~GB download)

```bash
cd "/Users/saumyamehta/Gen AI/all-about-llms"
chmod +x scripts/setup-local-gemma-e4b-mlx.sh scripts/start-local-gemma-e4b-proxy.sh
./scripts/setup-local-gemma-e4b-mlx.sh
```

Leave this terminal running (MLX server on **8080**).

## Step 2 — Start audio proxy (second terminal)

```bash
cd "/Users/saumyamehta/Gen AI/all-about-llms"
./scripts/start-local-gemma-e4b-proxy.sh
```

Proxy listens on **8090** → `/gemma-audio-stream`

## Step 3 — Point Agent Studio at local endpoint

In `.env`:

```env
HF_TOKEN_FILE=.secrets/hf_token
LOCAL_PROVIDER_CONFIG_FILE=.secrets/local_provider_config.json
GEMMA4_MULTIMODAL_ENDPOINT_URL=http://127.0.0.1:8090/gemma-audio-stream
```

Or copy template:

```bash
cp .secrets/local_provider_config.json.template .secrets/local_provider_config.json
```

## Step 4 — App stack (terminals 3–5)

Same as [[local-livekit-setup]]:

1. `uv run all-about-llms`
2. `uv run all-about-llms-admin run-voice-agent --dev`
3. `cd frontend/next-app && npm run dev -- --hostname 127.0.0.1 --port 3000`

## Step 5 — Verify

```bash
curl -s http://127.0.0.1:8090/health
curl -s http://127.0.0.1:8000/api/provider-readiness | python3 -m json.tool | grep -A2 multimodal
```

Open http://127.0.0.1:3000 → Live Voice → create run → speak.

## Move to Hugging Face later

Swap one env var:

```env
GEMMA4_MULTIMODAL_ENDPOINT_URL=https://YOUR-ENDPOINT.endpoints.huggingface.cloud/v1/chat/completions
```

Stop local MLX + proxy. No code changes.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `gemma4-multimodal` still missing_config | Restart API after `.env` change |
| Proxy import error `mlx_vlm` | Run `./scripts/setup-local-gemma-e4b-mlx.sh` first |
| Model download slow | Normal first run; uses HF token |
| Preflight fails | Check proxy logs; ensure 8090 reachable |

## Files added (implementation)

- `scripts/setup-local-gemma-e4b-mlx.sh`
- `scripts/start-local-gemma-e4b-proxy.sh`
- `scripts/local_gemma_e4b_proxy.py`
