import importlib.util
import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import httpx
from all_about_llms.config import Settings
from all_about_llms.contracts import (
    RuntimeHealthStatus,
    VoiceRuntimeReadinessCheck,
    VoiceRuntimeReadinessResult,
)
from all_about_llms.providers.interfaces import ProviderConfigurationError
from all_about_llms.realtime_safety import redact_realtime_string
from all_about_llms.voice_agent.adapters import (
    HuggingFaceKokoroTTSStreamer,
    normalize_backend_event_sink_base_url,
)
from all_about_llms.voice_agent.engine import VoiceAgentCancellationToken
from all_about_llms.voice_agent.livekit_app import (
    _build_voice_edge_client,
    _preflight_voice_edge_client,
    build_livekit_voice_agent_server,
)
from all_about_llms.voice_agent.edge import FallbackVoiceEdgeClient, describe_vad_runtime
from all_about_llms.voice_agent.gemma import (
    gemma_audio_endpoint_metadata,
)
from all_about_llms.voice_agent.reasoning import (
    build_voice_reasoner,
    gemma_native_audio_reasoning_route,
    openrouter_voice_reasoning_route,
    voice_reasoning_route,
)
from all_about_llms.voice_agent.kokoro import (
    KokoroRuntimeRoute,
    kokoro_runtime_route,
)
from all_about_llms.voice_agent.models import (
    RealtimeVoiceAgentConfig,
    RealtimeVoiceTurnInput,
)

LIVEKIT_LOCAL_DEV_DOCS = "https://docs.livekit.io/home/self-hosting/local"
LIVEKIT_PORTS_DOCS = "https://docs.livekit.io/oss/deployment/ports-firewall/"


async def build_voice_runtime_readiness(
    settings: Settings,
    *,
    preflight_livekit: bool = False,
    preflight_edge: bool = False,
    preflight_agent: bool = False,
    preflight_gemma: bool = False,
    preflight_tts: bool = False,
) -> VoiceRuntimeReadinessResult:
    reasoning_checks = await _voice_reasoning_checks(
        settings,
        preflight_gemma=preflight_gemma,
    )
    checks = [
        await _livekit_check(settings, preflight_livekit=preflight_livekit),
        _livekit_agent_participant_check(settings, preflight_agent=preflight_agent),
        await _voice_agent_event_sink_check(
            settings,
            preflight_sink=preflight_agent,
        ),
        *reasoning_checks,
        await _kokoro_check(settings, preflight_tts=preflight_tts),
        await _voice_edge_check(settings, preflight_edge=preflight_edge),
        _context_pruning_check(settings),
    ]
    required_blockers = [
        check.label
        for check in checks
        if check.required and check.status != RuntimeHealthStatus.READY
    ]
    degraded_checks = [
        check.label for check in checks if check.status == RuntimeHealthStatus.DEGRADED
    ]
    if required_blockers:
        status = RuntimeHealthStatus.BLOCKED
        summary = (
            "Voice runtime is blocked until required LiveKit, OpenRouter/Kokoro, "
            "backend event sink, and Rust voice-edge checks are ready."
        )
    elif degraded_checks:
        status = RuntimeHealthStatus.DEGRADED
        summary = "Voice runtime is usable but has degraded checks to review."
    else:
        status = RuntimeHealthStatus.READY
        summary = "Voice runtime readiness checks are ready for OpenRouter/Kokoro LiveKit sessions."

    next_actions: list[str] = []
    for check in checks:
        if check.required and check.status != RuntimeHealthStatus.READY:
            next_actions.extend(check.next_actions)
        elif check.status == RuntimeHealthStatus.DEGRADED:
            next_actions.extend(check.next_actions)

    return VoiceRuntimeReadinessResult(
        status=status,
        selected_provider=settings.realtime_default_provider,
        transport_framework=settings.gemma4_realtime_transport_framework,
        audio_input_model=settings.gemma4_realtime_audio_input_model,
        reasoning_model=settings.gemma4_realtime_reasoning_model,
        audio_output_model=settings.gemma4_realtime_audio_output_model,
        preflight_livekit=preflight_livekit,
        preflight_edge=preflight_edge,
        preflight_agent=preflight_agent,
        preflight_gemma=preflight_gemma,
        preflight_tts=preflight_tts,
        checks=checks,
        blockers=required_blockers,
        next_actions=_dedupe(next_actions),
        summary=summary,
    )


async def _livekit_check(
    settings: Settings,
    *,
    preflight_livekit: bool,
) -> VoiceRuntimeReadinessCheck:
    livekit_url = settings.realtime_livekit_url()
    required_env = {
        "OPENROUTER_LIVEKIT_URL": livekit_url,
        "LIVEKIT_API_KEY": settings.livekit_api_key,
        "LIVEKIT_API_SECRET": settings.livekit_api_secret,
    }
    missing_env = [name for name, value in required_env.items() if not value]
    local_dev_hint = {
        "native_command": "livekit-server --dev",
        "compose_command": "docker compose --profile voice up -d livekit",
        "supervised_compose_command": "docker compose --profile voice up livekit",
        "url": "ws://127.0.0.1:7880",
        "api_key_env": "LIVEKIT_API_KEY",
        "api_secret_env": "LIVEKIT_API_SECRET",
        "credential_profile": "LiveKit local dev defaults",
        "docs": LIVEKIT_LOCAL_DEV_DOCS,
        "ports_docs": LIVEKIT_PORTS_DOCS,
        "development_only": True,
    }
    configured_for_local_dev = _is_livekit_local_dev_config(
        livekit_url,
        settings.livekit_api_key,
        settings.livekit_api_secret,
    )
    metadata = {
        "framework": settings.gemma4_realtime_transport_framework,
        "has_livekit_url": bool(livekit_url),
        "has_api_key": bool(settings.livekit_api_key),
        "has_api_secret": bool(settings.livekit_api_secret),
        "configured_for_local_dev": configured_for_local_dev,
        "local_dev_hint": local_dev_hint,
        "connectivity_preflight_performed": preflight_livekit,
        "connectivity_preflight_timeout_seconds": (
            settings.livekit_connectivity_preflight_timeout_seconds
        ),
    }
    if not missing_env and preflight_livekit:
        preflight_result = await _preflight_livekit_room_service(
            livekit_url=str(livekit_url),
            api_key=str(settings.livekit_api_key),
            api_secret=str(settings.livekit_api_secret),
            timeout_seconds=settings.livekit_connectivity_preflight_timeout_seconds,
        )
        ready = bool(preflight_result["ok"])
        return VoiceRuntimeReadinessCheck(
            check_id="livekit-transport",
            label="LiveKit media transport",
            status=(
                RuntimeHealthStatus.READY if ready else RuntimeHealthStatus.BLOCKED
            ),
            missing_env=[],
            evidence=[str(preflight_result["evidence"])],
            next_actions=(
                []
                if ready
                else [
                    "Start or fix the LiveKit server, verify URL/key/secret, then rerun Runtime preflight."
                ]
            ),
            metadata={**metadata, **dict(preflight_result["metadata"])},
        )
    evidence = (
        [
            (
                "LiveKit URL and signing credentials are configured. "
                "Connectivity preflight was not requested."
            )
        ]
        if not missing_env
        else ["LiveKit room grants cannot be minted without URL/key/secret."]
    )
    next_actions = (
        ["Run Runtime preflight to verify the LiveKit RoomService API is reachable."]
        if not missing_env
        else [
            "Configure OPENROUTER_LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET.",
            "For local development, run `livekit-server --dev`, supervised foreground `docker compose --profile voice up livekit`, or manual detached `docker compose --profile voice up -d livekit`, then set LiveKit dev key/secret from the official local mode.",
        ]
    )
    return VoiceRuntimeReadinessCheck(
        check_id="livekit-transport",
        label="LiveKit media transport",
        status=(
            RuntimeHealthStatus.READY
            if not missing_env
            else RuntimeHealthStatus.BLOCKED
        ),
        missing_env=missing_env,
        evidence=evidence,
        next_actions=next_actions,
        metadata=metadata,
    )


async def _preflight_livekit_room_service(
    *,
    livekit_url: str,
    api_key: str,
    api_secret: str,
    timeout_seconds: float,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "connectivity_preflight_method": "RoomService/ListRooms",
    }
    try:
        base_url = _livekit_http_base_url(livekit_url)
    except ValueError as exc:
        metadata["connectivity_error_type"] = "ValueError"
        return {
            "ok": False,
            "evidence": (
                "LiveKit RoomService/ListRooms preflight could not start: "
                f"{exc}"
            ),
            "metadata": metadata,
        }
    endpoint = f"{base_url}/twirp/livekit.RoomService/ListRooms"
    path_prefix = urlparse(base_url).path or "/"
    metadata: dict[str, object] = {
        "connectivity_preflight_endpoint": endpoint,
        "connectivity_preflight_method": "RoomService/ListRooms",
        "connectivity_preflight_path_prefix": path_prefix,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": (
                        f"Bearer {_mint_livekit_room_list_token(api_key, api_secret)}"
                    ),
                    "Content-Type": "application/json",
                },
                json={},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        metadata["connectivity_status_code"] = exc.response.status_code
        return {
            "ok": False,
            "evidence": (
                "LiveKit RoomService/ListRooms preflight failed with "
                f"HTTP {exc.response.status_code}."
            ),
            "metadata": metadata,
        }
    except Exception as exc:
        metadata["connectivity_error_type"] = type(exc).__name__
        return {
            "ok": False,
            "evidence": f"LiveKit RoomService/ListRooms preflight failed: {exc}",
            "metadata": metadata,
        }
    metadata["connectivity_status_code"] = response.status_code
    return {
        "ok": True,
        "evidence": "LiveKit RoomService/ListRooms preflight succeeded.",
        "metadata": metadata,
    }


def _livekit_http_base_url(livekit_url: str) -> str:
    parsed = urlparse(livekit_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("LiveKit URL must include a scheme and host.")
    if parsed.query or parsed.fragment:
        raise ValueError(
            "LiveKit RoomService preflight does not support query strings or fragments; "
            "configure the root or path-prefix LiveKit URL instead."
        )
    scheme = {"ws": "http", "wss": "https"}.get(parsed.scheme, parsed.scheme)
    if scheme not in {"http", "https"}:
        raise ValueError("LiveKit URL scheme must be ws, wss, http, or https.")
    return urlunparse((scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))


def _is_livekit_local_dev_config(
    livekit_url: str | None,
    api_key: str | None,
    api_secret: str | None,
) -> bool:
    if api_key != "devkey" or api_secret != "secret" or not livekit_url:
        return False
    parsed = urlparse(livekit_url)
    return (
        parsed.scheme in {"ws", "wss", "http", "https"}
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and (parsed.port or 7880) == 7880
        and parsed.path in {"", "/"}
    )


def _mint_livekit_room_list_token(api_key: str, api_secret: str) -> str:
    now = int(time.time())
    payload = {
        "iss": api_key,
        "nbf": now,
        "exp": now + 60,
        "video": {"roomList": True},
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join([_base64url_json(header), _base64url_json(payload)])
    signature = hmac.new(
        api_secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_base64url(signature)}"


def _base64url_json(payload: dict[str, object]) -> str:
    return _base64url(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )


def _base64url(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _livekit_agent_participant_check(
    settings: Settings,
    *,
    preflight_agent: bool,
) -> VoiceRuntimeReadinessCheck:
    livekit_agents_available = _module_available("livekit.agents")
    launch_command = "all-about-llms-admin run-voice-agent"
    base_metadata = {
        "agent_name": settings.livekit_agent_name,
        "livekit_agents_available": livekit_agents_available,
        "launch_command": launch_command,
        "participant_role": "openrouter_kokoro_dialogue_reasoning_and_tts",
        "requires_livekit_room_grant": True,
        "startup_preflight_performed": preflight_agent,
    }
    if not livekit_agents_available or not settings.livekit_agent_name:
        return VoiceRuntimeReadinessCheck(
            check_id="livekit-agent-participant",
            label="OpenRouter/Kokoro LiveKit agent participant",
            status=RuntimeHealthStatus.BLOCKED,
            evidence=[
                "The browser can join a room only after a backend OpenRouter/Kokoro LiveKit participant is runnable."
            ],
            next_actions=[
                "Install the voice extra and start `all-about-llms-admin run-voice-agent` before claiming live voice readiness."
            ],
            metadata=base_metadata,
        )
    if not preflight_agent:
        return VoiceRuntimeReadinessCheck(
            check_id="livekit-agent-participant",
            label="OpenRouter/Kokoro LiveKit agent participant",
            status=RuntimeHealthStatus.READY,
            evidence=[
                "LiveKit Agents runtime is importable and the OpenRouter/Kokoro agent name is configured. Startup preflight was not requested."
            ],
            next_actions=[
                "Run Runtime preflight before a production voice session to construct the agent server without starting it."
            ],
            metadata=base_metadata,
        )
    try:
        build_livekit_voice_agent_server(settings)
    except Exception as exc:
        return VoiceRuntimeReadinessCheck(
            check_id="livekit-agent-participant",
            label="OpenRouter/Kokoro LiveKit agent participant",
            status=RuntimeHealthStatus.BLOCKED,
            evidence=[f"Agent server startup preflight failed: {exc}"],
            next_actions=[
                "Fix the LiveKit agent runtime or voice dependencies, then rerun Runtime preflight."
            ],
            metadata={**base_metadata, "startup_preflight_error": str(exc)},
        )
    return VoiceRuntimeReadinessCheck(
        check_id="livekit-agent-participant",
        label="OpenRouter/Kokoro LiveKit agent participant",
        status=RuntimeHealthStatus.READY,
        evidence=["Agent server startup preflight constructed the LiveKit participant server."],
        metadata=base_metadata,
    )


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


async def _voice_agent_event_sink_check(
    settings: Settings,
    *,
    preflight_sink: bool,
) -> VoiceRuntimeReadinessCheck:
    metadata = {
        "enabled": settings.voice_agent_backend_event_sink_enabled,
        "preflight_performed": preflight_sink,
        "timeout_seconds": settings.voice_agent_backend_event_sink_timeout_seconds,
    }
    if not settings.voice_agent_backend_event_sink_enabled:
        return VoiceRuntimeReadinessCheck(
            check_id="voice-agent-backend-event-sink",
            label="Voice event direct persistence",
            status=RuntimeHealthStatus.DEGRADED,
            required=False,
            evidence=[
                "Direct voice-agent event persistence is disabled; browser data-channel persistence remains available."
            ],
            next_actions=[
                "Enable VOICE_AGENT_BACKEND_EVENT_SINK_ENABLED for always-on voice-agent event persistence without an open browser tab."
            ],
            metadata=metadata,
        )
    try:
        sink_url = _normalized_backend_event_sink_url(
            settings.voice_agent_backend_event_sink_url
        )
    except ValueError as exc:
        return VoiceRuntimeReadinessCheck(
            check_id="voice-agent-backend-event-sink",
            label="Voice event direct persistence",
            status=RuntimeHealthStatus.DEGRADED,
            required=False,
            evidence=[f"Direct voice-event sink URL is not usable: {exc}"],
            next_actions=[
                "Set VOICE_AGENT_BACKEND_EVENT_SINK_URL to the FastAPI backend origin, for example http://127.0.0.1:8000."
            ],
            metadata={**metadata, "configuration_error": str(exc)},
        )
    if not preflight_sink:
        return VoiceRuntimeReadinessCheck(
            check_id="voice-agent-backend-event-sink",
            label="Voice event direct persistence",
            status=RuntimeHealthStatus.READY,
            required=False,
            evidence=[
                "Direct voice-agent event persistence is configured. HTTP preflight was not requested."
            ],
            next_actions=[
                "Run Runtime preflight to verify the voice agent can reach the FastAPI event sink."
            ],
            metadata={**metadata, "base_url": sink_url},
        )
    preflight = await _preflight_backend_event_sink(
        base_url=sink_url,
        timeout_seconds=settings.voice_agent_backend_event_sink_timeout_seconds,
    )
    return VoiceRuntimeReadinessCheck(
        check_id="voice-agent-backend-event-sink",
        label="Voice event direct persistence",
        status=(
            RuntimeHealthStatus.READY
            if preflight["ok"]
            else RuntimeHealthStatus.DEGRADED
        ),
        required=False,
        evidence=[str(preflight["evidence"])],
        next_actions=(
            []
            if preflight["ok"]
            else [
                "Start the FastAPI backend or fix VOICE_AGENT_BACKEND_EVENT_SINK_URL, then rerun Runtime preflight."
            ]
        ),
        metadata={**metadata, "base_url": sink_url, **dict(preflight["metadata"])},
    )


def _normalized_backend_event_sink_url(value: str | None) -> str:
    return normalize_backend_event_sink_base_url(value)


async def _voice_reasoning_checks(
    settings: Settings,
    *,
    preflight_gemma: bool,
) -> list[VoiceRuntimeReadinessCheck]:
    selected_route = voice_reasoning_route(settings)
    if selected_route.provider == "openrouter":
        return [
            await _openrouter_live_dialogue_check(
                settings,
                preflight_gemma=preflight_gemma,
            ),
            await _gemma_audio_check(
                settings,
                preflight_gemma=preflight_gemma,
                required=False,
            ),
        ]
    return [
        await _gemma_audio_check(
            settings,
            preflight_gemma=preflight_gemma,
            required=True,
        )
    ]


async def _preflight_backend_event_sink(
    *,
    base_url: str,
    timeout_seconds: float,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, object]:
    endpoint = f"{base_url}/health"
    metadata: dict[str, object] = {
        "preflight_endpoint": endpoint,
        "preflight_method": "GET /health",
    }
    client_kwargs: dict[str, object] = {"timeout": timeout_seconds}
    if transport is not None:
        client_kwargs["transport"] = transport
    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        metadata["status_code"] = exc.response.status_code
        return {
            "ok": False,
            "evidence": (
                "FastAPI voice-event sink preflight failed with "
                f"HTTP {exc.response.status_code}."
            ),
            "metadata": metadata,
        }
    except Exception as exc:
        metadata["error_type"] = type(exc).__name__
        return {
            "ok": False,
            "evidence": f"FastAPI voice-event sink preflight failed: {exc}",
            "metadata": metadata,
        }
    metadata["status_code"] = response.status_code
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if isinstance(payload, dict):
        metadata["health_status"] = payload.get("status")
        metadata["database"] = payload.get("database")
        metadata["vector_store"] = payload.get("vector_store")
    return {
        "ok": True,
        "evidence": "FastAPI voice-event sink /health preflight succeeded.",
        "metadata": metadata,
    }


async def _gemma_audio_check(
    settings: Settings,
    *,
    preflight_gemma: bool,
    required: bool = True,
) -> VoiceRuntimeReadinessCheck:
    route = gemma_native_audio_reasoning_route(settings)
    endpoint_metadata = gemma_audio_endpoint_metadata(settings)
    metadata = {
        "audio_input_model": settings.gemma4_realtime_audio_input_model,
        "reasoning_model": settings.gemma4_realtime_reasoning_model,
        "streaming_enabled": settings.gemma4_realtime_stream_gemma,
        "gemma_preflight_requested": preflight_gemma,
        "gemma_preflight_performed": False,
        "voice_reasoning_provider": route.provider,
        **endpoint_metadata,
    }
    missing_env = list(route.missing_env)
    if not missing_env and preflight_gemma:
        preflight_result = await _preflight_voice_reasoning_endpoint(settings, route)
        ready = bool(preflight_result["ok"])
        return VoiceRuntimeReadinessCheck(
            check_id="gemma-audio-reasoning",
            label="Gemma 4 E4B audio reasoning",
            status=(
                RuntimeHealthStatus.READY if ready else RuntimeHealthStatus.BLOCKED
            ),
            required=required,
            missing_env=[],
            evidence=[str(preflight_result["evidence"])],
            next_actions=(
                []
                if ready
                else [
                    "Fix Gemma native-audio voice reasoning configuration, then rerun Runtime preflight."
                ]
            ),
            metadata={**metadata, **dict(preflight_result["metadata"])},
        )
    if not missing_env:
        evidence = ["Hugging Face token and dedicated Gemma audio endpoint are configured."]
    elif endpoint_metadata["gemma_audio_endpoint_error"] and settings.hf_token:
        evidence = [
            "GEMMA4_MULTIMODAL_ENDPOINT_URL is configured but is not a valid HTTP(S) URL. "
            "Configure a valid dedicated Gemma 4 E4B native-audio endpoint."
        ]
    elif (
        not route.endpoint_url
        and endpoint_metadata["gemma_primary_endpoint_configured"]
        and settings.hf_token
    ):
        evidence = [
            "GEMMA4_PRIMARY_ENDPOINT_URL is configured for text/chat expert routing, "
            "but it does not satisfy native audio proof. Configure a dedicated "
            "GEMMA4_MULTIMODAL_ENDPOINT_URL for Gemma 4 E4B audio input."
        ]
    elif (
        not route.endpoint_url
        and endpoint_metadata["hf_router_chat_completions_configured"]
        and settings.hf_token
    ):
        evidence = [
            "HF router chat-completions is configured for text/chat, but it does not satisfy native audio proof. "
            "Configure a dedicated Gemma multimodal endpoint for Gemma 4 E4B audio input."
        ]
    else:
        evidence = ["Gemma native-audio reasoning needs HF_TOKEN and a dedicated Gemma audio endpoint."]
    return VoiceRuntimeReadinessCheck(
        check_id="gemma-audio-reasoning",
        label="Gemma 4 E4B audio reasoning",
        status=(
            RuntimeHealthStatus.READY
            if not missing_env
            else RuntimeHealthStatus.BLOCKED
        ),
        required=required,
        missing_env=missing_env,
        evidence=evidence,
        next_actions=(
            []
            if not missing_env
            else [
                "Configure HF_TOKEN and a dedicated GEMMA4_MULTIMODAL_ENDPOINT_URL "
                "for Gemma 4 E4B native audio."
            ]
        ),
        metadata=metadata,
    )


async def _openrouter_live_dialogue_check(
    settings: Settings,
    *,
    preflight_gemma: bool,
) -> VoiceRuntimeReadinessCheck:
    route = openrouter_voice_reasoning_route(settings)
    metadata = {
        "audio_input_model": settings.gemma4_realtime_audio_input_model,
        "reasoning_model": settings.gemma4_realtime_reasoning_model,
        "streaming_enabled": settings.gemma4_realtime_stream_gemma,
        "gemma_preflight_requested": preflight_gemma,
        "gemma_preflight_performed": False,
        "voice_reasoning_provider": route.provider,
        "openrouter_chat_completions_configured": bool(route.endpoint_url),
    }
    missing_env = list(route.missing_env)
    if not missing_env and preflight_gemma:
        preflight_result = await _preflight_voice_reasoning_endpoint(settings, route)
        ready = bool(preflight_result["ok"])
        return VoiceRuntimeReadinessCheck(
            check_id="openrouter-live-dialogue-reasoning",
            label="OpenRouter live dialogue reasoning",
            status=(
                RuntimeHealthStatus.READY if ready else RuntimeHealthStatus.BLOCKED
            ),
            missing_env=[],
            evidence=[str(preflight_result["evidence"])],
            next_actions=(
                []
                if ready
                else [
                    "Fix OpenRouter live dialogue configuration, then rerun Runtime preflight."
                ]
            ),
            metadata={**metadata, **dict(preflight_result["metadata"])},
        )
    evidence = (
        ["OpenRouter API key and chat endpoint are configured."]
        if not missing_env
        else ["OpenRouter live dialogue needs OPENROUTER_API_KEY."]
    )
    return VoiceRuntimeReadinessCheck(
        check_id="openrouter-live-dialogue-reasoning",
        label="OpenRouter live dialogue reasoning",
        status=(
            RuntimeHealthStatus.READY
            if not missing_env
            else RuntimeHealthStatus.BLOCKED
        ),
        missing_env=missing_env,
        evidence=evidence,
        next_actions=(
            []
            if not missing_env
            else ["Configure OPENROUTER_API_KEY for OpenRouter live dialogue."]
        ),
        metadata=metadata,
    )


class _StreamingOnlyGemmaProvider:
    async def complete(self, _request):
        raise ProviderConfigurationError(
            "Gemma provider-complete fallback is unavailable for runtime audio preflight."
        )


def _realtime_voice_preflight_config(settings: Settings) -> RealtimeVoiceAgentConfig:
    return RealtimeVoiceAgentConfig(
        audio_input_model=settings.gemma4_realtime_audio_input_model,
        reasoning_model=settings.gemma4_realtime_reasoning_model,
        audio_output_model=settings.gemma4_realtime_audio_output_model,
        sample_rate=settings.gemma4_realtime_sample_rate,
        audio_format=settings.gemma4_realtime_audio_format,
        context_window_turns=settings.gemma4_realtime_context_window_turns,
        prune_after_turns=settings.gemma4_realtime_context_prune_after_turns,
        max_raw_audio_seconds_per_turn=(
            settings.gemma4_realtime_max_audio_seconds_per_turn
        ),
        tts_flush_chars=settings.gemma4_realtime_tts_flush_chars,
        gemma_streaming_enabled=settings.gemma4_realtime_stream_gemma,
        gemma_stream_timeout_seconds=(
            settings.gemma4_realtime_gemma_stream_timeout_seconds
        ),
    )


def _gemma_probe_pcm(config: RealtimeVoiceAgentConfig) -> bytes:
    frame_ms = 32
    samples = int(config.sample_rate * frame_ms / 1000)
    return b"\0\0" * samples


async def _preflight_voice_reasoning_endpoint(
    settings: Settings,
    route,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "gemma_preflight_performed": False,
        "voice_reasoning_provider": route.provider,
    }
    config = _realtime_voice_preflight_config(settings)
    if not config.gemma_streaming_enabled:
        safe_error = "GEMMA4_REALTIME_STREAM_GEMMA must be true for runtime audio preflight."
        metadata["gemma_preflight_error"] = safe_error
        return {"ok": False, "evidence": safe_error, "metadata": metadata}

    metadata["gemma_preflight_performed"] = True
    reasoner = build_voice_reasoner(
        settings,
        config,
        provider=_StreamingOnlyGemmaProvider(),
        route=route,
    )
    if route.provider == "openrouter":
        turn = RealtimeVoiceTurnInput(
            run_id=uuid4(),
            realtime_session_id=uuid4(),
            room_name="runtime-readiness-preflight",
            participant_identity="runtime-readiness-preflight",
            transcript="Reply with one short word to confirm live dialogue readiness.",
            metadata={"workflow": "voice_runtime_readiness_openrouter_preflight"},
        )
        metadata["gemma_preflight_audio_duration_ms"] = 0
    else:
        turn = RealtimeVoiceTurnInput(
            run_id=uuid4(),
            realtime_session_id=uuid4(),
            room_name="runtime-readiness-preflight",
            participant_identity="runtime-readiness-preflight",
            audio_pcm=_gemma_probe_pcm(config),
            audio_duration_ms=32,
            metadata={"workflow": "voice_runtime_readiness_gemma_preflight"},
        )
        metadata["gemma_preflight_audio_duration_ms"] = 32
    try:
        cancellation = VoiceAgentCancellationToken("gemma-readiness-preflight")
        first_delta: str | None = None
        async for delta in reasoner.stream_text(turn, [], cancellation):
            if delta.strip():
                first_delta = delta
                break
    except ProviderConfigurationError as exc:
        safe_error = redact_realtime_string(str(exc))
        metadata["gemma_preflight_error"] = safe_error
        provider_name = (
            "OpenRouter" if route.provider == "openrouter" else "Gemma 4 E4B audio"
        )
        return {
            "ok": False,
            "evidence": f"{provider_name} endpoint preflight failed: {safe_error}",
            "metadata": metadata,
        }
    except Exception as exc:
        safe_error = redact_realtime_string(str(exc))
        metadata["gemma_preflight_error_type"] = type(exc).__name__
        metadata["gemma_preflight_error"] = safe_error
        provider_name = (
            "OpenRouter" if route.provider == "openrouter" else "Gemma 4 E4B audio"
        )
        return {
            "ok": False,
            "evidence": f"{provider_name} endpoint preflight failed: {safe_error}",
            "metadata": metadata,
        }
    if not first_delta:
        metadata["gemma_preflight_error"] = (
            "Voice reasoning endpoint returned no text delta."
        )
        return {
            "ok": False,
            "evidence": "Voice reasoning endpoint preflight returned no text delta.",
            "metadata": metadata,
        }
    metadata["gemma_preflight_text_chars"] = len(first_delta)
    provider_name = (
        "OpenRouter live dialogue"
        if route.provider == "openrouter"
        else "Gemma 4 E4B audio"
    )
    return {
        "ok": True,
        "evidence": f"{provider_name} endpoint preflight returned a text delta.",
        "metadata": metadata,
    }


async def _preflight_gemma_audio_endpoint(
    settings: Settings,
    endpoint_url: str | None,
) -> dict[str, object]:
    return await _preflight_voice_reasoning_endpoint(
        settings,
        voice_reasoning_route(settings),
    )


async def _kokoro_check(
    settings: Settings,
    *,
    preflight_tts: bool,
) -> VoiceRuntimeReadinessCheck:
    route = kokoro_runtime_route(settings)
    metadata = {
        "model_id": settings.gemma4_realtime_audio_output_model,
        "chunk_bytes": settings.kokoro_tts_chunk_bytes,
        "kokoro_preflight_requested": preflight_tts,
        "kokoro_preflight_performed": False,
        **route.metadata(),
    }
    if route.transport == "hf_endpoint" and preflight_tts:
        preflight_result = await _preflight_hosted_kokoro_tts(settings, route)
        ready = bool(preflight_result["ok"])
        return VoiceRuntimeReadinessCheck(
            check_id="kokoro-tts",
            label="Kokoro TTS output",
            status=(
                RuntimeHealthStatus.READY if ready else RuntimeHealthStatus.BLOCKED
            ),
            missing_env=[],
            evidence=[str(preflight_result["evidence"])],
            next_actions=(
                []
                if ready
                else [
                    "Fix KOKORO_TTS_ENDPOINT_URL or hosted Kokoro availability, then rerun Runtime preflight."
                ]
            ),
            metadata={**metadata, **dict(preflight_result["metadata"])},
        )
    return VoiceRuntimeReadinessCheck(
        check_id="kokoro-tts",
        label="Kokoro TTS output",
        status=RuntimeHealthStatus.READY if route.ready else RuntimeHealthStatus.BLOCKED,
        missing_env=[] if route.ready else ["KOKORO_TTS_ENDPOINT_URL"],
        evidence=[route.evidence()],
        next_actions=_kokoro_next_actions(route),
        metadata=metadata,
    )


async def _preflight_hosted_kokoro_tts(
    settings: Settings,
    route: KokoroRuntimeRoute,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "kokoro_preflight_performed": True,
        "kokoro_preflight_text_chars": 2,
    }
    streamer = HuggingFaceKokoroTTSStreamer(
        token=settings.hf_token,
        endpoint_url=route.endpoint_url,
        model_id=settings.gemma4_realtime_audio_output_model,
        chunk_bytes=settings.kokoro_tts_chunk_bytes,
        timeout_seconds=settings.kokoro_tts_timeout_seconds,
    )
    try:
        cancellation = VoiceAgentCancellationToken("kokoro-readiness-preflight")
        first_chunk: bytes | None = None
        async for chunk in streamer.stream_audio(
            response_id="kokoro-readiness-preflight",
            text="ok",
            voice=None,
            cancellation=cancellation,
        ):
            first_chunk = chunk
            break
    except ProviderConfigurationError as exc:
        safe_error = redact_realtime_string(str(exc))
        metadata["kokoro_preflight_error"] = safe_error
        return {
            "ok": False,
            "evidence": f"Hosted Kokoro endpoint preflight failed: {safe_error}",
            "metadata": metadata,
        }
    except Exception as exc:
        safe_error = redact_realtime_string(str(exc))
        metadata["kokoro_preflight_error_type"] = type(exc).__name__
        metadata["kokoro_preflight_error"] = safe_error
        return {
            "ok": False,
            "evidence": f"Hosted Kokoro endpoint preflight failed: {safe_error}",
            "metadata": metadata,
        }
    if not first_chunk:
        metadata["kokoro_preflight_error"] = "Kokoro endpoint returned no audio bytes."
        return {
            "ok": False,
            "evidence": "Hosted Kokoro endpoint preflight returned no audio bytes.",
            "metadata": metadata,
        }
    metadata["kokoro_preflight_audio_bytes"] = len(first_chunk)
    return {
        "ok": True,
        "evidence": "Hosted Kokoro endpoint preflight returned audio bytes.",
        "metadata": metadata,
    }


def _kokoro_next_actions(route: KokoroRuntimeRoute) -> list[str]:
    if route.ready and route.endpoint_error:
        return [
            "Fix or remove malformed KOKORO_TTS_ENDPOINT_URL; "
            "local Kokoro is currently being used."
        ]
    if route.ready:
        return []
    if route.endpoint_error:
        return [
            "Set KOKORO_TTS_ENDPOINT_URL to a valid http(s) URL or install "
            "the voice extra with local Kokoro support."
        ]
    return [
        "Configure KOKORO_TTS_ENDPOINT_URL or install the voice extra with "
        "local Kokoro support."
    ]


async def _voice_edge_check(
    settings: Settings,
    *,
    preflight_edge: bool,
) -> VoiceRuntimeReadinessCheck:
    binary_path = Path(settings.rust_voice_edge_binary_path)
    binary_executable = binary_path.is_file() and os.access(binary_path, os.X_OK)
    http_configured = bool(settings.rust_voice_edge_http_url)
    if not binary_executable and not http_configured:
        return VoiceRuntimeReadinessCheck(
            check_id="rust-voice-edge",
            label="Rust VAD and barge-in edge",
            status=RuntimeHealthStatus.BLOCKED,
            evidence=["No executable voice-edge binary or HTTP sidecar URL is configured."],
            next_actions=["Build services/voice-edge or configure RUST_VOICE_EDGE_HTTP_URL."],
            metadata={
                "binary_path_configured": bool(settings.rust_voice_edge_binary_path),
                "binary_executable": False,
                "http_configured": False,
                "target_vad_model": settings.gemma4_realtime_rust_vad_model,
                "vad_model_path_configured": bool(settings.rust_voice_edge_vad_model_path),
                "vad_fallback_allowed": settings.rust_voice_edge_allow_vad_fallback,
                **_settings_vad_metadata(settings),
            },
        )

    if not preflight_edge:
        return VoiceRuntimeReadinessCheck(
            check_id="rust-voice-edge",
            label="Rust VAD and barge-in edge",
            status=RuntimeHealthStatus.READY,
            evidence=["Rust voice-edge is configured. Startup preflight was not requested."],
            next_actions=["Run edge preflight from the voice panel before a production voice session."],
            metadata={
                "binary_path_configured": bool(settings.rust_voice_edge_binary_path),
                "binary_executable": binary_executable,
                "http_configured": http_configured,
                "http_url": settings.rust_voice_edge_http_url,
                "preflight_performed": False,
                "target_vad_model": settings.gemma4_realtime_rust_vad_model,
                "vad_model_path_configured": bool(settings.rust_voice_edge_vad_model_path),
                "vad_fallback_allowed": settings.rust_voice_edge_allow_vad_fallback,
                **_settings_vad_metadata(settings),
            },
        )

    client = _build_voice_edge_client(settings)
    if client is None:
        return VoiceRuntimeReadinessCheck(
            check_id="rust-voice-edge",
            label="Rust VAD and barge-in edge",
            status=RuntimeHealthStatus.BLOCKED,
            evidence=["No available Rust voice-edge transport could be built."],
            next_actions=["Build services/voice-edge or fix RUST_VOICE_EDGE_HTTP_URL."],
            metadata={"preflight_performed": True},
        )
    selected_client = None
    try:
        selected_client = await _preflight_voice_edge_client(client)
        return VoiceRuntimeReadinessCheck(
            check_id="rust-voice-edge",
            label="Rust VAD and barge-in edge",
            status=RuntimeHealthStatus.READY,
            evidence=[f"Startup preflight passed on {selected_client.transport if selected_client else client.transport}."],
            metadata={
                "binary_path_configured": bool(settings.rust_voice_edge_binary_path),
                "binary_executable": binary_executable,
                "http_configured": http_configured,
                "http_url": settings.rust_voice_edge_http_url,
                "preflight_performed": True,
                "selected_transport": _selected_preflight_transport(
                    selected_client or client
                ),
                "runtime_transport": (selected_client or client).transport,
                "fallback_transport_configured": isinstance(client, FallbackVoiceEdgeClient),
                "fallback_transport_available": _fallback_transport_available(client),
                "fallback_transport_used": (
                    isinstance(client, FallbackVoiceEdgeClient)
                    and selected_client is client.fallback
                ),
                "target_vad_model": settings.gemma4_realtime_rust_vad_model,
                "vad_model_path_configured": bool(settings.rust_voice_edge_vad_model_path),
                "vad_fallback_allowed": settings.rust_voice_edge_allow_vad_fallback,
                **_client_vad_metadata(selected_client or client),
            },
        )
    except Exception as exc:
        return VoiceRuntimeReadinessCheck(
            check_id="rust-voice-edge",
            label="Rust VAD and barge-in edge",
            status=RuntimeHealthStatus.BLOCKED,
            evidence=[f"Startup preflight failed: {exc}"],
            next_actions=["Start the HTTP sidecar or rebuild services/voice-edge, then rerun preflight."],
            metadata={
                "binary_path_configured": bool(settings.rust_voice_edge_binary_path),
                "binary_executable": binary_executable,
                "http_configured": http_configured,
                "http_url": settings.rust_voice_edge_http_url,
                "preflight_performed": True,
                "error": str(exc),
                "target_vad_model": settings.gemma4_realtime_rust_vad_model,
                "vad_model_path_configured": bool(settings.rust_voice_edge_vad_model_path),
                "vad_fallback_allowed": settings.rust_voice_edge_allow_vad_fallback,
                **_settings_vad_metadata(settings),
            },
        )
    finally:
        close_target = selected_client or client
        await close_target.aclose()


def _settings_vad_metadata(settings: Settings) -> dict[str, str | None]:
    return {
        "vad_backend_requested": settings.rust_voice_edge_vad_backend,
        **describe_vad_runtime(
            vad_backend=settings.rust_voice_edge_vad_backend,
            allow_vad_fallback=settings.rust_voice_edge_allow_vad_fallback,
        ),
    }


def _client_vad_metadata(client: Any) -> dict[str, str | None]:
    return {
        "vad_backend_requested": client.vad_backend,
        "vad_backend_effective": client.vad_backend_effective,
        "vad_model_effective": client.vad_model_effective,
        "vad_fallback_reason": client.vad_fallback_reason,
    }


def _selected_preflight_transport(client: Any) -> str:
    if isinstance(client, FallbackVoiceEdgeClient):
        return client.primary.transport
    return client.transport


def _fallback_transport_available(client: Any) -> bool:
    return isinstance(client, FallbackVoiceEdgeClient) and client.fallback.available


def _context_pruning_check(settings: Settings) -> VoiceRuntimeReadinessCheck:
    ready = (
        settings.gemma4_realtime_context_prune_after_turns
        <= settings.gemma4_realtime_context_window_turns
    )
    return VoiceRuntimeReadinessCheck(
        check_id="voice-context-pruning",
        label="Audio context pruning",
        status=RuntimeHealthStatus.READY if ready else RuntimeHealthStatus.BLOCKED,
        evidence=[
            (
                "Raw audio is pruned after "
                f"{settings.gemma4_realtime_context_prune_after_turns} turns in a "
                f"{settings.gemma4_realtime_context_window_turns}-turn window."
            )
        ],
        next_actions=(
            []
            if ready
            else ["Set GEMMA4_REALTIME_CONTEXT_PRUNE_AFTER_TURNS <= GEMMA4_REALTIME_CONTEXT_WINDOW_TURNS."]
        ),
        metadata={
            "context_window_turns": settings.gemma4_realtime_context_window_turns,
            "prune_after_turns": settings.gemma4_realtime_context_prune_after_turns,
            "max_raw_audio_seconds_per_turn": settings.gemma4_realtime_max_audio_seconds_per_turn,
        },
    )


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
