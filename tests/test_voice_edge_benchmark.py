import argparse
import asyncio
import os
import struct
import wave

import pytest

from all_about_llms.config import (
    MAX_RUST_VOICE_EDGE_BENCHMARK_SPEECH_FRAMES,
    Settings,
)
from all_about_llms.cli import (
    _benchmark_speech_frame_limit,
    _positive_int,
    _probability_thresholds,
    _speech_wav_paths,
    _validate_threshold_sweep_inputs,
)
from all_about_llms.voice_agent.benchmark import (
    VoiceEdgeBenchmarkConfig,
    VoiceEdgeSpeechFixture,
    load_wav_pcm_s16le,
    run_voice_edge_benchmark,
    run_voice_edge_benchmark_corpus,
    run_voice_edge_threshold_sweep,
)
from all_about_llms.voice_agent.edge import (
    FallbackVoiceEdgeClient,
    PersistentRustVoiceEdgeClient,
    VoiceEdgeAnalysisResult,
    VoiceEdgeCancellationAck,
    VoiceEdgeClient,
)


def test_voice_edge_benchmark_reports_latency_and_quality(tmp_path):
    fake_binary = _write_fake_voice_edge(tmp_path)
    client = PersistentRustVoiceEdgeClient(binary_path=fake_binary, timeout_seconds=1.0)

    async def run():
        try:
            return await run_voice_edge_benchmark(client)
        finally:
            await client.aclose()

    result = asyncio.run(run())

    assert result["benchmark"] == "voice_edge_vad_and_barge_in_v1"
    assert result["status"] == "passed"
    assert result["process_mode"] == "persistent_jsonl"
    assert result["latency"]["count"] == 15
    assert result["vad"]["backend"] == "deterministic_energy"
    assert result["concurrency"]["enabled"] is True
    assert result["concurrency"]["streams"] == 4
    assert result["concurrency"]["iterations"] == 2
    assert result["concurrency"]["request_count"] == 8
    assert result["concurrency"]["serialized_by_client"] is True
    assert result["concurrency"]["quality"] == {"missed_speech_start_count": 0}
    assert result["quality"] == {
        "false_positive_count": 0,
        "missed_speech_start_count": 0,
        "missed_cancellation_count": 0,
    }
    assert {
        item["scenario"]
        for item in result["scenarios"]
        if item["cancellation_acknowledged"]
    } == {"barge_in_cancellation"}


def test_voice_edge_benchmark_reports_http_sidecar_mode():
    client = _FakeHttpVoiceEdgeClient()

    async def run():
        return await run_voice_edge_benchmark(
            client,
            config=VoiceEdgeBenchmarkConfig(
                runs_per_scenario=1,
                concurrent_streams=2,
                concurrent_iterations=1,
            ),
        )

    result = asyncio.run(run())

    assert result["status"] == "passed"
    assert result["process_mode"] == "http_sidecar"
    assert result["concurrency"]["serialized_by_client"] is False
    assert result["concurrency"]["request_count"] == 2
    assert result["tuning"]["status"] == "ready"
    assert result["tuning"]["recommended_vad_session_pool_size"] == 4


def test_voice_edge_benchmark_flags_latency_tuning_risk():
    client = _SlowHttpVoiceEdgeClient(
        delay_seconds=0.01,
        vad_session_pool_size=1,
        vad_stream_state_cache_size=1,
    )

    async def run():
        return await run_voice_edge_benchmark(
            client,
            config=VoiceEdgeBenchmarkConfig(
                runs_per_scenario=1,
                concurrent_streams=3,
                concurrent_iterations=2,
                target_single_request_p95_ms=1.0,
                target_concurrency_p95_ms=1.0,
                target_batch_wall_p95_ms=1.0,
            ),
        )

    result = asyncio.run(run())

    assert result["status"] == "needs_attention"
    assert result["tuning"]["status"] == "needs_tuning"
    assert result["tuning"]["recommended_vad_session_pool_size"] == 3
    assert result["tuning"]["recommended_vad_stream_state_cache_size"] == 6
    assert "single_request_p95_above_target" in result["tuning"]["warnings"]
    assert "concurrency_p95_above_target" in result["tuning"]["warnings"]
    assert "batch_wall_p95_above_target" in result["tuning"]["warnings"]
    assert any(
        "Increase RUST_VOICE_EDGE_VAD_SESSION_POOL_SIZE" in item
        for item in result["tuning"]["recommendations"]
    )


def test_voice_edge_benchmark_checks_http_primary_latency_with_jsonl_fallback():
    client = FallbackVoiceEdgeClient(
        primary=_SlowHttpVoiceEdgeClient(delay_seconds=0.01),
        fallback=_SerialFallbackVoiceEdgeClient(),
    )

    async def run():
        return await run_voice_edge_benchmark(
            client,
            config=VoiceEdgeBenchmarkConfig(
                runs_per_scenario=1,
                concurrent_streams=3,
                concurrent_iterations=2,
                target_single_request_p95_ms=1000.0,
                target_concurrency_p95_ms=1.0,
                target_batch_wall_p95_ms=1.0,
            ),
        )

    result = asyncio.run(run())

    assert result["status"] == "needs_attention"
    assert result["concurrency"]["serialized_by_client"] is False
    assert result["concurrency"]["fallback_used_count"] == 0
    assert result["tuning"]["fallback_used_count"] == 0
    assert result["tuning"]["measured_serialized_by_client"] is False
    assert "client_serializes_concurrent_requests" not in result["tuning"]["notes"]
    assert "concurrency_p95_above_target" in result["tuning"]["warnings"]
    assert "batch_wall_p95_above_target" in result["tuning"]["warnings"]


def test_voice_edge_benchmark_uses_wav_speech_fixture(tmp_path):
    wav_path = tmp_path / "speech.wav"
    _write_wav_fixture(wav_path, samples=[2200] * 1024)
    speech_pcm = load_wav_pcm_s16le(wav_path, expected_sample_rate=16_000)
    client = _FakeHttpVoiceEdgeClient()

    async def run():
        return await run_voice_edge_benchmark(
            client,
            config=VoiceEdgeBenchmarkConfig(
                runs_per_scenario=1,
                samples_per_frame=512,
                concurrent_streams=2,
                concurrent_iterations=1,
                speech_pcm_s16le=speech_pcm,
                speech_source=f"wav:{wav_path}",
            ),
        )

    result = asyncio.run(run())

    assert result["status"] == "passed"
    assert result["stimulus"]["speech_source"] == f"wav:{wav_path}"
    assert result["stimulus"]["speech_frame_count"] == 2
    assert result["concurrency"]["quality"] == {"missed_speech_start_count": 0}


def test_voice_edge_benchmark_corpus_summarizes_multiple_fixtures(tmp_path):
    wav_a = tmp_path / "speech-a.wav"
    wav_b = tmp_path / "speech-b.wav"
    _write_wav_fixture(wav_a, samples=[2200] * 1024)
    _write_wav_fixture(wav_b, samples=[2400] * 1024)
    fixtures = [
        VoiceEdgeSpeechFixture(
            source=f"wav:{wav_a}",
            pcm_s16le=load_wav_pcm_s16le(wav_a, expected_sample_rate=16_000),
        ),
        VoiceEdgeSpeechFixture(
            source=f"wav:{wav_b}",
            pcm_s16le=load_wav_pcm_s16le(wav_b, expected_sample_rate=16_000),
        ),
    ]
    client = _FakeHttpVoiceEdgeClient()

    async def run():
        return await run_voice_edge_benchmark_corpus(
            client,
            fixtures=fixtures,
            config=VoiceEdgeBenchmarkConfig(
                runs_per_scenario=1,
                samples_per_frame=512,
                concurrent_streams=2,
                concurrent_iterations=1,
            ),
        )

    result = asyncio.run(run())

    assert result["benchmark"] == "voice_edge_vad_corpus_v1"
    assert result["status"] == "passed"
    assert result["fixture_count"] == 2
    assert result["summary"]["passed_count"] == 2
    assert result["summary"]["missed_speech_start_count"] == 0


def test_voice_edge_threshold_sweep_reports_passing_thresholds(tmp_path):
    wav_path = tmp_path / "speech.wav"
    _write_wav_fixture(wav_path, samples=[2200] * 1024)
    fixture = VoiceEdgeSpeechFixture(
        source=f"wav:{wav_path}",
        pcm_s16le=load_wav_pcm_s16le(wav_path, expected_sample_rate=16_000),
    )
    client = _FakeHttpVoiceEdgeClient()

    async def run():
        return await run_voice_edge_threshold_sweep(
            client,
            thresholds=[0.01, 0.5],
            fixtures=[fixture],
            config=VoiceEdgeBenchmarkConfig(
                runs_per_scenario=1,
                samples_per_frame=512,
                concurrent_streams=2,
                concurrent_iterations=1,
            ),
        )

    result = asyncio.run(run())

    assert result["benchmark"] == "voice_edge_vad_threshold_sweep_v1"
    assert result["status"] == "passed"
    assert result["passing_thresholds"] == [0.01, 0.5]
    assert result["recommended_threshold"] == 0.01
    assert client.vad_probability_threshold == 0.5


def test_voice_edge_threshold_sweep_requires_real_fixtures():
    client = _FakeHttpVoiceEdgeClient()

    async def run():
        return await run_voice_edge_threshold_sweep(
            client,
            thresholds=[0.1],
            fixtures=[],
            config=VoiceEdgeBenchmarkConfig(runs_per_scenario=1),
        )

    with pytest.raises(ValueError, match="requires at least one real speech fixture"):
        asyncio.run(run())


def test_voice_edge_benchmark_cli_rejects_degenerate_counts():
    assert _positive_int("1") == 1
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_int("0")


def test_voice_edge_benchmark_cli_rejects_bad_threshold_sweep_values():
    assert _probability_thresholds("0.01, 0.5") == [0.01, 0.5]
    with pytest.raises(argparse.ArgumentTypeError, match="empty"):
        _probability_thresholds("0.1,")
    with pytest.raises(argparse.ArgumentTypeError, match="numbers"):
        _probability_thresholds("0.1,not-a-number")
    with pytest.raises(argparse.ArgumentTypeError, match="between 0 and 1"):
        _probability_thresholds("1.5")


def test_voice_edge_benchmark_cli_loads_nested_case_insensitive_wav_dir(tmp_path):
    nested_dir = tmp_path / "fixtures" / "nested"
    nested_dir.mkdir(parents=True)
    wav_path = nested_dir / "SPEECH.WAV"
    _write_wav_fixture(wav_path, samples=[2200] * 1024)

    paths = _speech_wav_paths(
        argparse.Namespace(speech_wav=None, speech_wav_dir=[str(tmp_path / "fixtures")])
    )

    assert paths == [wav_path]


def test_voice_edge_benchmark_cli_validates_explicit_wav_paths(tmp_path):
    wav_path = tmp_path / "speech.WAV"
    _write_wav_fixture(wav_path, samples=[2200] * 1024)

    paths = _speech_wav_paths(
        argparse.Namespace(speech_wav=[str(wav_path)], speech_wav_dir=None)
    )

    assert paths == [wav_path]

    with pytest.raises(argparse.ArgumentTypeError, match="does not exist"):
        _speech_wav_paths(
            argparse.Namespace(
                speech_wav=[str(tmp_path / "missing.wav")],
                speech_wav_dir=None,
            )
        )

    non_wav = tmp_path / "speech.txt"
    non_wav.write_text("not a wav")
    with pytest.raises(argparse.ArgumentTypeError, match="must end in .wav"):
        _speech_wav_paths(
            argparse.Namespace(speech_wav=[str(non_wav)], speech_wav_dir=None)
        )


def test_voice_edge_benchmark_cli_rejects_bad_wav_dir(tmp_path):
    missing_dir = tmp_path / "missing"
    with pytest.raises(argparse.ArgumentTypeError, match="does not exist"):
        _speech_wav_paths(
            argparse.Namespace(speech_wav=None, speech_wav_dir=[str(missing_dir)])
        )

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(argparse.ArgumentTypeError, match="contains no WAV"):
        _speech_wav_paths(
            argparse.Namespace(speech_wav=None, speech_wav_dir=[str(empty_dir)])
        )


def test_voice_edge_benchmark_cli_caps_frame_limit():
    assert _benchmark_speech_frame_limit("4096") == 4096
    too_large = str(MAX_RUST_VOICE_EDGE_BENCHMARK_SPEECH_FRAMES + 1)
    with pytest.raises(argparse.ArgumentTypeError, match="must be <="):
        _benchmark_speech_frame_limit(too_large)


def test_voice_edge_benchmark_cli_requires_fixtures_for_threshold_sweep():
    args = argparse.Namespace(vad_probability_threshold_sweep=[0.1, 0.5])
    with pytest.raises(argparse.ArgumentTypeError, match="requires --speech-wav"):
        _validate_threshold_sweep_inputs(args, [])

    _validate_threshold_sweep_inputs(args, [object()])


def test_voice_edge_benchmark_settings_reject_bad_frame_limit():
    with pytest.raises(ValueError, match="max_speech_frames"):
        Settings(rust_voice_edge_benchmark_max_speech_frames=0)
    with pytest.raises(ValueError, match="must be <="):
        Settings(
            rust_voice_edge_benchmark_max_speech_frames=(
                MAX_RUST_VOICE_EDGE_BENCHMARK_SPEECH_FRAMES + 1
            )
        )


def _write_wav_fixture(path, *, samples):
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16_000)
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))


class _FakeHttpVoiceEdgeClient(VoiceEdgeClient):
    transport = "http_sidecar"

    async def _run(self, payload):
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


class _SlowHttpVoiceEdgeClient(_FakeHttpVoiceEdgeClient):
    def __init__(self, *, delay_seconds: float, **kwargs):
        super().__init__(**kwargs)
        self.delay_seconds = delay_seconds

    async def _run(self, payload):
        await asyncio.sleep(self.delay_seconds)
        return await super()._run(payload)


class _SerialFallbackVoiceEdgeClient(_FakeHttpVoiceEdgeClient):
    transport = "persistent_jsonl"

    @property
    def serializes_requests(self) -> bool:
        return True


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
