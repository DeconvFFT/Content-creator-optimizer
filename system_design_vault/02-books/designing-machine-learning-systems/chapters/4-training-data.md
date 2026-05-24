---
type: book-chapter-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
source_title: "Designing Machine Learning Systems"
source_author: "Chip Huyen"
source_path: "/Users/saumyamehta/DS interview prep/books/Designing machine learning systems - an iterative process.pdf"
rights_status: user_provided_local
chapter: 4
chapter_title: "Training Data"
source_lines: "3741-5291"
---

# Chapter 4 - Training Data

## Reading Status

Direct source reading and official cross-check completed for chapter 4. This note is compact original synthesis for Agent Studio design use and does not include raw book text or long excerpts.

## Core Thesis

Training data is not a passive input. It is designed, sampled, labeled, audited, and maintained. The model inherits the selection bias, label definitions, feedback timing, privacy constraints, class balance, and synthetic-data assumptions embedded in the training data.

For Agent Studio, the same logic applies to notes, retrieved sources, examples, reviewer feedback, and generated artifacts. A content studio trained or tuned on weak source ledgers, biased examples, or unclear labels will operationalize those weaknesses.

## Sampling Shapes The System

The chapter distinguishes probability sampling from nonprobability sampling and shows why sampling is an engineering decision, not a clerical step. Simple random sampling is easy but can miss rare slices. Stratified sampling protects important groups. Weighted sampling can correct a known mismatch. Reservoir sampling supports streaming data where the full population is not known in advance. Importance sampling can emphasize examples that matter more to the downstream task.

Agent Studio implications:

- Treat source selection as sampling. The corpus should deliberately cover books, official docs, white papers, lectures, provider docs, engineering blogs, and internal product traces.
- Protect rare but high-impact slices: refusal failures, citation errors, stale-source issues, tool misuse, privacy-sensitive documents, multilingual sources, and long-context degradation.
- Record corpus sampling policy in source manifests so downstream users know whether a note set is broad, official-only, local-book-heavy, or skewed toward a provider.
- For ongoing ingestion, use streaming-friendly selection rules so new sources can enter review without rebuilding the whole planning process.

## Labeling Is A Product Function

Labels encode task definitions. The chapter stresses that labels can be expensive, subjective, privacy-sensitive, inconsistent, and slow. Label quality depends on clear instructions, annotator expertise, conflict resolution, and lineage.

Agent Studio implications:

- Define labels for every evaluation dataset: grounded, unsupported, partially supported, stale, unsafe, duplicate, low-value, off-brand, tool-error, and publish-ready should not be informal reviewer vibes.
- Preserve label provenance: who supplied the label, under which rubric, against which source snapshot, and after which model route.
- Reviewer edits are labels. The vault should treat accepted edits, rejected edits, and rewritten claims as structured feedback, not only as final prose.
- Ambiguous labels need adjudication workflows, especially for subjective quality such as tone, audience fit, source sufficiency, or claim importance.

## Natural Labels And Feedback Delay

The chapter treats user behavior as a possible source of natural labels, while emphasizing that feedback can be delayed and biased. Clicks, purchases, returns, and engagement can proxy usefulness, but they do not equal ground truth.

Agent Studio implications:

- Use approvals, edits, publish events, retrieval clicks, dwell time, and later corrections as feedback signals, but avoid treating any one signal as truth.
- Track feedback delay by workflow. A citation error may be found immediately by a reviewer; bad audience fit may appear only after publication metrics arrive.
- Separate immediate quality gates from delayed learning signals. Publishing should not wait for long-horizon metrics, but model-route promotion should use them.

## Weak, Semi-Supervised, Transfer, And Active Learning

The chapter frames weak supervision as a way to encode human heuristics into reusable labeling functions, with denoising and conflict handling. Semi-supervision expands from a smaller labeled set using structural assumptions. Transfer learning reuses pretrained representations. Active learning selects the most useful examples to label next.

Agent Studio implications:

- Encode editorial and source-quality heuristics as versioned rules: official source, primary source, stale page, missing date, citation mismatch, policy-sensitive claim, generated-source risk.
- Use weak supervision only as a bootstrap for triage, not as a final truth layer. Heuristic labels should carry confidence and conflict traces.
- Use active learning for review queues: send uncertain claims, low-confidence retrievals, disputed citations, and route disagreements to humans first.
- Treat foundation models as transfer-learning infrastructure, but evaluate them on Agent Studio-specific tasks before trusting them for notes, retrieval, or publishing.

## Class Imbalance

The chapter shows why aggregate metrics fail when important classes are rare. Accuracy can hide poor performance on minority or high-cost cases. Useful mitigations include choosing class-aware metrics, resampling after splitting, cost-sensitive learning, class-balanced loss, focal loss, and targeted data collection.

Agent Studio implications:

- Failure classes are imbalanced by default. Most generated content may be acceptable, while the dangerous cases are rare: fabricated citations, source inversion, privacy leaks, unsupported medical/legal/financial claims, and unsafe autonomous actions.
- Eval dashboards need precision, recall, F1, false positive/false negative rates, and slice-level metrics for high-cost failure types.
- Oversampling failure examples must happen after train/eval splitting to avoid leakage.
- Human review should focus on rare high-cost errors instead of randomly sampling only easy successful outputs.

## Data Augmentation And Synthetic Data

Data augmentation can improve robustness when transformations preserve labels. Perturbation tests and synthetic examples can expose brittle models, but generated data can also distort the task if assumptions are wrong.

Agent Studio implications:

- Use perturbations to test robustness: source formatting changes, citation order changes, noisy OCR, near-duplicate passages, prompt paraphrases, missing metadata, and adversarial instructions inside retrieved text.
- Synthetic examples are useful for eval coverage but should be marked synthetic and reviewed before influencing canonical behavior.
- Do not let generated notes become training truth without provenance. Synthetic notes can amplify mistakes because they look polished.

## Failure Modes

- Building an eval set from whatever sources are easiest to ingest.
- Treating reviewer approval, clicks, or edits as perfect labels.
- Ignoring feedback delay and optimizing for immediate engagement only.
- Letting weak supervision rules become invisible product policy.
- Reporting aggregate quality while rare failure slices remain weak.
- Resampling or augmenting before splitting and leaking examples across eval boundaries.
- Mixing synthetic and human-authored material without lineage.

## Agent Studio Design Commitments

- Every source, note, label, and feedback signal should carry provenance and version.
- Evaluation corpora should be intentionally sampled and slice-aware.
- Human review queues should prioritize uncertain and high-cost examples.
- Weak labels, heuristic labels, model labels, and human labels should be stored separately.
- Synthetic data should be allowed for stress tests and coverage, but never silently promoted to ground truth.

## Follow-Ups

- Define Agent Studio label taxonomy for citation, retrieval, writing, tool-use, and publication readiness.
- Add source-sampling policy fields to the corpus manifest.
- Build active-learning queues around uncertain claims and route disagreements.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
