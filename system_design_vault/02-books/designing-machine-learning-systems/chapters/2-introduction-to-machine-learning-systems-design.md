---
type: book-chapter-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
source_title: "Designing Machine Learning Systems"
source_author: "Chip Huyen"
source_path: "/Users/saumyamehta/DS interview prep/books/Designing machine learning systems - an iterative process.pdf"
rights_status: user_provided_local
chapter: 2
chapter_title: "Introduction to Machine Learning Systems Design"
source_lines: "1635-2473"
---

# Chapter 2 - Introduction To Machine Learning Systems Design

## Core Thesis

ML systems design starts with objectives and requirements, not model choice. Business objectives must be translated into ML objectives, and the system must satisfy reliability, scalability, maintainability, and adaptability. Development is iterative because data, labels, objectives, and deployment conditions keep changing.

For Agent Studio, this chapter argues that agent workflows need explicit product goals, measurable proxy metrics, and a loop for revising data, prompts, retrieval, models, and product behavior.

## Business Objectives Before ML Metrics

The chapter warns that optimizing ML metrics without connecting them to business outcomes causes fragile or short-lived projects. A small accuracy lift is not useful unless it changes a product metric that matters.

Agent Studio should define product metrics before workflow metrics.

| Product goal | Candidate system metrics |
|---|---|
| faster content production | time from source intake to reviewed draft, reviewer edit distance |
| better source grounding | claim coverage, citation precision, retrieval recall, unsupported-claim rate |
| higher trust | reviewer approval rate, correction rate, source freshness, policy violations |
| lower operating cost | cost per approved artifact, cache hit rate, rerank/generation spend |
| safer autonomy | human-intervention rate, unsafe-action blocks, successful approval gates |

## Requirements

The chapter's four broad system requirements map directly to Agent Studio:

- Reliability: the system should continue doing the right thing under faults, bad inputs, model errors, and human mistakes.
- Scalability: the system should handle more traffic, more models, more sources, more workflows, and more artifacts.
- Maintainability: many contributors should be able to inspect, reproduce, debug, and improve the system.
- Adaptability: the system should detect changes and update without breaking production behavior.

## Agent Studio Implications

- Reliability requires semantic checks, not only uptime. A response can be syntactically valid and still be wrong.
- Scalability includes artifact management. More books, notes, embeddings, prompts, agents, and eval suites need automation and registries.
- Maintainability requires versioned prompts, source manifests, schemas, trace viewers, and runbooks.
- Adaptability requires retraining-style loops for retrieval indexes, prompts, eval datasets, and feedback policies.

## Iterative Process

The chapter describes ML development as a cycle: scope the project, engineer data, develop models, deploy, monitor, learn, and revisit business analysis. Errors discovered late can send the team back to labels, metrics, features, or even objectives.

Agent Studio should assume that every source and workflow will need repeated passes:

1. source intake and rights/provenance check;
2. extraction and validation;
3. chunking, metadata, and indexing;
4. retrieval and generation;
5. evaluation and reviewer feedback;
6. promotion to canonical notes or publishable artifacts;
7. monitoring and future refresh.

## Problem Framing

The chapter emphasizes that a real-world objective can be framed into different ML tasks, and the framing controls cost, data requirements, evaluation, and maintainability. Multi-objective problems should often be decomposed instead of compressed into one opaque objective function.

## Agent Studio Implications

- Decouple objectives instead of hiding them in one agent prompt.
- Keep separate scoring lanes for source relevance, factual grounding, writing quality, safety, latency, and cost.
- Use weighted combination at the policy layer where product owners can adjust priorities without retraining or rewriting every workflow.
- Keep task framing visible in agent cards: classify, retrieve, rerank, summarize, critique, transform, plan, or publish.

## Data Over Model Cleverness

The chapter closes with the data-versus-architecture debate and lands on a practical point: current ML success depends heavily on data quality and quantity, and bad or outdated data can hurt performance.

For Agent Studio, this reinforces the vault strategy. A rich, provenance-aware, well-structured source corpus is a production asset. Better prompts cannot compensate for missing, stale, untrusted, or poorly chunked source material.

## Design Commitments

- Require a product objective and eval objective for each major agent workflow.
- Treat source/data quality as a design dependency, not an ingestion detail.
- Use iterative promotion gates: raw source to extracted text to direct note to cross-check to canon.
- Decouple competing objectives into separate metrics and policy weights.
- Build maintenance paths for prompts, tools, retrieval indexes, evals, and notes.

## Follow-Ups

- Add Agent Studio metric taxonomy to the LLD.
- Define objective declarations for the primary agents.
- Create promotion gates that separate source-read notes from cross-checked canon.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
