import base64
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import httpx

from all_about_llms.providers.interfaces import (
    ProviderConfigurationError,
    RealtimeSessionRequest,
    RealtimeSessionResponse,
)
from all_about_llms.voice_agent.control_binding import (
    build_livekit_control_binding_token,
)
from all_about_llms.voice_agent.edge import describe_vad_runtime


def _mint_livekit_join_token(
    *,
    api_key: str,
    api_secret: str,
    room_name: str,
    participant_identity: str,
    agent_identity: str,
    ttl_seconds: int,
    metadata: dict[str, str],
    agent_name: str | None = None,
    agent_dispatch_metadata: dict[str, object] | None = None,
) -> tuple[str, int]:
    now = int(time.time())
    expires_at = now + ttl_seconds
    payload = {
        "iss": api_key,
        "sub": participant_identity,
        "nbf": now,
        "exp": expires_at,
        "video": {
            "room": room_name,
            "roomJoin": True,
            "canPublish": True,
            "canPublishData": True,
            "canSubscribe": True,
        },
        "metadata": json.dumps(
            {
                **metadata,
                "agent_identity": agent_identity,
            },
            separators=(",", ":"),
        ),
    }
    if agent_name:
        dispatch_metadata = _string_metadata(
            agent_dispatch_metadata
            or {
                **metadata,
                "room_name": room_name,
                "participant_identity": participant_identity,
                "agent_participant_identity": agent_identity,
            }
        )
        payload["roomConfig"] = {
            "agents": [
                {
                    "agentName": agent_name,
                    "metadata": json.dumps(
                        dispatch_metadata,
                        separators=(",", ":"),
                    ),
                }
            ]
        }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _base64url_json(header),
            _base64url_json(payload),
        ]
    )
    signature = hmac.new(
        api_secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_base64url(signature)}", expires_at


def _base64url_json(payload: dict[str, object]) -> str:
    return _base64url(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )


def _base64url(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _string_metadata(metadata: dict[str, object]) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in metadata.items()
        if value is not None and str(value) != ""
    }


class OpenAIRealtimeProvider:
    def __init__(self, *, api_key: str | None, model: str):
        self._api_key = api_key
        self._model = model

    async def create_session(
        self, request: RealtimeSessionRequest
    ) -> RealtimeSessionResponse:
        if not self._api_key:
            raise ProviderConfigurationError("OPENAI_API_KEY is not configured.")

        payload = {
            "session": {
                "type": "realtime",
                "model": self._model,
                "instructions": request.instructions,
                "audio": {
                    "output": {
                        "voice": request.voice or "marin",
                    },
                    "input": {
                        "transcription": {
                            "model": str(
                                request.metadata.get("transcription_model")
                                or "gpt-4o-mini-transcribe"
                            ),
                            "language": str(
                                request.metadata.get("transcription_language") or "en"
                            ),
                        },
                        "turn_detection": {
                            "type": "semantic_vad",
                            "interrupt_response": True,
                            "create_response": True,
                            "eagerness": "auto",
                        }
                    },
                },
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            raw = response.json()

        secret = raw.get("value") or raw.get("client_secret", {}).get("value")
        return RealtimeSessionResponse(
            provider="openai_realtime",
            session_id=raw.get("id", request.run_id),
            client_secret=secret,
            expires_at_unix=raw.get("expires_at"),
            metadata={
                "raw_response": raw,
                "model": self._model,
                "connection_transport": "webrtc_ephemeral",
                "webrtc_offer_url": "https://api.openai.com/v1/realtime/calls",
                "realtime_interaction": "speech_to_speech",
                "input_transcription_model": str(
                    request.metadata.get("transcription_model")
                    or "gpt-4o-mini-transcribe"
                ),
                "input_transcription_language": str(
                    request.metadata.get("transcription_language") or "en"
                ),
            },
        )


class OpenSourceRealtimeVoiceProvider:
    def __init__(
        self,
        *,
        websocket_url: str | None,
        stt_model: str,
        llm_model: str,
        tts_model: str,
        audio_format: str,
        sample_rate: int,
    ):
        self._websocket_url = websocket_url
        self._stt_model = stt_model
        self._llm_model = llm_model
        self._tts_model = tts_model
        self._audio_format = audio_format
        self._sample_rate = sample_rate

    async def create_session(
        self, request: RealtimeSessionRequest
    ) -> RealtimeSessionResponse:
        if not self._websocket_url:
            raise ProviderConfigurationError(
                "OPEN_SOURCE_REALTIME_WS_URL is not configured."
            )

        return RealtimeSessionResponse(
            provider="open_source_realtime",
            session_id=f"open-source-{request.run_id}",
            websocket_url=self._websocket_url,
            metadata={
                "connection_transport": "websocket_pcm",
                "realtime_interaction": "speech_to_speech",
                "audio_format": self._audio_format,
                "sample_rate": self._sample_rate,
                "input_sample_rate": self._sample_rate,
                "output_sample_rate": self._sample_rate,
                "stt_model": request.metadata.get("stt_model") or self._stt_model,
                "llm_model": request.metadata.get("llm_model") or self._llm_model,
                "tts_model": request.metadata.get("tts_model") or self._tts_model,
                "recommended_runtime": "huggingface/speech-to-speech",
                "protocol": (
                    "Client sends mono PCM16 audio bytes and may receive JSON "
                    "transcript/control events plus PCM16 audio bytes."
                ),
            },
        )


class Gemma4RealtimeVoiceProvider:
    def __init__(
        self,
        *,
        provider_name: str = "openrouter_livekit",
        transport_framework: str,
        livekit_url: str | None,
        livekit_api_key: str | None,
        livekit_api_secret: str | None,
        livekit_token_ttl_seconds: int,
        websocket_url: str | None,
        audio_input_model: str,
        reasoning_model: str,
        audio_output_model: str,
        audio_format: str,
        sample_rate: int,
        context_prune_after_turns: int,
        max_audio_seconds_per_turn: int,
        rust_vad_model: str,
        livekit_agent_name: str | None = "openrouter-kokoro-agent",
        rust_vad_backend: str = "deterministic_energy",
        rust_vad_fallback_allowed: bool = True,
        gemma_streaming_enabled: bool = True,
    ):
        self._provider_name = provider_name
        self._transport_framework = transport_framework
        self._livekit_url = livekit_url
        self._livekit_api_key = livekit_api_key
        self._livekit_api_secret = livekit_api_secret
        self._livekit_agent_name = livekit_agent_name
        self._livekit_token_ttl_seconds = livekit_token_ttl_seconds
        self._websocket_url = websocket_url
        self._audio_input_model = audio_input_model
        self._reasoning_model = reasoning_model
        self._audio_output_model = audio_output_model
        self._audio_format = audio_format
        self._sample_rate = sample_rate
        self._context_prune_after_turns = context_prune_after_turns
        self._max_audio_seconds_per_turn = max_audio_seconds_per_turn
        self._rust_vad_model = rust_vad_model
        self._rust_vad_backend = rust_vad_backend
        self._rust_vad_fallback_allowed = rust_vad_fallback_allowed
        self._gemma_streaming_enabled = gemma_streaming_enabled

    async def create_session(
        self, request: RealtimeSessionRequest
    ) -> RealtimeSessionResponse:
        if not (self._livekit_url or self._websocket_url):
            livekit_env_name = (
                "OPENROUTER_LIVEKIT_URL"
                if self._provider_name == "openrouter_livekit"
                else "GEMMA4_REALTIME_LIVEKIT_URL"
            )
            raise ProviderConfigurationError(
                f"{livekit_env_name} is not configured for LiveKit production transport."
            )

        production_transport = (
            self._transport_framework
            if self._transport_framework in {"livekit", "pipecat", "livekit_pipecat"}
            else "livekit"
        )
        room_name = str(
            request.metadata.get("room_name") or f"agent-studio-{request.run_id}"
        )
        participant_identity = str(
            request.metadata.get("participant_identity")
            or f"creator-{request.run_id}"
        )
        agent_identity = str(
            request.metadata.get("agent_participant_identity")
            or request.metadata.get("agent_identity")
            or f"openrouter-livekit-agent-{request.run_id}"
        )
        realtime_session_id = str(request.metadata.get("realtime_session_id") or "")
        control_binding_token = build_livekit_control_binding_token(
            self._livekit_api_secret,
            run_id=str(request.run_id),
            realtime_session_id=realtime_session_id,
            room_name=room_name,
            participant_identity=participant_identity,
            agent_identity=agent_identity,
        )
        websocket_url = (
            self._websocket_url
            if production_transport not in {"livekit", "pipecat", "livekit_pipecat"}
            else None
        )
        vad_contract = describe_vad_runtime(
            vad_backend=self._rust_vad_backend,
            allow_vad_fallback=self._rust_vad_fallback_allowed,
        )
        expires_at_unix = None
        token = None
        if self._livekit_api_key and self._livekit_api_secret and self._livekit_url:
            dispatch_metadata = {
                "provider": self._provider_name,
                "run_id": request.run_id,
                "realtime_session_id": realtime_session_id,
                "room_name": room_name,
                "participant_identity": participant_identity,
                "agent_identity": agent_identity,
                "agent_participant_identity": agent_identity,
                "voice": request.voice or "",
                "audio_input_model": self._audio_input_model,
                "audio_output_model": self._audio_output_model,
            }
            token, expires_at_unix = _mint_livekit_join_token(
                api_key=self._livekit_api_key,
                api_secret=self._livekit_api_secret,
                room_name=room_name,
                participant_identity=participant_identity,
                agent_identity=agent_identity,
                agent_name=self._livekit_agent_name,
                ttl_seconds=self._livekit_token_ttl_seconds,
                metadata={
                    "provider": self._provider_name,
                    "run_id": request.run_id,
                    "voice": request.voice or "",
                    "audio_input_model": self._audio_input_model,
                    "audio_output_model": self._audio_output_model,
                },
                agent_dispatch_metadata=dispatch_metadata,
            )
        transport = {
            "framework": "livekit" if production_transport == "livekit" else production_transport,
            "url": self._livekit_url,
            "room_name": room_name,
            "participant_identity": participant_identity,
            "agent_identity": agent_identity,
            "token": token,
            "has_token": token is not None,
            "token_persisted": False,
            "expires_at_unix": expires_at_unix,
            "metadata": {
                "provider": self._provider_name,
                "public_media_transport": "livekit",
                "pipecat_role": "optional_internal_pipeline_layer",
                "control_binding_token": control_binding_token,
                "control_binding_required": control_binding_token is not None,
                "agent_name": self._livekit_agent_name,
                "agent_dispatch_via_room_config": bool(
                    self._livekit_agent_name and token is not None
                ),
            },
        }

        session_prefix = (
            "gemma4" if self._provider_name == "gemma4_realtime" else "openrouter-livekit"
        )
        return RealtimeSessionResponse(
            provider=self._provider_name,
            session_id=f"{session_prefix}-{request.run_id}",
            websocket_url=websocket_url,
            transport=transport,
            expires_at_unix=expires_at_unix,
            metadata={
                "connection_transport": production_transport,
                "transport_framework": production_transport,
                "livekit_url": self._livekit_url,
                "room_name": room_name,
                "participant_identity": participant_identity,
                "agent_participant_identity": agent_identity,
                "has_transport_token": token is not None,
                "control_binding_token_issued": control_binding_token is not None,
                "livekit_token_expires_at_unix": expires_at_unix,
                "raw_websocket_production_allowed": False,
                "dev_websocket_url": self._websocket_url,
                "realtime_interaction": "gemma4_speech_to_speech",
                "audio_format": self._audio_format,
                "sample_rate": self._sample_rate,
                "input_sample_rate": self._sample_rate,
                "output_sample_rate": self._sample_rate,
                "stt_model": request.metadata.get("stt_model")
                or self._audio_input_model,
                "llm_model": request.metadata.get("llm_model")
                or self._reasoning_model,
                "tts_model": request.metadata.get("tts_model")
                or self._audio_output_model,
                "audio_input_model": request.metadata.get("audio_input_model")
                or self._audio_input_model,
                "reasoning_model": request.metadata.get("reasoning_model")
                or self._reasoning_model,
                "audio_output_model": request.metadata.get("audio_output_model")
                or self._audio_output_model,
                "model_family": "gemma4",
                "gemma_audio_input_native": True,
                "gemma_streaming": {
                    "enabled": self._gemma_streaming_enabled,
                    "protocol": "sse_openai_chat_compatible",
                    "reason": (
                        "Kokoro first-audio latency depends on Gemma "
                        "time-to-first-token, not only final completion latency."
                    ),
                },
                "tts_layer": "kokoro",
                "gemma_audio_output_requires_tts_adapter": True,
                "recommended_runtime": (
                    "LiveKit transport with a Rust realtime edge and Python "
                    "Gemma/Kokoro agent engine. Pipecat can be added later as "
                    "an internal pipeline layer."
                ),
                "context_pruning": {
                    "enabled": True,
                    "prune_after_turns": self._context_prune_after_turns,
                    "max_raw_audio_seconds_per_turn": self._max_audio_seconds_per_turn,
                    "replacement": "text_transcript_plus_compact_turn_summary",
                    "reason": "raw audio tensors must not accumulate in multi-turn context",
                },
                "barge_in": {
                    "enabled": True,
                    "rust_vad_model": self._rust_vad_model,
                    "vad_backend_requested": self._rust_vad_backend,
                    "vad_backend_effective": vad_contract["vad_backend_effective"],
                    "vad_runtime": vad_contract["vad_model_effective"],
                    "vad_fallback_reason": vad_contract["vad_fallback_reason"],
                    "on_user_speech_while_agent_speaking": [
                        "drop_outbound_audio_packets",
                        "send_turn_cancel_to_python_agent",
                        "cancel_gemma_inference",
                        "clear_kokoro_tts_buffer",
                        "commit_interruption_event",
                    ],
                },
                "rust_edge": {
                    "current_runtime": "persistent_jsonl_subprocess_or_http_sidecar",
                    "target_runtime": "streaming_session_state_plus_silero",
                    "responsibilities": [
                        "client_connection_control",
                        "vad_frame_loop",
                        "audio_buffer_backpressure",
                        "barge_in_detection",
                        "python_cancellation_signal",
                    ],
                    "current_ipc": ["stdin_stdout_jsonl", "http_json"],
                    "current_http_routes": [
                        "GET /healthz",
                        "POST /v1/voice-edge",
                        "POST /v1/voice-edge/analyze",
                        "POST /v1/voice-edge/cancel",
                    ],
                    "target_ipc": "streaming_http_or_grpc",
                    "vad_backend_requested": self._rust_vad_backend,
                    "vad_backend_effective": vad_contract["vad_backend_effective"],
                    "vad_model_effective": vad_contract["vad_model_effective"],
                    "vad_model_target": self._rust_vad_model,
                    "vad_fallback_allowed": self._rust_vad_fallback_allowed,
                    "vad_fallback_reason": vad_contract["vad_fallback_reason"],
                },
                "python_agent_engine": {
                    "runtime": "asyncio",
                    "entrypoint": (
                        "all_about_llms.voice_agent."
                        "GemmaKokoroLiveKitAgentEngine"
                    ),
                    "responsibilities": [
                        "conversation_state_buffer",
                        "gemma4_e4b_hf_calls",
                        "kokoro_tts_streaming",
                        "context_pruning",
                        "durable_turn_events",
                    ],
                },
                "protocol": (
                    "Browser joins LiveKit transport. Rust edge handles VAD, "
                    "buffers, concurrency, and barge-in. Python engine calls "
                    "google/gemma-4-E4B-it for audio understanding/reasoning and "
                    "streams text into hexgrad/Kokoro-82M for speech output."
                ),
            },
        )


class ElevenLabsRealtimeProvider:
    def __init__(self, *, api_key: str | None, agent_id: str | None):
        self._api_key = api_key
        self._agent_id = agent_id

    async def create_session(
        self, request: RealtimeSessionRequest
    ) -> RealtimeSessionResponse:
        if not self._api_key:
            raise ProviderConfigurationError("ELEVENLABS_API_KEY is not configured.")
        agent_id = request.metadata.get("agent_id") or self._agent_id
        if not agent_id:
            raise ProviderConfigurationError("ELEVENLABS_AGENT_ID is not configured.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.elevenlabs.io/v1/convai/conversation/get-signed-url",
                params={"agent_id": agent_id},
                headers={"xi-api-key": self._api_key},
            )
            response.raise_for_status()
            raw = response.json()

        return RealtimeSessionResponse(
            provider="elevenlabs",
            session_id=request.run_id,
            websocket_url=raw["signed_url"],
            metadata={"raw_response": raw, "agent_id": agent_id},
        )


class CartesiaRealtimeTTSProvider:
    def __init__(self, *, api_key: str | None, model_id: str, voice_id: str | None):
        self._api_key = api_key
        self._model_id = model_id
        self._voice_id = voice_id

    async def create_session(
        self, request: RealtimeSessionRequest
    ) -> RealtimeSessionResponse:
        if not self._api_key:
            raise ProviderConfigurationError("CARTESIA_API_KEY is not configured.")
        voice_id = request.voice or request.metadata.get("voice_id") or self._voice_id
        if not voice_id:
            raise ProviderConfigurationError("CARTESIA_VOICE_ID is not configured.")

        query = urlencode({"cartesia_version": "2025-04-16"})
        return RealtimeSessionResponse(
            provider="cartesia",
            session_id=request.run_id,
            websocket_url=f"wss://api.cartesia.ai/tts/websocket?{query}",
            metadata={
                "model_id": self._model_id,
                "voice_id": voice_id,
                "requires_header": "X-API-Key",
            },
        )
