from all_about_llms.voice_agent.engine import (
    GemmaKokoroLiveKitAgentEngine,
    VoiceAgentCancellationToken,
)
from all_about_llms.voice_agent.edge import (
    FallbackVoiceEdgeClient,
    PersistentRustVoiceEdgeClient,
    RustVoiceEdgeHttpClient,
    RustVoiceEdgeClient,
    VoiceEdgeAnalysisResult,
    VoiceEdgeCancellationAck,
    VoiceEdgeClient,
    VoiceEdgeFrame,
)
from all_about_llms.voice_agent.models import (
    AssistantAudioChunk,
    RealtimeVoiceAgentConfig,
    RealtimeVoiceAgentEvent,
    RealtimeVoiceAgentResult,
    RealtimeVoiceTurnInput,
    VoiceConversationTurn,
)

__all__ = [
    "AssistantAudioChunk",
    "FallbackVoiceEdgeClient",
    "GemmaKokoroLiveKitAgentEngine",
    "PersistentRustVoiceEdgeClient",
    "RealtimeVoiceAgentConfig",
    "RealtimeVoiceAgentEvent",
    "RealtimeVoiceAgentResult",
    "RealtimeVoiceTurnInput",
    "RustVoiceEdgeHttpClient",
    "RustVoiceEdgeClient",
    "VoiceAgentCancellationToken",
    "VoiceEdgeAnalysisResult",
    "VoiceEdgeCancellationAck",
    "VoiceEdgeClient",
    "VoiceEdgeFrame",
    "VoiceConversationTurn",
    "build_livekit_voice_agent_server",
    "run_livekit_voice_agent_server",
]


def __getattr__(name: str):
    if name in {
        "build_livekit_voice_agent_server",
        "run_livekit_voice_agent_server",
    }:
        from all_about_llms.voice_agent.livekit_app import (
            build_livekit_voice_agent_server,
            run_livekit_voice_agent_server,
        )

        return {
            "build_livekit_voice_agent_server": build_livekit_voice_agent_server,
            "run_livekit_voice_agent_server": run_livekit_voice_agent_server,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
