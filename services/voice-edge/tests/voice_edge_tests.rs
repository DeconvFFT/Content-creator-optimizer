use axum::body::{to_bytes, Body};
use axum::http::{Request, StatusCode};
use pretty_assertions::assert_eq;
use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio};
use tower::ServiceExt;
use voice_edge::cli::{parse_args, RunMode};
use voice_edge::{
    analyze_pcm_s16le, handle_request, AudioFrame, VadBackend, VoiceEdgeConfig, VoiceEdgeRequest,
    VoiceEdgeRuntime,
};

fn frame(sequence: u64, amplitude: i16) -> AudioFrame {
    AudioFrame {
        sequence,
        timestamp_ms: Some(sequence * 32),
        pcm_s16le: vec![amplitude; 512],
    }
}

#[test]
fn deterministic_vad_separates_silence_from_speech() {
    let config = VoiceEdgeConfig::default();
    let silence = analyze_pcm_s16le(&frame(1, 0).pcm_s16le, &config);
    let speech = analyze_pcm_s16le(&frame(2, 2400).pcm_s16le, &config);

    assert_eq!(silence.is_speech, false);
    assert_eq!(speech.is_speech, true);
    assert!(speech.speech_probability > silence.speech_probability);
}

#[test]
fn silero_onnx_bundled_runtime_records_real_backend() {
    let config = VoiceEdgeConfig {
        vad_backend: VadBackend::SileroOnnx,
        ..VoiceEdgeConfig::default()
    };
    let response = VoiceEdgeRuntime::new(config).analyze(
        Some("silero-bundled".to_string()),
        "session-1".to_string(),
        None,
        false,
        vec![frame(1, 0)],
    );
    let analyzed = response
        .events
        .iter()
        .find(|event| event.event_type == "voice_vad_frame_analyzed")
        .expect("vad analysis event");

    assert_eq!(analyzed.metadata["vad_backend_requested"], "silero_onnx");
    assert_eq!(analyzed.metadata["vad_backend_effective"], "silero_onnx");
    assert_eq!(analyzed.metadata["target_vad_model"], "silero-vad-rust");
    assert_eq!(analyzed.metadata["vad_model_path_configured"], "false");
    assert!(!analyzed.metadata.contains_key("vad_fallback_reason"));
    assert!(analyzed.speech_probability.unwrap_or(-1.0) >= 0.0);
    assert!(analyzed.speech_probability.unwrap_or(2.0) <= 1.0);
}

#[test]
fn silero_onnx_invalid_model_path_falls_back_with_explicit_metadata() {
    let config = VoiceEdgeConfig {
        vad_backend: VadBackend::SileroOnnx,
        vad_model_path: Some("/missing/silero_vad.onnx".to_string()),
        ..VoiceEdgeConfig::default()
    };
    let response = VoiceEdgeRuntime::new(config).analyze(
        Some("silero-fallback".to_string()),
        "session-1".to_string(),
        None,
        false,
        vec![frame(1, 2600), frame(2, 2600)],
    );
    let analyzed = response
        .events
        .iter()
        .find(|event| event.event_type == "voice_vad_frame_analyzed")
        .expect("vad analysis event");

    assert_eq!(analyzed.metadata["vad_backend_requested"], "silero_onnx");
    assert_eq!(
        analyzed.metadata["vad_backend_effective"],
        "deterministic_energy_gate"
    );
    assert_eq!(analyzed.metadata["target_vad_model"], "silero-vad-rust");
    assert_eq!(analyzed.metadata["vad_model_path_configured"], "true");
    assert_eq!(
        analyzed.metadata["vad_fallback_reason"],
        "silero_onnx_inference_failed"
    );
    assert!(response
        .events
        .iter()
        .any(|event| event.event_type == "voice_user_speech_started"));
}

#[test]
fn silero_onnx_without_fallback_is_conservative() {
    let config = VoiceEdgeConfig {
        vad_backend: VadBackend::SileroOnnx,
        vad_model_path: Some("/missing/silero_vad.onnx".to_string()),
        allow_vad_fallback: false,
        ..VoiceEdgeConfig::default()
    };
    let response = VoiceEdgeRuntime::new(config).analyze(
        None,
        "session-1".to_string(),
        Some("response-1".to_string()),
        true,
        vec![frame(1, 2600), frame(2, 2600)],
    );
    let analyzed = response
        .events
        .iter()
        .find(|event| event.event_type == "voice_vad_frame_analyzed")
        .expect("vad analysis event");

    assert_eq!(analyzed.is_speech, Some(false));
    assert_eq!(analyzed.metadata["vad_backend_effective"], "unavailable");
    assert_eq!(
        analyzed.metadata["vad_fallback_reason"],
        "silero_onnx_inference_failed_no_fallback"
    );
    assert!(!response
        .events
        .iter()
        .any(|event| event.event_type == "voice_barge_in_detected"));
}

#[test]
fn detects_barge_in_and_acknowledges_all_cancellation_actions() {
    let response = VoiceEdgeRuntime::new(VoiceEdgeConfig::default()).analyze(
        Some("voice-edge-1".to_string()),
        "session-1".to_string(),
        Some("response-1".to_string()),
        true,
        vec![frame(1, 2600), frame(2, 2600)],
    );

    let event_types: Vec<&str> = response
        .events
        .iter()
        .map(|event| event.event_type.as_str())
        .collect();
    assert!(event_types.contains(&"voice_user_speech_started"));
    assert!(event_types.contains(&"voice_barge_in_detected"));
    assert!(event_types.contains(&"voice_edge_cancellation_acknowledged"));

    let cancellation = response
        .events
        .iter()
        .find(|event| event.event_type == "voice_edge_cancellation_acknowledged")
        .and_then(|event| event.cancellation.as_ref())
        .expect("cancellation ack");
    assert_eq!(cancellation.response_id, "response-1");
    assert_eq!(cancellation.drop_outbound_audio, true);
    assert_eq!(cancellation.cancel_gemma, true);
    assert_eq!(cancellation.clear_kokoro_buffers, true);
    assert_eq!(cancellation.stop_livekit_audio, true);
    assert_eq!(response.final_state.cancellation_acknowledged, true);
}

#[test]
fn does_not_interrupt_for_single_speech_frame_by_default() {
    let response = VoiceEdgeRuntime::new(VoiceEdgeConfig::default()).analyze(
        None,
        "session-1".to_string(),
        Some("response-1".to_string()),
        true,
        vec![frame(1, 2600)],
    );

    assert!(!response
        .events
        .iter()
        .any(|event| event.event_type == "voice_barge_in_detected"));
    assert_eq!(response.final_state.cancellation_acknowledged, false);
}

#[test]
fn trims_inbound_buffer_to_configured_limit() {
    let config = VoiceEdgeConfig {
        max_inbound_buffer_bytes: 1024,
        ..VoiceEdgeConfig::default()
    };
    let response = VoiceEdgeRuntime::new(config).analyze(
        None,
        "session-1".to_string(),
        None,
        false,
        vec![frame(1, 0), frame(2, 0)],
    );

    assert_eq!(response.final_state.inbound_buffer_bytes, 1024);
    assert!(response
        .events
        .iter()
        .any(|event| event.event_type == "voice_edge_inbound_buffer_trimmed"));
}

#[test]
fn dispatches_json_friendly_analyze_requests() {
    let response = handle_request(VoiceEdgeRequest::Analyze(
        voice_edge::contracts::AnalyzeVoiceRequest {
            request_id: Some("dispatch-voice".to_string()),
            session_id: "session-1".to_string(),
            response_id: Some("response-1".to_string()),
            agent_speaking: true,
            config: VoiceEdgeConfig::default(),
            frames: vec![frame(1, 2600), frame(2, 2600)],
        },
    ));

    assert_eq!(response.request_id.as_deref(), Some("dispatch-voice"));
    assert_eq!(response.session_id, "session-1");
    assert!(response.final_state.cancellation_acknowledged);
}

#[test]
fn cli_parser_keeps_modes_unambiguous() {
    let jsonl_args = vec!["--jsonl".to_string()];
    assert_eq!(parse_args(&jsonl_args).expect("jsonl mode"), RunMode::Jsonl);

    let http_args = vec!["--http".to_string(), "127.0.0.1:7072".to_string()];
    assert_eq!(
        parse_args(&http_args).expect("http mode"),
        RunMode::Http("127.0.0.1:7072".parse().expect("http addr"))
    );

    let serve_args = vec!["serve".to_string()];
    assert_eq!(
        parse_args(&serve_args).expect("default serve mode"),
        RunMode::Http("127.0.0.1:7071".parse().expect("default serve addr"))
    );

    let help_args = vec!["--help".to_string()];
    assert_eq!(parse_args(&help_args).expect("help mode"), RunMode::Help);

    let version_args = vec!["--version".to_string()];
    assert_eq!(
        parse_args(&version_args).expect("version mode"),
        RunMode::Version
    );
}

#[test]
fn cli_parser_rejects_mixed_or_unknown_args() {
    let mixed_args = vec![
        "--jsonl".to_string(),
        "--http".to_string(),
        "127.0.0.1:7071".to_string(),
    ];
    assert!(parse_args(&mixed_args)
        .expect_err("mixed modes rejected")
        .contains("invalid voice-edge arguments"));

    let unknown_args = vec!["--bogus".to_string()];
    assert!(parse_args(&unknown_args)
        .expect_err("unknown mode rejected")
        .contains("invalid voice-edge arguments"));

    let malformed_http_args = vec!["--http".to_string()];
    assert!(parse_args(&malformed_http_args)
        .expect_err("missing http address rejected")
        .contains("voice-edge --http 127.0.0.1:7071"));
}

#[tokio::test]
async fn http_healthz_exposes_voice_edge_boundary() {
    let response = voice_edge::http::router()
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/healthz")
                .body(Body::empty())
                .expect("health request"),
        )
        .await
        .expect("health response");

    assert_eq!(response.status(), StatusCode::OK);
    let body = to_bytes(response.into_body(), usize::MAX)
        .await
        .expect("health body");
    let json: serde_json::Value = serde_json::from_slice(&body).expect("health json");
    assert_eq!(json["status"], "ok");
    assert_eq!(json["service"], "voice-edge");
    assert_eq!(json["transport"], "http");
    assert_eq!(json["target_vad_model"], "silero-vad-rust");
    assert_eq!(json["default_vad_backend"], "deterministic_energy");
    assert_eq!(
        json["effective_vad_model"],
        "request_scoped_by_voice_edge_config"
    );
    assert_eq!(
        json["silero_onnx_runtime"],
        "linked_with_bundled_model_and_file_override"
    );
    assert_eq!(json["supported_vad_backends"][1], "silero_onnx");
    assert_eq!(json["state_model"], "stateless_request_response");
}

#[tokio::test]
async fn http_voice_edge_dispatches_barge_in_cancellation() {
    let request = serde_json::json!({
        "kind": "analyze",
        "request_id": "http-1",
        "session_id": "session-http",
        "response_id": "response-http",
        "agent_speaking": true,
        "frames": [
            {"sequence": 1, "timestamp_ms": 32, "pcm_s16le": vec![2600; 512]},
            {"sequence": 2, "timestamp_ms": 64, "pcm_s16le": vec![2600; 512]}
        ]
    });

    let response = voice_edge::http::router()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/v1/voice-edge")
                .header("content-type", "application/json")
                .body(Body::from(request.to_string()))
                .expect("voice-edge request"),
        )
        .await
        .expect("voice-edge response");

    assert_eq!(response.status(), StatusCode::OK);
    let body = to_bytes(response.into_body(), usize::MAX)
        .await
        .expect("voice-edge body");
    let json: serde_json::Value = serde_json::from_slice(&body).expect("voice-edge json");
    assert_eq!(json["request_id"], "http-1");
    assert_eq!(json["session_id"], "session-http");
    assert_eq!(json["final_state"]["cancellation_acknowledged"], true);
    assert!(json["events"]
        .as_array()
        .expect("events array")
        .iter()
        .any(
            |event| event["event_type"] == "voice_edge_cancellation_acknowledged"
                && event["cancellation"]["cancel_gemma"] == true
                && event["cancellation"]["clear_kokoro_buffers"] == true
        ));
}

#[tokio::test]
async fn http_analyze_route_accepts_typed_request_without_tag() {
    let request = serde_json::json!({
        "request_id": "http-analyze-1",
        "session_id": "session-http",
        "response_id": "response-http",
        "agent_speaking": true,
        "frames": [
            {"sequence": 1, "timestamp_ms": 32, "pcm_s16le": vec![2600; 512]},
            {"sequence": 2, "timestamp_ms": 64, "pcm_s16le": vec![2600; 512]}
        ]
    });

    let response = voice_edge::http::router()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/v1/voice-edge/analyze")
                .header("content-type", "application/json")
                .body(Body::from(request.to_string()))
                .expect("analyze request"),
        )
        .await
        .expect("analyze response");

    assert_eq!(response.status(), StatusCode::OK);
    let body = to_bytes(response.into_body(), usize::MAX)
        .await
        .expect("analyze body");
    let json: serde_json::Value = serde_json::from_slice(&body).expect("analyze json");
    assert_eq!(json["request_id"], "http-analyze-1");
    assert_eq!(json["final_state"]["cancellation_acknowledged"], true);
}

#[tokio::test]
async fn http_voice_edge_cancel_route_returns_full_stop_ack() {
    let request = serde_json::json!({
        "request_id": "http-cancel-1",
        "session_id": "session-http",
        "response_id": "response-http",
        "reason": "manual barge-in"
    });

    let response = voice_edge::http::router()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/v1/voice-edge/cancel")
                .header("content-type", "application/json")
                .body(Body::from(request.to_string()))
                .expect("cancel request"),
        )
        .await
        .expect("cancel response");

    assert_eq!(response.status(), StatusCode::OK);
    let body = to_bytes(response.into_body(), usize::MAX)
        .await
        .expect("cancel body");
    let json: serde_json::Value = serde_json::from_slice(&body).expect("cancel json");
    let cancellation = &json["events"][0]["cancellation"];
    assert_eq!(cancellation["reason"], "manual barge-in");
    assert_eq!(cancellation["drop_outbound_audio"], true);
    assert_eq!(cancellation["cancel_gemma"], true);
    assert_eq!(cancellation["clear_kokoro_buffers"], true);
    assert_eq!(cancellation["stop_livekit_audio"], true);
}

#[tokio::test]
async fn http_rejects_malformed_json_without_panicking() {
    let response = voice_edge::http::router()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/v1/voice-edge")
                .header("content-type", "application/json")
                .body(Body::from("{not-json"))
                .expect("malformed request"),
        )
        .await
        .expect("malformed response");

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[test]
fn jsonl_mode_handles_multiple_requests_without_restarting() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_voice-edge"))
        .arg("--jsonl")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("spawn voice-edge jsonl");
    let mut stdin = child.stdin.take().expect("stdin");
    let stdout = child.stdout.take().expect("stdout");
    let mut reader = BufReader::new(stdout);

    let first = serde_json::json!({
        "kind": "analyze",
        "request_id": "jsonl-1",
        "session_id": "session-jsonl",
        "response_id": "response-jsonl",
        "agent_speaking": true,
        "frames": [
            {"sequence": 1, "timestamp_ms": 32, "pcm_s16le": vec![2600; 512]},
            {"sequence": 2, "timestamp_ms": 64, "pcm_s16le": vec![2600; 512]}
        ]
    });
    let second = serde_json::json!({
        "kind": "cancel",
        "request_id": "jsonl-2",
        "session_id": "session-jsonl",
        "response_id": "response-jsonl",
        "reason": "manual interrupt"
    });
    writeln!(stdin, "{first}").expect("write first request");
    writeln!(stdin, "{second}").expect("write second request");
    drop(stdin);

    let mut first_line = String::new();
    let mut second_line = String::new();
    reader
        .read_line(&mut first_line)
        .expect("read first response");
    reader
        .read_line(&mut second_line)
        .expect("read second response");

    let first_response: serde_json::Value =
        serde_json::from_str(&first_line).expect("first json response");
    let second_response: serde_json::Value =
        serde_json::from_str(&second_line).expect("second json response");
    assert_eq!(first_response["request_id"], "jsonl-1");
    assert_eq!(
        first_response["final_state"]["cancellation_acknowledged"],
        true
    );
    assert_eq!(second_response["request_id"], "jsonl-2");
    assert_eq!(
        second_response["events"][0]["cancellation"]["reason"],
        "manual interrupt"
    );

    let status = child.wait().expect("wait for child");
    assert!(status.success());
}
