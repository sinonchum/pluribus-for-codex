"""Bounded, non-writing Codex CLI preflight."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import shutil
import time

from .config import CodexConfig
from .models import CodexPreflightResult


def build_preflight_args() -> tuple[str, ...]:
    """Return the minimal non-writing probe supported by Codex CLI."""

    return ("--version",)


def _decode(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _failure(
    *,
    executable: str | None,
    started: float,
    error_code: str,
    message: str,
    stdout: str = "",
    stderr: str = "",
    exit_code: int | None = None,
) -> CodexPreflightResult:
    return CodexPreflightResult(
        available=False,
        executable=executable,
        version=None,
        probe_succeeded=False,
        exit_code=exit_code,
        duration_seconds=time.monotonic() - started,
        stdout=stdout,
        stderr=stderr,
        error_code=error_code,
        error_message=message,
    )


async def run_preflight(
    config: CodexConfig,
    *,
    resolver: Callable[[str], str | None] = shutil.which,
) -> CodexPreflightResult:
    """Resolve and execute a bounded ``codex --version`` probe."""

    started = time.monotonic()
    executable = resolver(config.executable)
    if executable is None:
        return _failure(
            executable=None,
            started=started,
            error_code="executable_missing",
            message=(
                f"Codex CLI executable {config.executable!r} was not found on PATH. "
                "Install Codex CLI or configure CODEX_EXECUTABLE."
            ),
        )
    try:
        process = await asyncio.create_subprocess_exec(
            executable,
            *build_preflight_args(),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError:
        return _failure(
            executable=executable,
            started=started,
            error_code="cannot_start",
            message="Codex CLI was found but could not be started. Reinstall it or configure CODEX_EXECUTABLE.",
        )
    try:
        communication = asyncio.create_task(process.communicate())
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            asyncio.shield(communication), timeout=config.preflight_timeout_seconds
        )
    except TimeoutError:
        process.kill()
        await process.wait()
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                asyncio.shield(communication), timeout=config.termination_grace_seconds
            )
        except (TimeoutError, OSError, RuntimeError, asyncio.CancelledError):
            communication.cancel()
            stdout_bytes, stderr_bytes = b"", b""
        return _failure(
            executable=executable,
            started=started,
            error_code="timeout",
            message=(
                f"Codex CLI preflight timed out after "
                f"{config.preflight_timeout_seconds:g} seconds."
            ),
            stdout=_decode(stdout_bytes),
            stderr=_decode(stderr_bytes),
        )
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        communication.cancel()
        return _failure(
            executable=executable,
            started=started,
            error_code="cancelled",
            message="Codex CLI preflight was cancelled.",
        )
    stdout = _decode(stdout_bytes)
    stderr = _decode(stderr_bytes)
    if process.returncode != 0:
        lowered = stderr.lower()
        authentication = "auth" in lowered or "login" in lowered or "credential" in lowered
        packaged_binary_missing = "enoent" in lowered and "spawn" in lowered
        return _failure(
            executable=executable,
            started=started,
            error_code=(
                "authentication_failed"
                if authentication
                else "cannot_start"
                if packaged_binary_missing
                else "probe_failed"
            ),
            message=(
                "Codex CLI preflight reported an authentication problem. Run the Codex login flow."
                if authentication
                else "Codex CLI launcher could not start its packaged binary. Reinstall Codex CLI."
                if packaged_binary_missing
                else f"Codex CLI preflight exited with code {process.returncode}."
            ),
            stdout=stdout,
            stderr=stderr,
            exit_code=process.returncode,
        )
    version = stdout.strip().splitlines()[0] if stdout.strip() else None
    return CodexPreflightResult(
        available=True,
        executable=executable,
        version=version,
        probe_succeeded=True,
        exit_code=process.returncode,
        duration_seconds=time.monotonic() - started,
        stdout=stdout,
        stderr=stderr,
        error_code=None,
        error_message=None,
    )
