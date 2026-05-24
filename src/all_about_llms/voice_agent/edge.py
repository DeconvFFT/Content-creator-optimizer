import asyncio
import json
import os
import struct
from collections import OrderedDict, deque
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from all_about_llms.providers.interfaces import ProviderConfigurationError

VOICE_BARGE_IN_EVENT = "voice_barge_in_detected"
VOICE_EDGE_CANCELLATION_ACK_EVENT = "voice_edge_cancellation_acknowledged"
VOICE_EDGE_REQUIRED_HEALTH = {
    "service": "voice-edge",
    "transport": "http",
    "request_contract": "voice_edge_request_v1",
    "state_model": "stateless_request_response",
}


def describe_vad_runtime(
    *,
    vad_backend: str,
    allow_vad_fallback: bool,
) -> dict[str, str | None]:
    if vad_backend == "silero_onnx":
        if allow_vad_fallback:
            return {
                "vad_backend_effective": "silero_onnx_with_deterministic_fallback",
                "vad_model_effective": "silero_onnx_bundled_or_configured_model",
                "vad_fallback_reason": None,
            }
        return {
            "vad_backend_effective": "silero_onnx_required",
            "vad_model_effective": "silero_onnx_bundled_or_configured_model",
            "vad_fallback_reason": None,
        }
    return {
        "vad_backend_effective": "deterministic_energy",
        "vad_model_effective": "deterministic_energy_gate",
        "vad_fallback_reason": None,
    }


@dataclass(frozen=True, slots=True)
class VoiceEdgeFrame:
    sequence: int
    pcm_s16le: bytes
    timestamp_ms: int | None = None


@dataclass(frozen=True, slots=True)
class VoiceEdgeCancellationAck:
    response_id: str
    reason: str
    drop_outbound_audio: bool
    cancel_gemma: bool
    clear_kokoro_buffers: bool
    stop_livekit_audio: bool


@dataclass(frozen=True, slots=True)
class VoiceEdgeAnalysisResult:
    request_id: str | None
    session_id: str
    events: list[dict[str, Any]]
    final_state: dict[str, Any]
    cancellation_ack: VoiceEdgeCancellationAck | None


class VoiceEdgeClient:
    """Common request builder for Rust voice-edge transports."""

    transport = "abstract"

    def __init__(
        self,
        *,
        timeout_seconds: float = 1.0,
        sample_rate: int = 16_000,
        frame_ms: int = 32,
        vad_backend: str = "deterministic_energy",
        target_vad_model: str = "silero-vad-rust",
        vad_model_path: str | Path | None = None,
        allow_vad_fallback: bool = True,
        vad_threshold: float = 0.018,
        vad_probability_threshold: float = 0.5,
        vad_session_pool_size: int = 4,
        vad_stream_state_cache_size: int = 512,
        min_speech_frames: int = 2,
        max_inbound_buffer_bytes: int = 16_000 * 2 * 30,
        max_outbound_buffer_bytes: int = 16_000 * 2 * 2,
        max_recent_frame_windows: int = 1024,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.vad_backend = vad_backend
        self.target_vad_model = target_vad_model
        self.vad_model_path = str(vad_model_path) if vad_model_path else None
        self.allow_vad_fallback = allow_vad_fallback
        self.vad_threshold = vad_threshold
        self.vad_probability_threshold = vad_probability_threshold
        self.vad_session_pool_size = max(1, min(vad_session_pool_size, 16))
        self.vad_stream_state_cache_size = max(
            1, min(vad_stream_state_cache_size, 4096)
        )
        self.min_speech_frames = max(1, min_speech_frames)
        self.max_inbound_buffer_bytes = max_inbound_buffer_bytes
        self.max_outbound_buffer_bytes = max_outbound_buffer_bytes
        self.max_recent_frame_windows = max(1, max_recent_frame_windows)
        self._recent_frames: OrderedDict[str, deque[VoiceEdgeFrame]] = OrderedDict()

    @property
    def available(self) -> bool:
        return True

    @property
    def process_mode(self) -> str:
        return self.transport

    @property
    def serializes_requests(self) -> bool:
        return False

    async def analyze_pcm_frame(
        self,
        *,
        session_id: str,
        response_id: str | None,
        agent_speaking: bool,
        sequence: int,
        pcm_s16le: bytes,
        timestamp_ms: int | None = None,
        request_id: str | None = None,
    ) -> VoiceEdgeAnalysisResult:
        frame = VoiceEdgeFrame(
            sequence=sequence,
            pcm_s16le=pcm_s16le,
            timestamp_ms=timestamp_ms,
        )
        recent = self._recent_frame_window(f"{session_id}:{response_id or ''}")
        recent.append(frame)
        return await self.analyze_frames(
            session_id=session_id,
            response_id=response_id,
            agent_speaking=agent_speaking,
            frames=list(recent),
            request_id=request_id,
        )

    async def analyze_frames(
        self,
        *,
        session_id: str,
        response_id: str | None,
        agent_speaking: bool,
        frames: Sequence[VoiceEdgeFrame],
        request_id: str | None = None,
    ) -> VoiceEdgeAnalysisResult:
        return await self._run(
            {
                "kind": "analyze",
                "request_id": request_id or f"voice-edge-{uuid4()}",
                "session_id": session_id,
                "response_id": response_id,
                "agent_speaking": agent_speaking,
                "config": self._config_payload(),
                "frames": [
                    {
                        "sequence": frame.sequence,
                        "timestamp_ms": frame.timestamp_ms,
                        "pcm_s16le": _pcm_s16le_to_samples(frame.pcm_s16le),
                    }
                    for frame in frames
                ],
            }
        )

    async def cancel_response(
        self,
        *,
        session_id: str,
        response_id: str,
        reason: str = "barge-in detected",
        request_id: str | None = None,
    ) -> VoiceEdgeAnalysisResult:
        return await self._run(
            {
                "kind": "cancel",
                "request_id": request_id or f"voice-edge-{uuid4()}",
                "session_id": session_id,
                "response_id": response_id,
                "reason": reason,
            }
        )

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "transport": self.transport,
        }

    @property
    def vad_backend_effective(self) -> str:
        return str(
            describe_vad_runtime(
                vad_backend=self.vad_backend,
                allow_vad_fallback=self.allow_vad_fallback,
            )["vad_backend_effective"]
        )

    @property
    def vad_model_effective(self) -> str:
        return str(
            describe_vad_runtime(
                vad_backend=self.vad_backend,
                allow_vad_fallback=self.allow_vad_fallback,
            )["vad_model_effective"]
        )

    @property
    def vad_fallback_reason(self) -> str | None:
        reason = describe_vad_runtime(
            vad_backend=self.vad_backend,
            allow_vad_fallback=self.allow_vad_fallback,
        )["vad_fallback_reason"]
        return str(reason) if reason is not None else None

    async def aclose(self) -> None:
        return None

    async def _run(self, payload: dict[str, Any]) -> VoiceEdgeAnalysisResult:
        raise NotImplementedError

    def _recent_frame_window(self, key: str) -> deque[VoiceEdgeFrame]:
        recent = self._recent_frames.get(key)
        if recent is not None:
            self._recent_frames.move_to_end(key)
            return recent
        while len(self._recent_frames) >= self.max_recent_frame_windows:
            self._recent_frames.popitem(last=False)
        recent = deque(maxlen=self.min_speech_frames)
        self._recent_frames[key] = recent
        return recent

    def _config_payload(self) -> dict[str, Any]:
        return {
            "sample_rate": self.sample_rate,
            "frame_ms": self.frame_ms,
            "vad_backend": self.vad_backend,
            "target_vad_model": self.target_vad_model,
            "vad_model_path": self.vad_model_path,
            "allow_vad_fallback": self.allow_vad_fallback,
            "vad_threshold": self.vad_threshold,
            "vad_probability_threshold": self.vad_probability_threshold,
            "vad_session_pool_size": self.vad_session_pool_size,
            "vad_stream_state_cache_size": self.vad_stream_state_cache_size,
            "min_speech_frames": self.min_speech_frames,
            "max_inbound_buffer_bytes": self.max_inbound_buffer_bytes,
            "max_outbound_buffer_bytes": self.max_outbound_buffer_bytes,
        }


class RustVoiceEdgeClient(VoiceEdgeClient):
    """One-shot subprocess adapter for the Rust voice-edge contract core."""

    transport = "subprocess"

    @property
    def process_mode(self) -> str:
        return "one_request_per_process"

    def __init__(
        self,
        *,
        binary_path: str | Path,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.binary_path = Path(binary_path)

    @property
    def available(self) -> bool:
        return self.binary_path.is_file() and os.access(self.binary_path, os.X_OK)

    async def _run(self, payload: dict[str, Any]) -> VoiceEdgeAnalysisResult:
        if not self.available:
            raise ProviderConfigurationError(
                f"Rust voice-edge binary not found: {self.binary_path}"
            )

        process = await asyncio.create_subprocess_exec(
            str(self.binary_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(json.dumps(payload).encode("utf-8")),
                timeout=self.timeout_seconds,
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise RuntimeError(
                f"Rust voice-edge timed out after {self.timeout_seconds}s"
            ) from exc

        if process.returncode != 0:
            raise RuntimeError(
                "Rust voice-edge failed: "
                f"{stderr.decode('utf-8', errors='replace').strip()}"
            )

        try:
            response = json.loads(stdout.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Rust voice-edge returned invalid JSON") from exc
        return _parse_voice_edge_response(response)


class RustVoiceEdgeHttpClient(VoiceEdgeClient):
    """HTTP sidecar adapter for the Rust voice-edge Axum/Tokio surface."""

    transport = "http_sidecar"

    def __init__(self, *, base_url: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def health_check(self) -> dict[str, Any]:
        client = self._ensure_client()
        response = await client.get(f"{self.base_url}/healthz")
        response.raise_for_status()
        raw_payload = response.json()
        if not isinstance(raw_payload, dict):
            raise RuntimeError(
                "Rust voice-edge HTTP sidecar health check returned "
                f"non-object JSON payload: {type(raw_payload).__name__}"
            )
        payload = dict(raw_payload)
        if payload.get("status") != "ok":
            raise RuntimeError(
                "Rust voice-edge HTTP sidecar health check returned "
                f"status={payload.get('status')!r}"
            )
        mismatches = {
            key: payload.get(key)
            for key, expected in VOICE_EDGE_REQUIRED_HEALTH.items()
            if payload.get(key) != expected
        }
        if mismatches:
            raise RuntimeError(
                "Rust voice-edge HTTP sidecar health contract mismatch: "
                f"{mismatches!r}"
            )
        supported_vad_backends = payload.get("supported_vad_backends") or []
        if self.vad_backend not in supported_vad_backends:
            raise RuntimeError(
                "Rust voice-edge HTTP sidecar does not advertise requested "
                f"VAD backend {self.vad_backend!r}"
            )
        return payload

    async def _run(self, payload: dict[str, Any]) -> VoiceEdgeAnalysisResult:
        client = self._ensure_client()
        try:
            response = await client.post(
                f"{self.base_url}/v1/voice-edge",
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Rust voice-edge HTTP request failed: {exc}") from exc
        try:
            raw = response.json()
        except ValueError as exc:
            raise RuntimeError("Rust voice-edge HTTP returned invalid JSON") from exc
        return _parse_voice_edge_response(dict(raw))

    async def aclose(self) -> None:
        if self._client is None:
            return
        await self._client.aclose()
        self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self._client


class FallbackVoiceEdgeClient(VoiceEdgeClient):
    """Primary voice-edge transport with a secondary fallback transport."""

    transport = "http_sidecar_with_persistent_jsonl_fallback"

    def __init__(
        self,
        *,
        primary: VoiceEdgeClient,
        fallback: VoiceEdgeClient,
    ) -> None:
        super().__init__(
            timeout_seconds=primary.timeout_seconds,
            sample_rate=primary.sample_rate,
            frame_ms=primary.frame_ms,
            vad_backend=primary.vad_backend,
            target_vad_model=primary.target_vad_model,
            vad_model_path=primary.vad_model_path,
            allow_vad_fallback=primary.allow_vad_fallback,
            vad_threshold=primary.vad_threshold,
            vad_probability_threshold=primary.vad_probability_threshold,
            vad_session_pool_size=primary.vad_session_pool_size,
            vad_stream_state_cache_size=primary.vad_stream_state_cache_size,
            min_speech_frames=primary.min_speech_frames,
            max_inbound_buffer_bytes=primary.max_inbound_buffer_bytes,
            max_outbound_buffer_bytes=primary.max_outbound_buffer_bytes,
            max_recent_frame_windows=primary.max_recent_frame_windows,
        )
        self.primary = primary
        self.fallback = fallback

    @property
    def available(self) -> bool:
        return self.primary.available or self.fallback.available

    @property
    def process_mode(self) -> str:
        return f"{self.primary.process_mode}_with_{self.fallback.process_mode}_fallback"

    @property
    def serializes_requests(self) -> bool:
        return self.primary.serializes_requests or self.fallback.serializes_requests

    @property
    def base_url(self) -> str | None:
        return getattr(self.primary, "base_url", None)

    @property
    def binary_path(self) -> Path | None:
        return getattr(self.fallback, "binary_path", None)

    async def _run(self, payload: dict[str, Any]) -> VoiceEdgeAnalysisResult:
        try:
            return await self.primary._run(payload)
        except Exception as exc:
            if not self.fallback.available:
                raise
            result = await self.fallback._run(payload)
            result.events.insert(
                0,
                {
                    "event_type": "voice_edge_transport_fallback",
                    "metadata": {
                        "primary_transport": self.primary.transport,
                        "fallback_transport": self.fallback.transport,
                        "error": str(exc),
                    },
                },
            )
            return result

    async def aclose(self) -> None:
        first_error: Exception | None = None
        for client in (self.primary, self.fallback):
            try:
                await client.aclose()
            except Exception as exc:
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise RuntimeError("voice-edge fallback transport cleanup failed") from first_error


class PersistentRustVoiceEdgeClient(RustVoiceEdgeClient):
    """Long-lived JSONL adapter for frame-by-frame realtime audio use."""

    transport = "persistent_jsonl"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._process: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()

    @property
    def process_mode(self) -> str:
        return "persistent_jsonl"

    @property
    def serializes_requests(self) -> bool:
        return True

    async def health_check(self) -> dict[str, Any]:
        result = await self.cancel_response(
            session_id="voice-edge-preflight",
            response_id="voice-edge-preflight",
            reason="startup preflight",
            request_id="voice-edge-jsonl-preflight",
        )
        if result.cancellation_ack is None:
            raise RuntimeError("Rust voice-edge JSONL preflight missing cancellation ack")
        return {
            "status": "ok",
            "transport": self.transport,
            "request_id": result.request_id,
            "process_mode": "jsonl",
        }

    async def aclose(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.stdin is not None:
            process.stdin.close()
            await process.stdin.wait_closed()
        try:
            await asyncio.wait_for(process.wait(), timeout=1.0)
        except TimeoutError:
            process.kill()
            await process.wait()

    async def _run(self, payload: dict[str, Any]) -> VoiceEdgeAnalysisResult:
        if not self.available:
            raise ProviderConfigurationError(
                f"Rust voice-edge binary not found: {self.binary_path}"
            )
        async with self._lock:
            process = await self._ensure_process()
            if process.stdin is None or process.stdout is None:
                raise RuntimeError("Rust voice-edge JSONL process has no pipes")
            request = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            process.stdin.write(request + b"\n")
            await process.stdin.drain()
            try:
                line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=self.timeout_seconds,
                )
            except TimeoutError as exc:
                await self._restart_after_failure()
                raise RuntimeError(
                    f"Rust voice-edge timed out after {self.timeout_seconds}s"
                ) from exc
            if not line:
                await self._restart_after_failure()
                stderr = await _read_process_stderr(process)
                raise RuntimeError(f"Rust voice-edge JSONL process exited: {stderr}")
        try:
            response = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as exc:
            await self._restart_after_failure()
            raise RuntimeError("Rust voice-edge returned invalid JSON") from exc
        return _parse_voice_edge_response(response)

    async def _ensure_process(self) -> asyncio.subprocess.Process:
        if self._process is not None and self._process.returncode is None:
            return self._process
        self._process = await asyncio.create_subprocess_exec(
            str(self.binary_path),
            "--jsonl",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return self._process

    async def _restart_after_failure(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.returncode is None:
            process.kill()
        await process.wait()


def _parse_voice_edge_response(response: dict[str, Any]) -> VoiceEdgeAnalysisResult:
    cancellation_ack = None
    events = list(response.get("events") or [])
    for event in events:
        raw_ack = event.get("cancellation")
        if raw_ack:
            cancellation_ack = VoiceEdgeCancellationAck(
                response_id=str(raw_ack["response_id"]),
                reason=str(raw_ack["reason"]),
                drop_outbound_audio=bool(raw_ack["drop_outbound_audio"]),
                cancel_gemma=bool(raw_ack["cancel_gemma"]),
                clear_kokoro_buffers=bool(raw_ack["clear_kokoro_buffers"]),
                stop_livekit_audio=bool(raw_ack["stop_livekit_audio"]),
            )

    return VoiceEdgeAnalysisResult(
        request_id=response.get("request_id"),
        session_id=str(response["session_id"]),
        events=events,
        final_state=dict(response.get("final_state") or {}),
        cancellation_ack=cancellation_ack,
    )


def _pcm_s16le_to_samples(pcm: bytes) -> list[int]:
    even_length = len(pcm) - (len(pcm) % 2)
    if even_length <= 0:
        return []
    return list(struct.unpack(f"<{even_length // 2}h", pcm[:even_length]))


async def _read_process_stderr(process: asyncio.subprocess.Process) -> str:
    if process.stderr is None:
        return ""
    try:
        raw = await asyncio.wait_for(process.stderr.read(), timeout=0.2)
    except TimeoutError:
        return ""
    return raw.decode("utf-8", errors="replace").strip()
