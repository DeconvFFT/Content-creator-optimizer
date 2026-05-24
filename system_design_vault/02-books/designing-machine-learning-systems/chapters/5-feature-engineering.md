---
type: book-chapter-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
source_title: "Designing Machine Learning Systems"
source_author: "Chip Huyen"
source_path: "/Users/saumyamehta/DS interview prep/books/Designing machine learning systems - an iterative process.pdf"
rights_status: user_provided_local
chapter: 5
chapter_title: "Feature Engineering"
source_lines: "5291-6347"
---

# Chapter 5 - Feature Engineering

## Reading Status

Direct source reading and official cross-check completed for chapter 5. This note is compact original synthesis for Agent Studio design use and does not include raw book text or long excerpts.

## Core Thesis

Feature engineering is the work of making raw data usable for models while preserving the information that matters and preventing leakage. Deep learning changes the shape of feature work, but it does not remove the need to understand missingness, scaling, categorical evolution, positional information, lineage, and generalization.

For Agent Studio, features are not only model inputs. They include source metadata, chunk attributes, retrieval scores, graph relationships, prompt context, user history, route configuration, and evaluation traces.

## Missing Values Are Signals

The chapter distinguishes missing values caused by chance from missing values caused by the data-generation process. Dropping or imputing values without understanding the cause can introduce bias or erase useful signal.

Agent Studio implications:

- Missing source metadata is itself metadata. Missing publication date, author, official-domain status, transcript availability, or extraction confidence should be explicit fields.
- Avoid silently filling missing provenance with plausible guesses. Unknown, inferred, and verified should be separate states.
- Retrieval and ranking should be allowed to use missingness as a signal, especially when source quality or recency matters.

## Scaling And Normalization

Scaling makes feature magnitudes comparable, but global statistics can leak information if computed before splitting. Production drift also makes stale statistics dangerous.

Agent Studio implications:

- Compute evaluation transforms from the training or calibration slice only, then apply them to validation/test slices.
- Keep retrieval/ranking score normalization versioned. Changing embedding model, reranker, chunker, or score scaling changes behavior.
- Monitor score distributions over time. If source mix or model provider changes, old thresholds for relevance, confidence, or citation sufficiency may stop meaning the same thing.

## Discretization, Encoding, And Hashing

The chapter covers turning continuous features into buckets and categorical features into usable encodings. Categorical values evolve in production, so systems need unknown handling, stable vocabularies, or hashing strategies.

Agent Studio implications:

- Important categories include source type, provider, domain, author, course, book, chapter, content license, workflow type, model route, audience, platform, and risk tier.
- Unknown categories must not crash ingestion or route selection. Use explicit unknown buckets where interpretability matters and hashing where cardinality is large.
- Version categorical mappings so a note generated under an old source taxonomy remains reproducible.

## Feature Crossing And Positional Features

Feature crossing captures interactions that individual features miss. Positional embeddings show that order and location can be features, especially for sequence models.

Agent Studio implications:

- Useful crosses include source type by topic, provider by workflow, audience by platform, retrieval score by source authority, chapter by concept, and error type by model route.
- Position matters in documents and agent traces. Chunk position, heading hierarchy, citation location, claim order, and tool-call order should be retained.
- Knowledge-graph traversal should preserve relationship type and traversal depth instead of flattening all context into undifferentiated text.

## Data Leakage

The chapter is especially strong on leakage. Leakage happens when information unavailable at inference sneaks into training or evaluation. Common causes include random splits of time-correlated data, scaling before splitting, imputing from the full dataset, duplicate leakage, group leakage, and leakage from the data-generation process.

Agent Studio implications:

- Split evals by source, time, workflow, and user where needed. Random claim-level splitting can leak the same article, chapter, or generated artifact into both train and test.
- Deduplicate and near-deduplicate before splitting source-derived examples.
- Do not tune prompts, retrieval filters, or rerankers on the final test set.
- Avoid evaluating a generator on notes it helped create unless the eval is explicitly about self-consistency, not generalization.
- Understand source-generation processes. A lecture transcript, book chapter, doc page, and generated summary have different leakage risks.

## Engineering Good Features

More features are not automatically better. Features can increase leakage, overfitting, memory cost, latency, and maintenance burden. Good features should matter to the model and generalize to unseen data.

Agent Studio implications:

- Keep feature definitions owned and discoverable. Retrieval, reranking, routing, eval, and publishing should not each invent incompatible definitions for authority, freshness, or confidence.
- Track feature importance for route decisions and eval judges. If a model over-relies on provider name, note length, or formatting artifacts, investigate.
- Prefer features with strong coverage and stable meaning across sources.
- Remove features that add latency or maintenance cost without improving Agent Studio task quality.

## Failure Modes

- Treating missing provenance as if it were verified provenance.
- Computing normalization or imputation statistics on evaluation data.
- Randomly splitting correlated source-derived examples.
- Letting duplicates cross eval boundaries.
- Adding features because they are available, not because they improve decisions.
- Ignoring feature coverage differences between local books, official docs, web pages, and videos.
- Using high-cardinality identifiers that memorize examples instead of generalizing.

## Agent Studio Design Commitments

- Maintain a feature registry for source, chunk, retrieval, graph, route, prompt, and eval features.
- Store train-only statistics and transformation versions with each eval run.
- Run leakage checks before promoting eval results.
- Keep source lineage and group identifiers available for splitting.
- Monitor feature coverage and distribution drift by source class and workflow.

## Follow-Ups

- Define feature schemas for source cards, chunks, retrieval candidates, graph nodes, and agent traces.
- Add leakage tests for duplicate source material and generated-note contamination.
- Add feature-coverage dashboards for official docs, books, lectures, and local files.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
