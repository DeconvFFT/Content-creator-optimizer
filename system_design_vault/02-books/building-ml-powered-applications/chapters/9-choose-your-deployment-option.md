---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Building Machine Learning Powered Applications"
authors: "Emmanuel Ameisen"
chapter: "9"
chapter_title: "Choose Your Deployment Option"
source_path: "/Users/saumyamehta/DS interview prep/books/building-machine-learning-powered-applications-going-from-idea-to-product.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# Building ML Powered Applications - Chapter 9: Choose Your Deployment Option

## Source Reading Scope

Direct-read extraction span: `/tmp/building_ml_powered_applications_text.txt` lines 6540-6893.

This note is original synthesis only. It does not preserve raw source text.

## Core Takeaways

Deployment choice should follow latency, hardware, network, privacy, cost, and complexity requirements. The chapter compares server-side streaming APIs, batch predictions, client-side/on-device inference, browser-side execution, and federated learning.

Server-side APIs are easiest to prototype and centralize operational control, but they require infrastructure scaling and expose latency/network dependencies. Batch workflows fit precomputable predictions and scheduled decisions. Client-side models reduce server cost and improve privacy/latency for some use cases, but deployment and model update complexity increase.

Federated learning is presented as a privacy-preserving personalization option, but with significant complexity around model quality, aggregation, anonymization, and fleet management.

The chapter's practical rule is to start simple and move to more complex deployment only after requirements demand it.

## Agent Studio Design Implications

- Keep distinct execution lanes: realtime user interaction, background batch ingestion, scheduled refresh, and local/offline rehearsal.
- Use server-side orchestration for shared memory, source ledgers, and agent coordination; use local/client execution only where privacy, latency, or cost justify it.
- Precompute expensive retrieval, embeddings, graph features, and briefings when batch timing is acceptable.
- Treat provider selection as a deployment decision with latency, cost, privacy, and operational complexity trade-offs.
- Do not adopt federated or edge patterns until there is a clear user-data/privacy requirement and evaluation plan.

## Failure Modes To Guard Against

- Using a single serving pattern for all workflows.
- Pushing realtime interactions through slow batch-oriented infrastructure.
- Moving models client-side without update, monitoring, or compatibility plans.
- Choosing privacy-preserving complexity without proving the product need.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
