---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS336 Language Modeling from Scratch"
source_status: official_public
updated: 2026-05-21
scope:
  - "2026 Lecture 13 - Data I"
  - "2026 Lecture 14 - Data II"
  - "2026 Lecture 16 - Post-training / RLVR"
  - "2025 Lecture 13 - Data"
  - "2025 Lecture 14 - Data"
  - "2025 Lecture 15 - RLHF Alignment"
  - "2025 Lecture 16 - Reinforcement Learning from Verifiable Rewards"
  - "2025 Lecture 17 - Alignment RL systems/mechanics"
  - "2026 Lecture 15 - Mid/post-training SFT/RLHF/DPO"
  - "2026 current course schedule and Assignment 5 availability check through May 21, 2026"
sources:
  - https://cs336.stanford.edu/
  - https://cs336.stanford.edu/lectures/?trace=lecture_13
  - https://cs336.stanford.edu/lectures/?trace=lecture_14
  - https://raw.githubusercontent.com/stanford-cs336/lectures/main/lecture_13.py
  - https://raw.githubusercontent.com/stanford-cs336/lectures/main/lecture_14.py
  - https://raw.githubusercontent.com/stanford-cs336/lectures/main/lecture_15.pdf
  - https://github.com/stanford-cs336/lectures/blob/main/lecture_16.pdf
  - https://cs336.stanford.edu/spring2025/index.html
  - https://www.youtube.com/playlist?list=PLoROMvodv4rOY23Y0BoGoBGgQ1zmU_MT_
  - https://github.com/stanford-cs336/assignment5-alignment
  - https://raw.githubusercontent.com/stanford-cs336/assignment5-alignment/main/cs336_spring2026_assignment5_alignment.pdf
  - https://raw.githubusercontent.com/stanford-cs336/assignment5-alignment/main/cs336_alignment/drgrpo_grader.py
  - https://github.com/huggingface/Math-Verify
  - https://arxiv.org/abs/2206.14858
  - https://raw.githubusercontent.com/stanford-cs336/spring2025-lectures/main/lecture_13.py
  - https://raw.githubusercontent.com/stanford-cs336/spring2025-lectures/main/lecture_14.py
  - https://github.com/stanford-cs336/spring2025-lectures/blob/61eddac004df975466cff0329b615f2d24230069/nonexecutable/2025%20Lecture%2015%20-%20RLHF%20Alignment.pdf
  - https://github.com/stanford-cs336/spring2025-lectures/blob/e94e33f433985e57036b25215dff2a4292e67a4f/nonexecutable/2025%20Lecture%2016%20-%20RLVR.pdf
  - https://raw.githubusercontent.com/stanford-cs336/spring2025-lectures/main/lecture_17.py
---

# CS336 - Data And Alignment

## Reading Status

Canon-ready direct read of the official CS336 course pages and official lecture source files for data sources, transformation, filtering/deduplication, data mixing, post-training data, SFT/RLHF, DPO, RLVR, and alignment RL systems/mechanics. The 2026 Lecture 13 and Lecture 14 links were read from the official current course trace/source pages and rechecked on 2026-05-18. The official 2026 course page was rechecked again on 2026-05-18 and now links Lecture 15, "Mid/post-training," as a public PDF. That PDF was downloaded to `/private/tmp` from the official `stanford-cs336/lectures` repository for local text extraction and read for original synthesis. The official course page was rechecked again on 2026-05-20 and visibly linked Lecture 16, `lecture_16.pdf`, for `Post-training - RLVR [Tatsu]`; that PDF was also downloaded to `/private/tmp`, text-extracted locally, and read for original synthesis. A live 2026-05-21 recheck confirmed that Lecture 16 remains the visible official anchor and that the current course page does **not** visibly expose a public Lecture 17 material link; the Lecture 17 row is present only as schedule text, and hidden or commented candidates do not count as current-source availability. This pass still does not claim a current-2026 Lecture 17 direct-read synthesis; the substantive refresh below stays grounded in the visible Lecture 16 + public Assignment 5 surface. The 2025 Lecture 15 and Lecture 16 official PDFs were retained as archive corroboration. No raw slide text is stored in the vault.

This note is original synthesis only and does not include raw lecture text or long excerpts.

## Why This Matters

CS336's data and alignment lectures are directly useful for Agent Studio because the product is a knowledge and agent workflow system. Its quality will depend less on one clever prompt and more on the data pipeline: source choice, provenance, filtering, deduplication, licensing, privacy, feedback, synthetic data, and reward/eval definitions.

The alignment material adds the operational warning: once a system optimizes against rewards, feedback, or automatic graders, the reward definition becomes product infrastructure. If Agent Studio measures the wrong thing, its agents will learn to produce fluent artifacts that satisfy shallow metrics while losing grounding, source diversity, rights discipline, or editorial usefulness.

## Lecture 13 - Data Sources And Training Stages

The lecture frames data as the major differentiator in language models. Model architecture and training details may be disclosed, but training data is often obscure because it is commercially valuable and legally sensitive.

Useful mental model:

- live services produce raw material;
- crawls, API dumps, or snapshots capture raw data;
- conversion, filtering, deduplication, and transformation produce usable text;
- aggregated datasets combine sources for pretraining, mid-training, and post-training.

Agent Studio implications:

- Treat every source as a lifecycle object, not a file path. Track original source, acquisition route, rights status, extraction method, conversion loss, cleaning policy, dedupe policy, and downstream use.
- Separate source notes by training/use stage analogs: foundational references, task-specific playbooks, production implementation docs, evaluation cases, and feedback-derived examples.
- Do not let generated notes become indistinguishable from primary materials. The lecture's source-chain framing supports the vault policy: primary source, extracted artifact, chunk, synthesis note, and generated answer must stay separate.

## Data Provenance And Legal/Ethical Risk

The data lecture spends real attention on copyright, licenses, shadow libraries, public-domain materials, permissive code, and privacy. This is not a side concern; it determines which data can safely enter a production system.

Agent Studio implications:

- Keep the existing no-shadow-library rule as a datastore invariant.
- Source inventory should preserve license/provenance even when a local file is user-provided.
- For code and documentation corpora, prefer permissive or official sources and store license metadata where available.
- For user/private materials, synthesize compact notes and design implications; avoid raw text reuse and large excerpts.
- When source status is unclear, mark it as `needs_user_rights_confirmation` or local-user material rather than silently promoting it to official/open.

## Data Quality Is Heuristic And Empirical

The lecture's survey of BERT, GPT-2/WebText, Common Crawl, C4, The Pile, LLaMA-style data, Dolma, DCLM, and Nemotron-CC shows that no universal cleaning recipe wins everywhere. Dataset builders repeatedly mix manual heuristics, classifiers, language filters, deduplication, quality models, toxicity filters, domain-specific rules, and synthetic data.

Agent Studio implications:

- Do not hard-code one chunking or filtering policy for all corpora.
- Create source-type handlers for books, official docs, white papers, lectures, code docs, social posts, eval traces, and feedback.
- Store per-corpus filtering decisions so retrieval failures can be traced back to what was removed, transformed, or downweighted.
- Add "dataset card" fields to ingestion manifests: intended use, excluded content, known bias, freshness, provenance, and evaluation coverage.

## Lecture 14 - Filtering Mechanics

The second data lecture turns source selection into algorithms: n-gram language models, fastText-style classifiers, importance resampling, language identification, quality filtering, toxicity filtering, Bloom filters, MinHash, and locality-sensitive hashing.

Core pattern:

- define target data;
- score raw data for similarity, quality, language, toxicity, or domain;
- filter, resample, or deduplicate at corpus scale;
- validate with downstream behavior, not only apparent cleanliness.

Agent Studio implications:

- Use simple fast filters first for large corpora: file extension, source type, rights status, language, extraction quality, duplication, and document length.
- Use model-based or judge-based filters only where the value justifies cost and bias risk.
- Keep rejected-source and rejected-chunk counts in manifests. A clean corpus without rejection evidence is not debuggable.
- For local books and official docs, near-duplicate detection should prevent double-ingesting duplicate PDFs, mirrored docs, and generated-note copies.

## Deduplication And Memorization

Deduplication is both an efficiency and safety tool. It reduces repeated tokens, lowers memorization risk, and prevents the system from over-weighting duplicated content.

Agent Studio implications:

- Deduplicate at multiple levels: file hash, extraction hash, normalized document hash, chunk hash, near-duplicate chunk signature, and URL canonical form.
- Do not deduplicate away provenance. If two sources contain the same passage, preserve that multiple sources agreed, while storing one canonical chunk body.
- Duplicate-hit count can be useful as an authority signal, but it should not blindly dominate retrieval ranking.
- Generated notes should be excluded from primary-source dedupe pools so derivative synthesis does not overwrite source evidence.

## 2026 Data Lecture Refresh - Transformation, Mixing, And Synthetic Data

The current 2026 Lecture 13 keeps the data-provenance lesson sharp: source acquisition is not just "the web." It is a chain from live services to crawls, dumps, or repositories, then through conversion, filtering, deduplication, and mixing. The lecture explicitly calls out technical restrictions, terms of service, copyright, licensing, robots policies, rate limits, private/authenticated surfaces, shadow libraries, and privacy as separate constraints. That supports the vault rule that official/source provenance, local-user material, private material, and blocked sources are different states.

The current 2026 Lecture 14 adds three Agent Studio-relevant details beyond the earlier baseline:

- Transformation is lossy. HTML, PDFs, code repositories, tables, images, and layout-heavy artifacts do not become clean text for free; extraction choices change downstream quality.
- Data mixing is an experiment, not a constant. A source mixture can look good at small scale and fail at larger scale because scarce high-quality sources get repeated too many times. Small experiments should simulate large-run constraints instead of overfitting to a cheap pilot.
- Post-training data starts with environments and tasks, then uses teacher responses, filtering, and sometimes executable or non-executable agent trajectories. Teacher strength, source size, environment realism, and filtering details are all part of the dataset, not metadata to ignore.

Agent Studio implications:

- Add `extraction_transform_record` before chunking. It should record source format, adapter, text-loss risks, table/image handling, boilerplate stripping, OCR/layout status, and extraction-quality signals.
- Treat source mixtures as versioned route inputs. A retrieval or training dataset should record source-family weights, caps, epoching/reuse limits, pilot-eval results, and the product slice it is optimized for.
- Distinguish synthetic tasks, semi-synthetic environment tasks, real user/reviewer tasks, and model-generated responses. They can all be useful, but they carry different leakage, realism, and teacher-bias risks.
- For code or tool-agent datasets, record whether the environment was actually executable, approximated, or non-executable. Non-executable trajectories may teach useful behavior, but they are weaker evidence for tool correctness.
- Do not use answer filtering alone as proof of data quality. Preserve rejected examples, filtering policy, teacher model, prompt/task source, execution availability, and reviewer approval.

## Lecture 15 - SFT, RLHF, And DPO

The first alignment lecture separates imitation from optimization. SFT copies a reference behavior distribution; RLHF optimizes a reward that may be cheaper to verify than to demonstrate. For Agent Studio, this maps directly onto reviewer workflows: it is often easier for a domain reviewer to say which note, caption, retrieval answer, or storyboard is better than to author the perfect one.

The lecture also warns that instruction data is not one thing. Examples vary by style, length, citation behavior, factual complexity, scale, and safety policy. Preference evaluation is especially sensitive to style and length. A route can win a preference comparison because it is longer, more assertive, or more polished while being less grounded.

Agent Studio implications:

- Keep SFT data separate from preference data. Demonstrations teach "do this"; preference pairs teach "choose this over that."
- Do not fine-tune on tail facts as a substitute for retrieval. Factual local notes and official docs belong in source memory; tuning should shape behavior, format, refusal, or reasoning style only after evals show it is appropriate.
- Store style and length metadata on preference pairs so the system can detect when users, reviewers, or model judges are rewarding verbosity instead of correctness.
- Treat safety examples as high-leverage but regression-prone: a small number of examples can shift behavior, but over-refusal must be measured separately.
- Mark the source of feedback: expert reviewer, crowdworker, user, model judge, self-training loop, automatic test, or production analytics. These signals are not equivalent.
- Preserve annotator or judge provenance because demographic, expertise, model-family, and instruction differences can change the learned behavior.

The DPO portion matters operationally because it makes pairwise preference optimization accessible without a separate reward model and on-policy rollout loop. That lowers implementation cost, but it does not remove the need for high-quality pairs, held-out evals, length/style controls, and regression checks.

Agent Studio design rule: DPO-style tuning should be treated as a route-change proposal, not as a background cleanup job. It needs a baseline route, candidate route, preference dataset, blocked tradeoffs, eval gates, rollback plan, and serving-cost estimate.

## 2026 Lecture 15 - Mid/Post-Training

The current 2026 Lecture 15 makes the post-training boundary more concrete for Agent Studio. Pretraining gives broad language-model capability; post-training is the control layer that tries to make the model follow instructions, use tools, follow safety policy, and optimize for preferred outputs. The lecture also makes the evidence situation explicit: public details about modern post-training recipes are much thinner than older RLHF and open-source release material, so production systems need stronger local measurement rather than copying vague recipes.

The SFT part reinforces three design rules:

- Instruction datasets differ by style, length, citation behavior, factual complexity, tool-use traces, scale, and safety content. Treating them as one undifferentiated "instruction data" bucket is a schema bug.
- Preference evaluation is vulnerable to style and length effects. A longer or more confident answer can win comparisons while being less grounded.
- Fine-tuning on rare factual knowledge can be the wrong storage mechanism. For Agent Studio, freshness-sensitive facts, book notes, official docs, and citations should stay in retrieval/source memory unless a route-change review proves that model adaptation is safer and better.

The lecture's midtraining/two-phase training discussion matters for source-derived data. Mixing instruction data into a pretraining-style phase can scale behavior learning, but it also raises catastrophic-forgetting, source-mixture, and reuse-cap questions. Agent Studio should therefore record whether behavior examples are used as few-shot context, retrieval examples, prompt policy, SFT data, midtraining mixture, or preference data. Those are different interventions with different rollback and rights requirements.

The RLHF part adds a data-quality warning. Pairwise feedback can come from crowdworkers, experts, model judges, self-training loops, or production users, but those signals are not interchangeable. Annotator demographics, expertise, compensation, AI-assistance, verification effort, style preferences, and length bias can all change the learned route behavior.

Agent Studio implications:

- `preference_pair` should include response length, style tags, citation behavior, source-grounding score, annotator class, reviewer expertise, AI-assistance flag where known, and verification effort.
- `feedback_origin_record` should separate user corrections, expert review, crowd labels, model-judge comparisons, automatic verifiers, and passive analytics.
- `alignment_dataset_record` should distinguish SFT demonstrations, behavior/style examples, safety examples, tool-use traces, preference pairs, rejected candidates, and verifier-labeled examples.
- `midtraining_mixture_record` should be required before any source-derived examples are mixed into broad adaptation data. It needs source-family weights, caps, reuse/epoching limits, rights policy, scale-transfer caveat, and rollback target.
- `preference_bias_audit` should measure length effects, style effects, annotator/source skew, model-judge agreement, and hard factuality slices before a preference dataset can steer a production route.

For Agent Studio, the usable rule is conservative: use SFT for stable behavior formats and narrow tool/citation habits; use retrieval for changing knowledge; use pairwise preference only after bias audits; use DPO/PPO-style optimization only through a route-change gate with held-out grounding, safety, style, and cost regressions.

Use `[[../../01-sources/official-open/cs336-lecture15-mid-post-training-cross-check]]` as the supporting release-contract companion note for hidden-variable control, midtraining governance, reference-policy retention, and post-training artifact/eval requirements.

![[assets/cs336-lecture15-post-training-release-contract.svg]]

## Lecture 16 - RLVR And Reasoning RL

The second alignment lecture shifts from preference rewards to verifiable rewards. The main motivation is not simply that some tasks have checks; it is that broad RLHF-style reward optimization can overfit weak proxies, so RL should be pushed toward domains where correctness is narrower and more externally auditable.

The lecture's concrete verifier examples are close to what Agent Studio would actually care about: math answer equivalence, code tests, JSON validity, citation validity, tool success, policy compliance, and format constraints. The operating rule is therefore strict: RLVR is most appropriate when verification is easier and more reliable than demonstration.

The lecture contrasts PPO, DPO, and GRPO-style approaches in a way that matters operationally:

- PPO is the baseline online RL recipe: generate rollouts, score them, keep KL control to a reference policy, estimate advantages, and update with a clipped objective.
- In language-model practice, PPO is expensive because the route is effectively a bandit with dense token actions but reward mostly at the end, so implementations lean heavily on reward shaping, KL stabilization, and a separate value model that consumes memory and tuning effort.
- DPO avoids online rollouts, but it inherits pair quality, reference-policy assumptions, and style/length-bias risk from the preference data.
- GRPO is introduced as the practical simplification: remove the value function, sample a rollout group for the same prompt, normalize rewards within the group, and apply a PPO-like update with KL control.

The lecture is also explicit about GRPO caveats, and those details should not be lost:

- group standard-deviation normalization is convenient, but it is not a neutral unbiased-baseline trick in the classic policy-gradient sense;
- group normalization can distort difficulty weighting across prompts;
- length normalization and objective choice can create a real bias toward longer reasoning traces;
- apparent "reasoning gains" can therefore partly reflect objective shape rather than a cleanly discovered new reasoning mechanism.

The case studies make verifier design more concrete than a generic RL overview:

- R1-zero uses a small verifier stack: answer accuracy plus required output-format tags.
- R1 adds SFT initialization, language-consistency reward, and later-stage non-verifiable reward components.
- Kimi K1.5 filters for genuinely hard tasks by excluding trivial multiple-choice/true-false settings and selecting problems the model still fails under best-of-8 sampling; it also uses generated tests for code and answer-equivalence style checking for math.
- Qwen 3 reinforces the low-data, high-filtering recipe: keep only tasks that really need reasoning, drop validation-near samples, manually filter lucky/non-reasoning chains, and then run GRPO on a compact curated set.

The lecture also sharpens the relationship between RLVR and test-time selection. Best-of-n, pass@k, self-consistency, rejection sampling, and expert-iteration style learning are all adjacent tools. The practical distinction is that selection improves what is already sampled, while RL aims to change the future sampling policy itself. RL becomes easier to justify when positive-only selection is not enough and a trustworthy verifier can shape the policy toward better future outputs.

The official Lecture 16 artifact also implies a stage-composition lesson that matters for product design: reasoning RL is usually not the final broad post-training state. It is better treated as a capability-building stage inside a larger stack. A model may get a reasoning-specific boost from verifier-backed RL, then later go through broader SFT, safety, or preference-alignment follow-through that changes the deployed behavior and can partially trade away some STEM sharpness for broader usability.

That means the real release artifact is not just `used_rlvr=true`; it is the ordered pipeline and its handoff boundaries:

- base model and starting capability surface;
- reasoning bootstrap choices such as SFT seed data or prompt-family setup;
- RLVR objective, verifier scope, rollout-group setup, normalization mode, clipping mode, and KL/reference control;
- later broad-alignment stages that can reshape style, language behavior, safety behavior, or general helpfulness;
- held-out retention checks proving which reasoning gains survived the downstream broadening steps.

For Agent Studio, this is a strong warning against evaluating a reasoning-RL stage in isolation. A verifier-backed gain only matters if the final route still preserves the intended math/coding/citation/tool behavior after the later broad-alignment layers are applied.

![[assets/cs336-lecture16-stage-composition.svg]]

Agent Studio implications:

- Use RLVR only for narrow, checkable route behavior: valid JSON, source citation resolves, cited claim is supported, tool call succeeds, generated file passes validation, moderation policy holds, or benchmark answer matches.
- Keep verifier-backed rewards separate from semi-verifiable reward-model signals and broad heuristic/editorial judgments.
- Version rollout-group size, reward components, normalization policy, length policy, KL/reference policy, and verifier version. Without those records, a training win is not reproducible or debuggable.
- Add explicit audits for normalization bias, difficulty skew, and length bias if GRPO-style optimization or reranking is ever used.
- Keep pass@k / best-of-n, rejection sampling / positive-only reinforcement, and online RLVR as separate levers in eval and route-review documents.
- Track reward overoptimization. More reward can mean worse product behavior after a point, especially when the reward misses grounding, originality, safety, or user usefulness.
- Treat long reasoning traces with care. Distilled traces can be useful supervision artifacts, but Agent Studio should store answer/verifier evidence and not depend on exposing or persisting hidden reasoning text.

## Alignment - Reward Definition And Optimization Risk

The official 2025 alignment material covers SFT, RLHF, DPO, RL from verifiable rewards, and RL systems. Lecture 17's source file focuses on language-model RL mechanics: state as prompt plus generated tokens, actions as next-token choices, rewards over completed responses, policy-gradient updates, baselines/advantages, GRPO-style group baselines, KL regularization, and the extra systems complexity of RL.

Agent Studio implications:

- Treat reviewer feedback, eval scores, citation checks, tool success, and user ratings as reward signals only after schema design and review.
- Separate verifiable rewards from preference rewards. Citation-validity, JSON validity, and tool success can be deterministic; editorial taste and usefulness often need rubrics or human review.
- Use baselines and slices when comparing workflows. A score of 9 on an easy source is not better than 2 on a hard source without normalizing by task difficulty.
- Add KL-style policy thinking at the product level: optimization should improve the target behavior without destroying existing capabilities such as grounding, safety, tone, source diversity, and rights discipline.
- Reward hacking risk is real. If the metric rewards "more citations," the agent may cite irrelevant sources; if it rewards "short answers," it may omit necessary caveats.

## Alignment Systems Implications

RL and preference optimization are not just algorithms; they create new serving and data workflows. The system must generate candidate responses, compute rewards, compare old and new policies, store rollouts, run evals, and monitor regressions.

Operational hardening from the latest official/open cross-check:

- PPO in language-model RL behaves more like a bandit-style end-of-trajectory optimization loop than a dense-control setting, so rollout generation and verifier latency can dominate wall-clock cost.
- GRPO removes the value model, but not the release burden: grouped sampling, normalization mode, length policy, KL/reference control, and verifier scope still decide what behavior gets reinforced.
- Runtime placement choices matter. Separating generation, reward, reference, and update services can improve throughput, but it also creates trace-consistency and regression-debugging obligations.
- Outcome-only reward is often too weak for brittle reasoning tasks; the run record should state whether the verifier checks only final answers, intermediate steps, citations/tool traces, or a mixture.
- Grouped rollouts per prompt are a mechanics choice with product consequences, not just a trainer convenience. They define the within-task baseline that later normalization and clipping build on.
- Frozen old/reference policy snapshots are part of the release contract because ratio clipping and KL control are only meaningful if the comparison policies are versioned and synchronized explicitly.
- Keep the old rollout snapshot and the frozen reference snapshot separate. The old rollout policy answers "which policy actually generated these sampled responses for ratio/clipping purposes?" while the reference policy answers "which drift anchor, if any, is KL measured against?"
- Reward decomposition should stay visible. Correctness, citation validity, tool success, formatting, and verbosity controls should be logged as separate reward components before they are combined into a scalar.
- Prompt family is part of the runtime contract. The current public Assignment 5 surface exposes `question_only`, `r1_zero`, and few-shot variants, so rollout behavior can change before the optimizer even runs.
- Clipping mode belongs in the release record. Token-level PPO/GRPO clipping and sequence-level clipping stabilize different failure modes and should not be flattened into a generic "used RL" label.
- Weight-sync topology matters when generation and updates run on separate services. If rollout workers lag the learner or reference snapshot, reward improvements can be measurement noise rather than true policy gains.
- The public Assignment 5 helper surface sharpens this from a generic warning into a concrete contract: pause the generator, sync learner weights into the vLLM service, clear prefix-cache state, then resume the next rollout epoch. Generator freshness is therefore a provenance field, not just an implementation detail.
- Group identity should survive the whole loop. Because prompts and ground truths are repeated by `group_size`, the real accounting unit is `(prompt_id, group_index, sample_index, sync_epoch)` rather than a flat sample list.
- The learner itself is a third policy identity. In practice the system tracks the currently updated learner, the old rollout snapshot used for clipped ratios, and the frozen reference policy used for KL control; collapsing those into one generic baseline hides real failure modes.
- Off-policy ratios only mean what they claim if `old_log_probs` and `response_mask` came from the same rollout boundary. A stale old-logprob tensor or a mask that leaks prompt/padding tokens can change apparent clipping or loss behavior without any real policy improvement.
- Microbatch accumulation is part of the RL contract, not just memory plumbing. The public Assignment 5 train-step surface makes it explicit that a large rollout batch may need to be split across learner microbatches, but the accumulated gradient still has to preserve the full-batch objective under the chosen sequence-versus-constant normalization policy.

Use `[[../../01-sources/official-open/cs336-assignment5-learner-generator-weight-sync-cross-check]]` as the supporting companion note for learner/generator boundaries, rollout-sync epochs, cache-reset obligations, stale-rollout handling, and microbatch-equivalence governance.

![[assets/cs336-assignment5-learner-generator-weight-sync.svg]]

Agent Studio implications:

- Before using feedback to tune prompts, rerankers, policies, or models, store the full trace and source context behind that feedback.
- Feedback-derived datasets should have provenance: user/reviewer, workflow version, model route, source IDs, correction type, severity, and approval status.
- Promotion from feedback should follow the same artifact lifecycle as model routes and retrieval indexes: candidate, eval, shadow, canary, production, rollback.
- Do not optimize agent behavior directly from raw popularity or engagement; route through reviewed, task-specific labels.
- RLVR-style routes add an inference/training loop: generate multiple candidates, verify them, normalize or rank rewards, update a candidate route, and then re-run product evals. That loop needs capacity estimates because rollout generation can be the expensive part.
- Treat KL drift, length penalties, and reward-shaping policy as explicit release parameters rather than hidden trainer defaults.
- Length-control and style-control policies are part of alignment infrastructure. They should be explicit records, not hidden prompt preferences.
- Use `[[../../01-sources/official-open/cs336-alignment-rl-systems-runtime-cross-check]]` for runtime/governance hardening and `[[../../01-sources/official-open/cs336-lecture17-rl-systems-mechanics-cross-check]]` for policy-gradient, grouped-rollout, and frozen-reference mechanics while current 2026 Lecture 17 materials remain unpublished.

![[assets/cs336-lecture16-rollout-runtime-contract.svg]]

## Spring 2026 Assignment 5 - Reasoning RL Operationalization

The public CS336 Assignment 5 surface is now useful corroboration for how Stanford expects reasoning RL to be implemented in practice. It turns Lecture 16's verifier-first framing into a concrete training contract built around a small public model, GSM8K-style math tasks, rollout generation, answer verification, and explicit algorithm variants.

High-value operational details from the public artifact:

- Prompt family is part of the RL recipe, not a cosmetic choice. The public surface distinguishes `question_only`, `r1_zero`, and a three-shot GSM8K-style prompt, so prompt structure changes rollout behavior and exploration.
- Decode and stop policy complete that same rollout contract. The public Assignment 5 surface fixes baseline-style sampling at `temperature = 1.0`, `top_p = 1.0`, and a 512-token generation ceiling, while `r1_zero` additionally uses `</answer>` as an explicit stop string with stop-text retention. Those settings shape which trajectories are sampled and which parser/verifier path is even reachable before any optimizer step runs.
- Reward instrumentation is separated from the optimization target. Format reward can be logged independently, while correctness remains the actual target instead of silently blending parser compliance into task reward.
- Prompt family, parser, and stop policy are one coupled reward-surface bundle. `r1_zero` and `r1_zero_three_shot` require `<think> ... </think> <answer> ... </answer>` structure, bind that structure to the tag-aware `r1_zero_reward_fn`, and pair it with an `</answer>` stop string whose text is retained in output; `question_only` switches to `question_only_reward_fn` and must not inherit that stop contract. A prompt-family swap therefore changes parser hit rate, termination behavior, and effective reward surface even when the optimizer stays fixed.
- Stanford exposes a family of GRPO-style choices rather than one "default" algorithm: GRPO, Dr. GRPO, RFT, and MaxRL differ in baseline and normalization strategy.
- The normalizer is not just a numeric stabilizer. The public variant family makes it clear that baseline/normalizer choice implicitly changes prompt-difficulty weighting: no-normalizer variants keep weighting flatter, mean-style normalization leans harder into low-success prompts, and standard group-std normalization can over-amplify both very easy and very hard prompts relative to the middle.
- The self-including group-mean baseline also carries a finite-group shrinkage contract. The public Assignment 5 handout shows that subtracting the per-group mean preserves the expected policy gradient only up to a `(G-1)/G` factor, so `group_size` changes effective update scale rather than acting as batch metadata only.
- Off-policy control is not one knob. The public interface distinguishes no clipping, token-level PPO/GRPO-style clipping, and sequence-level clipping over response tokens, which means stability policy must be versioned explicitly.
- Clip telemetry inherits that same unit split. Token-level GRPO/PPO clipping makes `clip_fraction` a count of clipped response-token ratios, while GSPO-style sequence clipping can make the same field a count of clipped whole-response ratios. Similar clip fractions across those modes do not imply similar trust-region saturation.
- Off-policy correction is also a rollout-reuse budget. The handout explicitly frames multiple gradient steps per inference batch as off-policy training on stale data, and the public interface then exposes `none`, `noclip`, `grpo`, and `gspo` reuse policies. That means one expensive rollout batch can intentionally fund several learner steps before regeneration, but only if old-policy lineage and drift telemetry are still trustworthy.
- Token-level off-policy reweighting also changes the objective, not just the variance. The public Assignment 5 derivation shows that token-level PPO/GRPO-style reweighting evaluates token `t` under the current learner while leaving the prefix and suffix under the stale rollout policy, so the effective objective is a mixed old/new surrogate rather than true current-policy reward.
- GSPO makes that sequence-level option more specific than "clip once per response." The public Assignment 5 handout defines GSPO with a geometric-mean importance weight over response-token ratios, so the reweighting rule already induces a sequence-normalized objective. If a run instead wants constant-normalized loss, the exponent in the GSPO sequence ratio must change or the effective objective silently changes.
- Old-policy provenance is part of that same contract. The public adapter surface requires `old_log_probs` whenever off-policy reweighting is active, so the run record must preserve which rollout snapshot produced those old probabilities rather than treating them as anonymous cached tensors.
- Sequence-level control depends on a correct response boundary. The same public surface requires `response_mask` for sequence-level reweighting because the ratio is averaged over response tokens only; prompt tokens and padding are not harmless extras.
- Loss aggregation policy matters. Sequence-normalized and constant-normalized views are treated as real experimental choices rather than implementation trivia.
- Train-step equivalence across microbatches matters too. The public Assignment 5 train-step surface makes a large-batch / small-memory trade explicit: split the learner step across microbatches, but preserve the same effective objective by weighting losses correctly under the chosen normalization mode before one accumulated optimizer step.
- Rollout termination is part of the optimization contract. Stop strings, stop-text retention, max-token ceilings, finish reasons, and response masks define which tokens count as the response before sequence-level clipping or loss normalization is even applied.
- Verifier provenance belongs in the same contract. The public grader extracts a final answer, normalizes it with Minerva-lineage rules, and then runs semantic or symbolic equivalence checks, so `answer_reward` is truth-after-parser-plus-normalizer-plus-verifier rather than raw exact-match over model text.
- The optional DPO/safety supplement is adjacent to, but distinct from, the core verifier-backed reasoning-RL lane.

Agent Studio implications:

- Add a `reasoning_rl_recipe` record with prompt family, verifier scope, reward components, baseline mode, normalization mode, clipping mode, loss aggregation, and trace-length policy.
- Add a `rollout_sampling_contract` record with prompt family, decode parameters, max-token ceiling, stop strings, stop-text retention policy, finish/stop reason, and parser-entry expectations.
- Add `prompt_output_grammar`, `prompt_bound_reward_fn`, `prompt_stop_contract`, and `parse_termination_compatibility_check` so prompt swaps that change extractability or stop behavior are logged as reward-surface changes rather than mislabeled as pure optimizer deltas.
- Add a `rollout_reuse_contract` with `updates_per_inference_batch`, `rollout_reuse_budget`, `importance_reweighting_method`, `old_policy_snapshot`, `old_logprob_source`, and clip-saturation telemetry so sample-efficiency claims stay separate from true fresh-rollout gains.
- Add `clip_metric_unit`, `clip_bound_direction`, and `response_mask_scope` to that same contract so clip telemetry remains interpretable across token-level and sequence-level trust-region modes.
- Add an explicit `train_policy_snapshot` alongside `old_policy_snapshot` and `reference_policy_snapshot`; the actively updated learner is not interchangeable with either baseline object.
- Add a separate `rollout_termination_contract` record with response-mask policy and sequence-versus-constant loss normalization so termination lineage stays distinct from reward lineage.
- Add `importance_sampling_level`, `importance_reweighting_method`, `sequence_ratio_token_scope`, and `gspo_exponent_contract` so GSPO-style sequence-level runs do not get flattened into token-level GRPO records with the wrong implied length policy.
- Add `surrogate_objective_scope` or equivalent lineage showing whether the run used token-level mixed-trajectory reweighting or sequence-level response reweighting; otherwise the optimizer contract gets flattened into a misleading generic "off-policy GRPO" label.
- Add a `microbatch_update_contract` or `train_step_equivalence_contract` with `rollout_batch_size`, `gradient_accumulation_steps`, `microbatch_partition_rule`, `loss_normalization`, `normalization_constant`, `response_mask_scope`, `grad_clip_point`, and `max_grad_norm`.
- Add distinct `old_policy_snapshot` and `reference_policy_snapshot` fields; do not flatten clipping lineage and KL lineage into one generic baseline.
- Add `old_logprob_source`, `response_mask_policy`, and `masked_ratio_scope` so off-policy corrections can be audited against the exact response-token boundary used in training.
- Add `advantage_variant`, `group_baseline_policy`, `advantage_normalizer`, `advantage_eps`, `raw_reward_retention_ref`, and `per_group_reward_stats_ref` so grouped advantages remain interpretable after the run is over.
- Add `group_baseline_estimator`, `baseline_includes_self_sample`, and `group_size_shrinkage_factor` so grouped baselines keep their finite-group objective semantics instead of being flattened into a generic `baseline = mean` field.
- Record an `implicit_prompt_weighting_policy` or `difficulty_weighting_note` whenever grouped normalization is used; otherwise a denominator change can masquerade as a reasoning gain.
- Treat one `(prompt, group_size, sync_epoch, verifier_recipe)` bundle as the minimal auditable training unit when grouped normalization or grouped baselines are used.
- Add `verifier_recipe` fields for answer-extraction policy, normalization rule set, semantic-equivalence backend, and verifier-library version so reward shifts can be traced to verifier changes rather than mislabeled as policy gains.
- Separate `selection_only_improvement` from `policy_update_improvement` so pass@k or self-consistency gains are not mislabeled as training wins.
- Preserve the distinction between answer-only verifiers, process-aware verifiers, and mixed reward stacks.
- Keep safety/DPO follow-through as a separate alignment lane from narrow reasoning-RL optimization, even when both appear in the same course artifact.

Use `[[../../01-sources/official-open/cs336-assignment5-reasoning-rl-variants-cross-check]]` as the companion note for the assignment-level operational contract and rollout sampling semantics, `[[../../01-sources/official-open/cs336-assignment5-verifier-normalization-provenance-cross-check]]` for the parser / normalizer / semantic-verifier lineage that defines what correctness reward actually means, and `[[../../01-sources/official-open/cs336-alignment-rl-systems-runtime-cross-check]]` for the three-policy / prompt-group runtime contract.

![[assets/cs336-assignment5-rollout-sampling-contract.svg]]

![[assets/cs336-assignment5-advantage-scaling.svg]]

![[assets/cs336-assignment5-group-baseline-shrinkage.svg]]

![[assets/cs336-assignment5-token-level-surrogate-objective.svg]]

![[assets/cs336-assignment5-gspo-sequence-ratio-contract.svg]]

![[assets/cs336-assignment5-stale-rollout-reuse-contract.svg]]

![[assets/cs336-assignment5-clip-fraction-provenance.svg]]

![[assets/cs336-three-policy-prompt-group-contract.svg]]

![[assets/cs336-dual-policy-mask-lineage.svg]]

![[assets/cs336-assignment5-verifier-provenance.svg]]

![[assets/cs336-assignment5-microbatch-equivalence-contract.svg]]

![[assets/cs336-assignment5-prompt-parser-stop-bundle.svg]]

## 2026 Alignment Availability Check - 2026-05-20

The current CS336 Spring 2026 page now lists Assignment 5 as "Alignment and Reasoning RL." The assignment description says students apply supervised finetuning and reinforcement learning to train language models to reason when solving math problems, with an optional safety-alignment part involving DPO.

The 2026 schedule now lists:

- May 18: Mid/post-training (SFT/RLHF)
- May 20: Alignment - RL algorithms
- May 27: Alignment - RL systems

As of the latest 2026-05-20 late-evening check, the official schedule still links a public 2026 Lecture 15 PDF for mid/post-training and a visible public `lecture_16.pdf` link for `Post-training - RLVR [Tatsu]`. Both materials have now been read and integrated above. A same-day recheck corrected the temporary queue assumption that Lecture 17 had become visibly public: the live official course page currently shows no visible public Lecture 17 material link, so RL systems remains unpublished in current-2026 course materials. The public `assignment5-alignment` repository still points to the Spring 2025 assignment handout and optional safety/RLHF supplement, with a Spring 2025 archive release.

Agent Studio implication:

- Treat current 2026 Lecture 15 and Lecture 16 as direct-read public coverage for SFT, instruction-data variation, mid/post-training, PPO, DPO, RLVR, verifier design, and reward-overoptimization caveats.
- Keep current 2026 Lecture 17 pending until the official public materials are linked or otherwise republished on the visible course page.
- Continue using the 2025 archive as a valid official baseline for RL systems concepts and as corroboration for RLVR mechanics, but do not label RL systems coverage as current 2026 Lecture 17 yet.
- Use the new Lecture 17 mechanics cross-check to harden rollout-group, baseline, frozen-reference, and reward-component records without overstating current-source availability.
- When the remaining 2026 materials land, compare them against the LLM Engineers Handbook SFT/DPO notes and update the preference-pair/eval/reward schema if CS336 changes the recommended mechanics.

## Agent Studio Design Decisions

- Add `dataset_card` or equivalent fields to every corpus: source class, rights status, intended use, excluded material, filtering policy, dedupe policy, freshness, and known limitations.
- Add manifest counters for raw documents, extracted documents, rejected documents, chunks, rejected chunks, duplicates, near duplicates, embedding failures, and notes produced.
- Keep a separate `rejection_reason` taxonomy for provenance, rights, extraction failure, language, duplicate, quality, toxicity/safety, out-of-scope, and low source authority.
- Use hash-based exact dedupe immediately; add near-duplicate signatures before large-scale official-doc and web-source ingestion.
- Treat feedback as data with lineage, not as a direct command to mutate prompts or agent policies.
- Define reward/eval dimensions separately: groundedness, citation validity, completeness, relevance, tool correctness, safety, style, latency, and cost.
- Require reward/eval reports to include hard examples and failure slices, not only aggregate scores.
- Add explicit bias audits for preference data: length preference, style preference, annotator distribution, model-judge agreement, and factuality/source-grounding slices.
- Keep midtraining mixtures separate from SFT and preference datasets so route reviewers can see whether examples shaped broad behavior, final instruction following, or pairwise preferences.
- Version verifier-backed reward components separately: correctness/equivalence, format, citation validity, tool success, language consistency, and length controls.
- Add post-RL release checks for verified-capability regression, verbosity drift, and latency/cost drift from longer reasoning behavior.

## Release Gate Contract

`data_alignment_release_gate` is required before a source-filtering policy, source mixture, synthetic/post-training dataset, preference dataset, verifier reward, feedback-derived label set, prompt-policy update, reranker tuning run, fine-tuning run, or alignment recipe can change a production route, eval suite, retrieval index, or canon-backed architecture decision.

The gate rejects promotion unless the release record binds:

- source provenance, rights status, acquisition route, transformation/extraction loss risks, and blocked-source policy;
- source-filter policy with accepted/rejected counts, rejection reasons, false-positive/false-negative caveats, toxicity/safety/language/quality filters, exact and near-dedupe policy, and downstream validation evidence;
- source mixture experiment with family weights, caps, reuse/epoching limits, pilot-eval results, scale-transfer caveats, and selected product slice;
- post-training data provenance that separates demonstrations, behavior/style examples, safety examples, tool-use traces, preference pairs, rejected candidates, verifier-labeled examples, synthetic tasks, semi-synthetic environments, real reviewer/user tasks, model-generated responses, and executable versus non-executable trajectories;
- midtraining or two-phase-training mixture records with source-family weights, caps, reuse/epoching limits, scale-transfer caveats, rights policy, and rollback target;
- teacher, judge, verifier, reviewer, prompt/task-source, annotator class, AI-assistance flag where known, length/style, citation behavior, source-grounding score, verification effort, and approval metadata for examples that can affect behavior;
- preference-bias audits for length effects, style effects, annotator demographics or expertise skew, model-judge correlation limits, and hard factuality/source-grounding cases;
- reward specification with reward-type separation, verifier scope, known blind spots, normalization/length/KL policy where relevant, and reward-overoptimization checks;
- held-out evals for grounding, citation validity, source diversity, safety, tool correctness, style drift, latency, cost, and hard failure slices;
- decontamination/overlap checks across training, eval, retrieval, prompt, and feedback data;
- route-change record with baseline, candidate, rejected lighter interventions, capacity estimate, serving impact, fallback, rollback, incident feedback path, and human approval.

## Remaining Work

- Refresh current 2026 CS336 Lecture 17 after Stanford visibly republishes the current RL systems material on the official course page.

## Mental Model Image

![[./assets/cs336-lecture16-rlvr-verifier-loop.svg]]

## Related Official Video Sources

The current CS336 2026 alignment refresh is public-material driven, not video-driven. The Spring 2025 Stanford Online playlist remains a useful public navigation source for archive context, but this note does not claim watched-video, transcript, caption, comment, or timestamp-level coverage.

| Video source | URL | Relevant topics | Status |
|---|---|---|---|
| Stanford CS336 Language Modeling from Scratch public playlist | https://www.youtube.com/playlist?list=PLoROMvodv4rOY23Y0BoGoBGgQ1zmU_MT_ | data, filtering/deduplication, SFT/RLHF/RLVR alignment archive context | playlist candidate; individual videos not watched in full |
| CS336 Spring 2026 Lecture 16/17 videos | Official page currently exposes a public Lecture 16 PDF but no public video source and no visible Lecture 17 material link in current vault evidence | RL algorithms and RL systems | Lecture 16 direct-read from PDF; Lecture 17 remains blocked in current evidence; no watched-video claim |
