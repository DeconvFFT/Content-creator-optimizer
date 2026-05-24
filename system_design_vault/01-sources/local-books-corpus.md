---
type: local-corpus-inventory
project: agent-studio-system-design
status: active
updated: 2026-05-19
local_folder: /Users/saumyamehta/DS interview prep/books
---

# Local Books Corpus

This folder is now in ingestion scope for Agent Studio system-design planning:

`/Users/saumyamehta/DS interview prep/books`

Current file-parity audit found 34 allowed local files and 34 manifest records. The local folder contains no disallowed file types after removing a transient macOS metadata file:

- 33 PDFs
- 1 DOCX
- 0 disallowed file types

The user confirmed these are clean official-source files. Treat the PDFs as user-provided local material unless a filename or PDF metadata explicitly indicates Anna's Archive, LibGen, Z-Library, EBooksWorld, or another shadow-library/export origin.

No current filename contains an explicit Anna's Archive, LibGen, Z-Library, or EBooksWorld marker. A lightweight PDF metadata pass also found no explicit shadow-library origin markers. Some files are clearly publisher PDFs, official/open PDFs, browser-saved official web PDFs, or user/private notes.

## Safe Notes Strategy

Allowed:

- compact original synthesis notes;
- chapter maps and reading queues;
- Agent Studio design implications;
- page references and short quotes only when necessary;
- cross-source comparison tables;
- source status summaries and extraction issue notes.

Avoid:

- raw book text dumps;
- long excerpts;
- copied tables, copied figures, or book-replacement summaries;
- storing full extracted PDF text in tracked vault files;
- browsing or downloading from Anna's Archive, LibGen, Z-Library, or similar sources.

## Priority Queue

| Priority | Local file | Relevance | Ingestion status | Rights/provenance status | Notes strategy |
|---:|---|---:|---|---|---|
| 1 | `AI Engineering.pdf` | critical | `canon_ready` | `user_provided_local` / `user_confirmed_official_clean` | Use as canonical AI Engineering copy; compact chapter synthesis and Agent Studio implications only. |
| 2 | `Inference Engineering.pdf` | critical | `canon_ready` | `user_provided_local` / `user_confirmed_official_clean` | Use for inference runtime, serving, latency budgets, hardware/runtime/tooling split, and reliability patterns. |
| 3 | `LLM Engineers Handbook.pdf` | critical | `canon_ready` | `user_provided_local` / `user_confirmed_official_clean` | Use for practical LLMOps, RAG system structure, deployment, monitoring, testing, and production handoff patterns. |
| 4 | `Designing machine learning systems - an iterative process.pdf` | critical | `canon_ready` | `user_provided_local` / `user_confirmed_official_clean` | Use for ML system framing, data/label pipelines, monitoring, drift, feedback loops, and eval discipline. |
| 5 | `Practical MLOps_ Operationalizing Machine Learning Models.pdf` | high | `canon_ready` | `user_provided_local` / `user_confirmed_official_clean` | Use for CI/CD, MLOps maturity, operational excellence, deployment, monitoring, and governance. |
| 6 | `building-machine-learning-powered-applications-going-from-idea-to-product.pdf` | high | `canon_ready` | `user_provided_local` / `user_confirmed_official_clean` | Use for product-to-ML shipping discipline, first pipeline, data acquisition, iteration, deployment, and monitoring. |
| 7 | `Build a Large Language Model (From Scratch).pdf` | high | `canon_ready` | `user_provided_local` / `user_confirmed_official_clean` | Use for tokenizer, transformer, training/inference, and implementation-intuition notes. |
| 8 | `Prompt Engineering for LLMs- The Art and Science of Building.pdf` | high | `canon_ready` | `user_provided_local` / `user_confirmed_official_clean` | Use for prompt programs, structured outputs, tool instructions, failure modes, and evalable workflows. |
| 9 | `ISLP_website.pdf` | medium | `canon_ready` | `official_or_open_local` / `user_confirmed_official_clean` | Canon-ready local-book validation slice for model accuracy, cross-validation, bootstrap, model-selection validation, split labeling, selection-versus-assessment separation, metric uncertainty, validation reuse, and selection-assessment release gates. |
| 10 | `Bishop-Pattern-Recognition-and-Machine-Learning-2006.pdf` | medium | `canon_ready` | `official_or_open_local` / `user_confirmed_official_clean` | Canon-ready local-book probabilistic decision slice for Bayesian uncertainty, expected-loss decisions, reject/abstain options, conditional independence, d-separation, graph-message traces, failure hypotheses, and uncertainty-decision release gates. |
| 11 | `Deep Learning by Ian Goodfellow, Yoshua Bengio, Aaron Courville.pdf` | medium | `canon_ready` | `official_or_open_local` / `user_confirmed_official_clean` | Canon-ready local-book capacity/optimization slice for numerical stability, capacity/generalization, validation reuse, regularization, practical methodology, sequence-memory limits, gradient clipping, neural language-model foundations, chapter-level regularization-policy coverage, and capacity-optimization release gates. |
| 12 | `Comprehensive Guide to Recommendation System Metri.pdf` | medium | `canon_ready` | `user_provided_local` / `user_confirmed_official_clean` | Canon-ready local-book ranking/eval slice for Precision/Recall@K, HitRate, MRR, MAP, NDCG, coverage, diversity, novelty, online feedback, adaptive-system metrics, and ranking-quality release gates. |
| 13 | `NeurIPS-2020-gradient-surgery-for-multi-task-learning-Paper.pdf` | out_of_scope | `exclude` | `open_paper_local` / `user_confirmed_official_clean` | Do not ingest for Agent Studio; out of scope per user. Keep only as local file-parity inventory. |

## Full File Classification

| Local file | Relevance | Ingestion status | Rights/provenance status | Safe use |
|---|---:|---|---|---|
| `0812_Machine-Learning-for-Absolute-Beginners.pdf` | low | `defer` | `user_provided_local` | Use only for beginner-facing explanations if needed; not system-design canon. |
| `AI Engineering.pdf` | critical | `canon_ready` | `user_provided_local` | Use as canonical AI Engineering copy; compact chapter synthesis and Agent Studio implications only. |
| `Applied-Machine-Learning-and-AI-for-Engineers.pdf` | medium | `canon_ready` | `user_provided_local` | Canon-ready local-book applied ML route slice. Direct-read synthesis now includes Chapter 14 deepening for managed AI service boundaries, OCR route choice, moderation semantics, container/privacy tradeoffs, provider drift, plus Chapter 4 deepening for sparse text vectorization contracts, Count/TF-IDF/Hashing tradeoffs, Naive Bayes versus Logistic Regression baselines, threshold semantics, and sklearn pipeline persistence. Store only original notes, not raw book text. |
| `Artificial Intelligence. A modern approach (Stuart Russell  Peter Norvig).pdf` | low_medium | `canon_ready` | `user_provided_local` | Canon-ready Agent Studio slice captured Chapter 2 task-environment and agent-architecture contracts, Chapter 4 complex-environment search, Chapter 5 adversarial-search/game-surface controls, Chapter 6 constraint-satisfaction route feasibility controls, Chapter 11 automated-planning action-schema and scheduling controls, Chapter 17 sequential decisions, Chapter 18 multiagent decisions, and agent-environment-planning release gates; keep to compact original notes only. |
| `Bishop-Pattern-Recognition-and-Machine-Learning-2006.pdf` | medium | `canon_ready` | `official_or_open_local` | Canon-ready local-book probabilistic decision slice for Bayesian uncertainty, expected-loss decisions, reject/abstain options, conditional independence, d-separation, graph-message traces, failure hypotheses, and uncertainty-decision release gates. |
| `Build a Large Language Model (From Scratch).pdf` | high | `canon_ready` | `user_provided_local` | Use for tokenizer, transformer, training/inference, and implementation-intuition notes. |
| `Chip Huyen - AI Engineering_ Building Applications with Foundation Models (2025, O'Reilly Media).pdf` | critical_duplicate | `avoid_double_ingestion` | `user_provided_local_duplicate` | Do not ingest separately unless needed to resolve differences from AI Engineering.pdf. |
| `Comprehensive Guide to Recommendation System Metri.pdf` | medium | `canon_ready` | `user_provided_local` | Canon-ready local-book ranking/eval slice for Precision/Recall@K, HitRate, MRR, MAP, NDCG, coverage, diversity, novelty, online feedback, adaptive-system metrics, and ranking-quality release gates. |
| `Data Scientist Interview Prep_V5.pdf` | low_private | `defer_private_notes` | `user_private_notes` | Do not treat as source canon unless user explicitly asks. |
| `Deep Learning by Ian Goodfellow, Yoshua Bengio, Aaron Courville.pdf` | medium | `canon_ready` | `official_or_open_local` | Canon-ready local-book capacity/optimization slice for numerical stability, capacity/generalization, validation reuse, regularization, practical methodology, sequence-memory limits, gradient clipping, neural language-model foundations, chapter-level regularization-policy coverage, and capacity-optimization release gates. |
| `Designing machine learning systems - an iterative process.pdf` | critical | `canon_ready` | `user_provided_local` | Use for ML system framing, data/label pipelines, monitoring, drift, feedback loops, and eval discipline. |
| `Gans-in-action-deep-learning-with-generative-adversarial-networks.pdf` | medium | `canon_ready` | `user_provided_local` | Canon-ready local-book GAN synthetic media control slice for GAN training dynamics, generator/discriminator eval, mode collapse, latent/conditioning controls, CycleGAN image translation, adversarial media cases, synthetic-data lineage, and the gan_synthetic_media_release_gate. No raw text or copied code stored. |
| `Generative-AI-and-LLMs-for-Dummies.pdf` | low_medium | `defer` | `user_provided_local` | Use for glossary/background only. |
| `Generative-Deep-Learning.pdf` | low_medium | `canon_ready` | `user_provided_local` | Canon-ready local-book generative model route slice. Direct-read synthesis captures generative model taxonomy, diffusion and latent-diffusion sampling controls, multimodal bridge patterns, world-model simulation risks, music/audio representations, originality checks, and the generative_model_route_release_gate; do not store raw book text or copied code. |
| `Hands-On Generative AI with Transformers and Diffusion.pdf` | medium | `canon_ready` | `user_provided_local` | Canon-ready local-book generative media pipeline slice. Direct-read synthesis now includes chapter-level deepening for Chapter 8 controllable image editing, Chapter 9 audio route contracts/evaluation, Chapter 10 video-generation governance / multimodal frontier, and Appendix A/B open-model serving runtime fit, covering diffusion controls, adaptation methods, audio route families, browser/local/server execution surfaces, scheduler and batching policy, runtime-engine choice, memory-fit/offload gates, provider video runtime implications, provenance/disclosure gates, multimodal bridge patterns, and generative-media release gates without storing raw book text or copied code. |
| `How to excel during an Amazon interview.docx` | low_private | `defer_private_notes` | `user_private_notes` | Not part of Agent Studio system-design canon unless explicitly requested. |
| `ISLP_website.pdf` | medium | `canon_ready` | `official_or_open_local` | Canon-ready local-book validation slice for model accuracy, cross-validation, bootstrap, model-selection validation, split labeling, selection-versus-assessment separation, metric uncertainty, validation reuse, and selection-assessment release gates. |
| `Inference Engineering.pdf` | critical | `canon_ready` | `user_provided_local` | Use for inference runtime, serving, latency budgets, hardware/runtime/tooling split, and reliability patterns. |
| `LLM Engineers Handbook.pdf` | critical | `canon_ready` | `user_provided_local` | Use for practical LLMOps, RAG system structure, deployment, monitoring, testing, and production handoff patterns. |
| `LLM Questions.pdf` | medium_backlog | `question_backlog_ready` | `user_private_notes` | Converted into an LLM concept coverage and eval/review backlog only; do not use as factual source canon or answer evidence. |
| `ML Machine Learning-A Probabilistic Perspective.pdf` | medium | `canon_ready` | `user_provided_local` | Canon-ready local-book adaptive-inference slice for probabilistic ML uncertainty, calibration, model evidence, online learning/regret, ranking exposure, graph authority, belief-state snapshots, candidate-diversity diagnostics, and adaptive-belief-state release gates. |
| `ML Math.pdf` | low_medium | `canon_ready` | `user_provided_local_official_free_pdf` | Canon-ready compact original synthesis only. Captures metric policy, representation transforms, optimization objectives, uncertainty models, validation splits, latent assignments, decision margins, and math_assumption_release_gate controls; do not store raw book text, proofs, formulas, or exercises. |
| `Machine.Learning.with.PyTorch.and.Scikit-Learn.Sebastian.Raschka.Packt.pdf` | medium | `canon_ready` | `user_provided_local` | Canon-ready local-book implementation route slice with Chapter 12 direct-read deepening for `Dataset`/`DataLoader` semantics, raw training loops, and inference-versus-resume checkpoint behavior, plus Chapter 13 deepening for Lightning trainer structure, split lineage, checkpoint-resume semantics, experiment logs, bounded reproducibility, and the implementation_route_release_gate. No raw text or copied code stored. |
| `NLP with Transformer models.pdf` | medium | `canon_ready` | `user_provided_local` | Canon-ready local-book transformer application route slice. Direct-read synthesis captures transformer task pipelines, tokenization/context assembly, QA/RAG pipeline separation, generated-text metric caveats, production optimization, few-label adaptation, training-from-scratch, scaling, efficient attention, multimodal/document implications, and the transformer_application_route_release_gate; do not store raw book text. |
| `NLPbook.pdf` | medium | `canon_ready` | `user_provided_local` | Chapters 14, 15, 16, 20, and 23 now have canon-ready chapter-level QA/IR/RAG, dialogue-systems, ASR/TTS, information-extraction, coreference, and entity-linking synthesis. Do not store raw book text. |
| `NeurIPS-2020-gradient-surgery-for-multi-task-learning-Paper.pdf` | out_of_scope | `exclude` | `open_paper_local` | Do not ingest for Agent Studio; out of scope per user. Keep only as local file-parity inventory. |
| `Practical MLOps_ Operationalizing Machine Learning Models.pdf` | high | `canon_ready` | `user_provided_local` | Use for CI/CD, MLOps maturity, operational excellence, deployment, monitoring, and governance. |
| `Probabilistic Machine Learning Advanced Topics.pdf` | medium | `canon_ready` | `user_provided_local` | Canon-ready local-book approximation and shift slice. Direct-read synthesis now includes Chapter 20 deepening for typed distribution-shift diagnosis, OOD detection and abstention policy, cross-distribution adaptation caveats, continual-learning retention tradeoffs, adversarial threat-model evidence, and the approximation_shift_release_gate; do not store raw book text or derivation dumps. |
| `Prompt Engineering for LLMs- The Art and Science of Building.pdf` | high | `canon_ready` | `user_provided_local` | Use for prompt programs, structured outputs, tool instructions, failure modes, and evalable workflows. |
| `Python Natural Language Processing Cookbook, 2nd Edition.pdf` | medium | `canon_ready` | `user_provided_local` | Canon-ready local-book NLP ingestion adapter slice for sentence/token boundaries, normalization, grammar extraction candidates, embeddings, RAG adapter surfaces, reproducible recipe runtime profiles, and the nlp_ingestion_adapter_release_gate. No raw text or copied code stored. |
| `building-machine-learning-powered-applications-going-from-idea-to-product.pdf` | high | `canon_ready` | `user_provided_local` | Use for product-to-ML shipping discipline, first pipeline, data acquisition, iteration, deployment, and monitoring. |
| `gen ai for dummies.pdf` | low_medium | `defer` | `user_provided_local` | Use for glossary/background only. |
| `machine_learning.pdf` | low_medium | `defer` | `user_provided_local` | Beginner ML primer by Vishal Maini and Samer Sabri; keep as background only unless a simple explainer is needed. Do not use as Agent Studio architecture canon. |
| `python-cheatsheets.pdf` | low | `defer` | `user_provided_local` | Utility reference only; not system-design canon. |

## Current Extraction Guardrails

- Extract table of contents, headings, and short snippets only when needed to build chapter maps.
- Prefer book-level synthesis and Agent Studio implications over detailed chapter paraphrase.
- Store extracted metadata and manifests, not raw text.
- If metadata later shows an explicit shadow-library origin, move that file to `blocked` status and use official/open alternatives.
