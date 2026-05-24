---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Building Machine Learning Powered Applications"
authors: "Emmanuel Ameisen"
chapter: "6"
chapter_title: "Debug Your ML Problems"
source_path: "/Users/saumyamehta/DS interview prep/books/building-machine-learning-powered-applications-going-from-idea-to-product.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# Building ML Powered Applications - Chapter 6: Debug Your ML Problems

## Source Reading Scope

Direct-read extraction span: `/tmp/building_ml_powered_applications_text.txt` lines 4626-5463.

This note is original synthesis only. It does not preserve raw source text.

## Core Takeaways

ML debugging must be progressive. First validate that one example flows correctly through data loading, cleaning, formatting, features, model input, and model output. Then validate that tests encode those assumptions. Only after the wiring is trusted should the team reason about training performance and generalization.

The chapter distinguishes three problem classes: pipeline wiring errors, inability to fit training data, and inability to generalize. Each class points to different fixes: visualization/tests, model capacity or optimization work, and data representation/split/dataset redesign.

Testing ML code means checking ingestion, processing, output shape, expected ranges, and stable assumptions. Visual validation remains important because a model can produce numerically plausible nonsense.

When generalization fails, the recommended remedies start with data and representation before model complexity: better labels, better features, augmentation, balanced splits, and reframing the task if the signal is not present.

## Agent Studio Design Implications

- Add one-example trace tooling for every source-to-output path.
- Test extraction, chunking, metadata, embeddings, reranking inputs, claim-verification outputs, and feedback writes separately.
- Separate wiring failures from retrieval quality failures and model reasoning failures in ledgers.
- Keep visual/manual review loops for generated notes and claim decisions, especially after parser or chunker changes.
- Prefer data/representation fixes over larger models when retrieval or generation fails systematically.

## Failure Modes To Guard Against

- Treating plausible output as evidence that the pipeline is correct.
- Debugging model behavior before validating the input and transformation path.
- Expanding model complexity when labels, splits, or representation are the real issue.
- Missing silent failures because only end-to-end tests exist.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
