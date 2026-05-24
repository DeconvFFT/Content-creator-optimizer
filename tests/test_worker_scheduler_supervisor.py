import asyncio
from uuid import uuid4

import pytest

from all_about_llms.config import Settings
from all_about_llms.contracts import (
    VoiceAgentProcessStatus,
    WorkerProfileExecutionMode,
    WorkerSchedulerProcessStartRequest,
)
from all_about_llms.orchestration.scheduler_supervisor import (
    LocalWorkerSchedulerSupervisor,
)


@pytest.mark.asyncio
async def test_local_worker_scheduler_supervisor_redacts_secret_log_tail():
    supervisor = LocalWorkerSchedulerSupervisor(
        Settings(
            database_url="postgresql://user:secret-db@localhost:5432/app",
            hf_token="hf-secret-token",
            tavily_api_key="tvly-secret-token",
            serpapi_api_key="serp-secret-token",
        )
    )

    supervisor._append_log(
        "scheduler saw hf-secret-token tvly-secret-token serp-secret-token "
        "postgresql://user:secret-db@localhost:5432/app"
    )

    status = await supervisor.status()

    assert status.log_tail == [
        "scheduler saw [redacted] [redacted] [redacted] [redacted]"
    ]
    assert "secret" not in str(status.log_tail).lower()


def test_local_worker_scheduler_supervisor_builds_run_scoped_watch_command():
    run_id = uuid4()
    supervisor = LocalWorkerSchedulerSupervisor(Settings())
    request = WorkerSchedulerProcessStartRequest(
        run_id=run_id,
        execution_mode=WorkerProfileExecutionMode.AUTONOMOUS_PASS,
        max_profiles=7,
        poll_interval_seconds=2.5,
    )

    command = supervisor._command_for(request)

    assert command[:4] == [
        command[0],
        "-m",
        "all_about_llms.cli",
        "run-worker-scheduler",
    ]
    assert "--watch" in command
    assert command[command.index("--run-id") + 1] == str(run_id)
    assert command[command.index("--execution-mode") + 1] == "autonomous_pass"
    assert command[command.index("--max-profiles") + 1] == "7"
    assert command[command.index("--poll-interval-seconds") + 1] == "2.5"


def test_worker_scheduler_process_request_accepts_profile_cadence_floor():
    request = WorkerSchedulerProcessStartRequest(
        run_id=uuid4(),
        poll_interval_seconds=0.25,
    )

    assert request.poll_interval_seconds == 0.25


class FakeSupervisorProcess:
    pid = 9876
    stdout = None

    def __init__(self):
        self.returncode = None
        self.terminated = False
        self.killed = False

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    async def wait(self):
        return self.returncode


class FakeUnstoppableSupervisorProcess(FakeSupervisorProcess):
    def terminate(self):
        self.terminated = True

    async def wait(self):
        raise asyncio.TimeoutError

    def kill(self):
        self.killed = True
        raise OSError("permission denied")


@pytest.mark.asyncio
async def test_local_worker_scheduler_supervisor_stop_is_not_reported_as_failure():
    run_id = uuid4()
    supervisor = LocalWorkerSchedulerSupervisor(Settings())
    process = FakeSupervisorProcess()
    supervisor._process = process
    supervisor._run_id = run_id

    status = await supervisor.stop()

    assert process.terminated is True
    assert process.killed is False
    assert status.status == VoiceAgentProcessStatus.STOPPED
    assert status.running is False
    assert status.returncode == -15
    assert status.run_id == run_id
    assert "failed" not in status.summary.lower()


@pytest.mark.asyncio
async def test_local_worker_scheduler_supervisor_stop_race_keeps_running_state():
    supervisor = LocalWorkerSchedulerSupervisor(Settings())
    process = FakeUnstoppableSupervisorProcess()
    supervisor._process = process

    status = await supervisor.stop()

    assert process.terminated is True
    assert process.killed is True
    assert status.status == VoiceAgentProcessStatus.RUNNING
    assert status.running is True
    assert status.returncode is None
    assert status.last_error is not None
    assert "permission denied" in status.last_error
    assert "Retry Stop scheduler." in status.next_actions
