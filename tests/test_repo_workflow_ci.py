from pathlib import Path
import subprocess

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
