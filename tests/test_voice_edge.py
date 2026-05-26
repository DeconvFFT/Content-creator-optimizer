import asyncio
import os
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest

from all_about_llms.providers.interfaces import ProviderConfigurationError
from all_about_llms.voice_agent import edge as edge_module
from all_about_llms.voice_agent.edge import (
    FallbackVoiceEdgeClient,
    PersistentRustVoiceEdgeClient,
    RustVoiceEdgeHttpClient,
    RustVoiceEdgeClient,
    VoiceEdgeFrame,
    _pcm_s16le_to_samples,
)

ROOT = Path(__file__).resolve().parents[1]


def test_pcm_s16le_conversion_drops_trailing_partial_sample():
    assert _pcm_s16le_to_samples(b"\x01\x00\xff\xff\x00") == [1, -1]


def test_rust_voice_edge_client_parses_barge_in_ack(tmp_path):
    fake_binary = _write_fake_voice_edge(tmp_path)
    client = RustVoiceEdgeClient(
        binary_path=fake_binary,
        timeout_seconds=1.0,
        min_speech_frames=2,
    )

    result = asyncio.run(
        client.analyze_frames(
            session_id="voice-session-1",
            response_id="voice-response-1",
            agent_speaking=True,
            frames=[
                VoiceEdgeFrame(sequence=1, pcm_s16le=b"\x00\x00\x00\x00"),
                VoiceEdgeFrame(sequence=2, pcm_s16le=b"\x01\x00\x02\x00"),
            ],
            request_id="request-1",
        )
    )

    assert result.request_id == "request-1"
    assert result.session_id == "voice-session-1"
    assert result.cancellation_ack is not None
    assert result.cancellation_ack.response_id == "voice-response-1"
    assert result.cancellation_ack.cancel_gemma is True
    assert result.cancellation_ack.clear_kokoro_buffers is True
    assert result.cancellation_ack.stop_livekit_audio is True
    assert result.final_state["cancellation_acknowledged"] is True
    assert result.events[0]["metadata"]["last_frame_sample_count"] == "2"


def test_rust_voice_edge_client_sends_cancel_contract(tmp_path):
    fake_binary = _write_fake_voice_edge(tmp_path)
    client = RustVoiceEdgeClient(binary_path=fake_binary, timeout_seconds=1.0)

    result = asyncio.run(
        client.cancel_response(
            session_id="voice-session-1",
            response_id="voice-response-1",
            reason="manual interrupt",
            request_id="cancel-1",
        )
    )

    assert result.cancellation_ack is not None
    assert result.cancellation_ack.reason == "manual interrupt"
    assert result.events[0]["event_type"] == "voice_edge_cancellation_acknowledged"


def test_persistent_rust_voice_edge_client_reuses_jsonl_process(tmp_path):
    fake_binary = _write_fake_voice_edge(tmp_path)
    client = PersistentRustVoiceEdgeClient(binary_path=fake_binary, timeout_seconds=1.0)

    async def run_requests():
        first = await client.analyze_frames(
            session_id="voice-session-1",
            response_id="voice-response-1",
            agent_speaking=True,
            frames=[VoiceEdgeFrame(sequence=1, pcm_s16le=b"\x01\x00\x02\x00")],
            request_id="request-1",
        )
        first_pid = client._process.pid
        second = await client.cancel_response(
            session_id="voice-session-1",
            response_id="voice-response-1",
            reason="manual interrupt",
            request_id="request-2",
        )
        second_pid = client._process.pid
        await client.aclose()
        return first, first_pid, second, second_pid

    first, first_pid, second, second_pid = asyncio.run(run_requests())

    assert first.request_id == "request-1"
    assert second.request_id == "request-2"
    assert first_pid == second_pid
    assert second.cancellation_ack is not None
    assert second.cancellation_ack.reason == "manual interrupt"


def test_persistent_rust_voice_edge_client_health_check_starts_jsonl_process(tmp_path):
    fake_binary = _write_fake_voice_edge(tmp_path)
    client = PersistentRustVoiceEdgeClient(binary_path=fake_binary, timeout_seconds=1.0)

    async def run_health_check():
        health = await client.health_check()
        pid = client._process.pid
        await client.aclose()
        return health, pid

    health, pid = asyncio.run(run_health_check())

    assert health["status"] == "ok"
    assert health["transport"] == "persistent_jsonl"
    assert health["request_id"] == "voice-edge-jsonl-preflight"
    assert isinstance(pid, int)


def test_recent_frame_windows_are_bounded(tmp_path):
    fake_binary = _write_fake_voice_edge(tmp_path)
    client = RustVoiceEdgeClient(
        binary_path=fake_binary,
        timeout_seconds=1.0,
        max_recent_frame_windows=2,
    )

    async def run_requests():
        for index in range(4):
            await client.analyze_pcm_frame(
                session_id=f"voice-session-{index}",
                response_id=f"voice-response-{index}",
                agent_speaking=False,
                sequence=1,
                pcm_s16le=b"\x01\x00\x02\x00",
            )

    asyncio.run(run_requests())

    assert len(client._recent_frames) == 2
    assert "voice-session-0:voice-response-0" not in client._recent_frames
    assert "voice-session-3:voice-response-3" in client._recent_frames


def test_rust_voice_edge_http_client_posts_tagged_contract(monkeypatch):
    FakeVoiceEdgeHttpClient.requests = []
    FakeVoiceEdgeHttpClient.instances = []
    monkeypatch.setattr(edge_module.httpx, "AsyncClient", FakeVoiceEdgeHttpClient)
    client = RustVoiceEdgeHttpClient(
        base_url="http://voice-edge.local:7071/",
        timeout_seconds=1.0,
        min_speech_frames=2,
    )

    async def run_request():
        return await client.analyze_frames(
            session_id="voice-session-1",
            response_id="voice-response-1",
            agent_speaking=True,
            frames=[
                VoiceEdgeFrame(sequence=1, pcm_s16le=b"\x00\x00\x00\x00"),
                VoiceEdgeFrame(sequence=2, pcm_s16le=b"\x01\x00\x02\x00"),
            ],
            request_id="http-request-1",
        )

    result = asyncio.run(run_request())

    assert result.request_id == "http-request-1"
    assert result.cancellation_ack is not None
    assert result.cancellation_ack.cancel_gemma is True
    request = FakeVoiceEdgeHttpClient.requests[0]
    assert request["method"] == "POST"
    assert request["url"] == "http://voice-edge.local:7071/v1/voice-edge"
    assert request["json"]["kind"] == "analyze"
    assert request["json"]["config"]["min_speech_frames"] == 2
    assert request["json"]["config"]["vad_backend"] == "deterministic_energy"
    assert request["json"]["config"]["target_vad_model"] == "silero-vad-rust"
    assert request["json"]["config"]["allow_vad_fallback"] is True
    assert request["json"]["config"]["vad_probability_threshold"] == 0.5
    assert request["json"]["config"]["vad_session_pool_size"] == 4
    assert request["json"]["config"]["vad_stream_state_cache_size"] == 512
    assert request["json"]["frames"][-1]["pcm_s16le"] == [1, 2]
    assert len(FakeVoiceEdgeHttpClient.instances) == 1


def test_rust_voice_edge_http_client_sends_cancel_and_health(monkeypatch):
    FakeVoiceEdgeHttpClient.requests = []
    FakeVoiceEdgeHttpClient.instances = []
    monkeypatch.setattr(edge_module.httpx, "AsyncClient", FakeVoiceEdgeHttpClient)
    client = RustVoiceEdgeHttpClient(
        base_url="http://voice-edge.local:7071",
        timeout_seconds=1.0,
    )

    async def run_requests():
        health = await client.health_check()
        cancel = await client.cancel_response(
            session_id="voice-session-1",
            response_id="voice-response-1",
            reason="manual interrupt",
            request_id="cancel-http-1",
        )
        return health, cancel

    health, cancel = asyncio.run(run_requests())

    assert health["status"] == "ok"
    assert health["transport"] == "http"
    assert health["request_contract"] == "voice_edge_request_v1"
    assert cancel.cancellation_ack is not None
    assert cancel.cancellation_ack.reason == "manual interrupt"
    assert [request["method"] for request in FakeVoiceEdgeHttpClient.requests] == [
        "GET",
        "POST",
    ]
    assert FakeVoiceEdgeHttpClient.requests[1]["json"]["kind"] == "cancel"
    assert len(FakeVoiceEdgeHttpClient.instances) == 1


def test_rust_voice_edge_http_client_rejects_unhealthy_health_payload(monkeypatch):
    FakeUnhealthyVoiceEdgeHttpClient.requests = []
    monkeypatch.setattr(
        edge_module.httpx, "AsyncClient", FakeUnhealthyVoiceEdgeHttpClient
    )
    client = RustVoiceEdgeHttpClient(
        base_url="http://voice-edge.local:7071",
        timeout_seconds=1.0,
    )

    with pytest.raises(RuntimeError, match="status='degraded'"):
        asyncio.run(client.health_check())


def test_rust_voice_edge_http_client_rejects_wrong_health_contract(monkeypatch):
    FakeWrongContractVoiceEdgeHttpClient.requests = []
    monkeypatch.setattr(
        edge_module.httpx, "AsyncClient", FakeWrongContractVoiceEdgeHttpClient
    )
    client = RustVoiceEdgeHttpClient(
        base_url="http://not-voice-edge.local:7071",
        timeout_seconds=1.0,
    )

    with pytest.raises(RuntimeError, match="health contract mismatch"):
        asyncio.run(client.health_check())


def test_rust_voice_edge_http_client_rejects_non_object_health_payload(monkeypatch):
    FakeNonObjectHealthVoiceEdgeHttpClient.requests = []
    monkeypatch.setattr(
        edge_module.httpx, "AsyncClient", FakeNonObjectHealthVoiceEdgeHttpClient
    )
    client = RustVoiceEdgeHttpClient(
        base_url="http://not-voice-edge.local:7071",
        timeout_seconds=1.0,
    )

    with pytest.raises(RuntimeError, match="non-object JSON payload"):
        asyncio.run(client.health_check())


def test_voice_edge_fallback_client_uses_jsonl_when_http_fails(tmp_path):
    fake_binary = _write_fake_voice_edge(tmp_path)
    client = FallbackVoiceEdgeClient(
        primary=AlwaysFailVoiceEdgeClient(),
        fallback=PersistentRustVoiceEdgeClient(
            binary_path=fake_binary,
            timeout_seconds=1.0,
        ),
    )

    async def run():
        try:
            return await client.analyze_frames(
                session_id="voice-session-1",
                response_id="voice-response-1",
                agent_speaking=True,
                frames=[VoiceEdgeFrame(sequence=1, pcm_s16le=b"\x01\x00\x02\x00")],
                request_id="fallback-1",
            )
        finally:
            await client.aclose()

    result = asyncio.run(run())

    assert (
        client.process_mode
        == "http_sidecar_with_persistent_jsonl_fallback"
    )
    assert client.serializes_requests is True
    assert result.request_id == "fallback-1"
    assert result.events[0]["event_type"] == "voice_edge_transport_fallback"
    assert result.events[0]["metadata"]["primary_transport"] == "http_sidecar"
    assert result.events[0]["metadata"]["fallback_transport"] == "persistent_jsonl"
    assert result.cancellation_ack is not None
    assert result.cancellation_ack.cancel_gemma is True

def test_voice_edge_fallback_client_closes_fallback_when_primary_close_fails():
    primary = CloseFailVoiceEdgeClient()
    fallback = CloseTrackVoiceEdgeClient()
    client = FallbackVoiceEdgeClient(primary=primary, fallback=fallback)

    with pytest.raises(RuntimeError, match="cleanup failed"):
        asyncio.run(client.aclose())

    assert primary.close_attempted is True
    assert fallback.close_attempted is True


def test_real_rust_voice_edge_http_sidecar_health_and_cancel_smoke():
    binary = ROOT / "services/voice-edge/target/debug/voice-edge"
    if not binary.is_file() or not os.access(binary, os.X_OK):
        pytest.skip("compiled Rust voice-edge binary is not available")
    try:
        port = _free_loopback_port()
    except PermissionError:
        pytest.skip("loopback binding is not permitted in this environment")
    process = subprocess.Popen(
        [str(binary), "--http", f"127.0.0.1:{port}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    client = RustVoiceEdgeHttpClient(
        base_url=f"http://127.0.0.1:{port}",
        timeout_seconds=1.0,
    )
    try:
        _wait_for_sidecar_health(port, process)
        analyze_response = httpx.post(
            f"http://127.0.0.1:{port}/v1/voice-edge/analyze",
            json={
                "request_id": "real-sidecar-analyze",
                "session_id": "real-sidecar-smoke",
                "response_id": "real-sidecar-response",
                "agent_speaking": True,
                "frames": [
                    {"sequence": 1, "timestamp_ms": 32, "pcm_s16le": [2600] * 512},
                    {"sequence": 2, "timestamp_ms": 64, "pcm_s16le": [2600] * 512},
                ],
            },
            timeout=1.0,
        )
        analyze_response.raise_for_status()
        analyze_payload = analyze_response.json()
        assert analyze_payload["request_id"] == "real-sidecar-analyze"
        assert analyze_payload["final_state"]["cancellation_acknowledged"] is True
        _assert_payload_has_full_stop_ack(analyze_payload)

        typed_cancel_response = httpx.post(
            f"http://127.0.0.1:{port}/v1/voice-edge/cancel",
            json={
                "request_id": "real-sidecar-typed-cancel",
                "session_id": "real-sidecar-smoke",
                "response_id": "real-sidecar-response",
                "reason": "typed cancel smoke",
            },
            timeout=1.0,
        )
        typed_cancel_response.raise_for_status()
        typed_cancel_payload = typed_cancel_response.json()
        assert typed_cancel_payload["request_id"] == "real-sidecar-typed-cancel"
        _assert_payload_has_full_stop_ack(typed_cancel_payload)

        async def run_generic_client_requests():
            speech_frame = (2600).to_bytes(2, "little", signed=True) * 512
            try:
                generic_analyze = await client.analyze_frames(
                    session_id="real-sidecar-smoke",
                    response_id="real-sidecar-response",
                    agent_speaking=True,
                    frames=[
                        VoiceEdgeFrame(sequence=1, pcm_s16le=speech_frame),
                        VoiceEdgeFrame(sequence=2, pcm_s16le=speech_frame),
                    ],
                    request_id="real-sidecar-generic-analyze",
                )
                result = await client.cancel_response(
                    session_id="real-sidecar-smoke",
                    response_id="real-sidecar-response",
                    reason="startup smoke",
                    request_id="real-sidecar-cancel",
                )
                return generic_analyze, result
            finally:
                await client.aclose()

        generic_analyze, result = asyncio.run(run_generic_client_requests())
        assert generic_analyze.request_id == "real-sidecar-generic-analyze"
        assert generic_analyze.cancellation_ack is not None
        _assert_full_stop_ack(generic_analyze.cancellation_ack)

        assert result.request_id == "real-sidecar-cancel"
        assert result.cancellation_ack is not None
        _assert_full_stop_ack(result.cancellation_ack)
    finally:
        asyncio.run(client.aclose())
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def test_rust_voice_edge_client_requires_binary(tmp_path):
    client = RustVoiceEdgeClient(binary_path=tmp_path / "missing-voice-edge")

    with pytest.raises(ProviderConfigurationError):
        asyncio.run(
            client.analyze_frames(
                session_id="voice-session-1",
                response_id=None,
                agent_speaking=False,
                frames=[],
            )
        )


def test_rust_voice_edge_client_requires_executable_binary(tmp_path):
    fake_binary = tmp_path / "voice-edge"
    fake_binary.write_text("#!/bin/sh\n", encoding="utf-8")
    fake_binary.chmod(0o644)
    client = RustVoiceEdgeClient(binary_path=fake_binary)

    assert client.available is False
    with pytest.raises(ProviderConfigurationError):
        asyncio.run(
            client.cancel_response(
                session_id="voice-session-1",
                response_id="voice-response-1",
            )
        )


def _write_fake_voice_edge(tmp_path):
    fake_binary = tmp_path / "voice-edge"
    fake_binary.write_text(
        """#!/usr/bin/env python3
import json
import sys

def handle(payload):
    response_id = payload.get("response_id") or "unknown-response"
    reason = payload.get("reason") or "barge-in detected"
    last_frame = (payload.get("frames") or [{"sequence": None, "pcm_s16le": []}])[-1]
    ack = {
        "response_id": response_id,
        "reason": reason,
        "drop_outbound_audio": True,
        "cancel_gemma": True,
        "clear_kokoro_buffers": True,
        "stop_livekit_audio": True,
    }
    return {
        "request_id": payload.get("request_id"),
        "session_id": payload["session_id"],
        "events": [{
            "event_type": "voice_edge_cancellation_acknowledged",
            "sequence": last_frame.get("sequence"),
            "response_id": response_id,
            "cancellation": ack,
            "metadata": {
                "request_kind": payload["kind"],
                "last_frame_sample_count": str(len(last_frame.get("pcm_s16le") or [])),
            },
        }],
        "final_state": {
            "inbound_buffer_bytes": 0,
            "outbound_buffer_bytes": 0,
            "consecutive_speech_frames": 2,
            "agent_speaking": bool(payload.get("agent_speaking")),
            "active_response_id": response_id,
            "cancellation_acknowledged": True,
        },
    }

if "--jsonl" in sys.argv:
    for line in sys.stdin:
        if line.strip():
            print(json.dumps(handle(json.loads(line))), flush=True)
else:
    print(json.dumps(handle(json.loads(sys.stdin.read()))))
""",
        encoding="utf-8",
    )
    os.chmod(fake_binary, 0o755)
    return fake_binary


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_sidecar_health(port: int, process: subprocess.Popen, timeout: float = 4.0):
    deadline = time.monotonic() + timeout
    last_error = None
    url = f"http://127.0.0.1:{port}/healthz"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError("voice-edge sidecar exited early")
        try:
            response = httpx.get(url, timeout=0.2)
            payload = response.json()
            if (
                response.status_code == 200
                and isinstance(payload, dict)
                and payload.get("status") == "ok"
                and payload.get("service") == "voice-edge"
                and payload.get("transport") == "http"
                and payload.get("request_contract") == "voice_edge_request_v1"
                and payload.get("state_model") == "stateless_request_response"
                and payload.get("target_vad_model") == "silero-vad-rust"
            ):
                return
            last_error = AssertionError(f"unexpected health payload: {payload!r}")
        except Exception as exc:
            last_error = exc
        time.sleep(0.05)
    raise AssertionError(f"voice-edge sidecar health check timed out: {last_error}")


def _assert_payload_has_full_stop_ack(payload):
    cancellation = None
    for event in payload["events"]:
        if event.get("cancellation") is not None:
            cancellation = event["cancellation"]
            break
    assert cancellation is not None, f"payload missing cancellation ack: {payload!r}"
    assert cancellation["drop_outbound_audio"] is True
    assert cancellation["cancel_gemma"] is True
    assert cancellation["clear_kokoro_buffers"] is True
    assert cancellation["stop_livekit_audio"] is True


def _assert_full_stop_ack(cancellation):
    assert cancellation.drop_outbound_audio is True
    assert cancellation.cancel_gemma is True
    assert cancellation.clear_kokoro_buffers is True
    assert cancellation.stop_livekit_audio is True


class FakeHttpResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeVoiceEdgeHttpClient:
    requests = []
    instances = []

    def __init__(self, timeout):
        self.timeout = timeout
        self.closed = False
        self.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def aclose(self):
        self.closed = True

    async def get(self, url):
        self.requests.append({"method": "GET", "url": url, "timeout": self.timeout})
        return FakeHttpResponse(
            {
                "status": "ok",
                "service": "voice-edge",
                "transport": "http",
                "request_contract": "voice_edge_request_v1",
                "default_vad_backend": "deterministic_energy",
                "effective_vad_model": "request_scoped_by_voice_edge_config",
                "target_vad_model": "silero-vad-rust",
                "supported_vad_backends": ["deterministic_energy", "silero_onnx"],
                "silero_onnx_runtime": "linked_with_bundled_model_and_file_override",
                "state_model": "stateless_request_response",
            }
        )

    async def post(self, url, json):
        self.requests.append(
            {"method": "POST", "url": url, "json": json, "timeout": self.timeout}
        )
        return FakeHttpResponse(_fake_voice_edge_response(json))


class FakeUnhealthyVoiceEdgeHttpClient(FakeVoiceEdgeHttpClient):
    async def get(self, url):
        self.requests.append({"method": "GET", "url": url, "timeout": self.timeout})
        return FakeHttpResponse(
            {
                "status": "degraded",
                "service": "voice-edge",
                "transport": "http",
            }
        )


class FakeWrongContractVoiceEdgeHttpClient(FakeVoiceEdgeHttpClient):
    async def get(self, url):
        self.requests.append({"method": "GET", "url": url, "timeout": self.timeout})
        return FakeHttpResponse(
            {
                "status": "ok",
                "service": "other-service",
                "transport": "http",
                "request_contract": "other_contract_v1",
                "state_model": "stateless_request_response",
                "supported_vad_backends": ["deterministic_energy", "silero_onnx"],
            }
        )


class FakeNonObjectHealthVoiceEdgeHttpClient(FakeVoiceEdgeHttpClient):
    async def get(self, url):
        self.requests.append({"method": "GET", "url": url, "timeout": self.timeout})
        return FakeHttpResponse(["ok"])


def _fake_voice_edge_response(payload):
    response_id = payload.get("response_id") or "unknown-response"
    reason = payload.get("reason") or "barge-in detected"
    last_frame = (payload.get("frames") or [{"sequence": None, "pcm_s16le": []}])[-1]
    ack = {
        "response_id": response_id,
        "reason": reason,
        "drop_outbound_audio": True,
        "cancel_gemma": True,
        "clear_kokoro_buffers": True,
        "stop_livekit_audio": True,
    }
    return {
        "request_id": payload.get("request_id"),
        "session_id": payload["session_id"],
        "events": [
            {
                "event_type": "voice_edge_cancellation_acknowledged",
                "sequence": last_frame.get("sequence"),
                "response_id": response_id,
                "cancellation": ack,
                "metadata": {
                    "request_kind": payload["kind"],
                    "last_frame_sample_count": str(
                        len(last_frame.get("pcm_s16le") or [])
                    ),
                },
            }
        ],
        "final_state": {
            "inbound_buffer_bytes": 0,
            "outbound_buffer_bytes": 0,
            "consecutive_speech_frames": 2,
            "agent_speaking": bool(payload.get("agent_speaking")),
            "active_response_id": response_id,
            "cancellation_acknowledged": True,
        },
    }


class AlwaysFailVoiceEdgeClient(RustVoiceEdgeHttpClient):
    def __init__(self):
        super().__init__(base_url="http://voice-edge.local:7071", timeout_seconds=1.0)

    async def _run(self, payload):
        raise RuntimeError("http sidecar unavailable")


class CloseFailVoiceEdgeClient(AlwaysFailVoiceEdgeClient):
    def __init__(self):
        super().__init__()
        self.close_attempted = False

    async def aclose(self):
        self.close_attempted = True
        raise RuntimeError("primary close failed")


class CloseTrackVoiceEdgeClient(RustVoiceEdgeClient):
    def __init__(self):
        super().__init__(binary_path="/tmp/missing-voice-edge")
        self.close_attempted = False

    async def aclose(self):
        self.close_attempted = True
