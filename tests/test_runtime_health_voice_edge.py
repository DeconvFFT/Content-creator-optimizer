import asyncio
import json
import os

from all_about_llms.config import Settings
from all_about_llms.contracts import (
    ArtifactType,
    RunEvent,
    RunState,
    RuntimeHealthLedgerRequest,
    RuntimeHealthStatus,
)
from all_about_llms.orchestration import runtime_health as runtime_health_module
from all_about_llms.orchestration.runtime_health import RuntimeHealthLedgerWorkflow
from all_about_llms.voice_agent.edge import (
    VoiceEdgeAnalysisResult,
    VoiceEdgeCancellationAck,
    VoiceEdgeClient,
)


def test_runtime_health_records_voice_edge_benchmark_evidence(tmp_path):
    fake_binary = _write_fake_voice_edge(tmp_path)
    store = FakeRuntimeHealthStore()

    result = asyncio.run(
        RuntimeHealthLedgerWorkflow(
            store,
            project_root=tmp_path,
            settings=Settings(rust_voice_edge_binary_path=fake_binary),
        ).build(
            store.run.run_id,
            RuntimeHealthLedgerRequest(
                record_artifact=True,
                include_static_checks=False,
                include_run_evidence=True,
                include_voice_edge_benchmark=True,
            ),
        )
    )

    check = next(
        item
        for item in result.checks
        if item.check_id == "voice-edge-local-benchmark"
    )
    assert check.status == RuntimeHealthStatus.READY
    assert any("Benchmark status: passed" in item for item in check.evidence)
    assert any("Process mode: persistent_jsonl" in item for item in check.evidence)
    assert any("frame_ms=32" in item for item in check.evidence)
    assert any("max_speech_frames=64" in item for item in check.evidence)
    assert any("false_positive=0" in item for item in check.evidence)
    assert any("missed_speech_start=0" in item for item in check.evidence)
    assert any("missed_cancellation=0" in item for item in check.evidence)
    assert store.artifacts[-1].artifact_type == ArtifactType.RUNTIME_HEALTH_LEDGER
    assert store.artifacts[-1].provenance["include_voice_edge_benchmark"] is True
    assert "voice_edge_benchmark_passed" in [
        event.event_type for event in store.events
    ]
    assert store.events[-1].event_type == "runtime_health_ledger_built"


def test_runtime_health_voice_edge_benchmark_falls_back_to_jsonl(
    tmp_path,
    monkeypatch,
):
    fake_binary = _write_fake_voice_edge(tmp_path)
    store = FakeRuntimeHealthStore()
    monkeypatch.setattr(
        runtime_health_module,
        "RustVoiceEdgeHttpClient",
        AlwaysFailRuntimeHealthHttpClient,
    )

    result = asyncio.run(
        RuntimeHealthLedgerWorkflow(
            store,
            project_root=tmp_path,
            settings=Settings(
                rust_voice_edge_binary_path=fake_binary,
                rust_voice_edge_http_url="http://voice-edge.local:7071",
            ),
        ).build(
            store.run.run_id,
            RuntimeHealthLedgerRequest(
                record_artifact=True,
                include_static_checks=False,
                include_run_evidence=True,
                include_voice_edge_benchmark=True,
            ),
        )
    )

    check = next(
        item
        for item in result.checks
        if item.check_id == "voice-edge-local-benchmark"
    )
    assert check.status == RuntimeHealthStatus.READY
    assert any(
        "Process mode: http_sidecar_with_persistent_jsonl_fallback" in item
        for item in check.evidence
    )
    assert any("serialized_by_client=True" in item for item in check.evidence)


def test_runtime_health_checks_http_primary_concurrency_with_jsonl_fallback(
    tmp_path,
    monkeypatch,
):
    fake_binary = _write_fake_voice_edge(tmp_path)
    store = FakeRuntimeHealthStore()
    monkeypatch.setattr(
        runtime_health_module,
        "RustVoiceEdgeHttpClient",
        SlowRuntimeHealthHttpClient,
    )

    result = asyncio.run(
        RuntimeHealthLedgerWorkflow(
            store,
            project_root=tmp_path,
            settings=Settings(
                rust_voice_edge_binary_path=fake_binary,
                rust_voice_edge_http_url="http://voice-edge.local:7071",
                rust_voice_edge_vad_session_pool_size=1,
            ),
        ).build(
            store.run.run_id,
            RuntimeHealthLedgerRequest(
                record_artifact=True,
                include_static_checks=False,
                include_run_evidence=True,
                include_voice_edge_benchmark=True,
            ),
        )
    )

    check = next(
        item
        for item in result.checks
        if item.check_id == "voice-edge-local-benchmark"
    )
    assert check.status == RuntimeHealthStatus.DEGRADED
    assert any("serialized_by_client=False" in item for item in check.evidence)
    assert any("fallback_used=0" in item for item in check.evidence)
    assert any("measured_serialized=False" in item for item in check.evidence)
    assert any("concurrency_p95_above_target" in item for item in check.evidence)
    assert "Increase RUST_VOICE_EDGE_VAD_SESSION_POOL_SIZE" in check.recommended_action


def test_runtime_health_records_voice_edge_tuning_recommendations(
    tmp_path,
    monkeypatch,
):
    fake_binary = _write_fake_voice_edge(tmp_path)
    store = FakeRuntimeHealthStore()

    async def fake_benchmark(_client, *, config):
        return {
            "benchmark": "voice_edge_vad_and_barge_in_v1",
            "status": "needs_attention",
            "process_mode": "http_sidecar",
            "stimulus": {
                "speech_source": "synthetic_constant",
                "speech_frame_count": 2,
                "samples_per_frame": 512,
                "frame_ms": 32,
                "max_speech_frames": 64,
            },
            "latency": {
                "count": 3,
                "mean_ms": 90.0,
                "p50_ms": 80.0,
                "p95_ms": 140.0,
                "max_ms": 140.0,
            },
            "quality": {
                "false_positive_count": 0,
                "missed_speech_start_count": 0,
                "missed_cancellation_count": 0,
            },
            "concurrency": {
                "enabled": True,
                "streams": 4,
                "iterations": 2,
                "request_count": 8,
                "serialized_by_client": False,
                "latency": {
                    "count": 8,
                    "mean_ms": 110.0,
                    "p50_ms": 100.0,
                    "p95_ms": 180.0,
                    "max_ms": 190.0,
                },
                "quality": {"missed_speech_start_count": 0},
            },
            "tuning": {
                "status": "needs_tuning",
                "target_single_request_p95_ms": 75.0,
                "target_concurrency_p95_ms": 120.0,
                "target_batch_wall_p95_ms": 150.0,
                "recommended_vad_session_pool_size": 4,
                "recommended_vad_stream_state_cache_size": 8,
                "warnings": ["single_request_p95_above_target"],
                "recommendations": [
                    "Increase RUST_VOICE_EDGE_VAD_SESSION_POOL_SIZE to at least 4."
                ],
            },
        }

    monkeypatch.setattr(
        runtime_health_module,
        "run_voice_edge_benchmark",
        fake_benchmark,
    )

    result = asyncio.run(
        RuntimeHealthLedgerWorkflow(
            store,
            project_root=tmp_path,
            settings=Settings(rust_voice_edge_binary_path=fake_binary),
        ).build(
            store.run.run_id,
            RuntimeHealthLedgerRequest(
                record_artifact=True,
                include_static_checks=False,
                include_run_evidence=True,
                include_voice_edge_benchmark=True,
            ),
        )
    )

    check = next(
        item
        for item in result.checks
        if item.check_id == "voice-edge-local-benchmark"
    )
    assert check.status == RuntimeHealthStatus.DEGRADED
    assert any("Tuning status: needs_tuning" in item for item in check.evidence)
    assert any("recommended_pool=4" in item for item in check.evidence)
    assert "Increase RUST_VOICE_EDGE_VAD_SESSION_POOL_SIZE" in check.recommended_action


def test_runtime_health_voice_edge_non_executable_path_is_degraded(tmp_path):
    non_executable = tmp_path / "voice-edge"
    non_executable.write_text("#!/bin/sh\n", encoding="utf-8")
    store = FakeRuntimeHealthStore()

    result = asyncio.run(
        RuntimeHealthLedgerWorkflow(
            store,
            project_root=tmp_path,
            settings=Settings(rust_voice_edge_binary_path=non_executable),
        ).build(
            store.run.run_id,
            RuntimeHealthLedgerRequest(
                record_artifact=True,
                include_static_checks=False,
                include_run_evidence=True,
                include_voice_edge_benchmark=True,
            ),
        )
    )

    check = next(
        item
        for item in result.checks
        if item.check_id == "voice-edge-local-benchmark"
    )
    assert check.status == RuntimeHealthStatus.DEGRADED
    assert any("missing or not executable" in item for item in check.evidence)


class FakeRuntimeHealthStore:
    def __init__(self):
        self.run = RunState(goal="Prove realtime voice edge health")
        self.events: list[RunEvent] = []
        self.artifacts = []
        self.checkpoints = []

    async def get_run(self, run_id):
        return self.run if run_id == self.run.run_id else None

    async def list_events(self, run_id, limit=250):
        return self.events[:limit]

    async def list_artifacts(self, run_id):
        return self.artifacts

    async def list_run_checkpoints(self, run_id, limit=50):
        return self.checkpoints[:limit]

    async def record_artifact(self, artifact):
        self.artifacts.append(artifact)
        self.run.artifact_ids.append(artifact.artifact_id)
        return artifact

    async def append_event(self, event):
        event.event_id = len(self.events) + 1
        self.events.append(event)
        return event


class AlwaysFailRuntimeHealthHttpClient(VoiceEdgeClient):
    transport = "http_sidecar"

    def __init__(self, *, base_url, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url

    async def _run(self, payload):
        raise RuntimeError("http sidecar unavailable")


class SlowRuntimeHealthHttpClient(VoiceEdgeClient):
    transport = "http_sidecar"

    def __init__(self, *, base_url, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url

    async def _run(self, payload):
        await asyncio.sleep(0.13)
        frames = payload.get("frames") or []
        response_id = payload.get("response_id")
        events = []
        speech_frames = 0
        for frame in frames:
            speech = any(
                abs(int(sample)) > 1000 for sample in frame.get("pcm_s16le", [])
            )
            speech_frames = speech_frames + 1 if speech else 0
            events.append(
                {
                    "event_type": "voice_vad_frame_analyzed",
                    "sequence": frame.get("sequence"),
                    "response_id": response_id,
                    "is_speech": speech,
                    "rms": 0.1 if speech else 0.0,
                    "speech_probability": 0.9 if speech else 0.0,
                    "metadata": {},
                }
            )
        cancellation = None
        if speech_frames >= 2:
            events.append(
                {
                    "event_type": "voice_user_speech_started",
                    "sequence": frames[-1].get("sequence"),
                    "response_id": response_id,
                    "metadata": {},
                }
            )
            if payload.get("agent_speaking"):
                cancellation = VoiceEdgeCancellationAck(
                    response_id=response_id or "unknown-response",
                    reason="barge-in detected",
                    drop_outbound_audio=True,
                    cancel_gemma=True,
                    clear_kokoro_buffers=True,
                    stop_livekit_audio=True,
                )
                events.append(
                    {
                        "event_type": "voice_edge_cancellation_acknowledged",
                        "sequence": frames[-1].get("sequence"),
                        "response_id": response_id,
                        "cancellation": {
                            "response_id": cancellation.response_id,
                            "reason": cancellation.reason,
                            "drop_outbound_audio": cancellation.drop_outbound_audio,
                            "cancel_gemma": cancellation.cancel_gemma,
                            "clear_kokoro_buffers": cancellation.clear_kokoro_buffers,
                            "stop_livekit_audio": cancellation.stop_livekit_audio,
                        },
                        "metadata": {},
                    }
                )
        return VoiceEdgeAnalysisResult(
            request_id=payload.get("request_id"),
            session_id=payload["session_id"],
            events=events,
            final_state={
                "consecutive_speech_frames": speech_frames,
                "cancellation_acknowledged": cancellation is not None,
            },
            cancellation_ack=cancellation,
        )


def _write_fake_voice_edge(tmp_path):
    fake_binary = tmp_path / "voice-edge"
    fake_binary.write_text(
        """#!/usr/bin/env python3
import json
import sys

def is_speech(frame):
    return any(abs(int(sample)) > 1000 for sample in frame.get("pcm_s16le", []))

def handle(payload):
    frames = payload.get("frames") or []
    response_id = payload.get("response_id")
    events = []
    speech_frames = 0
    for frame in frames:
        speech = is_speech(frame)
        if speech:
            speech_frames += 1
        else:
            speech_frames = 0
        events.append({
            "event_type": "voice_vad_frame_analyzed",
            "sequence": frame.get("sequence"),
            "response_id": response_id,
            "is_speech": speech,
            "rms": 0.1 if speech else 0.0,
            "speech_probability": 0.9 if speech else 0.0,
            "metadata": {},
        })
    cancellation = None
    if speech_frames >= 2:
        events.append({
            "event_type": "voice_user_speech_started",
            "sequence": frames[-1].get("sequence"),
            "response_id": response_id,
            "metadata": {},
        })
        if payload.get("agent_speaking"):
            cancellation = {
                "response_id": response_id or "unknown-response",
                "reason": "barge-in detected",
                "drop_outbound_audio": True,
                "cancel_gemma": True,
                "clear_kokoro_buffers": True,
                "stop_livekit_audio": True,
            }
            events.append({
                "event_type": "voice_edge_cancellation_acknowledged",
                "sequence": frames[-1].get("sequence"),
                "response_id": response_id,
                "cancellation": cancellation,
                "metadata": {},
            })
    return {
        "request_id": payload.get("request_id"),
        "session_id": payload["session_id"],
        "events": events,
        "final_state": {
            "inbound_buffer_bytes": 0,
            "outbound_buffer_bytes": 0,
            "consecutive_speech_frames": speech_frames,
            "agent_speaking": bool(payload.get("agent_speaking")),
            "active_response_id": response_id,
            "cancellation_acknowledged": cancellation is not None,
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
