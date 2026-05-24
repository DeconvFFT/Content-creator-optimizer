pub mod cli;
pub mod contracts;
pub mod http;
pub mod service;
pub mod vad;

pub use contracts::{
    AudioFrame, CancellationAck, VadBackend, VoiceEdgeConfig, VoiceEdgeEvent, VoiceEdgeRequest,
    VoiceEdgeResponse, VoiceEdgeStateSnapshot,
};
pub use service::{handle_request, VoiceEdgeRuntime};
pub use vad::{analyze_pcm_s16le, analyze_voice_activity, VadAnalysis, VadDecision};
