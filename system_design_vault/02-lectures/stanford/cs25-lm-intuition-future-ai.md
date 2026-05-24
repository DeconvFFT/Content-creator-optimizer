---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS25 Transformers United"
lecture_title: "Intuition on LMs, Shaping the Future of AI"
speaker: "Jason Wei and Hyung Won Chung, OpenAI"
source_status: official_public_video_pointer
updated: 2026-05-18
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://web.stanford.edu/class/cs25/recordings/
  - https://www.youtube.com/playlist?list=PLoROMvodv4rNiJRchCzutFw5ItR_Z27CM
  - https://arxiv.org/abs/2201.11903
  - https://arxiv.org/abs/2206.07682
  - https://arxiv.org/abs/2210.11416
related:
  - "[[../../03-patterns/transformer-systems/cs25-transformer-systems-canon]]"
  - "[[../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# CS25 - LM Intuition And Future AI

## Reading Status

Canon-ready source synthesis from the official Stanford CS25 recordings page entry for "Intuition on LMs, Shaping the Future of AI" by Jason Wei and Hyung Won Chung, rechecked on 2026-05-18, plus primary/open papers on chain-of-thought prompting, emergent abilities, and scaling instruction-finetuned language models. The CS25 recordings page exposes the lecture as a public YouTube pointer, but this note does not claim a full video-watch pass, timestamp-level coverage, or transcript ingestion.

## Core Pattern

Language-model capability is not one smooth product feature. The same base next-token training substrate can surface different behavior depending on model scale, instruction tuning, reasoning exemplars, task mixture, evaluation prompt, and benchmark slice. That makes Agent Studio route design a measurement problem before it is an automation problem.

The practical lesson is to avoid saying "the model can reason" or "the model follows instructions" as a global property. Agent Studio needs route-local capability records: what task family, what prompt or instruction recipe, what model size/family, what examples, what verifier, what failure slices, and what cost.

## Reasoning As Elicited Behavior

Chain-of-thought prompting shows that intermediate reasoning-format examples can unlock better arithmetic, symbolic, and commonsense performance in sufficiently capable language models. For Agent Studio, the key design move is not to store hidden reasoning as truth. The useful object is a route-level reasoning policy:

- when the route may spend extra tokens on decomposition;
- whether reasoning is private, summarized, or externally auditable;
- which verifier or judge checks the final answer;
- which failure cases trigger tool use, retrieval, or human review;
- how cost and latency increase when reasoning mode is enabled.

This supports a `reasoning_mode_release_gate`: routes that use decomposition, scratchpad-like prompting, candidate generation, or verifier loops need their own evals and budget records.

## Emergence And Capability Forecasting

Emergent-ability framing is a warning against extrapolating from small-model behavior alone. A capability that appears absent in one model class or scale can appear under a larger or differently trained model. That does not make the route safe; it makes route evaluation more important.

Agent Studio should treat capability forecasts as provisional until measured on the exact route:

- same model/provider or self-hosted artifact;
- same context assembly;
- same tool surface and source memory;
- same prompt/instruction style;
- same output format;
- same latency/cost budget.

This also cuts the other way: a capability seen in a paper, demo, or generic benchmark is not proof that the Agent Studio route can perform it under production constraints.

## Instruction Tuning And Task Mixtures

Scaling instruction finetuning across task count, model size, and chain-of-thought data shows that usability comes from a recipe, not from a base model alone. For Agent Studio, route behavior is similarly shaped by instruction libraries, examples, feedback datasets, reviewer rubrics, and eval tasks.

The datastore should preserve the route's task mixture and instruction provenance. If a route improves general helpfulness but regresses citation quality, abstention, safety, or source diversity, that is a failed release even if broad instruction-following metrics improve.

## Datastore Requirements

Add or strengthen:

| Object | Purpose |
|---|---|
| `capability_slice_record` | Task family, model/provider, prompt recipe, examples, tools, source memory, eval set, and measured pass/fail behavior for a capability claim. |
| `reasoning_mode_policy` | Route policy for decomposition, hidden or visible reasoning artifacts, verifier use, token budget, latency budget, and fallback. |
| `instruction_recipe_record` | Instruction-tuning or prompt-instruction source, task mixture, examples, safety/grounding clauses, owner, and version. |
| `emergence_caveat_record` | Warning that a capability claim may depend on scale, training recipe, prompt format, metric, or thresholding and cannot be generalized blindly. |
| `reasoning_mode_release_gate` | Promotion gate proving route-specific reasoning evals, verifier checks, budget impact, failure slices, fallback, rollback, and human review. |

## Agent Studio Design Implications

- Store capability at route-slice level, not model-brand level.
- Treat reasoning prompts, instruction recipes, and eval prompts as versioned source artifacts.
- Use chain-of-thought-style methods as controlled route policies with verifier and budget evidence, not as a blanket quality upgrade.
- Preserve benchmark and prompt details because metric thresholds can create misleading capability cliffs.
- Instruction-following gains must be checked against groundedness, citation behavior, abstention, safety, and cost.
- New model releases should trigger capability-slice refreshes before routes inherit stronger claims.

## Failure Modes

- Assuming a capability transfers from a paper benchmark to the production route.
- Treating generated reasoning text as proof instead of checking final answer support.
- Improving broad helpfulness while silently degrading source discipline.
- Adding chain-of-thought or candidate search without latency, cost, and verifier gates.
- Using small-model test results to rule out or guarantee larger-model route behavior.

## Related Official Video Sources

This public Stanford Online video pointer is listed from the official CS25 recordings page and tracked in [[../../05-ingestion-runs/stanford-public-video-ingestion-status]]. It is a navigation source only until a direct full-watch pass is completed; no raw captions, transcripts, comments, or long excerpts are stored.

| Video | URL | Status |
|---|---|---|
| Stanford CS25: V4 I Jason Wei & Hyung Won Chung of OpenAI | https://www.youtube.com/watch?v=3gb-ZkVRemQ | candidate; not watched in full |
