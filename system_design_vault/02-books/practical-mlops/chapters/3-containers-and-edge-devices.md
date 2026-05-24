---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Practical MLOps"
authors: "Noah Gift; Alfredo Deza"
chapter: "3"
chapter_title: "MLOps for Containers and Edge Devices"
source_path: "/Users/saumyamehta/DS interview prep/books/Practical MLOps_ Operationalizing Machine Learning Models.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# Practical MLOps - Chapter 3: MLOps for Containers and Edge Devices

## Source Reading Scope

Direct-read extraction span: `/tmp/practical_mlops_text.txt` lines 2856-3933.

This note is original synthesis only. It does not preserve raw source text.

## Core Takeaways

Containers make ML services portable, reproducible, and shareable. The chapter contrasts virtual machines with containerized microservices: production ML needs deployable application units that can be built, tagged, scanned, pushed, pulled, run, and inspected.

Container metadata matters. Tags, labels, model versions, runtime versions, and registry paths turn a container from an anonymous image into a traceable production artifact.

Container quality is not just "it runs." Dockerfiles should be linted, dependencies pinned, layers kept reasonable, vulnerabilities scanned, and service endpoints verified with realistic requests.

The HTTP model-serving example shows a core production contract: load model, receive request, transform input, predict, and return structured response. That contract is portable across many model types and provider platforms.

Edge deployment introduces different constraints: offline operation, latency near the user, limited storage, specialized chips, model format compatibility, compiler/runtime availability, and careful device support. Containers can help create repeatable tooling even when target hardware is constrained.

## Agent Studio Design Implications

- Package core services as containers or equivalent locked runtimes: extraction workers, embedding workers, retrieval APIs, rerankers, evaluators, and agent runtime services.
- Register artifacts with meaningful names and labels: model route, embedding model, index version, prompt bundle, evaluator suite, source manifest, and build ID.
- Add container checks to CI: Dockerfile lint, dependency scan, vulnerability threshold, smoke request, and metadata assertion.
- Provide service endpoints that expose model/index/runtime metadata without revealing raw protected content.
- Design local/offline modes explicitly: which models run locally, which indexes fit locally, which tasks require cloud connectivity, and what fallback behavior exists.

## Failure Modes To Guard Against

- Untagged or vaguely tagged production images.
- Inference containers with no model provenance metadata.
- Dependency pinning without a patch/update process.
- Vulnerability scans that report issues but never gate promotion.
- Edge or local workflows that assume cloud bandwidth, unlimited memory, or unsupported model formats.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
