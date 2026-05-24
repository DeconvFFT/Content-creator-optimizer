use std::io::{self, BufRead, Read, Write};
use voice_edge::cli::{parse_args, RunMode};
use voice_edge::{handle_request, VoiceEdgeRequest};

#[tokio::main]
async fn main() {
    if let Err(error) = run().await {
        eprintln!("{error}");
        std::process::exit(1);
    }
}

async fn run() -> Result<(), String> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match parse_args(&args)? {
        RunMode::Stdin => run_stdin(),
        RunMode::Jsonl => run_jsonl(),
        RunMode::Http(addr) => voice_edge::http::serve(addr).await,
        RunMode::Help => {
            println!("{}", voice_edge::cli::USAGE);
            Ok(())
        }
        RunMode::Version => {
            println!("voice-edge {}", env!("CARGO_PKG_VERSION"));
            Ok(())
        }
    }
}

fn run_stdin() -> Result<(), String> {
    let mut input = String::new();
    io::stdin()
        .read_to_string(&mut input)
        .map_err(|error| format!("failed to read stdin: {error}"))?;

    let request: VoiceEdgeRequest =
        serde_json::from_str(&input).map_err(|error| format!("invalid request json: {error}"))?;
    let response = handle_request(request);
    let output = serde_json::to_string_pretty(&response)
        .map_err(|error| format!("failed to encode response json: {error}"))?;
    println!("{output}");
    Ok(())
}

fn run_jsonl() -> Result<(), String> {
    let stdin = io::stdin();
    let mut stdout = io::stdout().lock();
    for line in stdin.lock().lines() {
        let line = line.map_err(|error| format!("failed to read stdin line: {error}"))?;
        if line.trim().is_empty() {
            continue;
        }
        let request: VoiceEdgeRequest = serde_json::from_str(&line)
            .map_err(|error| format!("invalid request json: {error}"))?;
        let response = handle_request(request);
        let output = serde_json::to_string(&response)
            .map_err(|error| format!("failed to encode response json: {error}"))?;
        stdout
            .write_all(output.as_bytes())
            .map_err(|error| format!("failed to write response json: {error}"))?;
        stdout
            .write_all(b"\n")
            .map_err(|error| format!("failed to write response newline: {error}"))?;
        stdout
            .flush()
            .map_err(|error| format!("failed to flush response json: {error}"))?;
    }
    Ok(())
}
