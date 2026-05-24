# Retrieval Ranker

Rust service boundary for deterministic retrieval ranking and lightweight graph traversal in All About LLMs Agent Studio.

This crate is intentionally modest. It does not call providers, databases, or network services. The current integration shape is a typed JSON contract plus a stdin/stdout CLI, so the Python FastAPI backend can call it later as a subprocess while the team validates contracts, latency, and failure modes. If this boundary earns its keep, the same request/response structs can back an HTTP or Unix-socket service.

## What It Owns

- Deterministic reranking for candidate chunks using vector, lexical, graph, authority, and freshness signals.
- Stable tie-breaking by candidate id.
- Serializable request/response contracts for Python orchestration.
- Bounded breadth-first graph traversal for provenance or knowledge-graph neighborhood expansion.
- Unit and integration tests for ranking, contracts, CLI behavior, and traversal determinism.

## What It Does Not Own Yet

- Embedding generation.
- pgvector queries.
- Provider-backed reranking.
- FastAPI routes.
- Long-running service supervision.

Those remain in the Python orchestration/backend layer until this Rust boundary is promoted.

## Build And Test

```bash
cargo test
```

Run a rank request through the CLI:

```bash
cargo run --quiet <<'JSON'
{
  "kind": "rank",
  "request_id": "demo-rank",
  "query": "retrieval quality graph evidence",
  "candidates": [
    {
      "id": "chunk-a",
      "title": "Retrieval quality ledger",
      "text": "Graph evidence and source grounding are recorded for retrieval quality.",
      "signals": {
        "vector_score": 0.82,
        "authority": 0.9,
        "freshness_days": 7
      }
    },
    {
      "id": "chunk-b",
      "text": "A general content draft without source evidence.",
      "signals": {
        "vector_score": 0.55,
        "authority": 0.4,
        "freshness_days": 120
      }
    }
  ]
}
JSON
```

Run a graph traversal request:

```bash
cargo run --quiet <<'JSON'
{
  "kind": "traverse_graph",
  "request_id": "demo-graph",
  "start_node_id": "claim:1",
  "max_depth": 2,
  "limit": 10,
  "edges": [
    {"from": "claim:1", "to": "source:1", "relation": "supported_by"},
    {"from": "source:1", "to": "chunk:9", "relation": "contains"}
  ]
}
JSON
```

## Python Call Path Later

The FastAPI backend can start with a narrow subprocess adapter:

```python
import json
import subprocess


def call_retrieval_ranker(payload: dict) -> dict:
    completed = subprocess.run(
        ["cargo", "run", "--quiet", "--manifest-path", "services/retrieval-ranker/Cargo.toml"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout)
```

For production, compile the binary once and call the binary directly instead of invoking Cargo:

```python
completed = subprocess.run(
    ["services/retrieval-ranker/target/release/retrieval-ranker"],
    input=json.dumps(payload),
    text=True,
    capture_output=True,
    check=True,
)
```

The expected contract is:

- Python owns retrieval from Postgres/pgvector, source metadata, and orchestration.
- Python sends candidate chunks plus known signals to Rust.
- Rust returns ranked ids, scores, explanations, and copied metadata.
- Python persists the result in the retrieval quality ledger and decides whether to call provider-backed rerankers.

## Contract Notes

- Scores are normalized to `0.0..=1.0`.
- Missing signals contribute `0.0`, except lexical score, which falls back to deterministic token overlap between the query and candidate title/text.
- Candidate ordering is stable across runs.
- Graph traversal includes the start node at depth `0` and then visits outgoing edges in sorted order.
