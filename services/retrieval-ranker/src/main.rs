use retrieval_ranker::{handle_request, RetrievalRankerRequest};
use std::io::{self, Read};

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let mut input = String::new();
    io::stdin()
        .read_to_string(&mut input)
        .map_err(|error| format!("failed to read stdin: {error}"))?;

    let request: RetrievalRankerRequest =
        serde_json::from_str(&input).map_err(|error| format!("invalid request json: {error}"))?;
    let response = handle_request(request);
    let output = serde_json::to_string_pretty(&response)
        .map_err(|error| format!("failed to encode response json: {error}"))?;
    println!("{output}");
    Ok(())
}
