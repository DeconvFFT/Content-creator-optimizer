---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_public
provenance_status: official_huggingface_hub_docs_direct_read
sources:
  - https://huggingface.co/docs/hub/en/model-cards
  - https://huggingface.co/docs/hub/en/datasets-cards
  - https://huggingface.co/docs/hub/en/models-gated
  - https://huggingface.co/docs/hub/en/datasets-gated
  - https://huggingface.co/docs/hub/data-studio
  - https://huggingface.co/docs/hub/en/security
  - https://huggingface.co/docs/hub/eval-results
  - https://huggingface.co/docs/hub/en/leaderboard-data-guide
---

# Hugging Face Hub Model And Dataset Governance

## Scope

Direct-read synthesis from official Hugging Face Hub docs for model cards, dataset cards, gated models, gated datasets, Data Studio, security, evaluation results, and leaderboard data. This note captures Agent Studio source/model registry implications. It stores no copied templates, raw card text, code blocks, or long excerpts.

Current-doc check on 2026-05-18: the official pages still present model and dataset cards as repo `README.md` plus metadata; model library inference now requires explicit care for newer repos; gated access remains per-user with shared contact fields and automatic/manual approval; Data Studio inspection may be partial for large non-Parquet datasets; evaluation results and leaderboard data are decentralized benchmark signals with community/verification state; Hub security covers access tokens, private repositories, resource groups, MFA, signed commits, malware scanning, pickle scanning, and secrets scanning.

## Core Pattern

Hugging Face Hub is not just a download site. For Agent Studio it is a model, dataset, benchmark, and access-control registry whose metadata can influence route selection, rights review, evaluation context, and release decisions.

The main design rule: a Hub repo should enter Agent Studio as a governed registry object, not as a bare model ID or dataset ID.

## Model Card Contract

Model cards combine human-readable descriptions with YAML metadata. The useful production fields are not limited to the model name. Agent Studio should capture:

- model repo ID and revision;
- library/runtime family;
- task or pipeline tag;
- license and custom license link when present;
- base model and base-model relation for fine-tunes, adapters, merges, and quantized variants;
- dataset IDs used for training when disclosed;
- intended use, unsupported use, limitations, bias/safety caveats, and ethical considerations;
- evaluation results and their sources;
- paper links and derived tags;
- version lineage through `new_version` metadata.

Model-card metadata supports discovery, filtering, dependency tracing, and compatibility review. It is not a safety guarantee. A card can be incomplete, stale, community-written, or disconnected from the actual artifact revision used in a route. Agent Studio should snapshot card metadata and tie it to a concrete revision/hash before using it in release evidence.

## Dataset Card Contract

Dataset cards are the dataset-side equivalent: repository README plus metadata that supports responsible use and discovery. For Agent Studio, dataset cards should feed source/dataset datasheets rather than be pasted into notes.

Capture:

- dataset repo ID and revision;
- license, language, size/scale hints, task categories, modality tags, and supported libraries;
- intended use and known limitations;
- construction or acquisition summary when present;
- bias, coverage, quality, privacy, and representativeness caveats;
- data-files configuration and split structure;
- linked paper tags or external references;
- gated/private status and access terms.

The card is a provenance signal, not a replacement for data inspection. A dataset can have a strong card but still fail route-specific quality, leakage, privacy, or rights checks.

## Access And Security Boundary

Gated models and gated datasets require users to share account/contact information with repo authors before file access. Authors can use automatic or manual approval, review pending/accepted/rejected requests, and manage access through UI or API. Access is granted to individual users rather than whole organizations in the base gating flow.

Agent Studio implications:

- Treat gated access as a rights and privacy event, not just authentication.
- Store who requested access, why, what fields were shared, approval mode, approval decision, and review expiry.
- Do not move gated model or dataset artifacts into production routes until intended-use, redistribution, retention, and team-access policy are reviewed.
- Keep token scope, private repo access, resource groups, malware/pickle/secrets scanning signals, and audit posture separate from model quality.

Security docs also make Hub artifacts part of the software supply chain. A route that loads remote models or datasets should record file type, scanner status where available, trust level, and whether executable or pickle-like formats are allowed.

## Data Studio And Dataset Inspection

Data Studio gives browser-level inspection over dataset rows, distributions, filters, string search, SQL queries, row links, and auto-converted Parquet files. It may show only a partial view for very large datasets depending on format.

Agent Studio should use this as an inspection surface, not as full validation. Store:

- viewer availability;
- partial-view or first-5GB caveat;
- inspected split/config/row anchors;
- distribution findings;
- missingness or class-balance findings;
- SQL/query inspection artifacts;
- data quality follow-up actions.

For local ingestion, this maps to the same pattern as Obsidian notes: row-level observations can inspire validation checks, but production trust requires reproducible data-quality contracts and leakage checks.

## Eval Results And Leaderboard Data

Hugging Face evaluation results are model-repo metadata, often stored in `.eval_results/` files, and benchmark datasets can aggregate model scores into leaderboards. Results may carry dataset ID, task ID, revision, metric value, date, source attribution, notes, community status, and verification tokens.

Agent Studio should treat these as benchmark context, not route approval:

- Benchmark scores need dataset/task/revision, evaluation framework, solver/scorer assumptions, source trace link, verification state, and community/author provenance.
- A community-provided or PR-visible score is useful signal, but it should not override route-specific evals.
- Leaderboard data should be stored separately from release gates. It can inform candidate selection, regression suspicion, and capacity estimates.
- Route promotion still depends on Agent Studio evals over the target workflow, source corpus, tools, latency budget, safety policy, and user-facing artifacts.

## Datastore Additions

| Object | Purpose | Key fields |
|---|---|---|
| `hf_hub_repo_record` | Canonical Hub model/dataset/space identity | `repo_id`, `repo_type`, `owner`, `visibility`, `gated_status`, `private_status`, `license`, `tags`, `library_or_modality`, `created_at`, `last_modified`, `revision_ref` |
| `hf_model_card_snapshot` | Versioned model-card metadata used by a route | `model_ref`, `repo_id`, `revision`, `card_hash`, `pipeline_tag`, `library_name`, `base_model_refs`, `base_model_relation`, `datasets_used`, `license`, `intended_use`, `limitations`, `eval_result_refs`, `new_version_ref`, `captured_at` |
| `hf_dataset_card_snapshot` | Versioned dataset-card metadata used by a route | `dataset_ref`, `repo_id`, `revision`, `card_hash`, `language`, `task_categories`, `modality_tags`, `license`, `size_or_config_refs`, `data_files_config_ref`, `bias_or_quality_caveats`, `paper_refs`, `captured_at` |
| `hub_access_review` | Gated/private artifact access decision | `access_review_id`, `repo_id`, `repo_type`, `requester_ref`, `shared_fields`, `approval_mode`, `approval_status`, `allowed_product_surfaces`, `redistribution_policy`, `review_expires_at` |
| `hub_security_scan_record` | Supply-chain scanner and format evidence | `scan_id`, `repo_id`, `revision`, `scanner_type`, `file_refs`, `finding_summary`, `executable_or_pickle_flag`, `trust_decision`, `reviewed_at` |
| `dataset_viewer_inspection` | Human or automated Data Studio inspection trace | `inspection_id`, `dataset_ref`, `revision`, `split_or_config`, `viewer_scope`, `partial_view_caveat`, `distribution_findings`, `row_anchor_refs`, `sql_or_filter_refs`, `follow_up_quality_checks` |
| `hub_eval_result_record` | External benchmark result context | `eval_result_id`, `model_ref`, `benchmark_dataset_id`, `task_id`, `dataset_revision`, `metric_name`, `metric_value`, `date`, `source_ref`, `community_or_author_status`, `verification_status`, `notes` |
| `leaderboard_snapshot` | Benchmark leaderboard snapshot for candidate selection | `leaderboard_id`, `benchmark_dataset_id`, `snapshot_time`, `entries_hash`, `ranking_fields`, `source_api`, `known_limitations`, `route_relevance_review` |
| `hf_hub_registry_release_gate` | Promotion gate for Hugging Face-sourced model, dataset, benchmark, or Space dependencies | `gate_id`, `route_id`, `candidate_release_id`, `hub_repo_ref`, `repo_type`, `repo_revision_ref`, `artifact_hash_refs`, `model_card_snapshot_ref`, `dataset_card_snapshot_ref`, `license_review_ref`, `custom_license_review_ref`, `base_model_lineage_refs`, `dataset_lineage_refs`, `gated_access_review_refs`, `private_repo_access_refs`, `shared_contact_fields`, `token_scope_ref`, `resource_group_ref`, `security_scan_refs`, `pickle_executable_policy_ref`, `secrets_scan_refs`, `signed_commit_refs`, `mfa_or_org_security_refs`, `data_studio_inspection_refs`, `partial_view_caveat`, `data_quality_followup_refs`, `hub_eval_result_refs`, `leaderboard_snapshot_refs`, `community_verification_status`, `route_specific_eval_refs`, `intended_use_surface_ref`, `unsupported_use_review_ref`, `redistribution_retention_policy_ref`, `fallback_model_or_dataset_ref`, `rollback_target_ref`, `decision`, `reviewed_at` |

## Hugging Face Hub Registry Release Gate

`hf_hub_registry_release_gate` is the promotion gate for any route that depends on a Hugging Face model, dataset, benchmark, or Space artifact. It must prove the local registry record is tied to the exact upstream revision and to local approval evidence before the dependency can affect production behavior.

Required evidence:

- `gate_id`, `route_id`, `candidate_release_id`, `hub_repo_ref`, `repo_type`, `repo_revision_ref`, and `artifact_hash_refs`;
- `model_card_snapshot_ref` or `dataset_card_snapshot_ref` as applicable;
- `license_review_ref` and `custom_license_review_ref` when the Hub card uses a custom or nonstandard license;
- `base_model_lineage_refs` for fine-tunes, adapters, merges, and quantized models, plus `dataset_lineage_refs` when training data is disclosed or reused;
- `gated_access_review_refs`, `private_repo_access_refs`, `shared_contact_fields`, approval mode/status, review expiry, and allowed product surfaces for gated/private repos;
- `token_scope_ref`, `resource_group_ref`, `security_scan_refs`, `pickle_executable_policy_ref`, `secrets_scan_refs`, `signed_commit_refs`, and `mfa_or_org_security_refs`;
- `data_studio_inspection_refs`, `partial_view_caveat`, and `data_quality_followup_refs` for datasets inspected through Data Studio;
- `hub_eval_result_refs`, `leaderboard_snapshot_refs`, `community_verification_status`, and `route_specific_eval_refs`;
- `intended_use_surface_ref`, `unsupported_use_review_ref`, `redistribution_retention_policy_ref`, `fallback_model_or_dataset_ref`, `rollback_target_ref`, `decision`, and `reviewed_at`.

Do not promote a Hugging Face-sourced model or dataset route when any of the following are true:

- model or dataset repo revision is not pinned;
- license or custom license link is missing from the route record;
- gated/private access was used without access-review evidence;
- model card lacks intended-use/limitation review for the product surface;
- base-model, adapter, merge, or quantization lineage is unknown for a model that affects safety, latency, or quality;
- dataset card is used as rights proof without independent acquisition/usage review;
- Data Studio inspection is partial but treated as whole-dataset validation;
- leaderboard scores are used as production approval without route-specific evals;
- community evaluation results are not distinguished from verified or author-published results;
- remote artifacts have unresolved malware/pickle/secrets or executable-format concerns.

Product rule: Hugging Face metadata seeds local model cards, dataset/source datasheets, benchmark context, and route records. It never substitutes for local source-rights review, artifact hashes, route-specific evals, security review, and an explicit release decision.

## Agent Studio Decision

Treat Hugging Face Hub records as structured registry inputs for model, dataset, benchmark, and access governance. Hub metadata should seed local model cards, source/dataset datasheets, route cards, eval context, and security reviews, but final production approval remains local: route-specific evals, source rights, artifact hashes, access decisions, and release gates.
