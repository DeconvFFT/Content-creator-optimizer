---
type: live-voice-setup
updated: 2026-05-23
status: local-first
---

# Local LiveKit Setup

Local realtime voice path for OpenRouter DeepSeek dialogue over LiveKit.

## Configured (or ready to configure)

| Item | Value | Status |
|------|-------|--------|
| LiveKit URL | `ws://127.0.0.1:7880` | Set in `.env` |
| LiveKit API key | `.secrets/livekit_api_key` → `devkey` | Local dev default |
| LiveKit API secret | `.secrets/livekit_api_secret` → `secret` | Local dev default |
| OpenRouter live dialogue | `deepseek/deepseek-v4-flash` | Ready for text-turn back-and-forth |
| Realtime default | `openrouter_livekit` | Current supported path |

## Step 1 — Ensure `.env`

```bash
cd "/Users/saumyamehta/Gen AI/all-about-llms"
test -f .env || cp .env.example .env
```

Confirm these lines in `.env`:

```env
REALTIME_DEFAULT_PROVIDER=openrouter_livekit
OPENROUTER_LIVEKIT_URL=ws://127.0.0.1:7880
LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key
LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret
OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key
OPENROUTER_REALTIME_REASONING_MODEL=deepseek/deepseek-v4-flash
OPENROUTER_REALTIME_AUDIO_INPUT_MODEL=deepseek/deepseek-v4-flash
```

## Step 2 — Start Docker (Postgres + LiveKit)

```bash
docker compose up -d postgres
docker compose --profile voice up -d livekit
docker compose ps
```

Expected: `postgres` on 5432, `livekit` on 7880.

## Step 3 — Database + voice deps

```bash
uv sync --extra voice
uv run all-about-llms-admin setup-durable-storage
cd services/voice-edge && cargo build && cd ../..
```

## Step 4 — Three terminals for browser test

**Terminal A — API**

```bash
cd "/Users/saumyamehta/Gen AI/all-about-llms"
uv run all-about-llms
```

**Terminal B — Voice agent (local dev)**

```bash
cd "/Users/saumyamehta/Gen AI/all-about-llms"
uv run all-about-llms-admin run-voice-agent --dev
```

**Terminal C — Creator UI**

```bash
cd "/Users/saumyamehta/Gen AI/all-about-llms/frontend/next-app"
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

## Step 5 — Browser

1. Open http://127.0.0.1:3000
2. Use **Live Voice** panel → **Create voice run**
3. Join room / start session when prompted
4. Operator cockpit: http://127.0.0.1:8000/cockpit

## What works with OpenRouter default

| Capability | Local? |
|------------|--------|
| LiveKit transport connect | Yes (with Docker LiveKit) |
| Kokoro TTS package check | Yes |
| Rust voice-edge VAD | Yes (after `cargo build`) |
| Voice run creation in UI | Yes |
| OpenRouter live dialogue via **Send text turn** | Yes |
| Kokoro spoken replies over LiveKit | Yes |
| Native Gemma/Gamma audio understanding | Not used for the current path |

Check readiness:

```bash
curl -s http://127.0.0.1:8000/api/provider-readiness | python3 -m json.tool
```

Look for `openrouter-live-dialogue-reasoning` -> ready for the OpenRouter text-turn path. Do not treat `gemma-audio-reasoning` or Hugging Face config as the current live-dialogue blocker.

## Security

- Keep OpenRouter and LiveKit secrets in `.secrets/*` files; do not paste token values into vault notes.
- LiveKit `devkey`/`secret` are **local dev only** — never use in production.

## Related

- [[operator-inputs-checklist]]
