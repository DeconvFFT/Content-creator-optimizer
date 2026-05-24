import asyncio
import base64
import json

import httpx
import pytest

from all_about_llms.providers.huggingface import (
    HuggingFaceGemmaProvider,
    _build_user_content,
    _extract_content,
)
from all_about_llms.providers.imagegen_boundary import ImagegenBoundaryProvider
from all_about_llms.providers.interfaces import (
    GemmaRequest,
    ProviderConfigurationError,
    RealtimeSessionRequest,
    SearchRequest,
)
from all_about_llms.providers.realtime import (
    CartesiaRealtimeTTSProvider,
    Gemma4RealtimeVoiceProvider,
)
from all_about_llms.providers.search import SerpApiSearchProvider, TavilySearchProvider
from all_about_llms.voice_agent.control_binding import (
    verify_livekit_control_binding_token,
)


def test_huggingface_extracts_openai_compatible_message_content():
    raw = {"choices": [{"message": {"content": "Gemma expert response"}}]}
    assert _extract_content(raw) == "Gemma expert response"


def test_huggingface_formats_gemma_audio_before_text_for_multimodal_requests():
    content = _build_user_content(
        "Transcribe this and answer naturally.",
        [
            {
                "type": "audio",
                "uri": "https://example.com/user-turn.wav",
                "audio_format": "pcm_s16le",
                "sample_rate": 16000,
            }
        ],
    )

    assert content == [
        {"type": "audio", "audio": "https://example.com/user-turn.wav"},
        {"type": "text", "text": "Transcribe this and answer naturally."},
    ]


def test_huggingface_prefers_inline_audio_over_artifact_uri_for_provider_call():
    content = _build_user_content(
        "Understand this captured LiveKit turn.",
        [
            {
                "type": "audio",
                "uri": "artifact://voice-audio/run/session/turn.pcm",
                "content_base64": base64.b64encode(b"raw-pcm").decode("ascii"),
                "audio_format": "pcm_s16le",
                "sample_rate": 16000,
            }
        ],
    )

    assert content == [
        {
            "type": "audio",
            "audio_base64": "cmF3LXBjbQ==",
            "audio_format": "pcm_s16le",
            "sample_rate": 16000,
        },
        {"type": "text", "text": "Understand this captured LiveKit turn."},
    ]


def test_huggingface_gemma_provider_maps_success_payload_without_network():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer hf-test-token"
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "google/gemma-4-E4B-it"
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["content"] == "Explain retrieval."
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "Gemma expert synthesis"}}
                ],
                "usage": {"total_tokens": 7},
            },
            request=request,
        )

    provider = HuggingFaceGemmaProvider(
        token="hf-test-token",
        default_endpoint_url="https://hf.test/v1/chat/completions",
        transport=httpx.MockTransport(handler),
    )

    response = asyncio.run(
        provider.complete(
            GemmaRequest(
                model_id="google/gemma-4-E4B-it",
                agent_id="context-engineering-agent",
                system_context="You are concise.",
                user_input="Explain retrieval.",
            )
        )
    )

    assert response.content == "Gemma expert synthesis"
    assert response.usage == {"total_tokens": 7}
    assert "hf-test-token" not in str(response.raw_response)


def test_huggingface_gemma_provider_wraps_http_status_failures():
    provider = HuggingFaceGemmaProvider(
        token="hf-test-token",
        default_endpoint_url="https://hf.test/v1/chat/completions",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(503, request=request)
        ),
    )

    with pytest.raises(ProviderConfigurationError, match="Gemma 4 request failed"):
        asyncio.run(provider.complete(_gemma_request()))


def test_huggingface_gemma_provider_wraps_network_failures_without_secret_leak():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    provider = HuggingFaceGemmaProvider(
        token="hf-test-token",
        default_endpoint_url="https://hf.test/v1/chat/completions",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ProviderConfigurationError, match="Gemma 4 request failed") as exc:
        asyncio.run(provider.complete(_gemma_request()))

    assert "hf-test-token" not in str(exc.value)


def test_huggingface_gemma_provider_blocks_invalid_json_payloads():
    provider = HuggingFaceGemmaProvider(
        token="hf-test-token",
        default_endpoint_url="https://hf.test/v1/chat/completions",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=b"not json",
                request=request,
            )
        ),
    )

    with pytest.raises(ProviderConfigurationError, match="invalid JSON"):
        asyncio.run(provider.complete(_gemma_request()))


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (["not", "an", "object"], "non-object JSON"),
        ({"choices": [{"message": {}}]}, "no usable content"),
        ({"choices": [None]}, "no usable content"),
        ({"choices": [{"message": "bad"}]}, "no usable content"),
    ],
)
def test_huggingface_gemma_provider_blocks_malformed_success_payloads(
    payload,
    match,
):
    provider = HuggingFaceGemmaProvider(
        token="hf-test-token",
        default_endpoint_url="https://hf.test/v1/chat/completions",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=payload,
                request=request,
            )
        ),
    )

    with pytest.raises(ProviderConfigurationError, match=match):
        asyncio.run(provider.complete(_gemma_request()))


def test_tavily_search_provider_maps_success_payload_without_network():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer tavily-key"
        assert request.url.path == "/search"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["query"] == "Gemma source-backed content"
        assert payload["max_results"] == 2
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Gemma provider docs",
                        "url": "https://huggingface.co/docs/gemma",
                        "content": "Gemma documentation snippet.",
                        "publisher": "Hugging Face",
                        "published_at": "2026-05-18T00:00:00Z",
                    }
                ]
            },
        )

    provider = TavilySearchProvider(
        api_key="tavily-key",
        base_url="https://api.tavily.test/search",
        transport=httpx.MockTransport(handler),
    )

    results = asyncio.run(
        provider.search(
            SearchRequest(
                query="Gemma source-backed content",
                max_results=2,
            )
        )
    )

    assert len(results) == 1
    assert results[0].title == "Gemma provider docs"
    assert results[0].publisher == "Hugging Face"


def test_tavily_search_provider_skips_malformed_result_items():
    provider = TavilySearchProvider(
        api_key="tavily-key",
        base_url="https://api.tavily.test/search",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "results": [
                        None,
                        {"title": "Missing URL", "content": "bad"},
                        {
                            "title": "Valid result",
                            "url": "https://example.com/valid",
                            "content": "usable source",
                        },
                    ]
                },
            )
        ),
    )

    results = asyncio.run(provider.search(SearchRequest(query="mixed payload")))

    assert len(results) == 1
    assert results[0].title == "Valid result"


def test_tavily_search_provider_blocks_when_no_result_items_are_valid():
    provider = TavilySearchProvider(
        api_key="tavily-key",
        base_url="https://api.tavily.test/search",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"results": [None, {"title": "Missing URL"}]},
            )
        ),
    )

    with pytest.raises(ProviderConfigurationError, match="no valid source"):
        asyncio.run(provider.search(SearchRequest(query="invalid payload")))


def test_tavily_search_provider_wraps_http_status_errors():
    provider = TavilySearchProvider(
        api_key="bad-key",
        base_url="https://api.tavily.test/search",
        transport=httpx.MockTransport(lambda request: httpx.Response(401)),
    )

    with pytest.raises(ProviderConfigurationError, match="Tavily search failed"):
        asyncio.run(provider.search(SearchRequest(query="bad auth")))


def test_tavily_search_provider_wraps_invalid_json():
    provider = TavilySearchProvider(
        api_key="tavily-key",
        base_url="https://api.tavily.test/search",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"not json")
        ),
    )

    with pytest.raises(ProviderConfigurationError, match="invalid JSON"):
        asyncio.run(provider.search(SearchRequest(query="bad json")))


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ([], "non-object JSON"),
        ({"results": None}, "invalid results JSON"),
    ],
)
def test_tavily_search_provider_wraps_unexpected_json_shapes(payload, match):
    provider = TavilySearchProvider(
        api_key="tavily-key",
        base_url="https://api.tavily.test/search",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload)
        ),
    )

    with pytest.raises(ProviderConfigurationError, match=match):
        asyncio.run(provider.search(SearchRequest(query="bad shape")))


def test_serpapi_search_provider_wraps_request_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    provider = SerpApiSearchProvider(
        api_key="serp-key",
        base_url="https://serpapi.test/search.json",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ProviderConfigurationError, match="SerpAPI search request"):
        asyncio.run(provider.search(SearchRequest(query="network down")))


def test_serpapi_search_provider_skips_malformed_result_items():
    provider = SerpApiSearchProvider(
        api_key="serp-key",
        base_url="https://serpapi.test/search.json",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "organic_results": [
                        None,
                        {"title": "Missing Link"},
                        {
                            "title": "Valid organic result",
                            "link": "https://example.com/organic",
                            "snippet": "usable organic source",
                        },
                    ]
                },
            )
        ),
    )

    results = asyncio.run(provider.search(SearchRequest(query="mixed payload")))

    assert len(results) == 1
    assert results[0].title == "Valid organic result"


def test_serpapi_search_provider_blocks_when_no_result_items_are_valid():
    provider = SerpApiSearchProvider(
        api_key="serp-key",
        base_url="https://serpapi.test/search.json",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"organic_results": [None, {"title": "Missing Link"}]},
            )
        ),
    )

    with pytest.raises(ProviderConfigurationError, match="no valid source"):
        asyncio.run(provider.search(SearchRequest(query="invalid payload")))


def test_serpapi_search_provider_blocks_all_invalid_non_dict_result_items():
    provider = SerpApiSearchProvider(
        api_key="serp-key",
        base_url="https://serpapi.test/search.json",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"organic_results": [None, "bad"]},
            )
        ),
    )

    with pytest.raises(ProviderConfigurationError, match="no valid source"):
        asyncio.run(provider.search(SearchRequest(query="invalid payload")))


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ([], "non-object JSON"),
        ({"organic_results": None}, "invalid organic results JSON"),
    ],
)
def test_serpapi_search_provider_wraps_unexpected_json_shapes(payload, match):
    provider = SerpApiSearchProvider(
        api_key="serp-key",
        base_url="https://serpapi.test/search.json",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload)
        ),
    )

    with pytest.raises(ProviderConfigurationError, match=match):
        asyncio.run(provider.search(SearchRequest(query="bad shape")))


def test_cartesia_realtime_tts_returns_websocket_descriptor_without_network():
    provider = CartesiaRealtimeTTSProvider(
        api_key="cartesia-key",
        model_id="sonic-3.5",
        voice_id="voice-123",
    )

    response = asyncio.run(
        provider.create_session(
            RealtimeSessionRequest(
                provider="cartesia",
                run_id="run-123",
                instructions="Speak clearly.",
            )
        )
    )

    assert response.provider == "cartesia"
    assert response.websocket_url.startswith("wss://api.cartesia.ai/tts/websocket")
    assert response.metadata["model_id"] == "sonic-3.5"
    assert response.metadata["voice_id"] == "voice-123"


def test_gemma4_realtime_provider_encodes_transport_pruning_and_barge_in_contract():
    provider = Gemma4RealtimeVoiceProvider(
        transport_framework="livekit",
        livekit_url="ws://127.0.0.1:7880",
        livekit_api_key=None,
        livekit_api_secret=None,
        livekit_token_ttl_seconds=3600,
        websocket_url=None,
        audio_input_model="google/gemma-4-E4B-it",
        reasoning_model="google/gemma-4-E4B-it",
        audio_output_model="hexgrad/Kokoro-82M",
        audio_format="pcm_s16le",
        sample_rate=16000,
        context_prune_after_turns=3,
        max_audio_seconds_per_turn=30,
        rust_vad_model="silero-vad-rust",
        rust_vad_backend="silero_onnx",
        rust_vad_fallback_allowed=True,
    )

    response = asyncio.run(
        provider.create_session(
            RealtimeSessionRequest(
                provider="gemma4_realtime",
                run_id="run-123",
                instructions="Talk naturally and stay interruptible.",
            )
        )
    )

    assert response.provider == "gemma4_realtime"
    assert response.websocket_url is None
    assert response.transport is not None
    assert response.transport["framework"] == "livekit"
    assert response.transport["room_name"] == "agent-studio-run-123"
    assert response.transport["agent_identity"] == "gemma4-kokoro-agent-run-123"
    assert response.transport["has_token"] is False
    assert response.transport["token_persisted"] is False
    assert response.metadata["transport_framework"] == "livekit"
    assert response.metadata["room_name"] == "agent-studio-run-123"
    assert response.metadata["raw_websocket_production_allowed"] is False
    assert response.metadata["audio_input_model"] == "google/gemma-4-E4B-it"
    assert response.metadata["reasoning_model"] == "google/gemma-4-E4B-it"
    assert response.metadata["audio_output_model"] == "hexgrad/Kokoro-82M"
    assert response.metadata["gemma_streaming"]["enabled"] is True
    assert response.metadata["gemma_streaming"]["protocol"] == (
        "sse_openai_chat_compatible"
    )
    assert response.metadata["context_pruning"]["prune_after_turns"] == 3
    assert (
        response.metadata["context_pruning"]["replacement"]
        == "text_transcript_plus_compact_turn_summary"
    )
    assert response.metadata["barge_in"]["rust_vad_model"] == "silero-vad-rust"
    assert response.metadata["barge_in"]["vad_backend_requested"] == "silero_onnx"
    assert response.metadata["barge_in"]["vad_backend_effective"] == (
        "silero_onnx_with_deterministic_fallback"
    )
    assert response.metadata["barge_in"]["vad_runtime"] == (
        "silero_onnx_bundled_or_configured_model"
    )
    assert "cancel_gemma_inference" in response.metadata["barge_in"][
        "on_user_speech_while_agent_speaking"
    ]
    assert "clear_kokoro_tts_buffer" in response.metadata["barge_in"][
        "on_user_speech_while_agent_speaking"
    ]
    assert response.metadata["rust_edge"]["current_runtime"] == (
        "persistent_jsonl_subprocess_or_http_sidecar"
    )
    assert (
        response.metadata["rust_edge"]["target_runtime"]
        == "streaming_session_state_plus_silero"
    )
    assert "stdin_stdout_jsonl" in response.metadata["rust_edge"]["current_ipc"]
    assert "http_json" in response.metadata["rust_edge"]["current_ipc"]
    assert "POST /v1/voice-edge" in response.metadata["rust_edge"][
        "current_http_routes"
    ]
    assert response.metadata["rust_edge"]["target_ipc"] == "streaming_http_or_grpc"
    assert response.metadata["rust_edge"]["vad_backend_requested"] == "silero_onnx"
    assert response.metadata["rust_edge"]["vad_model_effective"] == (
        "silero_onnx_bundled_or_configured_model"
    )
    assert response.metadata["rust_edge"]["vad_model_target"] == "silero-vad-rust"


def test_gemma4_realtime_provider_mints_livekit_join_token_without_persisting_it():
    provider = Gemma4RealtimeVoiceProvider(
        transport_framework="livekit",
        livekit_url="ws://127.0.0.1:7880",
        livekit_api_key="lk-api-key",
        livekit_api_secret="lk-secret",
        livekit_token_ttl_seconds=3600,
        websocket_url=None,
        audio_input_model="google/gemma-4-E4B-it",
        reasoning_model="google/gemma-4-E4B-it",
        audio_output_model="hexgrad/Kokoro-82M",
        audio_format="pcm_s16le",
        sample_rate=16000,
        context_prune_after_turns=3,
        max_audio_seconds_per_turn=30,
        rust_vad_model="silero-vad-rust",
    )

    response = asyncio.run(
        provider.create_session(
            RealtimeSessionRequest(
                provider="gemma4_realtime",
                run_id="run-token",
                voice="af_heart",
                instructions="Talk naturally and stay interruptible.",
                metadata={
                    "realtime_session_id": "11111111-1111-4111-8111-111111111111",
                    "room_name": "agent-studio-token-room",
                    "participant_identity": "creator-token",
                    "agent_participant_identity": "gemma4-kokoro-agent-token",
                },
            )
        )
    )

    token = response.transport["token"]
    assert token
    header, payload, signature = token.split(".")
    assert header
    assert signature
    decoded_payload = json.loads(_decode_base64url(payload))
    assert decoded_payload["iss"] == "lk-api-key"
    assert decoded_payload["sub"] == "creator-token"
    assert decoded_payload["video"]["room"] == "agent-studio-token-room"
    assert decoded_payload["video"]["roomJoin"] is True
    assert decoded_payload["video"]["canPublish"] is True
    assert decoded_payload["video"]["canSubscribe"] is True
    assert response.transport["has_token"] is True
    assert response.transport["token_persisted"] is False
    control_binding_token = response.transport["metadata"]["control_binding_token"]
    assert verify_livekit_control_binding_token(
        control_binding_token,
        "lk-secret",
        run_id="run-token",
        realtime_session_id="11111111-1111-4111-8111-111111111111",
        room_name="agent-studio-token-room",
        participant_identity="creator-token",
        agent_identity="gemma4-kokoro-agent-token",
    )
    assert response.expires_at_unix == decoded_payload["exp"]
    assert response.metadata["has_transport_token"] is True
    assert response.metadata["control_binding_token_issued"] is True
    assert "control_binding_token" not in response.metadata
    assert "lk-secret" not in str(response.metadata)


def _decode_base64url(payload: str) -> str:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(f"{payload}{padding}").decode("utf-8")


def _gemma_request() -> GemmaRequest:
    return GemmaRequest(
        model_id="google/gemma-4-E4B-it",
        agent_id="context-engineering-agent",
        system_context="You are concise.",
        user_input="Explain retrieval.",
    )


def test_imagegen_boundary_is_explicit_not_network_provider():
    provider = ImagegenBoundaryProvider()
    with pytest.raises(ProviderConfigurationError):
        asyncio.run(provider.generate("Create a reel visual", {}))
