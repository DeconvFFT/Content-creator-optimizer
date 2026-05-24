use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case", tag = "kind")]
pub enum VoiceEdgeRequest {
    Analyze(AnalyzeVoiceRequest),
    Cancel(CancelVoiceRequest),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AnalyzeVoiceRequest {
    #[serde(default)]
    pub request_id: Option<String>,
    pub session_id: String,
    #[serde(default)]
    pub response_id: Option<String>,
    #[serde(default)]
    pub agent_speaking: bool,
    #[serde(default)]
    pub config: VoiceEdgeConfig,
    #[serde(default)]
    pub frames: Vec<AudioFrame>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CancelVoiceRequest {
    #[serde(default)]
    pub request_id: Option<String>,
    pub session_id: String,
    pub response_id: String,
    #[serde(default = "default_cancel_reason")]
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AudioFrame {
    pub sequence: u64,
    #[serde(default)]
    pub timestamp_ms: Option<u64>,
    #[serde(default)]
    pub pcm_s16le: Vec<i16>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum VadBackend {
    DeterministicEnergy,
    SileroOnnx,
}

impl Default for VadBackend {
    fn default() -> Self {
        Self::DeterministicEnergy
    }
}

impl VadBackend {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::DeterministicEnergy => "deterministic_energy",
            Self::SileroOnnx => "silero_onnx",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VoiceEdgeConfig {
    #[serde(default = "default_sample_rate")]
    pub sample_rate: u32,
    #[serde(default = "default_frame_ms")]
    pub frame_ms: u32,
    #[serde(default)]
    pub vad_backend: VadBackend,
    #[serde(default = "default_target_vad_model")]
    pub target_vad_model: String,
    #[serde(default)]
    pub vad_model_path: Option<String>,
    #[serde(default = "default_allow_vad_fallback")]
    pub allow_vad_fallback: bool,
    #[serde(default = "default_vad_threshold")]
    pub vad_threshold: f64,
    #[serde(default = "default_vad_probability_threshold")]
    pub vad_probability_threshold: f64,
    #[serde(default = "default_vad_session_pool_size")]
    pub vad_session_pool_size: usize,
    #[serde(default = "default_vad_stream_state_cache_size")]
    pub vad_stream_state_cache_size: usize,
    #[serde(default = "default_min_speech_frames")]
    pub min_speech_frames: u32,
    #[serde(default = "default_max_inbound_buffer_bytes")]
    pub max_inbound_buffer_bytes: usize,
    #[serde(default = "default_max_outbound_buffer_bytes")]
    pub max_outbound_buffer_bytes: usize,
}

impl Default for VoiceEdgeConfig {
    fn default() -> Self {
        Self {
            sample_rate: default_sample_rate(),
            frame_ms: default_frame_ms(),
            vad_backend: VadBackend::default(),
            target_vad_model: default_target_vad_model(),
            vad_model_path: None,
            allow_vad_fallback: default_allow_vad_fallback(),
            vad_threshold: default_vad_threshold(),
            vad_probability_threshold: default_vad_probability_threshold(),
            vad_session_pool_size: default_vad_session_pool_size(),
            vad_stream_state_cache_size: default_vad_stream_state_cache_size(),
            min_speech_frames: default_min_speech_frames(),
            max_inbound_buffer_bytes: default_max_inbound_buffer_bytes(),
            max_outbound_buffer_bytes: default_max_outbound_buffer_bytes(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VoiceEdgeResponse {
    #[serde(default)]
    pub request_id: Option<String>,
    pub session_id: String,
    pub events: Vec<VoiceEdgeEvent>,
    pub final_state: VoiceEdgeStateSnapshot,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VoiceEdgeEvent {
    pub event_type: String,
    #[serde(default)]
    pub sequence: Option<u64>,
    #[serde(default)]
    pub response_id: Option<String>,
    #[serde(default)]
    pub is_speech: Option<bool>,
    #[serde(default)]
    pub rms: Option<f64>,
    #[serde(default)]
    pub speech_probability: Option<f64>,
    #[serde(default)]
    pub cancellation: Option<CancellationAck>,
    #[serde(default)]
    pub metadata: BTreeMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CancellationAck {
    pub response_id: String,
    pub reason: String,
    pub drop_outbound_audio: bool,
    pub cancel_gemma: bool,
    pub clear_kokoro_buffers: bool,
    pub stop_livekit_audio: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VoiceEdgeStateSnapshot {
    pub inbound_buffer_bytes: usize,
    pub outbound_buffer_bytes: usize,
    pub consecutive_speech_frames: u32,
    pub agent_speaking: bool,
    #[serde(default)]
    pub active_response_id: Option<String>,
    pub cancellation_acknowledged: bool,
}

pub fn event(
    event_type: impl Into<String>,
    sequence: Option<u64>,
    response_id: Option<String>,
) -> VoiceEdgeEvent {
    VoiceEdgeEvent {
        event_type: event_type.into(),
        sequence,
        response_id,
        is_speech: None,
        rms: None,
        speech_probability: None,
        cancellation: None,
        metadata: BTreeMap::new(),
    }
}

fn default_sample_rate() -> u32 {
    16_000
}

fn default_frame_ms() -> u32 {
    32
}

fn default_target_vad_model() -> String {
    "silero-vad-rust".to_string()
}

fn default_allow_vad_fallback() -> bool {
    true
}

fn default_vad_threshold() -> f64 {
    0.018
}

fn default_vad_probability_threshold() -> f64 {
    0.5
}

fn default_vad_session_pool_size() -> usize {
    4
}

fn default_vad_stream_state_cache_size() -> usize {
    512
}

fn default_min_speech_frames() -> u32 {
    2
}

fn default_max_inbound_buffer_bytes() -> usize {
    16_000 * 2 * 30
}

fn default_max_outbound_buffer_bytes() -> usize {
    16_000 * 2 * 2
}

fn default_cancel_reason() -> String {
    "barge-in detected".to_string()
}
