use std::net::SocketAddr;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RunMode {
    Stdin,
    Jsonl,
    Http(SocketAddr),
    Help,
    Version,
}

pub fn parse_args(args: &[String]) -> Result<RunMode, String> {
    match args {
        [] => Ok(RunMode::Stdin),
        [arg] if arg == "--help" || arg == "-h" => Ok(RunMode::Help),
        [arg] if arg == "--version" || arg == "-V" => Ok(RunMode::Version),
        [arg] if arg == "--jsonl" => Ok(RunMode::Jsonl),
        [arg, addr] if arg == "--http" => parse_addr("--http", addr).map(RunMode::Http),
        [arg] if arg == "serve" => parse_addr("serve", "127.0.0.1:7071").map(RunMode::Http),
        [arg, addr] if arg == "serve" => parse_addr("serve", addr).map(RunMode::Http),
        _ => Err(usage_error(args)),
    }
}

fn parse_addr(mode: &str, addr: &str) -> Result<SocketAddr, String> {
    addr.parse()
        .map_err(|error| format!("invalid {mode} address {addr}: {error}"))
}

fn usage_error(args: &[String]) -> String {
    let provided = if args.is_empty() {
        "<none>".to_string()
    } else {
        args.join(" ")
    };
    format!("invalid voice-edge arguments: {provided}.\n{USAGE}")
}

pub const USAGE: &str = "Usage:
  voice-edge < request.json
  voice-edge --jsonl
  voice-edge --http 127.0.0.1:7071
  voice-edge serve [127.0.0.1:7071]
  voice-edge --help
  voice-edge --version";
