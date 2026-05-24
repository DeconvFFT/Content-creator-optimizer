---
type: unresolved-high-value-book-gaps
project: agent-studio-system-design
status: active
updated: 2026-05-20
manifest: unresolved-high-value-book-gaps.json
---

# Unresolved High-Value Book Gaps

## Purpose

This queue isolates the remaining lawful local books that are still valuable for `system_design_vault`, but do not yet have broad chapter-level deepening or route-specific follow-through. It is narrower than `next-ingestion-queue` and more action-oriented than `local-book-coverage-granularity`.

Use this note when the nightly orchestrator needs to choose the next local-book-driven workstream.

## Selection Rules

- Prefer books here only when they can materially improve a concrete Agent Studio route, release gate, retrieval pattern, multimodal pipeline, or implementation playbook.
- Do not use this queue to justify shallow “book activity.”
- Promote the smallest high-value slice first.
- Cross-check any promoted slice against official docs, official/open whitepapers, official lectures, and/or highly cited primary papers before accepting architecture implications.
- If a book is already covered well enough for the current route surface, log “not highest-value tonight” and move on.

## Current Queue

No unresolved high-value local-book gaps remain right now. Future local-book work should stay maintenance-only unless a new concrete route exposes a fresh gap.

## Recent Resolution

- `Gans-in-action-deep-learning-with-generative-adversarial-networks.pdf` left this queue on 2026-05-20 after Chapter 10 was promoted into `[[02-books/gans-in-action/chapters/ch10-adversarial-examples-transferability-and-robustness-gates]]` with companion corroboration at `[[01-sources/official-open/gan-adversarial-examples-robustness-cross-check]]`. The targeted slice now makes iterative attacks, transferability, preprocessing fragility, robustness-evaluation rigor, and adversarial-training caveats explicit, so no unresolved local-book gap remains by default.

- `Generative-Deep-Learning.pdf` left this queue on 2026-05-20 after Chapter 11 was promoted into `[[02-books/generative-deep-learning/chapters/ch11-music-tokenization-symbolic-route-controls]]` with companion corroboration at `[[01-sources/official-open/gdl-ch11-music-generation-routes-cross-check]]`. The book now has chapter-level follow-through for the remaining music-representation gap, so future work is maintenance-only unless a new route needs deeper music-generation implementation detail.
- `Python Natural Language Processing Cookbook, 2nd Edition.pdf` left this queue on 2026-05-20 after Chapter 3 was promoted into `[[02-books/python-nlp-cookbook/chapters/ch03-embedding-compatibility-rag-adapter-traces]]` with companion corroboration at `[[01-sources/official-open/python-nlp-cookbook-ch3-embedding-rag-cross-check]]`. The book's current chapter-level coverage now makes boundary policy, normalization policy, grammar-candidate extraction, embedding-profile compatibility, and candidate-level RAG trace semantics explicit, so remaining cookbook work is no longer a high-value unresolved gap by default.
- `Deep Learning by Ian Goodfellow, Yoshua Bengio, Aaron Courville.pdf` left this queue on 2026-05-20 after a focused Chapter 10 follow-through note plus official/open cross-check closed the remaining explicit-memory and attention-versus-recurrence gap. The targeted slice now covers addressable memory, differentiable addressing, content-based versus location-based access, seq2seq bottleneck relief, and the associated release-gate evidence.
- `Hands-On Generative AI with Transformers and Diffusion.pdf` left this queue on 2026-05-20 after Appendix A/B was promoted into a canon-ready chapter note plus official/open deployment cross-check. The remaining diffusion-serving and open-model media-serving deployment follow-through gap is now covered by explicit execution-surface, memory-fit, scheduler/batching, runtime-engine, and fallback evidence.
- `Applied-Machine-Learning-and-AI-for-Engineers.pdf` left this queue on 2026-05-19 after Chapter 8 deep learning foundations was promoted to a canon-ready chapter note and cross-check. The remaining book gaps are now narrow maintenance opportunities rather than a high-priority unresolved slice.

## Not In This Queue

Do not treat these as urgent unresolved gaps by default:

- chapter-sweep books already covered broadly (`AI Engineering`, `Build a Large Language Model From Scratch`, `Building Machine Learning Powered Applications`, `Designing Machine Learning Systems`, `Inference Engineering`, `LLM Engineers Handbook`, `Practical MLOps`, `Prompt Engineering for LLMs`);
- deferred/private/backlog-only material tracked in `deferred-local-corpus-queue`;
- books that should only be revisited when a specific route surface demands them.

## Orchestrator Routing Hint

When selecting specialists for a nightly pass:

- send local-book gap triage to a book-ingestion specialist;
- send corroboration to an official-doc / paper / lecture specialist;
- send Obsidian integration and Mermaid map work to a vault-integrator specialist;
- synthesize only after evidence from those lanes is reconciled.

## Related Notes

- [[05-ingestion-runs/local-book-coverage-granularity]]
- [[05-ingestion-runs/next-ingestion-queue]]
- [[05-ingestion-runs/deferred-local-corpus-queue]]
- [[05-ingestion-runs/deep-reading-coverage-ledger]]
