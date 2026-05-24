use crate::contracts::{
    AnalyzeVoiceRequest, CancelVoiceRequest, VoiceEdgeRequest, VoiceEdgeResponse,
};
use crate::handle_request;
use axum::{extract::Json, routing::get, routing::post, Router};
use serde::Serialize;
use std::net::SocketAddr;
use tokio::net::TcpListener;

#[derive(Debug, Clone, Serialize)]
pub struct HealthResponse {
    pub status: &'static str,
    pub service: &'static str,
    pub transport: &'static str,
    pub request_contract: &'static str,
    pub default_vad_backend: &'static str,
    pub effective_vad_model: &'static str,
    pub target_vad_model: &'static str,
    pub supported_vad_backends: Vec<&'static str>,
    pub silero_onnx_runtime: &'static str,
    pub state_model: &'static str,
}

pub fn router() -> Router {
    Router::new()
        .route("/healthz", get(healthz))
        .route("/v1/voice-edge", post(voice_edge))
        .route("/v1/voice-edge/analyze", post(analyze_voice))
        .route("/v1/voice-edge/cancel", post(cancel_voice))
}

pub async fn serve(addr: SocketAddr) -> Result<(), String> {
    let listener = TcpListener::bind(addr)
        .await
        .map_err(|error| format!("failed to bind voice-edge http listener at {addr}: {error}"))?;
    axum::serve(listener, router())
        .await
        .map_err(|error| format!("voice-edge http server failed: {error}"))
}

async fn healthz() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok",
        service: "voice-edge",
        transport: "http",
        request_contract: "voice_edge_request_v1",
        default_vad_backend: "deterministic_energy",
        effective_vad_model: "request_scoped_by_voice_edge_config",
        target_vad_model: "silero-vad-rust",
        supported_vad_backends: vec!["deterministic_energy", "silero_onnx"],
        silero_onnx_runtime: "linked_with_bundled_model_and_file_override",
        state_model: "stateless_request_response",
    })
}

async fn voice_edge(Json(request): Json<VoiceEdgeRequest>) -> Json<VoiceEdgeResponse> {
    Json(handle_request(request))
}

async fn analyze_voice(Json(request): Json<AnalyzeVoiceRequest>) -> Json<VoiceEdgeResponse> {
    Json(handle_request(VoiceEdgeRequest::Analyze(request)))
}

async fn cancel_voice(Json(request): Json<CancelVoiceRequest>) -> Json<VoiceEdgeResponse> {
    Json(handle_request(VoiceEdgeRequest::Cancel(request)))
}
