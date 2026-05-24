---
type: runbook
updated: 2026-05-23
---

# OpenRouter + LiveKit Live Dialogue

Live voice dialogue no longer depends on local MLX servers (`8080` Gemma MLX, `8090` proxy). Reasoning runs through **OpenRouter**; transport, turn-taking, VAD, and spoken output still run through **LiveKit + Kokoro**.

## Model routing

| Role | Provider | Model ID |
|------|----------|----------|
| Live dialogue reasoning | OpenRouter | `deepseek/deepseek-v4-flash` |
| Spoken output | Local Kokoro package or hosted endpoint | `hexgrad/Kokoro-82M` |
| Realtime transport | Local LiveKit dev | `ws://127.0.0.1:7880` |

OpenRouter is **text-only**. Use the Live Voice panel **Send text turn** composer for provider-backed back-and-forth dialogue. Raw microphone PCM is not sent to OpenRouter; microphone turns prompt the user to repeat via text turn.

## Required env vars (no secrets)

```bash
# OpenRouter
OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key
OPENROUTER_CHAT_COMPLETIONS_URL=https://openrouter.ai/api/v1/chat/completions
GEMMA4_REALTIME_REASONING_MODEL=deepseek/deepseek-v4-flash
GEMMA4_REALTIME_AUDIO_INPUT_MODEL=deepseek/deepseek-v4-flash

# LiveKit (local dev)
REALTIME_DEFAULT_PROVIDER=openrouter_livekit
OPENROUTER_LIVEKIT_URL=ws://127.0.0.1:7880
LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key
LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret

# Voice agent + backend sink
VOICE_AGENT_BACKEND_EVENT_SINK_URL=http://127.0.0.1:8000
LIVEKIT_AGENT_NAME=openrouter-kokoro-agent
```

Do **not** set Hugging Face, Gamma/Gemma, or MLX as the default realtime path. Remove any `http://127.0.0.1:8090/...` value from `.env` and `.secrets/local_provider_config.json`.

## Startup commands

```bash
# 1. Infrastructure
docker compose --profile voice up -d postgres livekit

# 2. API
uv run uvicorn all_about_llms.app:app --host 127.0.0.1 --port 8000 --reload

# 3. Voice agent (separate terminal)
uv run all-about-llms-admin run-voice-agent --dev

# 4. Frontend
cd frontend/next-app && npm run dev
```

## Browser test

1. Open `http://127.0.0.1:3000` (or `3001`).
2. Create or open a run → **Live Voice**.
3. Confirm **Provider readiness** and **Runtime preflight** show `openrouter-live-dialogue-reasoning` ready for the OpenRouter text-turn path. `gemma-audio-reasoning` is legacy/optional and must not be treated as the current live-dialogue blocker.
4. Start local LiveKit if needed, **Start voice agent**, join room.
5. Wait for agent presence **ready**.
6. Type a prompt in **Send text turn** → hear Kokoro reply over LiveKit.

## What changed from MLX

| Before (MLX) | After (OpenRouter) |
|--------------|-------------------|
| `GEMMA4_MULTIMODAL_ENDPOINT_URL=http://127.0.0.1:8090/gemma-audio-stream` | unset / not used |
| Local MLX on `:8080`, proxy on `:8090` | not required |
| Native Gemma/Gamma audio model path | OpenRouter text chat streaming |
| Gemma/Gamma reasoning model | `deepseek/deepseek-v4-flash` |

You can stop/kill MLX processes on ports `8080` and `8090`.

## Readiness endpoints

```bash
curl -sS http://127.0.0.1:8000/api/provider-readiness | jq '.ready_provider_ids, .missing_provider_ids'
curl -sS 'http://127.0.0.1:8000/api/voice-runtime-readiness?preflight_gemma=true&preflight_tts=true&preflight_livekit=true&preflight_edge=true&preflight_agent=true' \
  | jq '.checks[] | select(.check_id=="openrouter-live-dialogue-reasoning")'
```

## Related notes

- [[local-livekit-setup]] — LiveKit container + credentials
- [[status-snapshot-2026-05-23]] — prior MLX-blocked snapshot (superseded for live dialogue)
