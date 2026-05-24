use crate::contracts::{
    event, AnalyzeVoiceRequest, CancelVoiceRequest, CancellationAck, VoiceEdgeConfig,
    VoiceEdgeRequest, VoiceEdgeResponse, VoiceEdgeStateSnapshot,
};
use crate::vad::analyze_voice_activity_for_stream;

pub fn handle_request(request: VoiceEdgeRequest) -> VoiceEdgeResponse {
    match request {
        VoiceEdgeRequest::Analyze(request) => VoiceEdgeRuntime::from_request(&request).analyze(
            request.request_id,
            request.session_id,
            request.response_id,
            request.agent_speaking,
            request.frames,
        ),
        VoiceEdgeRequest::Cancel(request) => cancel_response(request),
    }
}

#[derive(Debug, Clone)]
pub struct VoiceEdgeRuntime {
    config: VoiceEdgeConfig,
    inbound_buffer_bytes: usize,
    outbound_buffer_bytes: usize,
    consecutive_speech_frames: u32,
    cancellation_acknowledged: bool,
}

impl VoiceEdgeRuntime {
    pub fn new(config: VoiceEdgeConfig) -> Self {
        Self {
            config,
            inbound_buffer_bytes: 0,
            outbound_buffer_bytes: 0,
            consecutive_speech_frames: 0,
            cancellation_acknowledged: false,
        }
    }

    fn from_request(request: &AnalyzeVoiceRequest) -> Self {
        Self::new(request.config.clone())
    }

    pub fn analyze(
        mut self,
        request_id: Option<String>,
        session_id: String,
        response_id: Option<String>,
        agent_speaking: bool,
        frames: Vec<crate::contracts::AudioFrame>,
    ) -> VoiceEdgeResponse {
        let mut events = Vec::new();
        let mut user_turn_started = false;

        for frame in frames {
            self.inbound_buffer_bytes += frame.pcm_s16le.len() * 2;
            if self.inbound_buffer_bytes > self.config.max_inbound_buffer_bytes {
                self.inbound_buffer_bytes = self.config.max_inbound_buffer_bytes;
                events.push(event(
                    "voice_edge_inbound_buffer_trimmed",
                    Some(frame.sequence),
                    response_id.clone(),
                ));
            }

            let analysis = analyze_voice_activity_for_stream(
                &frame.pcm_s16le,
                &self.config,
                Some(&session_id),
            );
            let decision = analysis.decision;
            if decision.is_speech {
                self.consecutive_speech_frames += 1;
            } else {
                self.consecutive_speech_frames = 0;
            }

            let mut analyzed = event(
                "voice_vad_frame_analyzed",
                Some(frame.sequence),
                response_id.clone(),
            );
            analyzed.is_speech = Some(decision.is_speech);
            analyzed.rms = Some(round_metric(decision.rms));
            analyzed.speech_probability = Some(round_metric(decision.speech_probability));
            analyzed.metadata.insert(
                "vad_backend_requested".to_string(),
                analysis.requested_backend.as_str().to_string(),
            );
            analyzed.metadata.insert(
                "vad_backend_effective".to_string(),
                analysis.effective_backend.to_string(),
            );
            analyzed
                .metadata
                .insert("target_vad_model".to_string(), analysis.target_model);
            analyzed.metadata.insert(
                "vad_probability_threshold".to_string(),
                self.config.vad_probability_threshold.to_string(),
            );
            analyzed.metadata.insert(
                "vad_session_pool_size".to_string(),
                self.config.vad_session_pool_size.to_string(),
            );
            analyzed.metadata.insert(
                "vad_stream_state_cache_size".to_string(),
                self.config.vad_stream_state_cache_size.to_string(),
            );
            analyzed.metadata.insert(
                "vad_model_path_configured".to_string(),
                analysis.model_path_configured.to_string(),
            );
            if let Some(reason) = analysis.fallback_reason {
                analyzed
                    .metadata
                    .insert("vad_fallback_reason".to_string(), reason.to_string());
            }
            events.push(analyzed);

            if !user_turn_started && self.consecutive_speech_frames >= self.config.min_speech_frames
            {
                user_turn_started = true;
                events.push(event(
                    "voice_user_speech_started",
                    Some(frame.sequence),
                    response_id.clone(),
                ));

                if agent_speaking {
                    let ack = CancellationAck {
                        response_id: response_id
                            .clone()
                            .unwrap_or_else(|| "unknown-response".to_string()),
                        reason: "barge-in detected".to_string(),
                        drop_outbound_audio: true,
                        cancel_gemma: true,
                        clear_kokoro_buffers: true,
                        stop_livekit_audio: true,
                    };
                    self.outbound_buffer_bytes = 0;
                    self.cancellation_acknowledged = true;

                    let mut barge_in = event(
                        "voice_barge_in_detected",
                        Some(frame.sequence),
                        response_id.clone(),
                    );
                    barge_in.cancellation = Some(ack.clone());
                    events.push(barge_in);

                    let mut cancel = event(
                        "voice_edge_cancellation_acknowledged",
                        Some(frame.sequence),
                        response_id.clone(),
                    );
                    cancel.cancellation = Some(ack);
                    events.push(cancel);
                }
            }
        }

        VoiceEdgeResponse {
            request_id,
            session_id,
            events,
            final_state: VoiceEdgeStateSnapshot {
                inbound_buffer_bytes: self.inbound_buffer_bytes,
                outbound_buffer_bytes: self.outbound_buffer_bytes,
                consecutive_speech_frames: self.consecutive_speech_frames,
                agent_speaking,
                active_response_id: response_id,
                cancellation_acknowledged: self.cancellation_acknowledged,
            },
        }
    }
}

fn cancel_response(request: CancelVoiceRequest) -> VoiceEdgeResponse {
    let ack = CancellationAck {
        response_id: request.response_id.clone(),
        reason: request.reason,
        drop_outbound_audio: true,
        cancel_gemma: true,
        clear_kokoro_buffers: true,
        stop_livekit_audio: true,
    };
    let mut cancel = event(
        "voice_edge_cancellation_acknowledged",
        None,
        Some(request.response_id.clone()),
    );
    cancel.cancellation = Some(ack);

    VoiceEdgeResponse {
        request_id: request.request_id,
        session_id: request.session_id,
        events: vec![cancel],
        final_state: VoiceEdgeStateSnapshot {
            inbound_buffer_bytes: 0,
            outbound_buffer_bytes: 0,
            consecutive_speech_frames: 0,
            agent_speaking: false,
            active_response_id: Some(request.response_id),
            cancellation_acknowledged: true,
        },
    }
}

fn round_metric(value: f64) -> f64 {
    (value * 100_000.0).round() / 100_000.0
}
