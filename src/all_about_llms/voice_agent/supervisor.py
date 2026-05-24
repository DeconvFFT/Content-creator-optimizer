import asyncio
import os
import sys
from collections import deque
from datetime import datetime, timezone

from all_about_llms.config import PROJECT_ROOT, Settings
from all_about_llms.contracts import (
    LocalLiveKitProcessMode,
    LocalLiveKitProcessStartRequest,
    LocalLiveKitProcessStatusResult,
    VoiceAgentProcessStartRequest,
    VoiceAgentProcessStatus,
    VoiceAgentProcessStatusResult,
)


class LocalVoiceAgentSupervisor:
    """Small local process supervisor for the OpenRouter/Kokoro LiveKit participant."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._process: asyncio.subprocess.Process | None = None
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._last_returncode: int | None = None
        self._last_error: str | None = None
        self._status = (
            VoiceAgentProcessStatus.STOPPED
            if settings.voice_agent_supervisor_enabled
            else VoiceAgentProcessStatus.DISABLED
        )
        self._logs: deque[str] = deque(maxlen=settings.voice_agent_supervisor_log_lines)
        self._lock = asyncio.Lock()
        self._reader_tasks: set[asyncio.Task] = set()
        self._command: list[str] = self._base_command()
        self._secret_values = tuple(
            value
            for value in (
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

    async def status(self) -> VoiceAgentProcessStatusResult:
        async with self._lock:
            self._refresh_completed_process_locked()
            return self._snapshot_locked()

    async def start(
        self, request: VoiceAgentProcessStartRequest
    ) -> VoiceAgentProcessStatusResult:
        async with self._lock:
            if not self._settings.voice_agent_supervisor_enabled:
                self._status = VoiceAgentProcessStatus.DISABLED
                return self._snapshot_locked()
            self._refresh_completed_process_locked()
            if self._process is not None and self._process.returncode is None:
                if not request.force_restart:
                    return self._snapshot_locked()
                await self._terminate_locked()
                if self._process is not None and self._process.returncode is None:
                    return self._snapshot_locked()
            self._command = self._command_for(request)
            self._status = VoiceAgentProcessStatus.STARTING
            self._started_at = datetime.now(timezone.utc)
            self._stopped_at = None
            self._last_returncode = None
            self._last_error = None
            self._append_log(f"Starting local voice agent: {' '.join(self._command)}")
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
                    f"Failed to start local voice agent: {exc}"
                )
                self._append_log(self._last_error)
                return self._snapshot_locked()
            self._status = VoiceAgentProcessStatus.RUNNING
            self._start_reader_task_locked()
            return self._snapshot_locked()

    async def stop(self) -> VoiceAgentProcessStatusResult:
        async with self._lock:
            await self._terminate_locked()
            return self._snapshot_locked()

    def _base_command(self) -> list[str]:
        return [sys.executable, "-m", "all_about_llms.cli", "run-voice-agent"]

    def _command_for(self, request: VoiceAgentProcessStartRequest) -> list[str]:
        command = self._base_command()
        if request.dev:
            command.append("--dev")
        if request.unregistered:
            command.append("--unregistered")
        return command

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
            self._append_log(f"Unable to stop local voice agent cleanly: {self._last_error}.")
            return
        self._stopped_at = datetime.now(timezone.utc)
        self._last_returncode = process.returncode
        self._last_error = None
        if stopped_by_supervisor:
            self._status = VoiceAgentProcessStatus.STOPPED
            self._append_log(
                f"Local voice agent stopped by supervisor with return code {process.returncode}."
            )
        else:
            self._status = (
                VoiceAgentProcessStatus.EXITED
                if process.returncode == 0
                else VoiceAgentProcessStatus.FAILED
            )
            self._append_log(
                f"Local voice agent stopped with return code {process.returncode}."
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
                self._settings.voice_agent_supervisor_enabled
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

    def _snapshot_locked(self) -> VoiceAgentProcessStatusResult:
        process = self._process
        running = process is not None and process.returncode is None
        returncode = process.returncode if process is not None else self._last_returncode
        return VoiceAgentProcessStatusResult(
            enabled=self._settings.voice_agent_supervisor_enabled,
            status=self._status,
            running=running,
            pid=process.pid if running else None,
            returncode=returncode,
            last_error=self._last_error,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            command=[self._sanitize_process_text(part) for part in self._command],
            log_tail=[self._sanitize_process_text(line) for line in self._logs],
            next_actions=self._next_actions_locked(),
            summary=self._summary_locked(running=running, returncode=returncode),
        )

    def _next_actions_locked(self) -> list[str]:
        if not self._settings.voice_agent_supervisor_enabled:
            return ["Set VOICE_AGENT_SUPERVISOR_ENABLED=true for local process control."]
        if self._status == VoiceAgentProcessStatus.RUNNING:
            if self._last_error:
                return [
                    "Retry Stop agent.",
                    "If the process remains running, stop it outside the app and inspect the log tail.",
                ]
            return ["Join an OpenRouter/Kokoro LiveKit voice room and check participant presence."]
        if self._status in {
            VoiceAgentProcessStatus.FAILED,
            VoiceAgentProcessStatus.EXITED,
        }:
            return [
                "Inspect the local voice-agent log tail.",
                "Fix LiveKit/OpenRouter/Kokoro configuration, then start the agent again.",
            ]
        return ["Start the local OpenRouter/Kokoro LiveKit agent process."]

    def _summary_locked(self, *, running: bool, returncode: int | None) -> str:
        if not self._settings.voice_agent_supervisor_enabled:
            return "Local voice-agent process supervision is disabled."
        if running:
            if self._last_error:
                return f"Local voice-agent process is still running after a control error: {self._last_error}."
            return "Local OpenRouter/Kokoro LiveKit voice-agent process is running."
        if self._status == VoiceAgentProcessStatus.FAILED:
            return f"Local voice-agent process failed with return code {returncode}."
        if self._status == VoiceAgentProcessStatus.EXITED:
            return "Local voice-agent process exited."
        return "Local OpenRouter/Kokoro LiveKit voice-agent process is stopped."

    def _append_log(self, line: str) -> None:
        self._logs.append(self._sanitize_log_line(line))

    def _sanitize_log_line(self, line: str) -> str:
        sanitized = self._sanitize_process_text(line)
        for secret in self._secret_values:
            sanitized = sanitized.replace(secret, "[redacted]")
        return sanitized

    def _sanitize_process_text(self, text: str) -> str:
        sanitized = str(text)
        if sys.executable:
            sanitized = sanitized.replace(sys.executable, "<workspace-python>")
        sanitized = sanitized.replace(str(PROJECT_ROOT), "<workspace-root>")
        return sanitized


class LocalLiveKitDevServerSupervisor:
    """Small local process supervisor for the LiveKit dev transport server."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._process: asyncio.subprocess.Process | None = None
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._last_returncode: int | None = None
        self._last_error: str | None = None
        self._status = (
            VoiceAgentProcessStatus.STOPPED
            if settings.local_livekit_supervisor_enabled
            else VoiceAgentProcessStatus.DISABLED
        )
        self._mode = LocalLiveKitProcessMode.NATIVE
        self._logs: deque[str] = deque(maxlen=settings.local_livekit_supervisor_log_lines)
        self._lock = asyncio.Lock()
        self._reader_tasks: set[asyncio.Task] = set()
        self._command: list[str] = self._command_for_mode(self._mode)
        self._secret_values = tuple(
            value
            for value in (
                settings.livekit_api_key,
                settings.livekit_api_secret,
            )
            if value and len(value) >= 4
        )

    async def status(self) -> LocalLiveKitProcessStatusResult:
        async with self._lock:
            self._refresh_completed_process_locked()
            return self._snapshot_locked()

    async def start(
        self, request: LocalLiveKitProcessStartRequest
    ) -> LocalLiveKitProcessStatusResult:
        async with self._lock:
            if not self._settings.local_livekit_supervisor_enabled:
                self._status = VoiceAgentProcessStatus.DISABLED
                return self._snapshot_locked()
            self._refresh_completed_process_locked()
            if self._process is not None and self._process.returncode is None:
                if not request.force_restart:
                    return self._snapshot_locked()
                await self._terminate_locked()
                if self._process is not None and self._process.returncode is None:
                    return self._snapshot_locked()
            self._mode = request.mode
            self._command = self._command_for_mode(request.mode)
            self._status = VoiceAgentProcessStatus.STARTING
            self._started_at = datetime.now(timezone.utc)
            self._stopped_at = None
            self._last_returncode = None
            self._last_error = None
            self._append_log(f"Starting local LiveKit dev server: {' '.join(self._command)}")
            try:
                self._process = await asyncio.create_subprocess_exec(
                    *self._command,
                    cwd=PROJECT_ROOT,
                    env=dict(os.environ),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
            except Exception as exc:
                self._process = None
                self._status = VoiceAgentProcessStatus.FAILED
                self._stopped_at = datetime.now(timezone.utc)
                self._last_error = self._sanitize_log_line(
                    f"Failed to start local LiveKit dev server: {exc}"
                )
                self._append_log(self._last_error)
                return self._snapshot_locked()
            self._status = VoiceAgentProcessStatus.RUNNING
            self._start_reader_task_locked()
            return self._snapshot_locked()

    async def stop(self) -> LocalLiveKitProcessStatusResult:
        async with self._lock:
            await self._terminate_locked()
            return self._snapshot_locked()

    def _command_for_mode(self, mode: LocalLiveKitProcessMode) -> list[str]:
        if mode == LocalLiveKitProcessMode.COMPOSE:
            return ["docker", "compose", "--profile", "voice", "up", "livekit"]
        return ["livekit-server", "--dev"]

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
                f"Unable to stop local LiveKit dev server cleanly: {self._last_error}."
            )
            return
        self._stopped_at = datetime.now(timezone.utc)
        self._last_returncode = process.returncode
        self._last_error = None
        if stopped_by_supervisor:
            self._status = VoiceAgentProcessStatus.STOPPED
            self._append_log(
                f"Local LiveKit dev server stopped by supervisor with return code {process.returncode}."
            )
        else:
            self._status = (
                VoiceAgentProcessStatus.EXITED
                if process.returncode == 0
                else VoiceAgentProcessStatus.FAILED
            )
            self._append_log(
                f"Local LiveKit dev server stopped with return code {process.returncode}."
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
                self._settings.local_livekit_supervisor_enabled
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

    def _snapshot_locked(self) -> LocalLiveKitProcessStatusResult:
        process = self._process
        running = process is not None and process.returncode is None
        returncode = process.returncode if process is not None else self._last_returncode
        return LocalLiveKitProcessStatusResult(
            enabled=self._settings.local_livekit_supervisor_enabled,
            mode=self._mode,
            status=self._status,
            running=running,
            pid=process.pid if running else None,
            returncode=returncode,
            last_error=self._last_error,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            command=self._command,
            log_tail=list(self._logs),
            next_actions=self._next_actions_locked(),
            summary=self._summary_locked(running=running, returncode=returncode),
        )

    def _next_actions_locked(self) -> list[str]:
        if not self._settings.local_livekit_supervisor_enabled:
            return ["Set LOCAL_LIVEKIT_SUPERVISOR_ENABLED=true for local LiveKit process control."]
        if self._status == VoiceAgentProcessStatus.RUNNING:
            if self._last_error:
                return [
                    "Retry Stop LiveKit.",
                    "If the process remains running, stop it outside the app and inspect the log tail.",
                ]
            return [
                "Run voice runtime preflight to verify LiveKit RoomService connectivity.",
                "Start the OpenRouter/Kokoro LiveKit agent process after transport is reachable.",
            ]
        if self._status in {
            VoiceAgentProcessStatus.FAILED,
            VoiceAgentProcessStatus.EXITED,
        }:
            return [
                "Inspect the local LiveKit log tail.",
                "Install `livekit-server` or start with Compose mode, then retry.",
            ]
        return ["Start local LiveKit dev mode before joining a voice room."]

    def _summary_locked(self, *, running: bool, returncode: int | None) -> str:
        if not self._settings.local_livekit_supervisor_enabled:
            return "Local LiveKit dev-server supervision is disabled."
        if running:
            if self._last_error:
                return f"Local LiveKit dev server is still running after a control error: {self._last_error}."
            return "Local LiveKit dev server is running."
        if self._status == VoiceAgentProcessStatus.FAILED:
            return f"Local LiveKit dev server failed with return code {returncode}."
        if self._status == VoiceAgentProcessStatus.EXITED:
            return "Local LiveKit dev server exited."
        return "Local LiveKit dev server is stopped."

    def _append_log(self, line: str) -> None:
        self._logs.append(self._sanitize_log_line(line))

    def _sanitize_log_line(self, line: str) -> str:
        sanitized = line
        for secret in self._secret_values:
            sanitized = sanitized.replace(secret, "[redacted]")
        return sanitized
