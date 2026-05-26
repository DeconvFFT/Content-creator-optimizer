# Voice Edge

Rust boundary for the realtime voice path.

This crate owns the low-latency voice-edge contract for:

- frame-level voice activity decisions,
- bounded inbound audio buffers,
- barge-in detection while the assistant is speaking,
- cancellation acknowledgements for selected realtime-provider/OpenRouter response generation, Kokoro buffers, and LiveKit audio output.

The current implementation supports both deterministic local tests and real Silero ONNX inference. The request config accepts explicit VAD backend selection:

- `deterministic_energy` is the default effective backend.
- `silero_onnx` runs the bundled Silero ONNX model through the Rust `silero` crate, or a custom model file when `vad_model_path` is set.
- loaded Silero ONNX sessions are cached in a bounded process-wide pool keyed by model source and session id, so model bootstrap is not repeated on every VAD request and concurrent sessions do not all share one global inference lock.
- each session-pool slot keeps bounded recurrent `StreamState` entries keyed by stream id and sample rate, so short realtime frames reuse Silero context across JSONL/HTTP requests while the Rust process is alive.
- `vad_probability_threshold` controls Silero speech probability; `vad_threshold` remains the deterministic RMS threshold.
- `allow_vad_fallback=false` makes a failed Silero load/inference conservative instead of silently using energy-gate speech decisions.

The remaining production sidecar work is benchmarking/tuning the session-pool and stream-state cache sizing under concurrent streams, and the direct LiveKit-side Rust media bridge while preserving this typed request and cancellation contract.

Run locally:

```bash
cargo test
```

The CLI supports one-shot JSON, persistent JSONL, and HTTP sidecar modes:

```bash
# One request per process, useful for debugging.
voice-edge < request.json

# Long-running newline-delimited JSON mode for realtime callers.
voice-edge --jsonl

# Supervised HTTP sidecar mode.
voice-edge --http 127.0.0.1:7071
voice-edge serve

# Built-in usage and version output.
voice-edge --help
voice-edge --version
```

The JSONL mode reads one typed request per line and writes one compact response per line. Python's `PersistentRustVoiceEdgeClient` uses this mode so realtime audio frames do not pay process startup cost on every VAD check.

HTTP endpoints:

- `GET /healthz` returns service, transport, VAD backend, supported-backend, and state-model metadata.
- `POST /v1/voice-edge` accepts the tagged `VoiceEdgeRequest` contract, for example `{"kind":"analyze", ...}` or `{"kind":"cancel", ...}`.
- `POST /v1/voice-edge/analyze` accepts `AnalyzeVoiceRequest`.
- `POST /v1/voice-edge/cancel` accepts `CancelVoiceRequest`.

The HTTP sidecar is stateless request/response today. It is the correct service boundary for process supervision and typed cancellation testing, but the current Python LiveKit participant still uses the persistent JSONL bridge until the streaming session client is switched over.
