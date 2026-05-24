import re
from pathlib import Path
import subprocess
import tomllib

import yaml


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
    ]

    for term in required_terms:
        assert term in template


def test_repo_workflow_documents_manual_provider_proof_pr_handoff() -> None:
    workflow_doc = (ROOT / "docs/repo-workflow.md").read_text(encoding="utf-8")

    required_terms = [
        "provider-proof-pr-handoff",
        "manual PR",
        "no secret values",
        "--ci-url",
        "--head-sha",
        "provider-backed-live-voice-proof",
        "external-publication-proof",
        "external-publication-proof-runbook.md",
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "uv.lock",
    ]

    for term in required_terms:
        assert term in workflow_doc


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
        ROOT / "agent_progress_vault/01-implementation-matrix/feature-implementation-status.md",
        ROOT / "agent_progress_vault/02-remaining-work/prioritized-backlog.md",
        ROOT / "agent_progress_vault/03-agent-activity/background-agents-registry.md",
        ROOT / "agent_progress_vault/04-cross-vault-links/vault-sync-notes.md",
        ROOT / "social_media_optimiser/wiki/ops/active-codex-context.md",
        ROOT / "system_design_vault/04-agent-studio-implications/agent-studio-objective-completion-audit.md",
    ]
    stale_latest_claim = re.compile(r"latest branch-head[^\n`]*run `\d{8,}`")

    for path in handoff_paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not stale_latest_claim.search(line), (
                f"{path.relative_to(ROOT)}:{line_number} must not bake an exact "
                "CI run id into a durable latest-branch-head claim"
            )


def test_manual_pr_handoff_notes_do_not_pin_exact_current_head_evidence() -> None:
    handoff_paths = [
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
        "https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/123456789",
        "cd3106728909cb422a6b7687b91308119b17f7d9",
    ]

    for term in required_terms:
        assert term in handoff

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
    expected_operator_input = custom_workspace / "operator-inputs.template.env"

    assert f"- input_path: `{expected_operator_input}`" in handoff
    assert f"--output-dir {custom_workspace}" in handoff
    assert f"--input-path {expected_operator_input}" in handoff
