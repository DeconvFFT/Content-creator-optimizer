import asyncio
import statistics
import struct
import time
import wave
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from all_about_llms.voice_agent.edge import (
    VoiceEdgeClient,
    VoiceEdgeAnalysisResult,
    VoiceEdgeFrame,
)


@dataclass(frozen=True, slots=True)
class VoiceEdgeBenchmarkConfig:
    runs_per_scenario: int = 5
    samples_per_frame: int = 512
    speech_amplitude: int = 2600
    silence_amplitude: int = 0
    concurrent_streams: int = 4
    concurrent_iterations: int = 2
    speech_pcm_s16le: bytes | None = None
    speech_source: str = "synthetic_constant"
    max_speech_frames: int = 64
    frame_ms: int = 32
    target_single_request_p95_ms: float = 75.0
    target_concurrency_p95_ms: float = 120.0
    target_batch_wall_p95_ms: float = 180.0
    warmup_requests: int = 1


@dataclass(frozen=True, slots=True)
class VoiceEdgeSpeechFixture:
    source: str
    pcm_s16le: bytes


async def run_voice_edge_benchmark(
    client: VoiceEdgeClient,
    *,
    config: VoiceEdgeBenchmarkConfig | None = None,
) -> dict[str, Any]:
    config = config or VoiceEdgeBenchmarkConfig()
    speech_frames = _speech_frames(config)
    await _warm_up_voice_edge_client(client, config=config)
    scenarios = [
        _BenchmarkScenario(
            name="silence_false_positive",
            frames=_frames(
                [config.silence_amplitude, config.silence_amplitude],
                samples_per_frame=config.samples_per_frame,
                frame_ms=config.frame_ms,
            ),
            response_id=None,
            agent_speaking=False,
            expect_speech_started=False,
            expect_cancellation=False,
        ),
        _BenchmarkScenario(
            name="speech_start_detection",
            frames=speech_frames,
            response_id=None,
            agent_speaking=False,
            expect_speech_started=True,
            expect_cancellation=False,
        ),
        _BenchmarkScenario(
            name="barge_in_cancellation",
            frames=speech_frames,
            response_id="voice-response-benchmark",
            agent_speaking=True,
            expect_speech_started=True,
            expect_cancellation=True,
        ),
    ]
    scenario_results = []
    latencies_ms: list[float] = []
    false_positive_count = 0
    missed_speech_start_count = 0
    missed_cancellation_count = 0
    scenario_fallback_used_count = 0

    for scenario in scenarios:
        for index in range(config.runs_per_scenario):
            started = time.perf_counter()
            result = await client.analyze_frames(
                session_id=f"voice-edge-benchmark-{scenario.name}-{index}",
                response_id=scenario.response_id,
                agent_speaking=scenario.agent_speaking,
                frames=scenario.frames,
                request_id=f"voice-edge-benchmark-{scenario.name}-{index}",
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            latencies_ms.append(latency_ms)
            speech_started = _has_event(result, "voice_user_speech_started")
            cancellation = result.cancellation_ack is not None
            if speech_started and not scenario.expect_speech_started:
                false_positive_count += 1
            if scenario.expect_speech_started and not speech_started:
                missed_speech_start_count += 1
            if scenario.expect_cancellation and not cancellation:
                missed_cancellation_count += 1
            used_transport_fallback = _has_event(result, "voice_edge_transport_fallback")
            if used_transport_fallback:
                scenario_fallback_used_count += 1
            scenario_results.append(
                {
                    "scenario": scenario.name,
                    "iteration": index + 1,
                    "latency_ms": latency_ms,
                    "speech_started": speech_started,
                    "cancellation_acknowledged": cancellation,
                    "used_transport_fallback": used_transport_fallback,
                    "event_types": [event["event_type"] for event in result.events],
                }
            )

    latency_summary = _latency_summary(latencies_ms)
    concurrency_result = await _run_concurrency_probe(client, config=config)
    tuning = _voice_edge_tuning_recommendation(
        client,
        config=config,
        latency=latency_summary,
        concurrency=concurrency_result,
        fallback_used_count=(
            scenario_fallback_used_count
            + int(concurrency_result.get("fallback_used_count") or 0)
        ),
    )
    concurrency_missed_speech_start_count = int(
        concurrency_result.get("quality", {}).get("missed_speech_start_count", 0)
    )
    passed = (
        false_positive_count == 0
        and missed_speech_start_count == 0
        and missed_cancellation_count == 0
        and concurrency_missed_speech_start_count == 0
        and tuning["status"] == "ready"
    )
    return {
        "benchmark": "voice_edge_vad_and_barge_in_v1",
        "status": "passed" if passed else "needs_attention",
        "process_mode": client.process_mode,
        "runs_per_scenario": config.runs_per_scenario,
        "stimulus": {
            "speech_source": config.speech_source,
            "speech_frame_count": len(speech_frames),
            "samples_per_frame": config.samples_per_frame,
            "frame_ms": config.frame_ms,
            "max_speech_frames": config.max_speech_frames,
            "warmup_requests": config.warmup_requests,
        },
        "latency": latency_summary,
        "vad": {
            "backend": client.vad_backend,
            "model_path_configured": client.vad_model_path is not None,
            "session_pool_size": client.vad_session_pool_size,
            "stream_state_cache_size": client.vad_stream_state_cache_size,
        },
        "quality": {
            "false_positive_count": false_positive_count,
            "missed_speech_start_count": missed_speech_start_count,
            "missed_cancellation_count": missed_cancellation_count,
        },
        "concurrency": concurrency_result,
        "tuning": tuning,
        "scenarios": scenario_results,
    }


async def run_voice_edge_benchmark_corpus(
    client: VoiceEdgeClient,
    *,
    fixtures: list[VoiceEdgeSpeechFixture],
    config: VoiceEdgeBenchmarkConfig | None = None,
) -> dict[str, Any]:
    config = config or VoiceEdgeBenchmarkConfig()
    if not fixtures:
        result = await run_voice_edge_benchmark(client, config=config)
        return {
            "benchmark": "voice_edge_vad_corpus_v1",
            "status": result["status"],
            "fixture_count": 0,
            "process_mode": client.process_mode,
            "vad": result["vad"],
            "summary": _corpus_summary([result]),
            "results": [result],
        }

    results = []
    for fixture in fixtures:
        results.append(
            await run_voice_edge_benchmark(
                client,
                config=replace(
                    config,
                    speech_pcm_s16le=fixture.pcm_s16le,
                    speech_source=fixture.source,
                ),
            )
        )
    return {
        "benchmark": "voice_edge_vad_corpus_v1",
        "status": "passed"
        if all(result["status"] == "passed" for result in results)
        else "needs_attention",
        "fixture_count": len(fixtures),
        "process_mode": client.process_mode,
        "vad": results[0]["vad"] if results else {},
        "summary": _corpus_summary(results),
        "results": results,
    }


async def run_voice_edge_threshold_sweep(
    client: VoiceEdgeClient,
    *,
    thresholds: list[float],
    fixtures: list[VoiceEdgeSpeechFixture],
    config: VoiceEdgeBenchmarkConfig | None = None,
) -> dict[str, Any]:
    if not fixtures:
        raise ValueError("threshold sweep requires at least one real speech fixture")
    config = config or VoiceEdgeBenchmarkConfig()
    original_threshold = client.vad_probability_threshold
    results = []
    try:
        for threshold in thresholds:
            client.vad_probability_threshold = threshold
            result = await run_voice_edge_benchmark_corpus(
                client,
                fixtures=fixtures,
                config=config,
            )
            result["vad"]["probability_threshold"] = threshold
            results.append({"threshold": threshold, "result": result})
    finally:
        client.vad_probability_threshold = original_threshold

    passing = [
        item["threshold"]
        for item in results
        if item["result"]["status"] == "passed"
    ]
    return {
        "benchmark": "voice_edge_vad_threshold_sweep_v1",
        "status": "passed" if passing else "needs_attention",
        "thresholds": thresholds,
        "passing_thresholds": passing,
        "recommended_threshold": passing[0] if passing else None,
        "fixture_count": len(fixtures),
        "process_mode": client.process_mode,
        "results": results,
    }


@dataclass(frozen=True, slots=True)
class _BenchmarkScenario:
    name: str
    frames: list[VoiceEdgeFrame]
    response_id: str | None
    agent_speaking: bool
    expect_speech_started: bool
    expect_cancellation: bool


def _frames(
    amplitudes: list[int],
    *,
    samples_per_frame: int,
    frame_ms: int,
) -> list[VoiceEdgeFrame]:
    return [
        VoiceEdgeFrame(
            sequence=index,
            timestamp_ms=index * frame_ms,
            pcm_s16le=_pcm_frame(amplitude, samples_per_frame=samples_per_frame),
        )
        for index, amplitude in enumerate(amplitudes, start=1)
    ]


def _pcm_frame(amplitude: int, *, samples_per_frame: int) -> bytes:
    return struct.pack(f"<{samples_per_frame}h", *([amplitude] * samples_per_frame))


def _speech_frames(config: VoiceEdgeBenchmarkConfig) -> list[VoiceEdgeFrame]:
    if config.speech_pcm_s16le:
        return _frames_from_pcm_s16le(
            config.speech_pcm_s16le,
            samples_per_frame=config.samples_per_frame,
            max_frames=config.max_speech_frames,
            frame_ms=config.frame_ms,
        )
    return _frames(
        [config.speech_amplitude, config.speech_amplitude],
        samples_per_frame=config.samples_per_frame,
        frame_ms=config.frame_ms,
    )


def _frames_from_pcm_s16le(
    pcm_s16le: bytes,
    *,
    samples_per_frame: int,
    max_frames: int,
    frame_ms: int,
) -> list[VoiceEdgeFrame]:
    bytes_per_frame = max(1, samples_per_frame) * 2
    usable_length = len(pcm_s16le) - (len(pcm_s16le) % 2)
    frames = []
    for offset in range(0, usable_length, bytes_per_frame):
        chunk = pcm_s16le[offset : offset + bytes_per_frame]
        if len(chunk) < bytes_per_frame:
            break
        frames.append(
            VoiceEdgeFrame(
                sequence=len(frames) + 1,
                timestamp_ms=(len(frames) + 1) * frame_ms,
                pcm_s16le=chunk,
            )
        )
        if len(frames) >= max(1, max_frames):
            break
    if not frames:
        raise ValueError("speech PCM fixture is too short for one benchmark frame")
    return frames


def load_wav_pcm_s16le(
    path: str | Path,
    *,
    expected_sample_rate: int,
) -> bytes:
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        if sample_width != 2:
            raise ValueError(
                f"speech WAV must be 16-bit PCM; got sample_width={sample_width}"
            )
        if sample_rate != expected_sample_rate:
            raise ValueError(
                "speech WAV sample rate must match voice-edge sample rate; "
                f"got {sample_rate}, expected {expected_sample_rate}"
            )
        raw = wav_file.readframes(wav_file.getnframes())
    if channels == 1:
        return raw
    if channels < 1:
        raise ValueError(f"speech WAV must have at least one channel; got {channels}")
    return _downmix_pcm_s16le(raw, channels=channels)


def load_wav_speech_fixture(
    path: str | Path,
    *,
    expected_sample_rate: int,
) -> VoiceEdgeSpeechFixture:
    resolved = Path(path)
    return VoiceEdgeSpeechFixture(
        source=f"wav:{resolved}",
        pcm_s16le=load_wav_pcm_s16le(resolved, expected_sample_rate=expected_sample_rate),
    )


def _corpus_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "passed_count": sum(1 for result in results if result["status"] == "passed"),
        "needs_attention_count": sum(
            1 for result in results if result["status"] != "passed"
        ),
        "false_positive_count": sum(
            int(result["quality"]["false_positive_count"]) for result in results
        ),
        "missed_speech_start_count": sum(
            int(result["quality"]["missed_speech_start_count"]) for result in results
        ),
        "missed_cancellation_count": sum(
            int(result["quality"]["missed_cancellation_count"]) for result in results
        ),
        "concurrency_missed_speech_start_count": sum(
            int(result["concurrency"]["quality"]["missed_speech_start_count"])
            for result in results
        ),
        "needs_tuning_count": sum(
            1
            for result in results
            if result.get("tuning", {}).get("status") == "needs_tuning"
        ),
    }


def _downmix_pcm_s16le(raw: bytes, *, channels: int) -> bytes:
    sample_count = len(raw) // 2
    samples = struct.unpack(f"<{sample_count}h", raw[: sample_count * 2])
    mono_samples = []
    for offset in range(0, len(samples), channels):
        frame = samples[offset : offset + channels]
        if len(frame) == channels:
            mono_samples.append(round(sum(frame) / channels))
    return struct.pack(f"<{len(mono_samples)}h", *mono_samples)


def _has_event(result: VoiceEdgeAnalysisResult, event_type: str) -> bool:
    return any(event.get("event_type") == event_type for event in result.events)


async def _warm_up_voice_edge_client(
    client: VoiceEdgeClient,
    *,
    config: VoiceEdgeBenchmarkConfig,
) -> None:
    for index in range(max(0, config.warmup_requests)):
        await client.analyze_frames(
            session_id=f"voice-edge-benchmark-warmup-{index}",
            response_id=None,
            agent_speaking=False,
            frames=_frames(
                [config.silence_amplitude],
                samples_per_frame=config.samples_per_frame,
                frame_ms=config.frame_ms,
            ),
            request_id=f"voice-edge-benchmark-warmup-{index}",
        )


def _voice_edge_tuning_recommendation(
    client: VoiceEdgeClient,
    *,
    config: VoiceEdgeBenchmarkConfig,
    latency: dict[str, float],
    concurrency: dict[str, Any],
    fallback_used_count: int,
) -> dict[str, Any]:
    concurrency_latency = concurrency.get("latency", {})
    batch_wall_latency = concurrency.get("batch_wall_latency", {})
    streams = int(concurrency.get("streams") or config.concurrent_streams or 1)
    iterations = int(concurrency.get("iterations") or config.concurrent_iterations or 0)
    measured_serialized = _measured_serialized_by_client(
        client,
        fallback_used_count=fallback_used_count,
    )
    target_single = float(config.target_single_request_p95_ms)
    target_concurrency = float(config.target_concurrency_p95_ms)
    target_batch_wall = float(config.target_batch_wall_p95_ms)
    warnings: list[str] = []
    notes: list[str] = []
    recommendations: list[str] = []

    if _p95_above(latency, target_single):
        warnings.append("single_request_p95_above_target")
    if measured_serialized and streams > 1:
        notes.append("client_serializes_concurrent_requests")
        recommendations.append(
            "Use RUST_VOICE_EDGE_HTTP_URL with the supervised Rust HTTP sidecar "
            "for concurrent LiveKit sessions; persistent JSONL serializes requests."
        )
    else:
        if _p95_above(concurrency_latency, target_concurrency):
            warnings.append("concurrency_p95_above_target")
        if _p95_above(batch_wall_latency, target_batch_wall):
            warnings.append("batch_wall_p95_above_target")

    recommended_pool = client.vad_session_pool_size
    if streams > client.vad_session_pool_size:
        recommended_pool = min(16, streams)
    if warnings and not client.serializes_requests:
        recommended_pool = max(recommended_pool, min(16, streams))

    recommended_cache = max(
        client.vad_stream_state_cache_size,
        min(4096, streams * max(1, iterations)),
    )
    if recommended_pool > client.vad_session_pool_size:
        recommendations.append(
            "Increase RUST_VOICE_EDGE_VAD_SESSION_POOL_SIZE to at least "
            f"{recommended_pool} for {streams} concurrent stream(s)."
        )
    if recommended_cache > client.vad_stream_state_cache_size:
        recommendations.append(
            "Increase RUST_VOICE_EDGE_VAD_STREAM_STATE_CACHE_SIZE to at least "
            f"{recommended_cache} so recurrent VAD state is not evicted under load."
        )
    if warnings and not any("RUST_VOICE_EDGE" in item for item in recommendations):
        recommendations.append(
            "Reduce frame/model latency or move realtime voice traffic to the "
            "supervised Rust HTTP sidecar before provider-backed LiveKit load."
        )

    return {
        "status": "needs_tuning" if warnings else "ready",
        "target_single_request_p95_ms": target_single,
        "target_concurrency_p95_ms": target_concurrency,
        "target_batch_wall_p95_ms": target_batch_wall,
        "recommended_vad_session_pool_size": recommended_pool,
        "recommended_vad_stream_state_cache_size": recommended_cache,
        "measured_serialized_by_client": measured_serialized,
        "fallback_used_count": fallback_used_count,
        "warnings": warnings,
        "notes": notes,
        "recommendations": recommendations,
    }


def _measured_serialized_by_client(
    client: VoiceEdgeClient,
    *,
    fallback_used_count: int,
) -> bool:
    if (
        client.transport == "http_sidecar_with_persistent_jsonl_fallback"
        and fallback_used_count == 0
    ):
        return False
    return client.serializes_requests


def _p95_above(latency: dict[str, Any], target_ms: float) -> bool:
    count = int(latency.get("count") or 0)
    return count > 0 and float(latency.get("p95_ms") or 0.0) > target_ms


async def _run_concurrency_probe(
    client: VoiceEdgeClient,
    *,
    config: VoiceEdgeBenchmarkConfig,
) -> dict[str, Any]:
    concurrent_streams = max(1, config.concurrent_streams)
    concurrent_iterations = max(0, config.concurrent_iterations)
    if concurrent_streams <= 1 or concurrent_iterations == 0:
        return {
            "enabled": False,
            "streams": concurrent_streams,
            "iterations": concurrent_iterations,
            "request_count": 0,
            "latency": _latency_summary([]),
            "quality": {"missed_speech_start_count": 0},
            "serialized_by_client": _measured_serialized_by_client(
                client,
                fallback_used_count=0,
            ),
            "fallback_used_count": 0,
            "samples": [],
        }

    frames = _speech_frames(config)
    samples: list[dict[str, Any]] = []
    latencies_ms: list[float] = []
    batch_wall_ms: list[float] = []
    missed_speech_start_count = 0
    wall_started = time.perf_counter()

    for iteration in range(concurrent_iterations):
        batch_started = time.perf_counter()
        batch = await asyncio.gather(
            *[
                _time_concurrent_request(
                    client,
                    iteration=iteration,
                    stream_index=stream_index,
                    frames=frames,
                )
                for stream_index in range(concurrent_streams)
            ]
        )
        batch_wall_ms.append(round((time.perf_counter() - batch_started) * 1000, 3))
        for sample in batch:
            latencies_ms.append(float(sample["latency_ms"]))
            if not sample["speech_started"]:
                missed_speech_start_count += 1
            samples.append(sample)
    fallback_used_count = sum(1 for sample in samples if sample["used_transport_fallback"])

    return {
        "enabled": True,
        "streams": concurrent_streams,
        "iterations": concurrent_iterations,
        "request_count": len(samples),
        "wall_clock_ms": round((time.perf_counter() - wall_started) * 1000, 3),
        "batch_wall_latency": _latency_summary(batch_wall_ms),
        "latency": _latency_summary(latencies_ms),
        "quality": {"missed_speech_start_count": missed_speech_start_count},
        "serialized_by_client": _measured_serialized_by_client(
            client,
            fallback_used_count=fallback_used_count,
        ),
        "fallback_used_count": fallback_used_count,
        "transport": client.transport,
        "samples": samples,
    }


async def _time_concurrent_request(
    client: VoiceEdgeClient,
    *,
    iteration: int,
    stream_index: int,
    frames: list[VoiceEdgeFrame],
) -> dict[str, Any]:
    session_id = f"voice-edge-concurrency-{iteration}-{stream_index}"
    started = time.perf_counter()
    result = await client.analyze_frames(
        session_id=session_id,
        response_id=None,
        agent_speaking=False,
        frames=frames,
        request_id=f"voice-edge-concurrency-{iteration}-{stream_index}",
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    return {
        "iteration": iteration + 1,
        "stream_index": stream_index + 1,
        "session_id": session_id,
        "latency_ms": latency_ms,
        "speech_started": _has_event(result, "voice_user_speech_started"),
        "used_transport_fallback": _has_event(result, "voice_edge_transport_fallback"),
        "event_types": [event["event_type"] for event in result.events],
    }


def _latency_summary(latencies_ms: list[float]) -> dict[str, float]:
    if not latencies_ms:
        return {"count": 0, "mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    ordered = sorted(latencies_ms)
    p95_index = min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95)))
    return {
        "count": len(latencies_ms),
        "mean_ms": round(statistics.fmean(latencies_ms), 3),
        "p50_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[p95_index], 3),
        "max_ms": round(max(latencies_ms), 3),
    }
