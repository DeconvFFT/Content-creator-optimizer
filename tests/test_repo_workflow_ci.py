import argparse
import io
import json
import os
import re
from pathlib import Path
import subprocess
import tomllib

import yaml

from all_about_llms import cli as cli_module


ROOT = Path(__file__).resolve().parents[1]


def test_ci_uses_uv_lock_for_python_dependency_sync() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    jobs = workflow["jobs"]

    python_jobs = {
        name: job
        for name, job in jobs.items()
        if any(
            step.get("run", "").startswith("uv sync")
            for step in job.get("steps", [])
            if isinstance(step, dict)
        )
    }

    assert {"backend", "live-postgres"} <= set(python_jobs)
    for job_name, job in python_jobs.items():
        sync_steps = [
            step["run"]
            for step in job["steps"]
            if isinstance(step, dict)
            and step.get("name", "").startswith("Sync Python dependencies")
        ]
        assert sync_steps, f"{job_name} must sync Python dependencies explicitly"
        assert all(
            command.startswith("uv sync --locked ")
            for command in sync_steps
        ), f"{job_name} must install from the committed uv.lock"


def test_ci_checks_uv_lock_is_current_before_python_tests() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    jobs = workflow["jobs"]

    python_jobs = {
        name: job
        for name, job in jobs.items()
        if any(
            step.get("run", "").startswith("uv sync")
            for step in job.get("steps", [])
            if isinstance(step, dict)
        )
    }

    assert {"backend", "live-postgres"} <= set(python_jobs)
    for job_name, job in python_jobs.items():
        lock_check_steps = [
            step["run"]
            for step in job["steps"]
            if isinstance(step, dict)
            and step.get("name", "") == "Check uv.lock is current"
        ]
        assert lock_check_steps == ["uv lock --check"], (
            f"{job_name} must fail CI when pyproject.toml and uv.lock drift"
        )


def test_gitignore_excludes_local_scratch_course_checkouts() -> None:
    gitignore_lines = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert "/repo_check_temp/" in gitignore_lines

    root_scratch = subprocess.run(
        ["git", "check-ignore", "-q", "repo_check_temp/sentinel.txt"],
        cwd=ROOT,
        check=False,
    )
    assert root_scratch.returncode == 0, "root repo_check_temp/ must stay ignored"

    nested_scratch = subprocess.run(
        ["git", "check-ignore", "-q", "nested/repo_check_temp/sentinel.txt"],
        cwd=ROOT,
        check=False,
    )
    assert nested_scratch.returncode == 1, "nested repo_check_temp/ should not be ignored"


def test_uv_lock_is_tracked_and_not_ignored() -> None:
    gitignore_lines = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert "uv.lock" not in gitignore_lines

    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "uv.lock"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert tracked.returncode == 0, "uv.lock must remain tracked"

    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "uv.lock"],
        cwd=ROOT,
        check=False,
    )
    assert ignored.returncode == 1, "uv.lock must not be ignored"


def test_dev_extra_installs_livekit_sdk_for_stable_ci_voice_timing_tests() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    dev_dependencies = pyproject["project"]["optional-dependencies"]["dev"]

    assert any(
        dependency == "livekit" or dependency.startswith("livekit>=")
        for dependency in dev_dependencies
    ), (
        "CI runs tests/test_livekit_voice_timing_capture.py under the dev extra, "
        "so dev dependencies must install the livekit SDK"
    )


def test_agents_handoff_documents_pr_ci_and_proof_boundaries() -> None:
    agents_path = ROOT / "AGENTS.md"

    assert agents_path.exists(), "root AGENTS.md must capture repo operating rules"
    handoff = agents_path.read_text(encoding="utf-8")

    required_terms = [
        "uv.lock",
        "feature/",
        "fix_",
        "OpenRouter",
        "deepseek/deepseek-v4-flash",
        "LiveKit",
        "Kokoro",
        "Hugging Face",
        "Gemma4",
        "MLX",
        "provider-backed-live-voice-proof",
        "external-publication-proof",
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
        "social_media_optimiser",
        "system_design_vault",
        "Do not commit secrets",
        "Do not restart",
    ]

    for term in required_terms:
        assert term in handoff

    assert re.search(r"\buv[.]log\b", handoff) is None
    assert "local command-log artifacts" in handoff.lower()


def test_next_app_readme_keeps_openrouter_livekit_as_current_voice_proof_route() -> None:
    readme = (ROOT / "frontend/next-app/README.md").read_text(encoding="utf-8")

    required_terms = [
        "OpenRouter DeepSeek V4 Flash + LiveKit + Kokoro provenance",
        "OpenRouter/LiveKit/Kokoro preflight readiness",
    ]
    for term in required_terms:
        assert term in readme

    stale_current_route_terms = [
        "Gemma 4 E4B/Kokoro provenance",
        "LiveKit/Gemma/Kokoro preflight readiness",
    ]
    for term in stale_current_route_terms:
        assert term not in readme


def test_current_architecture_surfaces_do_not_present_gemma_as_default_provider() -> None:
    surface_paths = [
        ROOT / "planning/foundation-system-design.html",
        ROOT / "social_media_optimiser/00-system-design/agent-studio-hld-lld.html",
        ROOT / "system_design_vault/agent-studio-system-design-home.html",
        ROOT / "skills/agent-studio-conversation-harness/SKILL.md",
        ROOT / "skills/agent-studio-guardrails-review/SKILL.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in surface_paths)

    required_current_terms = [
        "OpenRouter DeepSeek V4 Flash",
        "OpenRouter/LiveKit/Kokoro",
        "Gemma/Gamma/Hugging Face/MLX are legacy or non-default",
    ]
    for term in required_current_terms:
        assert term in combined

    stale_current_provider_terms = [
        "Gemma 4 experts own reasoning",
        "Gemma 4 agents handle expert work",
        "Gemma 4 specialists research, reason, critique, write",
        "Gemma 4 Expert Layer",
        "Gemma 4 / HF boundary",
        "Gemma 4 is the expert-agent layer",
        "Gemma 4 is used for specialist reasoning",
        "Gemma/HF remains the expert layer",
        "Hugging Face Gemma 4",
        "Gemma Endpoint Gate",
    ]
    for term in stale_current_provider_terms:
        assert term not in combined


def test_conversation_harness_preserves_legacy_gemma_event_contract_names() -> None:
    skill = (ROOT / "skills/agent-studio-conversation-harness/SKILL.md").read_text(
        encoding="utf-8"
    )

    required_event_terms = [
        "gemma_worker_completed",
        "gemma_multimodal_review_completed",
    ]
    for term in required_event_terms:
        assert term in skill

    assert "existing provider-specific completion events" not in skill


def test_pull_request_template_requires_proof_gate_handoff() -> None:
    template_path = ROOT / ".github" / "pull_request_template.md"

    assert template_path.exists(), "PR template must exist for manual handoff"
    template = template_path.read_text(encoding="utf-8")

    required_terms = [
        "Provider Proof Gates",
        "provider-backed-live-voice-proof",
        "external-publication-proof",
        "OpenRouter",
        "deepseek/deepseek-v4-flash",
        "LiveKit",
        "Kokoro",
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "No Hugging Face, Gemma4, Gamma4, or MLX",
        "not committed",
        "CODEOWNERS",
    ]

    for term in required_terms:
        assert term in template


def test_auto_pr_workflow_creates_draft_pr_after_matching_branch_ci_success() -> None:
    workflow_path = ROOT / ".github" / "workflows" / "auto-pr.yml"

    assert workflow_path.exists(), (
        "feature/ and fix_ branches need a repo-owned draft PR workflow when "
        "local GitHub tokens or connector PR creation are unavailable"
    )
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)
    workflow_on = workflow.get("on") or workflow.get(True)

    assert workflow_on["push"]["branches"] == ["feature/**", "fix_*"]
    assert workflow["permissions"]["contents"] == "read"
    assert workflow["permissions"]["actions"] == "read"
    assert workflow["permissions"]["pull-requests"] == "write"

    job = workflow["jobs"]["draft-pr"]
    assert "github.ref_name != 'main'" in job["if"]
    assert "github.event_name == 'push'" in job["if"]
    assert "refs/heads/feature/" in job["if"]
    assert "refs/heads/fix_" in job["if"]

    step_names = [
        step.get("name", "")
        for step in job["steps"]
        if isinstance(step, dict)
    ]
    assert "Wait for matching CI success" in step_names
    assert "Generate no-secret provider proof PR body" in step_names
    assert "Create or update draft PR" in step_names

    assert "github.rest.actions.listWorkflowRuns" in workflow_text
    assert 'workflow_id: "ci.yml"' in workflow_text
    assert "head_sha === headSha" in workflow_text
    assert "conclusion === \"success\"" in workflow_text

    assert "provider-proof-pr-handoff" in workflow_text
    assert "docs/external-publication-operator-inputs.example.env" in workflow_text
    assert "PR_OPERATOR_INPUT_PATH" in workflow_text
    assert "ci-non-secret-openrouter-placeholder" in workflow_text
    assert "ci-non-secret-livekit-key-placeholder" in workflow_text
    assert "ci-non-secret-livekit-voice-placeholder" in workflow_text
    assert "wss://livekit.agent-studio.local" in workflow_text
    assert "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID" in workflow_text
    assert "<linkedin-policy-acknowledgement-artifact-id>" in workflow_text
    assert "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID" in workflow_text
    assert "<publication-rollback-or-postcondition-artifact-id>" in workflow_text
    assert "social_media_optimiser/output/provider-proof" not in workflow_text
    assert "--ci-url \"$CI_URL\"" in workflow_text
    assert "--head-sha \"$HEAD_SHA\"" in workflow_text
    assert "--branch \"$HEAD_BRANCH\"" in workflow_text
    assert "--repo \"$GITHUB_REPOSITORY\"" in workflow_text
    assert "secrets.GITHUB_TOKEN" in workflow_text

    assert "github.rest.pulls.list" in workflow_text
    assert "github.rest.pulls.create" in workflow_text
    assert "github.rest.pulls.update" in workflow_text
    assert "draft: true" in workflow_text
    assert "maintainer_can_modify: true" in workflow_text
    assert "error.status === 403" in workflow_text
    assert "core.warning(" in workflow_text
    assert "Auto PR skipped" in workflow_text
    assert "GITHUB_STEP_SUMMARY" in workflow_text
    assert "Allow GitHub Actions to create and approve pull requests" in workflow_text
    assert "GitHub denied Auto PR create/update with 403" not in workflow_text

    uv_log_artifact = "uv" + ".log"
    forbidden_terms = [
        "OPENROUTER_API_KEY=",
        "LIVEKIT_API_SECRET=",
        "LINKEDIN_ACCESS_TOKEN=",
        "sk-or-v1-",
        "ghp_",
        "hf_",
        uv_log_artifact,
    ]
    for term in forbidden_terms:
        assert term not in workflow_text


def test_repo_workflow_documents_manual_provider_proof_pr_handoff() -> None:
    workflow_doc = (ROOT / "docs/repo-workflow.md").read_text(encoding="utf-8")

    required_terms = [
        "provider-proof-pr-create",
        "provider-proof-pr-handoff",
        ".github/workflows/auto-pr.yml",
        "matching branch CI",
        "draft PR",
        "Allow GitHub Actions to create and approve pull requests",
        "manual PR",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "no secret values",
        "--ci-url",
        "--head-sha",
        "provider-backed-live-voice-proof",
        "external-publication-proof",
        "external-publication-proof-runbook.md",
        "external-publication-operator-inputs.example.env",
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "uv.lock",
        ".github/CODEOWNERS",
    ]

    for term in required_terms:
        assert term in workflow_doc


def test_cloud_handoff_documents_github_permission_and_proof_gate_setup() -> None:
    cloud_path = ROOT / "cloud.md"

    assert cloud_path.exists(), (
        "cloud.md should capture the GitHub-side CI/CD and auto-merge setup "
        "that cannot be represented fully in repository workflow files"
    )
    cloud = cloud_path.read_text(encoding="utf-8")

    required_terms = [
        "GitHub Actions workflow permissions",
        "Read and write permissions",
        "Allow GitHub Actions to create and approve pull requests",
        "main branch protection",
        "required status checks",
        "CODEOWNERS",
        "auto-merge",
        "feature/livekit-voice-proof-capture",
        "provider-proof-pr-handoff",
        "provider-proof-pr-create",
        "provider-backed-live-voice-proof",
        "external-publication-proof",
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "OpenRouter",
        "deepseek/deepseek-v4-flash",
        "LiveKit",
        "Kokoro",
        "uv.lock",
        "no secret values",
    ]

    for term in required_terms:
        assert term in cloud

    uv_log_artifact = "uv" + ".log"
    forbidden_terms = [
        uv_log_artifact,
        "LINKEDIN_ACCESS_TOKEN=",
        "OPENROUTER_API_KEY=",
        "LIVEKIT_API_SECRET=",
        "sk-or-v1-",
        "ghp_",
        "hf_",
    ]
    for term in forbidden_terms:
        assert term not in cloud


def test_manual_pr_handoff_notes_include_current_ci_evidence_inputs() -> None:
    handoff_paths = [
        ROOT / "docs/repo-workflow.md",
        ROOT / "agent_progress_vault/06-live-voice/openrouter-livekit-current-unblock-guide.md",
        ROOT / "social_media_optimiser/wiki/ops/active-codex-context.md",
        ROOT
        / "system_design_vault/07-agent-studio-knowledge-graph/Agent Studio Sidecar Pickup 2026-05-24.md",
    ]

    for path in handoff_paths:
        handoff = path.read_text(encoding="utf-8")

        assert "provider-proof-pr-handoff" in handoff
        assert "--ci-url" in handoff, (
            f"{path.relative_to(ROOT)} must pass the latest branch-head CI URL "
            "when it claims CI evidence"
        )
        assert "--head-sha" in handoff, (
            f"{path.relative_to(ROOT)} must pass the current branch head SHA "
            "when it claims CI evidence"
        )
        assert "docs/external-publication-operator-inputs.example.env" in handoff, (
            f"{path.relative_to(ROOT)} must point manual PR operators to the "
            "committed no-secret external-publication input example"
        )


def test_provider_proof_pr_handoff_commands_include_current_evidence_flags() -> None:
    handoff_paths = [
        ROOT / "docs/repo-workflow.md",
        ROOT / "agent_progress_vault/04-cross-vault-links/vault-sync-notes.md",
        ROOT / "agent_progress_vault/06-live-voice/openrouter-livekit-current-unblock-guide.md",
        ROOT / "social_media_optimiser/wiki/ops/active-codex-context.md",
        ROOT
        / "system_design_vault/04-agent-studio-implications/agent-studio-objective-completion-audit.md",
        ROOT
        / "system_design_vault/07-agent-studio-knowledge-graph/Agent Studio Sidecar Pickup 2026-05-24.md",
    ]

    for path in handoff_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        command_lines = [
            line_number
            for line_number, line in enumerate(lines)
            if "uv run all-about-llms-admin provider-proof-pr-handoff" in line
        ]
        assert command_lines, f"{path.relative_to(ROOT)} must document PR handoff"
        for line_number in command_lines:
            command_window = "\n".join(lines[line_number : line_number + 8])
            assert "--run-id" in command_window, (
                f"{path.relative_to(ROOT)} handoff command must include --run-id"
            )
            assert "--ci-url" in command_window, (
                f"{path.relative_to(ROOT)} handoff command must include --ci-url"
            )
            assert "--head-sha" in command_window, (
                f"{path.relative_to(ROOT)} handoff command must include --head-sha"
            )


def test_external_publication_operator_runbook_is_committed_no_secret_handoff() -> None:
    runbook_path = ROOT / "docs/external-publication-proof-runbook.md"

    assert runbook_path.exists(), (
        "external publication proof needs a committed no-secret operator runbook, "
        "not only ignored generated proof output"
    )
    runbook = runbook_path.read_text(encoding="utf-8")

    required_terms = [
        "external-publication-proof",
        "provider-backed-live-voice-proof",
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
        "operator-inputs.template.env",
        "provider-proof-operator-input-readiness",
        "--fail-on-blocked",
        "--fail-on-blocked > social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-input-readiness.json",
        "validate-provider-proof-preflight-artifacts --proof external-publication-proof",
        "provider-proof-record-template --proof external-publication-proof",
        "validate-provider-proof-record --proof external-publication-proof",
        "record-provider-proof-record --proof external-publication-proof",
        "provider-proof-completion-status",
        "provider-proof-closure-review-template",
        "record-provider-proof-blocker-state-update",
        "No secret values",
        "Do not commit",
        "OpenRouter",
        "deepseek/deepseek-v4-flash",
        "LiveKit",
        "Kokoro",
    ]

    for term in required_terms:
        assert term in runbook

    forbidden_terms = [
        "LINKEDIN_ACCESS_TOKEN=",
        "sk-or-v1-",
        "ghp_",
        "hf_",
    ]
    for term in forbidden_terms:
        assert term not in runbook


def test_external_publication_operator_input_example_is_committed_no_secret_template() -> None:
    example_path = ROOT / "docs/external-publication-operator-inputs.example.env"
    runbook = (ROOT / "docs/external-publication-proof-runbook.md").read_text(
        encoding="utf-8"
    )

    assert example_path.exists(), (
        "external publication proof should have a committed no-secret example "
        "for the ignored operator input file"
    )
    example = example_path.read_text(encoding="utf-8")

    required_fields = [
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
    ]
    for field in required_fields:
        assert f"{field}=" in example

    required_placeholders = [
        "/absolute/path/to/local/linkedin-access-token.txt",
        "https://docs.example.com/linkedin-policy-acknowledgement",
        "<durable-linkedin-publication-url-or-id>",
        "https://docs.example.com/publication-rollback-or-postcondition",
    ]
    for placeholder in required_placeholders:
        assert placeholder in example

    uv_log_artifact = "uv" + ".log"
    forbidden_terms = [
        uv_log_artifact,
        "LINKEDIN_ACCESS_TOKEN=",
        "sk-or-v1-",
        "ghp_",
        "hf_",
    ]
    for term in forbidden_terms:
        assert term not in example

    assert str(example_path.relative_to(ROOT)) in runbook
    assert uv_log_artifact not in runbook

    readiness = subprocess.run(
        [
            "uv",
            "run",
            "all-about-llms-admin",
            "provider-proof-operator-input-readiness",
            "--run-id",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            "--input-path",
            str(example_path.relative_to(ROOT)),
            "--fail-on-blocked",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert readiness.returncode == 2
    readiness_report = json.loads(readiness.stdout)
    publication_field = readiness_report["field_statuses"][
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"
    ]
    assert publication_field["state"] == "placeholder"
    assert publication_field["issue_code"] == "operator_input_placeholder"


def test_external_publication_runbook_is_linked_from_current_vault_handoffs() -> None:
    handoff_paths = [
        ROOT / "social_media_optimiser/01-work-tracking/Agent Studio Objective Completion Audit.md",
        ROOT / "social_media_optimiser/wiki/ops/active-codex-context.md",
        ROOT
        / "system_design_vault/07-agent-studio-knowledge-graph/Agent Studio Sidecar Pickup 2026-05-24.md",
    ]

    for path in handoff_paths:
        handoff = path.read_text(encoding="utf-8")

        assert "docs/external-publication-proof-runbook.md" in handoff
        assert "operator-unblocker-checklist.md" in handoff
        assert "LINKEDIN_ACCESS_TOKEN_FILE" in handoff
        assert "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL" in handoff


def test_live_voice_vault_unblock_guide_uses_current_openrouter_path() -> None:
    moc = (ROOT / "agent_progress_vault/MOC.md").read_text(encoding="utf-8")

    assert "[[06-live-voice/openrouter-livekit-current-unblock-guide]]" in moc
    assert "[[06-live-voice/unblock-guide-gemma4-e4b]]" not in moc
    assert not (
        ROOT / "agent_progress_vault/06-live-voice/unblock-guide-gemma4-e4b.md"
    ).exists()


def test_openrouter_voice_boundary_map_replaces_legacy_gemma_filename() -> None:
    current_map = (
        ROOT
        / "social_media_optimiser/02-research/openrouter-livekit-voice-boundary-map.html"
    )
    legacy_map = ROOT / "social_media_optimiser/02-research/gemma-voice-boundary-map.html"
    active_moc = (ROOT / "social_media_optimiser/Agent Studio MOC.md").read_text(
        encoding="utf-8"
    )
    progress_links = (
        ROOT / "agent_progress_vault/04-cross-vault-links/vault-sync-notes.md"
    ).read_text(encoding="utf-8")
    stable_ci_script = (
        ROOT / "scripts/ci-python-stable-tests.sh"
    ).read_text(encoding="utf-8")

    assert current_map.exists()
    assert not legacy_map.exists()
    assert "02-research/openrouter-livekit-voice-boundary-map.html" in active_moc
    assert "02-research/gemma-voice-boundary-map.html" not in active_moc
    assert "openrouter-livekit-voice-boundary-map.html" in progress_links
    assert "Legacy-named Gemma voice boundary" not in progress_links
    assert "tests/test_openrouter_livekit_voice_boundary_browser.py" in stable_ci_script
    assert "tests/test_gemma_voice_boundary_browser.py" not in stable_ci_script


def test_current_handoff_notes_avoid_exact_latest_ci_run_ids() -> None:
    handoff_paths = [
        ROOT / "agent_progress_vault/00-session-log/2026-05-23-ship-readiness-audit.md",
        ROOT / "agent_progress_vault/01-implementation-matrix/feature-implementation-status.md",
        ROOT / "agent_progress_vault/02-remaining-work/prioritized-backlog.md",
        ROOT / "agent_progress_vault/03-agent-activity/background-agents-registry.md",
        ROOT / "agent_progress_vault/04-cross-vault-links/vault-sync-notes.md",
        ROOT / "social_media_optimiser/01-work-tracking/Current Sprint.md",
        ROOT / "social_media_optimiser/wiki/ops/active-codex-context.md",
        ROOT / "system_design_vault/04-agent-studio-implications/agent-studio-objective-completion-audit.md",
    ]
    stale_latest_claim_patterns = [
        re.compile(r"latest branch-head[^\n`]*run `\d{8,}`", re.IGNORECASE),
        re.compile(r"branch-head CI run \d{8,} passed for [0-9a-f]{7,40}"),
        re.compile(r"branch-head CI run `\d{8,}` passed on `[0-9a-f]{7,40}`", re.IGNORECASE),
        re.compile(r"remote CI run[s]? `\d{8,}`", re.IGNORECASE),
    ]

    for path in handoff_paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for stale_latest_claim in stale_latest_claim_patterns:
                assert not stale_latest_claim.search(line), (
                    f"{path.relative_to(ROOT)}:{line_number} must not bake an exact "
                    "CI run id into a durable latest-branch-head claim"
                )


def test_manual_pr_handoff_notes_do_not_pin_exact_current_head_evidence() -> None:
    handoff_paths = [
        ROOT / "cloud.md",
        ROOT / "agent_progress_vault/06-live-voice/openrouter-livekit-current-unblock-guide.md",
        ROOT / "social_media_optimiser/wiki/ops/active-codex-context.md",
        ROOT
        / "system_design_vault/04-agent-studio-implications/agent-studio-objective-completion-audit.md",
    ]
    stale_pinned_current_evidence = [
        re.compile(r"Branch head: `[0-9a-f]{40}`"),
        re.compile(r"Green CI run: <https://github\.com/[^>]+/actions/runs/\d+>"),
        re.compile(r"source: .*GitHub Actions run `\d+`, branch head `[0-9a-f]{40}`"),
        re.compile(r"Source: .*GitHub Actions run `\d+`, and pushed branch head `[0-9a-f]{40}`"),
        re.compile(r"Latest verified branch snapshot.*head `[0-9a-f]{40}`.*CI run `\d+`"),
        re.compile(r"Current branch snapshot: .*`[0-9a-f]{40}`.*CI run `\d+`"),
        re.compile(r"Current branch head `[0-9a-f]{40}` has branch CI success at run `\d+`"),
    ]

    for path in handoff_paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for stale_pattern in stale_pinned_current_evidence:
                assert not stale_pattern.search(line), (
                    f"{path.relative_to(ROOT)}:{line_number} must not commit exact "
                    "current head/run evidence for a manual PR handoff; regenerate "
                    "provider-proof-pr-handoff at PR creation time instead"
                )


def test_current_handoff_notes_do_not_reopen_accepted_live_voice_proof() -> None:
    handoff_paths = [
        ROOT / "social_media_optimiser/01-work-tracking/Agent Studio Objective Completion Audit.md",
        ROOT / "social_media_optimiser/log.md",
        ROOT / "social_media_optimiser/wiki/ops/active-codex-context.md",
        ROOT / "system_design_vault/04-agent-studio-implications/agent-studio-objective-completion-audit.md",
    ]
    stale_live_voice_phrases = [
        "current live-voice blocker is accepted",
        "still needs accepted same-run proof-record capture/recheck",
        "provider-backed live voice remains unproven",
        "live-voice record capture/recheck and external publication remain unproven",
        "live voice waiting on proof-record capture/recheck",
        "accepted same-session OpenRouter/LiveKit/Kokoro proof still has to be captured",
        "does not satisfy accepted OpenRouter LiveKit",
        "accepted OpenRouter/LiveKit/Kokoro live voice proof and external publication proof records remain required",
        "does not create OpenRouter/LiveKit/Kokoro live voice evidence",
        "does not satisfy current OpenRouter/LiveKit/Kokoro live proof",
        "only Gemma audio reasoning remains blocked for live voice",
        "successful live proof is recorded",
    ]

    for path in handoff_paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for phrase in stale_live_voice_phrases:
                assert phrase not in line, (
                    f"{path.relative_to(ROOT)}:{line_number} reopens accepted live voice "
                    f"proof with stale phrase: {phrase}"
                )


def test_provider_proof_pr_handoff_cli_generates_manual_pr_body(tmp_path: Path) -> None:
    operator_input_path = tmp_path / "operator-inputs.template.env"
    operator_input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=",
                "LIVEKIT_API_SECRET_FILE=",
                "LINKEDIN_ACCESS_TOKEN_FILE=",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID=",
                "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL=",
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID=",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "uv",
            "run",
            "all-about-llms-admin",
            "provider-proof-pr-handoff",
            "--run-id",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            "--operator-input-path",
            str(operator_input_path),
            "--ci-url",
            "https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/123456789",
            "--head-sha",
            "cd3106728909cb422a6b7687b91308119b17f7d9",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    handoff = result.stdout

    required_terms = [
        "Agent Studio PR Handoff",
        "provider-backed-live-voice-proof",
        "accepted_record_found",
        "external-publication-proof",
        "latest_record_failed",
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "deepseek/deepseek-v4-flash",
        "LiveKit",
        "Kokoro",
        "No Hugging Face, Gemma4, Gamma4, or MLX",
        "Dependency changes include `uv.lock`",
        "local command logs stay untracked",
        "no secret values printed",
        "operator_input_example",
        "docs/external-publication-operator-inputs.example.env",
        "https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/123456789",
        "cd3106728909cb422a6b7687b91308119b17f7d9",
    ]

    for term in required_terms:
        assert term in handoff

    assert str(operator_input_path) not in handoff
    assert "<filled-ignored-operator-input-file>" in handoff

    forbidden_terms = [
        "OPENROUTER_API_KEY=",
        "LIVEKIT_API_SECRET=",
        "LINKEDIN_ACCESS_TOKEN=",
        ".secrets/openrouter_api_key",
        ".secrets/livekit_api_secret",
    ]
    for term in forbidden_terms:
        assert term not in handoff


def test_provider_proof_pr_handoff_cli_requires_current_ci_and_head_sha() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "all-about-llms-admin",
            "provider-proof-pr-handoff",
            "--run-id",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode != 0
    assert "--ci-url" in result.stderr
    assert "--head-sha" in result.stderr
    assert "Agent Studio PR Handoff" not in result.stdout


def test_provider_proof_pr_handoff_cli_rejects_non_current_evidence_values() -> None:
    valid_ci_url = (
        "https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/"
        "123456789"
    )
    valid_sha = "cd3106728909cb422a6b7687b91308119b17f7d9"
    invalid_cases = [
        (
            "<latest-branch-head-ci-url>",
            valid_sha,
            "GitHub Actions run URL",
        ),
        (
            "https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/example",
            valid_sha,
            "GitHub Actions run URL",
        ),
        (
            valid_ci_url,
            "<current-branch-head-sha>",
            "40-character hex commit SHA",
        ),
        (
            valid_ci_url,
            "not-a-sha",
            "40-character hex commit SHA",
        ),
    ]

    for ci_url, head_sha, expected_error in invalid_cases:
        result = subprocess.run(
            [
                "uv",
                "run",
                "all-about-llms-admin",
                "provider-proof-pr-handoff",
                "--run-id",
                "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
                "--ci-url",
                ci_url,
                "--head-sha",
                head_sha,
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        assert result.returncode != 0
        assert expected_error in result.stderr
        assert "Agent Studio PR Handoff" not in result.stdout


def test_provider_proof_pr_handoff_cli_rejects_ci_repo_mismatch() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "all-about-llms-admin",
            "provider-proof-pr-handoff",
            "--run-id",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            "--repo",
            "DeconvFFT/Content-creator-optimizer",
            "--ci-url",
            "https://github.com/OtherOwner/OtherRepo/actions/runs/123456789",
            "--head-sha",
            "cd3106728909cb422a6b7687b91308119b17f7d9",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode != 0
    assert "--ci-url repository" in result.stderr
    assert "--repo DeconvFFT/Content-creator-optimizer" in result.stderr
    assert "Agent Studio PR Handoff" not in result.stdout


def test_provider_proof_pr_handoff_cli_uses_custom_output_dir_workspace(
    tmp_path: Path,
) -> None:
    custom_workspace = tmp_path / "provider-proof" / "custom-run"

    result = subprocess.run(
        [
            "uv",
            "run",
            "all-about-llms-admin",
            "provider-proof-pr-handoff",
            "--run-id",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            "--output-dir",
            str(custom_workspace),
            "--ci-url",
            "https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/123456789",
            "--head-sha",
            "cd3106728909cb422a6b7687b91308119b17f7d9",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    handoff = result.stdout

    assert str(custom_workspace) not in handoff
    assert "- input_path: `<filled-ignored-operator-input-file>`" in handoff
    assert "--output-dir <provider-proof-output-dir>" in handoff
    assert "--input-path <filled-ignored-operator-input-file>" in handoff


def test_provider_proof_pr_create_cli_dry_run_outputs_no_secret_request(
    tmp_path: Path,
) -> None:
    operator_input_path = tmp_path / "operator-inputs.template.env"
    operator_input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=",
                "LIVEKIT_API_SECRET_FILE=",
                "LINKEDIN_ACCESS_TOKEN_FILE=",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID=",
                "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL=",
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID=",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "uv",
            "run",
            "all-about-llms-admin",
            "provider-proof-pr-create",
            "--run-id",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            "--operator-input-path",
            str(operator_input_path),
            "--ci-url",
            "https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/123456789",
            "--head-sha",
            "cd3106728909cb422a6b7687b91308119b17f7d9",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["status"] == "dry_run"
    assert (
        payload["post_url"]
        == "https://api.github.com/repos/DeconvFFT/Content-creator-optimizer/pulls"
    )
    assert (
        payload["compare_url"]
        == "https://github.com/DeconvFFT/Content-creator-optimizer/compare/main...feature/livekit-voice-proof-capture?expand=1"
    )
    assert payload["request"]["base"] == "main"
    assert payload["request"]["head"] == "feature/livekit-voice-proof-capture"
    assert payload["request"]["draft"] is True
    assert payload["body_source"] == "provider-proof-pr-handoff"
    assert payload["boundary"] == "no_secret_values_printed"

    forbidden_terms = [
        "Authorization",
        "OPENROUTER_API_KEY=",
        "LIVEKIT_API_SECRET=",
        "LINKEDIN_ACCESS_TOKEN=",
    ]
    combined_output = result.stdout + result.stderr
    for term in forbidden_terms:
        assert term not in combined_output


def test_provider_proof_pr_create_cli_reports_manual_required_without_token() -> None:
    operator_input_path = (
        ROOT
        / "social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env"
    )

    result = subprocess.run(
        [
            "uv",
            "run",
            "all-about-llms-admin",
            "provider-proof-pr-create",
            "--run-id",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            "--operator-input-path",
            str(operator_input_path),
            "--ci-url",
            "https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/123456789",
            "--head-sha",
            "cd3106728909cb422a6b7687b91308119b17f7d9",
        ],
        cwd=ROOT,
        env={
            "PATH": os.environ["PATH"],
            "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", str(ROOT / ".uv-cache")),
        },
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "manual_required"
    assert payload["issue_code"] == "github_token_unavailable"
    assert payload["token_env_candidates"] == ["GITHUB_TOKEN", "GH_TOKEN"]
    assert "<workspace-root>" not in payload["handoff_command"]
    assert (
        "social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env"
        in payload["handoff_command"]
    )
    assert "Agent Studio PR Handoff" not in result.stdout
    assert "LINKEDIN_ACCESS_TOKEN=" not in result.stdout


def test_provider_proof_pr_create_result_posts_with_token_without_leaking_it(
    tmp_path: Path,
) -> None:
    operator_input_path = tmp_path / "operator-inputs.template.env"
    operator_input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=",
                "LIVEKIT_API_SECRET_FILE=",
                "LINKEDIN_ACCESS_TOKEN_FILE=",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID=",
                "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL=",
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID=",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    args = argparse.Namespace(
        audit_target=None,
        base="main",
        branch="feature/livekit-voice-proof-capture",
        checked_at=None,
        ci_url="https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/123456789",
        draft=True,
        dry_run=False,
        env_example_path=ROOT / ".env.example",
        head_sha="cd3106728909cb422a6b7687b91308119b17f7d9",
        operator_input_path=operator_input_path,
        output_dir=None,
        repo="DeconvFFT/Content-creator-optimizer",
        run_id="190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
        timeout_seconds=5.0,
        title="Agent Studio LiveKit/OpenRouter proof gates",
    )
    captured_calls: list[dict[str, object]] = []

    class FakeResponse:
        def __init__(self, payload: object):
            self.payload = payload

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def fake_opener(request: object, timeout: float) -> FakeResponse:
        captured_calls.append(
            {
                "timeout": timeout,
                "headers": dict(request.header_items()),
                "body": (
                    json.loads(request.data.decode("utf-8"))
                    if request.data
                    else None
                ),
                "method": request.get_method(),
                "url": request.full_url,
            }
        )
        if request.get_method() == "GET":
            return FakeResponse([])
        return FakeResponse(
            {
                "number": 17,
                "html_url": (
                    "https://github.com/DeconvFFT/Content-creator-optimizer/pull/17"
                ),
                "state": "open",
                "draft": True,
            }
        )

    payload = cli_module._provider_proof_pr_create_result(
        args,
        env={"GITHUB_TOKEN": "local-test-token-not-secret"},
        opener=fake_opener,
    )

    assert payload["status"] == "created"
    assert payload["number"] == 17
    assert payload["url"] == (
        "https://github.com/DeconvFFT/Content-creator-optimizer/pull/17"
    )
    assert [call["method"] for call in captured_calls] == ["GET", "POST"]
    assert captured_calls[1]["url"] == (
        "https://api.github.com/repos/DeconvFFT/Content-creator-optimizer/pulls"
    )
    assert captured_calls[1]["headers"]["Authorization"] == (
        "Bearer local-test-token-not-secret"
    )
    request_body = captured_calls[1]["body"]
    assert request_body["head"] == "feature/livekit-voice-proof-capture"
    assert request_body["base"] == "main"
    assert request_body["draft"] is True
    assert "Agent Studio PR Handoff" in request_body["body"]
    assert "local-test-token-not-secret" not in json.dumps(payload)


def test_provider_proof_pr_create_result_updates_existing_open_pr_without_token_leak(
    tmp_path: Path,
) -> None:
    operator_input_path = tmp_path / "operator-inputs.template.env"
    operator_input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=",
                "LIVEKIT_API_SECRET_FILE=",
                "LINKEDIN_ACCESS_TOKEN_FILE=",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID=",
                "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL=",
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID=",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    args = argparse.Namespace(
        audit_target=None,
        base="main",
        branch="feature/livekit-voice-proof-capture",
        checked_at=None,
        ci_url="https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/123456789",
        draft=True,
        dry_run=False,
        env_example_path=ROOT / ".env.example",
        head_sha="cd3106728909cb422a6b7687b91308119b17f7d9",
        operator_input_path=operator_input_path,
        output_dir=None,
        repo="DeconvFFT/Content-creator-optimizer",
        run_id="190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
        timeout_seconds=5.0,
        title="Agent Studio LiveKit/OpenRouter proof gates",
    )
    calls: list[dict[str, object]] = []

    class FakeResponse:
        def __init__(self, payload: object):
            self.payload = payload

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def fake_opener(request: object, timeout: float) -> FakeResponse:
        calls.append(
            {
                "timeout": timeout,
                "headers": dict(request.header_items()),
                "body": (
                    json.loads(request.data.decode("utf-8"))
                    if request.data
                    else None
                ),
                "method": request.get_method(),
                "url": request.full_url,
            }
        )
        if request.get_method() == "GET":
            return FakeResponse(
                [
                    {
                        "number": 17,
                        "html_url": (
                            "https://github.com/DeconvFFT/Content-creator-optimizer/pull/17"
                        ),
                        "state": "open",
                        "draft": True,
                    }
                ]
            )
        return FakeResponse(
            {
                "number": 17,
                "html_url": (
                    "https://github.com/DeconvFFT/Content-creator-optimizer/pull/17"
                ),
                "state": "open",
                "draft": True,
            }
        )

    payload = cli_module._provider_proof_pr_create_result(
        args,
        env={"GITHUB_TOKEN": "local-test-token-not-secret"},
        opener=fake_opener,
    )

    assert payload["status"] == "updated"
    assert payload["number"] == 17
    assert payload["url"] == (
        "https://github.com/DeconvFFT/Content-creator-optimizer/pull/17"
    )
    assert [call["method"] for call in calls] == ["GET", "PATCH"]
    assert calls[0]["url"] == (
        "https://api.github.com/repos/DeconvFFT/Content-creator-optimizer/pulls"
        "?state=open&base=main&head=DeconvFFT%3Afeature%2Flivekit-voice-proof-capture"
    )
    assert calls[1]["url"] == (
        "https://api.github.com/repos/DeconvFFT/Content-creator-optimizer/pulls/17"
    )
    assert calls[1]["headers"]["Authorization"] == (
        "Bearer local-test-token-not-secret"
    )
    update_body = calls[1]["body"]
    assert update_body["title"] == "Agent Studio LiveKit/OpenRouter proof gates"
    assert update_body["body"].startswith("# Agent Studio PR Handoff")
    assert update_body["maintainer_can_modify"] is True
    assert "local-test-token-not-secret" not in json.dumps(payload)
    assert "local-test-token-not-secret" not in json.dumps(calls[1]["body"])


def test_provider_proof_pr_create_result_compacts_url_errors_without_token_leak(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        audit_target=None,
        base="main",
        branch="feature/livekit-voice-proof-capture",
        checked_at=None,
        ci_url="https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/123456789",
        draft=True,
        dry_run=False,
        env_example_path=ROOT / ".env.example",
        head_sha="cd3106728909cb422a6b7687b91308119b17f7d9",
        operator_input_path=tmp_path / "operator-inputs.template.env",
        output_dir=None,
        repo="DeconvFFT/Content-creator-optimizer",
        run_id="190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
        timeout_seconds=5.0,
        title="Agent Studio LiveKit/OpenRouter proof gates",
    )

    def failing_opener(_request: object, timeout: float) -> object:
        assert timeout == 5.0
        raise cli_module.urlerror.URLError("network unavailable")

    payload = cli_module._provider_proof_pr_create_result(
        args,
        env={"GITHUB_TOKEN": "local-test-token-not-secret"},
        opener=failing_opener,
    )

    assert payload["status"] == "github_api_error"
    assert payload["issue_code"] == "github_api_request_failed"
    assert payload["exit_code"] == 1
    assert "handoff_command" in payload
    assert "local-test-token-not-secret" not in json.dumps(payload)


def test_provider_proof_pr_create_result_reports_permission_denied_without_token_leak(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        audit_target=None,
        base="main",
        branch="feature/livekit-voice-proof-capture",
        checked_at=None,
        ci_url="https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/123456789",
        draft=True,
        dry_run=False,
        env_example_path=ROOT / ".env.example",
        head_sha="cd3106728909cb422a6b7687b91308119b17f7d9",
        operator_input_path=tmp_path / "operator-inputs.template.env",
        output_dir=None,
        repo="DeconvFFT/Content-creator-optimizer",
        run_id="190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
        timeout_seconds=5.0,
        title="Agent Studio LiveKit/OpenRouter proof gates",
    )

    def forbidden_opener(request: object, timeout: float) -> object:
        assert timeout == 5.0
        raise cli_module.urlerror.HTTPError(
            request.full_url,
            403,
            "Forbidden",
            {},
            io.BytesIO(b'{"message":"Resource not accessible by integration"}'),
        )

    payload = cli_module._provider_proof_pr_create_result(
        args,
        env={"GITHUB_TOKEN": "local-test-token-not-secret"},
        opener=forbidden_opener,
    )

    assert payload["status"] == "manual_required"
    assert payload["issue_code"] == "github_pr_permission_denied"
    assert payload["http_status"] == 403
    assert payload["exit_code"] == 2
    assert "workflow_permissions_next_action" in payload
    assert "Allow GitHub Actions to create and approve pull requests" in json.dumps(
        payload
    )
    assert "handoff_command" in payload
    assert "local-test-token-not-secret" not in json.dumps(payload)
    assert "Authorization" not in json.dumps(payload)


def test_provider_proof_pr_create_result_compacts_invalid_success_json(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        audit_target=None,
        base="main",
        branch="feature/livekit-voice-proof-capture",
        checked_at=None,
        ci_url="https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/123456789",
        draft=True,
        dry_run=False,
        env_example_path=ROOT / ".env.example",
        head_sha="cd3106728909cb422a6b7687b91308119b17f7d9",
        operator_input_path=tmp_path / "operator-inputs.template.env",
        output_dir=None,
        repo="DeconvFFT/Content-creator-optimizer",
        run_id="190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
        timeout_seconds=5.0,
        title="Agent Studio LiveKit/OpenRouter proof gates",
    )

    class InvalidJsonResponse:
        def __enter__(self) -> "InvalidJsonResponse":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def read(self) -> bytes:
            return b"not-json"

    def invalid_json_opener(
        _request: object, timeout: float
    ) -> InvalidJsonResponse:
        assert timeout == 5.0
        return InvalidJsonResponse()

    payload = cli_module._provider_proof_pr_create_result(
        args,
        env={"GITHUB_TOKEN": "local-test-token-not-secret"},
        opener=invalid_json_opener,
    )

    assert payload["status"] == "github_api_error"
    assert payload["issue_code"] == "github_api_response_invalid"
    assert payload["exit_code"] == 1
    assert "handoff_command" in payload
    assert "local-test-token-not-secret" not in json.dumps(payload)
