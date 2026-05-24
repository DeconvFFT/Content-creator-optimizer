---
type: quality-log
updated: 2026-05-23
---

# Errors And Failures

## 2026-05-23 - Cursor LiveKit setup interruption

- severity: infrastructure
- surface: Cursor subagent transcript `6255c42f-a428-4bb6-ac71-823c96754971`
- symptom: subagent stopped with `WritableIterable is closed` after starting read/glob/grep setup calls
- impact: setup work did not complete in that subagent, but this is not evidence of a LiveKit, Docker, OpenRouter, or app-code failure
- follow-up evidence: outside-sandbox checks at 2026-05-23 16:53 CDT showed Docker LiveKit/Postgres up, FastAPI `/health` ready, `livekit-transport` ready, `openrouter-live-dialogue-reasoning` ready, Kokoro ready, Rust voice-edge ready, and Cursor had an externally launched `run-voice-agent --dev` process
- remaining product proof blocker: accepted OpenRouter `deepseek/deepseek-v4-flash` + LiveKit + Kokoro proof-record capture/recheck still must verify LiveKit transport, the LiveKit agent participant, backend event sink, OpenRouter live-dialogue reasoning, Kokoro TTS, and Rust voice edge where applicable; native Gemma/Gamma endpoint setup is superseded legacy/optional, not the current blocker. External publication proof still needs LinkedIn credential/policy/destination/rollback evidence
