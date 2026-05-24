import asyncio
import os
import sys
from collections import deque
from datetime import datetime, timezone

from all_about_llms.config import PROJECT_ROOT, Settings
from all_about_llms.contracts import (
    VoiceAgentProcessStatus,
    WorkerProfileExecutionMode,
    WorkerSchedulerProcessStartRequest,
    WorkerSchedulerProcessStatusResult,
)


class LocalWorkerSchedulerSupervisor:
    """Local process supervisor for the long-running Autopilot scheduler."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._process: asyncio.subprocess.Process | None = None
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._last_returncode: int | None = None
        self._last_error: str | None = None
        self._status = (
            VoiceAgentProcessStatus.STOPPED
            if settings.worker_scheduler_supervisor_enabled
            else VoiceAgentProcessStatus.DISABLED
        )
        self._run_id = None
        self._execution_mode = WorkerProfileExecutionMode.AUTONOMOUS_PASS
        self._max_profiles = 25
        self._poll_interval_seconds = 5.0
        self._logs: deque[str] = deque(
            maxlen=settings.worker_scheduler_supervisor_log_lines
        )
        self._lock = asyncio.Lock()
        self._reader_tasks: set[asyncio.Task] = set()
        self._command: list[str] = self._base_command()
        self._secret_values = tuple(
            value
            for value in (
                settings.database_url,
                settings.hf_token,
                settings.livekit_api_key,
                settings.livekit_api_secret,
                settings.openai_api_key,
                settings.elevenlabs_api_key,
                settings.cartesia_api_key,
                settings.tavily_api_key,
                settings.serpapi_api_key,
            )
            if value and len(value) >= 4
        )

    async def status(self) -> WorkerSchedulerProcessStatusResult:
        async with self._lock:
            self._refresh_completed_process_locked()
            return self._snapshot_locked()

    async def start(
        self, request: WorkerSchedulerProcessStartRequest
    ) -> WorkerSchedulerProcessStatusResult:
        async with self._lock:
            if not self._settings.worker_scheduler_supervisor_enabled:
                self._status = VoiceAgentProcessStatus.DISABLED
                return self._snapshot_locked()
            self._refresh_completed_process_locked()
            if self._process is not None and self._process.returncode is None:
                if not request.force_restart:
                    return self._snapshot_locked()
                await self._terminate_locked()
                if self._process is not None and self._process.returncode is None:
                    return self._snapshot_locked()

            self._run_id = request.run_id
            self._execution_mode = request.execution_mode
            self._max_profiles = request.max_profiles
            self._poll_interval_seconds = request.poll_interval_seconds
            self._command = self._command_for(request)
            self._status = VoiceAgentProcessStatus.STARTING
            self._started_at = datetime.now(timezone.utc)
            self._stopped_at = None
            self._last_returncode = None
            self._last_error = None
            self._append_log(
                f"Starting local worker scheduler: {' '.join(self._command)}"
            )
            try:
                self._process = await asyncio.create_subprocess_exec(
                    *self._command,
                    cwd=PROJECT_ROOT,
                    env=self._subprocess_env(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
            except Exception as exc:
                self._process = None
                self._status = VoiceAgentProcessStatus.FAILED
                self._stopped_at = datetime.now(timezone.utc)
                self._last_error = self._sanitize_log_line(
                    f"Failed to start local worker scheduler: {exc}"
                )
                self._append_log(self._last_error)
                return self._snapshot_locked()
            self._status = VoiceAgentProcessStatus.RUNNING
            self._start_reader_task_locked()
            return self._snapshot_locked()

    async def stop(self) -> WorkerSchedulerProcessStatusResult:
        async with self._lock:
            await self._terminate_locked()
            return self._snapshot_locked()

    def _base_command(self) -> list[str]:
        return [sys.executable, "-m", "all_about_llms.cli", "run-worker-scheduler"]

    def _command_for(self, request: WorkerSchedulerProcessStartRequest) -> list[str]:
        return [
            *self._base_command(),
            "--watch",
            "--run-id",
            str(request.run_id),
            "--execution-mode",
            request.execution_mode.value,
            "--max-profiles",
            str(request.max_profiles),
            "--poll-interval-seconds",
            self._format_poll_interval(request.poll_interval_seconds),
        ]

    def _subprocess_env(self) -> dict[str, str]:
        env = dict(os.environ)
        source_path = str(PROJECT_ROOT / "src")
        current = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            source_path if not current else f"{source_path}{os.pathsep}{current}"
        )
        return env

    def _start_reader_task_locked(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        task = asyncio.create_task(self._read_stdout(process))
        self._reader_tasks.add(task)
        task.add_done_callback(self._reader_tasks.discard)

    async def _read_stdout(self, process: asyncio.subprocess.Process) -> None:
        if process.stdout is None:
            return
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            self._append_log(line.decode("utf-8", errors="replace").rstrip())

    async def _terminate_locked(self) -> None:
        process = self._process
        if process is None:
            if self._status != VoiceAgentProcessStatus.DISABLED:
                self._status = VoiceAgentProcessStatus.STOPPED
            return
        stopped_by_supervisor = process.returncode is None
        stop_error: str | None = None
        if process.returncode is None:
            try:
                process.terminate()
            except (ProcessLookupError, OSError) as exc:
                stop_error = f"terminate failed: {exc}"
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except (ProcessLookupError, OSError) as exc:
                    stop_error = f"kill failed: {exc}"
                except Exception as exc:
                    stop_error = f"wait after kill failed: {exc}"
            except Exception as exc:
                stop_error = f"wait failed: {exc}"
        if process.returncode is None:
            self._status = VoiceAgentProcessStatus.RUNNING
            self._last_error = self._sanitize_log_line(
                stop_error or "process is still running after stop request"
            )
            self._append_log(
                f"Unable to stop local worker scheduler cleanly: {self._last_error}."
            )
            return
        self._stopped_at = datetime.now(timezone.utc)
        self._last_returncode = process.returncode
        self._last_error = None
        if stopped_by_supervisor:
            self._status = VoiceAgentProcessStatus.STOPPED
            self._append_log(
                "Local worker scheduler stopped by supervisor with return code "
                f"{process.returncode}."
            )
        else:
            self._status = (
                VoiceAgentProcessStatus.EXITED
                if process.returncode == 0
                else VoiceAgentProcessStatus.FAILED
            )
            self._append_log(
                f"Local worker scheduler stopped with return code {process.returncode}."
            )
        await self._drain_reader_tasks_locked()
        self._process = None

    async def _drain_reader_tasks_locked(self) -> None:
        tasks = list(self._reader_tasks)
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._reader_tasks.clear()

    def _refresh_completed_process_locked(self) -> None:
        process = self._process
        if process is None:
            if (
                self._settings.worker_scheduler_supervisor_enabled
                and self._status == VoiceAgentProcessStatus.DISABLED
            ):
                self._status = VoiceAgentProcessStatus.STOPPED
            return
        if process.returncode is None:
            self._status = VoiceAgentProcessStatus.RUNNING
            return
        self._stopped_at = self._stopped_at or datetime.now(timezone.utc)
        self._last_returncode = process.returncode
        self._last_error = None
        self._status = (
            VoiceAgentProcessStatus.EXITED
            if process.returncode == 0
            else VoiceAgentProcessStatus.FAILED
        )

    def _snapshot_locked(self) -> WorkerSchedulerProcessStatusResult:
        process = self._process
        running = process is not None and process.returncode is None
        returncode = process.returncode if process is not None else self._last_returncode
        return WorkerSchedulerProcessStatusResult(
            enabled=self._settings.worker_scheduler_supervisor_enabled,
            status=self._status,
            running=running,
            pid=process.pid if running else None,
            returncode=returncode,
            last_error=self._last_error,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            run_id=self._run_id,
            execution_mode=self._execution_mode,
            max_profiles=self._max_profiles,
            poll_interval_seconds=self._poll_interval_seconds,
            command=self._command,
            log_tail=list(self._logs),
            next_actions=self._next_actions_locked(),
            summary=self._summary_locked(running=running, returncode=returncode),
        )

    def _next_actions_locked(self) -> list[str]:
        if not self._settings.worker_scheduler_supervisor_enabled:
            return [
                "Set WORKER_SCHEDULER_SUPERVISOR_ENABLED=true for local scheduler process control."
            ]
        if self._status == VoiceAgentProcessStatus.RUNNING:
            if self._last_error:
                return [
                    "Retry Stop scheduler.",
                    "If the process remains running, stop it outside the app and inspect the log tail.",
                ]
            return ["Leave this process running for always-on Autopilot wakeups."]
        if self._status in {
            VoiceAgentProcessStatus.FAILED,
            VoiceAgentProcessStatus.EXITED,
        }:
            return [
                "Inspect the local worker-scheduler log tail.",
                "Fix provider, Postgres, or worker-profile configuration, then start the scheduler again.",
            ]
        return ["Start the local worker scheduler for an active Autopilot run."]

    def _summary_locked(self, *, running: bool, returncode: int | None) -> str:
        if not self._settings.worker_scheduler_supervisor_enabled:
            return "Local worker scheduler supervision is disabled."
        if running:
            if self._last_error:
                return (
                    "Local worker scheduler is still running after a control error: "
                    f"{self._last_error}."
                )
            return "Local worker scheduler process is running."
        if self._status == VoiceAgentProcessStatus.FAILED:
            return f"Local worker scheduler process failed with return code {returncode}."
        if self._status == VoiceAgentProcessStatus.EXITED:
            return "Local worker scheduler process exited."
        return "Local worker scheduler process is stopped."

    def _append_log(self, line: str) -> None:
        self._logs.append(self._sanitize_log_line(line))

    def _sanitize_log_line(self, line: str) -> str:
        sanitized = line
        for secret in self._secret_values:
            sanitized = sanitized.replace(secret, "[redacted]")
        return sanitized

    def _format_poll_interval(self, value: float) -> str:
        if float(value).is_integer():
            return str(int(value))
        return str(value)
