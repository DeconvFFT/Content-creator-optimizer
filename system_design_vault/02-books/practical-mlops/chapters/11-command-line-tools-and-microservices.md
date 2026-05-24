---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Practical MLOps"
authors: "Noah Gift; Alfredo Deza"
chapter: "11"
chapter_title: "Building MLOps Command Line Tools and Microservices"
source_path: "/Users/saumyamehta/DS interview prep/books/Practical MLOps_ Operationalizing Machine Learning Models.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# Practical MLOps - Chapter 11: Building MLOps Command Line Tools and Microservices

## Source Reading Scope

Direct-read extraction span: `/tmp/practical_mlops_text.txt` lines 11945-13145.

This note is original synthesis only. It does not preserve raw source text.

## Core Takeaways

Operational ML work needs packaged interfaces. Shell scripts are acceptable for tiny tasks, but production workflows need testable tools with argument parsing, logging, error handling, packaging, and a path to reuse in CI or services.

The chapter's CSV-linter example is important because it treats data validation as an executable product surface. A check can start as a local command, then become a CI gate, then become part of a service. This only works when the validation logic is separated from the CLI wrapper.

Microservices are useful when they isolate responsibilities and make workflows composable. They are not automatically better than local tools. The useful pattern is choosing the smallest interface that lets another process invoke the capability reliably.

Serverless functions and managed cloud APIs are especially useful for lightweight automation, data-processing hooks, and ML capabilities that are not the product's differentiator. Authentication and deployment discipline remain required; a cloud function is still a production service.

The chapter repeatedly favors automation that can be packaged, distributed, and invoked consistently across local, CI, and cloud contexts.

## Agent Studio Design Implications

- Build ingestion operations as reusable commands: `scan-sources`, `verify-provenance`, `extract-text`, `validate-chunks`, `build-index`, `run-evals`, `publish-note`, and `promote-index`.
- Keep validation logic importable by CLIs, services, notebooks, and CI. The command wrapper should not own the core rule.
- Create source linters for local corpus hygiene: allowed extensions, blocked filename patterns, extraction availability, duplicate title detection, metadata capture, and missing provenance.
- Treat tool-call validators as first-class commands so agent runtime checks can run outside the agent.
- Use microservices or serverless functions for narrow capabilities such as official-doc change checks, OCR jobs, transcript fetches from official sources, webhook receivers, and provider-specific enrichment.
- Prefer managed provider services where custom implementation is not a product advantage.

## Candidate Tool Surfaces

| Tool Surface | Responsibility |
|---|---|
| `source-lint` | validate file type, metadata, provenance, duplicate status |
| `extract-audit` | compare extraction length, page count, empty-page rate, OCR need |
| `chunk-audit` | validate section boundaries, chunk size, overlap, source pointers |
| `retrieval-smoke` | test index availability and minimum grounding quality |
| `eval-runner` | execute fixed regression tasks and write machine-readable results |
| `note-promote` | promote direct-read notes only when coverage and checks pass |

## Failure Modes To Guard Against

- One-off scripts that cannot be invoked by CI.
- CLI commands whose validation logic cannot be reused by services.
- Silent data-quality checks that do not fail builds or publish status.
- Serverless utilities without authentication, logging, or owner metadata.
- Custom infrastructure for generic capabilities already handled by mature provider services.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
