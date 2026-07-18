"""Bounded asynchronous Codex subprocess execution."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

from .config import CodexConfig
from .models import CodexRunRequest, CodexRunResult
from .parser import parse_handoff


def build_agent_args(request: CodexRunRequest) -> tuple[str, ...]:
    """Build arguments for a non-interactive turn using prompt input on stdin."""

    return ("exec", *request.extra_args, "-")


def _bounded_decode(value: bytes, limit: int) -> tuple[str, bool]:
    truncated = len(value) > limit
    retained = value[:limit]
    return retained.decode("utf-8", errors="replace"), truncated


async def _stop_process(process: asyncio.subprocess.Process, grace: float) -> None:
    if process.returncode is not None:
        return
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=grace)
    except TimeoutError:
        process.kill()
        await process.wait()


async def _drain_after_stop(
    communication: asyncio.Task[tuple[bytes, bytes]], grace: float
) -> tuple[bytes, bytes]:
    try:
        return await asyncio.wait_for(asyncio.shield(communication), timeout=grace)
    except (TimeoutError, OSError, RuntimeError, asyncio.CancelledError):
        communication.cancel()
        return b"", b""


class CodexRunner:
    """Execute one Codex turn without shell interpolation."""

    def __init__(self, config: CodexConfig) -> None:
        self._config = config

    async def run(self, request: CodexRunRequest) -> CodexRunResult:
        if request.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        working_directory = request.working_directory.resolve()
        if not working_directory.is_dir():
            raise ValueError(f"Working directory does not exist: {working_directory}")
        command = (self._config.executable, *build_agent_args(request))
        started_at = datetime.now(UTC)
        started = time.monotonic()
        stdout_bytes = b""
        stderr_bytes = b""
        exit_code: int | None = None
        timed_out = False
        cancelled = False
        start_error: str | None = None

        try:
            process = await asyncio.create_subprocess_exec(
                command[0],
                *command[1:],
                cwd=str(working_directory),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError:
            process = None
            start_error = "Codex CLI could not be started. Check CODEX_EXECUTABLE and the installation."

        if process is not None:
            communication = asyncio.create_task(
                process.communicate(request.prompt.encode("utf-8"))
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    asyncio.shield(communication), timeout=request.timeout_seconds
                )
            except TimeoutError:
                timed_out = True
                await _stop_process(process, self._config.termination_grace_seconds)
                stdout_bytes, stderr_bytes = await _drain_after_stop(
                    communication, self._config.termination_grace_seconds
                )
            except asyncio.CancelledError:
                cancelled = True
                await _stop_process(process, self._config.termination_grace_seconds)
                stdout_bytes, stderr_bytes = await _drain_after_stop(
                    communication, self._config.termination_grace_seconds
                )
            exit_code = process.returncode

        stdout, stdout_truncated = _bounded_decode(
            stdout_bytes, self._config.max_stdout_bytes
        )
        stderr, stderr_truncated = _bounded_decode(
            stderr_bytes, self._config.max_stderr_bytes
        )
        parsed = parse_handoff(stdout)
        finished_at = datetime.now(UTC)
        return CodexRunResult(
            command=command,
            working_directory=str(working_directory),
            role=request.role,
            mission_id=request.mission_id,
            agent_id=request.agent_id,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=time.monotonic() - started,
            exit_code=exit_code,
            timed_out=timed_out,
            cancelled=cancelled,
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            structured_handoff=parsed.handoff,
            parse_error=parsed.error,
            start_error=start_error,
        )
