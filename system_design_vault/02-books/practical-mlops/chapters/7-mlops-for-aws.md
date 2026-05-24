---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Practical MLOps"
authors: "Noah Gift; Alfredo Deza"
chapter: "7"
chapter_title: "MLOps for AWS"
source_path: "/Users/saumyamehta/DS interview prep/books/Practical MLOps_ Operationalizing Machine Learning Models.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# Practical MLOps - Chapter 7: MLOps for AWS

## Source Reading Scope

Direct-read extraction span: `/tmp/practical_mlops_text.txt` lines 7152-8935.

This note is original synthesis only. It does not preserve raw source text.

## Core Takeaways

The AWS chapter is less valuable as a frozen service catalog and more valuable as a decision framework. It presents a ladder of abstraction: high-level AI APIs for quick wins, serverless functions for event handling, CaaS/PaaS for focused web services, and SageMaker-style platforms for larger teams and more complex lifecycle needs.

The chapter repeatedly returns to source-of-truth discipline. GitHub or another source repository should contain the application logic, model artifacts or artifact references, build instructions, container configuration, infrastructure definitions, and CI/CD recipes.

Serverless functions are useful because they map naturally to small units of ML work: respond to object upload, call a managed AI API, run a lightweight prediction, trigger a downstream pipeline, or orchestrate steps through a state machine.

Containers are a portability layer across AWS services. Once a prediction service or CLI is containerized, it can target Lambda container images, App Runner, Elastic Beanstalk, Fargate, EKS, or other runtimes.

The practitioner interviews reinforce that ML is software engineering: traceability, versioning, testing, automation, documentation, canary/blue-green deployment, monitoring, scaling, security, and business understanding are not optional.

## Agent Studio Design Implications

- Use high-level provider APIs when the capability is not a differentiator, such as commodity OCR, translation, entity extraction, or moderation-like checks.
- Use serverless functions for narrow ingestion events: new source detected, official-doc URL changed, extraction completed, OCR requested, or evaluation batch scheduled.
- Use containers for reusable Agent Studio services: source validators, extractors, embedding workers, rerank APIs, evaluator runners, and note-promotion services.
- Keep source repositories as the production truth for prompts, tool schemas, evaluator definitions, deployment recipes, and infrastructure code.
- Separate quick-win services from full lifecycle platforms; do not force every workflow into a heavy MLOps platform if a serverless or CaaS path gives better iteration.
- Apply least privilege, encryption, audit trails, and quality gates to development and test workflows, not only production.

## Portable AWS Patterns

| AWS Pattern | Agent Studio Equivalent |
|---|---|
| Comprehend/Rekognition-style AI APIs | managed source enrichment when custom modeling is not needed |
| Lambda and Step Functions | ingestion events and lightweight agent pipeline orchestration |
| App Runner/Fargate | containerized microservices with minimal platform burden |
| SageMaker | team-scale lifecycle management for training, registry, deployment, and monitoring |
| CloudWatch/logging | traces for extraction, retrieval, tool calls, and evaluator runs |

## Failure Modes To Guard Against

- Starting with the most complex cloud service before the workflow needs it.
- Treating API demos as production without authentication, monitoring, and rollback.
- Spreading model, prompt, infrastructure, and deployment truth across untracked consoles.
- Building custom services when mature provider APIs solve the problem well enough.
- Ignoring product KPIs and user retention signals while optimizing technical metrics.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
