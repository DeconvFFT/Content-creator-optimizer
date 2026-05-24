---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS25 Transformers United"
lecture_title: "Aligning Open Language Models"
speaker: "Nathan Lambert"
source_status: official_public_video_pointer
updated: 2026-05-18
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://web.stanford.edu/class/cs25/recordings/
  - https://allenai.org/tulu
  - https://allenai.org/blog/tulu-3
  - https://allenai.org/blog/tulu-3-technical
  - https://arxiv.org/abs/2411.15124
  - https://arxiv.org/abs/2403.13787
  - https://arxiv.org/abs/2305.18290
  - https://arxiv.org/abs/2203.02155
  - https://arxiv.org/abs/2302.13971
related:
  - "[[../../03-patterns/alignment/preference-alignment-systems-canon]]"
  - "[[../../02-lectures/stanford/cs224r-preference-optimization-rlhf-dpo]]"
  - "[[../../02-lectures/stanford/cs336-data-and-alignment]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# CS25 - Aligning Open Language Models

## Reading Status

Canon-ready direct-read pass over the official Stanford CS25 recordings page entry for "Aligning Open Language Models" by Nathan Lambert, plus official/open primary materials around open post-training: Ai2 Tülu 3 pages, the Tülu 3 report page, RewardBench, DPO, InstructGPT/RLHF, and LLaMA. The CS25 recordings page was rechecked on 2026-05-18 and still exposes an official YouTube pointer for the lecture, but this note does not claim transcript-level video ingestion, does not download video, and does not store raw transcript text.

## Why This Matters

Agent Studio needs alignment as an operational system, not a vague quality label. Open-model post-training shows what must be tracked when a base model becomes a usable assistant: data curation, supervised tuning, preference data, reward or verifier signals, evaluation, decontamination, training code, model checkpoints, and negative results.

The practical design lesson is transparency. A route that changes behavior through preference optimization should make the recipe inspectable enough to answer:

- what data changed the behavior;
- which skills were targeted;
- which eval suite approved the change;
- what decontamination or leakage checks were run;
- what regressions or negative results were found;
- which artifacts are reusable, reproducible, and legally usable.

## Open Alignment Pipeline

The open post-training stack is best understood as a staged system:

1. choose or train a base model;
2. curate prompts and demonstrations for target skills;
3. run supervised instruction tuning;
4. collect or synthesize preference comparisons;
5. tune with DPO, RLHF, or verifier-driven methods;
6. run standardized and held-out evaluations;
7. publish model, data, code, eval, and decontamination evidence where rights allow.

For Agent Studio, the same sequence should exist at route scale. A route may not fine-tune a model, but it still post-trains its behavior through prompts, examples, retrieval policies, feedback, evaluators, and human review. Those artifacts need the same provenance discipline.

## Tülu 3 Signals

Ai2's Tülu 3 materials are valuable because they treat open post-training as a release package: models, data, training code, evaluation suite, decontamination tools, recipe, and documented findings. The key Agent Studio lesson is that "open weights" alone are not enough. Useful openness includes the recipe and measurements that explain how the behavior was produced.

Tülu 3's staged recipe also separates capabilities: knowledge, reasoning, math, coding, instruction following, chat, multilingual behavior, and safety. Agent Studio should similarly tag alignment datasets and evals by capability slice instead of treating one general preference score as proof of route quality.

## Preference And Reward Lessons

InstructGPT establishes the core RLHF pattern: demonstrations, ranked outputs, reward modeling, then policy optimization against human preference. DPO simplifies the pipeline by removing an explicit reward-model/RL loop, but it still depends on preference-pair quality and a reference-policy assumption. RewardBench adds the warning that reward models themselves need evaluation, especially on reasoning, safety, refusal, instruction-following, and out-of-distribution comparisons.

Agent Studio implications:

- treat reward models, judges, and preference-tuned routes as evaluated components;
- store chosen and rejected outputs, not just the winning answer;
- preserve the reason a preference was selected;
- separate verifiable rewards from broad human/editorial preferences;
- keep safety, grounding, and source-diversity regressions visible after any preference optimization.

## Open Model Routing

LLaMA-style open foundation models made the open alignment ecosystem possible, but a base model is not an assistant route. Post-training and deployment still decide behavior, cost, safety, and reliability. For Agent Studio, open model selection needs two ledgers:

- `base_model_record`: model family, license/rights, architecture, context length, pretraining disclosure, known capabilities, and deployment constraints;
- `post_training_recipe_record`: prompts/data, SFT, DPO/RLHF/RLVR, evals, decontamination, checkpoints, and negative-result notes.

Without both ledgers, "use an open model" is too underspecified for production.

## Datastore Requirements

Add or strengthen:

| Object | Purpose |
|---|---|
| `base_model_record` | Base open or closed model identity, license, architecture, context limits, training disclosure, route eligibility, and deployment constraints. |
| `post_training_recipe_record` | Staged behavior-change recipe: prompt curation, demonstrations, preference data, reward/verifier method, eval suite, decontamination, and artifacts. |
| `post_training_artifact_release` | Released model/data/code/eval/checkpoint/decontamination artifact with rights status, hash, owner, and reproducibility caveats. |
| `negative_result_record` | Attempted data, reward, tuning, or eval strategy that failed or regressed, with reason and future-avoidance notes. |
| `capability_slice_target` | Skill slice targeted by post-training or route optimization: reasoning, coding, math, safety, chat, multilingual, citation, tool use, or platform style. |
| `reward_model_eval_record` | Reward model or judge evaluation with benchmark slice, preference type, safety/refusal behavior, OOD caveats, and calibration status. |
| `decontamination_record` | Evidence that eval, training, prompt, and retrieval data overlap was checked and mitigated. |
| `open_model_post_training_release_gate` | Promotion gate proving that open-model or route-level post-training is reproducible, rights-aware, capability-sliced, evaluated, decontaminated, and reversible. |

## Release Gate Contract

`open_model_post_training_release_gate` is required before Agent Studio promotes an open model, adapter, prompt-policy route, reranker, judge, verifier, or route-level post-training recipe that claims improved assistant behavior from SFT, DPO/RLHF, RLVR, synthetic data, preference data, or open-recipe reuse.

The gate rejects promotion unless the release record binds:

- base model identity, license/terms, architecture class, context limit, training disclosure, deployment constraints, and route eligibility;
- post-training recipe stages for prompt/task curation, demonstrations, preference data, reward or verifier method, SFT/DPO/RLHF/RLVR settings, eval suite, artifacts, and negative results;
- released artifacts for model/checkpoint, data, code, eval implementation, decontamination tooling, and recipe documentation, with rights status, content hashes, owner, and reproducibility caveats;
- capability slice targets for reasoning, math, coding, instruction following, chat, multilingual behavior, safety, citation behavior, tool use, and Agent Studio style;
- reward-model, judge, and verifier evaluations with reasoning, safety/refusal, instruction-following, OOD, calibration, and benchmark-contamination caveats;
- decontamination checks across training data, preference data, evals, prompts, retrieval snapshots, and feedback-derived examples;
- behavior-regression evidence for grounding, citation accuracy, abstention, source diversity, safety, style/length drift, latency, and cost;
- rejected candidates, failed data mixes, failed methods, and negative results so future route work does not repeat known regressions;
- fallback route, rollback target, incident feedback path, and human approval.

## Agent Studio Design Implications

- Open models should enter the route registry with both base-model and post-training metadata.
- Route tuning should produce a recipe record even when the change is "only" prompts, examples, or reranker weights.
- Preference data must remain contrastive and source-aware; it should not become factual truth.
- Negative results should be kept because they prevent repeated failed alignment experiments.
- Eval suites for aligned routes should be capability-sliced and decontamination-aware.
- Model judges and reward models require their own eval and calibration records before they can gate releases.
- Open-model reuse is not production evidence unless the route stores both base-model metadata and post-training recipe/release evidence.

## Failure Modes

- Treating open weights as equivalent to open recipes.
- Using preference wins to overwrite source-grounded truth.
- Optimizing for general chat quality and silently regressing citation accuracy, abstention, or safety behavior.
- Reusing benchmark-contaminated examples as proof of route improvement.
- Publishing a tuned route without the rejected candidates and negative-result evidence that explain its behavior.

## Related Official Video Sources

This public Stanford Online video pointer is listed from the official CS25 recordings page and tracked in [[../../05-ingestion-runs/stanford-public-video-ingestion-status]]. It is a navigation source only until a direct full-watch pass is completed; no raw captions, transcripts, comments, or long excerpts are stored.

| Video | URL | Status |
|---|---|---|
| Stanford CS25: V4 I Aligning Open Language Models | https://www.youtube.com/watch?v=AdLgPmcrXwQ | candidate; not watched in full |
