---
type: raw-source
project: agent-studio
status: captured
updated: 2026-05-17
source_title: Production agent system design canon
accessed: 2026-05-17
copyright_note: Metadata and paraphrased implementation observations only. Full book or article text is not stored.
derived_wiki:
  - [[../../wiki/concepts/production-agent-system-design-canon]]
  - [[../../00-system-design/HLD - Agent Studio]]
  - [[../../00-system-design/LLD - Agent Studio]]
---

# Raw Source - Production Agent System Design Canon

## Sources

- Designing Data-Intensive Applications, Martin Kleppmann: https://martin.kleppmann.com/2017/03/27/designing-data-intensive-applications.html
- Designing Machine Learning Systems, Chip Huyen/O'Reilly: https://www.oreilly.com/library/view/designing-machine-learning/9781098107956/
- Inference Engineering, Baseten: https://www.baseten.co/inference-engineering/
- Building effective agents, Anthropic: https://www.anthropic.com/engineering/building-effective-agents
- A practical guide to building agents, OpenAI: https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/
- OpenAI Realtime API docs: https://platform.openai.com/docs/guides/realtime/
- Google Developer's Guide to AI Agent Protocols: https://developers.googleblog.com/en/developers-guide-to-ai-agent-protocols/
- Google long-running ADK agents: https://developers.googleblog.com/en/build-long-running-ai-agents-that-pause-resume-and-never-lose-context-with-adk/
- AWS Well-Architected Machine Learning Lens: https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/machine-learning-lens.html
- Google Cloud AI/ML Reliability perspective: https://docs.cloud.google.com/architecture/framework/perspectives/ai-ml/reliability
- Uber Michelangelo ML platform: https://www.uber.com/ie/en/blog/michelangelo-machine-learning-platform/
- Metaflow, originally developed at Netflix: https://docs.metaflow.org/introduction/what-is-metaflow
- Max Mitcham, Obsidian three-layer memory architecture: https://maxmitcham.substack.com/p/how-to-build-an-ai-agent-operating

## Paraphrased Observations

- Data-intensive system design should explicitly optimize reliability, scalability, maintainability, consistency, fault tolerance, and operational simplicity.
- Production AI/ML systems need data quality checks, monitoring, feedback loops, evaluation, drift awareness, and lifecycle governance, not only model prompts.
- Inference engineering should start from product constraints: latency, cost, quality, modality, provider availability, streaming, batching, caching, and fallback policy.
- Effective agent systems should prefer explicit workflows and routing when the problem can be decomposed; autonomy should increase only when feedback loops, success criteria, and oversight are clear.
- Guardrails should be layered across input validation, tool/model permissions, privacy, content safety, provenance, and human approval gates.
- Realtime speech-to-speech should be handled by realtime providers; Gemma expert agents should handle reasoning, writing, critique, vision, synthesis, and multimodal analysis.
- A2A-style agent cards and standardized message schemas reduce custom integration code and make specialist delegation inspectable.
- Long-running agents need persistent sessions, checkpoints, memory, and resume gates so they pause and continue without relying on chat context.
- Large-scale AI/ML reliability guidance emphasizes modular, loosely coupled, observable, governed, scalable, and highly available systems.
- Platform examples such as Uber Michelangelo and Netflix/Metaflow point toward curated shared data/evidence layers, artifact provenance, workflow lifecycle management, and reusable infrastructure.
- Obsidian should remain a three-layer memory system: raw evidence, wiki synthesis, and generated outputs.

## Applied Design Implication

Agent Studio should be designed as a production system with durable data contracts, runtime ledgers, explicit specialist ownership, provider-backed smoke gates, retrieval quality evaluation, and Obsidian-first design memory. Generated HTML/JSON viewers explain the design but do not become the source of truth.
