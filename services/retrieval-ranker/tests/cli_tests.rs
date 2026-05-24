use pretty_assertions::assert_eq;
use serde_json::Value;
use std::io::Write;
use std::process::{Command, Stdio};

#[test]
fn cli_accepts_rank_json_on_stdin() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_retrieval-ranker"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("spawn retrieval-ranker");

    let payload = r#"{
        "kind": "rank",
        "request_id": "cli-rank",
        "query": "graph evidence",
        "candidates": [
            {
                "id": "chunk-2",
                "text": "unrelated",
                "signals": {"vector_score": 0.2}
            },
            {
                "id": "chunk-1",
                "text": "graph evidence",
                "signals": {"vector_score": 0.8}
            }
        ],
        "config": {"limit": 1}
    }"#;

    child
        .stdin
        .as_mut()
        .expect("stdin")
        .write_all(payload.as_bytes())
        .expect("write payload");

    let output = child.wait_with_output().expect("read output");
    assert!(output.status.success());

    let json: Value = serde_json::from_slice(&output.stdout).expect("valid response json");
    assert_eq!(json["kind"], "rank");
    assert_eq!(json["request_id"], "cli-rank");
    assert_eq!(json["results"][0]["id"], "chunk-1");
    assert_eq!(json["diagnostics"]["returned_count"], 1);
}
