"""Execute verification commands without involving a command shell."""

from __future__ import annotations

import asyncio
import hashlib
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

_READ_SIZE: Final = 64 * 1024
_TERMINATION_GRACE_SECONDS: Final = 0.5


class CommandStatus(StrEnum):
    """Outcome of one verification command."""

    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class VerificationTerminalState(StrEnum):
    """Policy-derived state of a complete verification run."""

    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """A command represented as an executable and an argument vector.

    ``cwd`` is mandatory by design. The command is always executed directly;
    strings are never parsed by a shell.
    """

    executable: str
    args: tuple[str, ...]
    cwd: Path
    timeout_seconds: float = 60.0
    required: bool = True
    output_limit_bytes: int = 64 * 1024
    name: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "cwd", Path(self.cwd))
        object.__setattr__(self, "args", tuple(self.args))
        if not self.executable or "\x00" in self.executable:
            raise ValueError("executable must be a non-empty string without NUL")
        if any(not isinstance(arg, str) or "\x00" in arg for arg in self.args):
            raise ValueError("args must contain only strings without NUL")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.output_limit_bytes < 0:
            raise ValueError("output_limit_bytes cannot be negative")

    @property
    def argv(self) -> tuple[str, ...]:
        return (self.executable, *self.args)


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Bounded evidence captured from one command."""

    spec: CommandSpec
    status: CommandStatus
    exit_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    stdout_sha256: str
    stderr_sha256: str
    command_sha256: str
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    @property
    def passed(self) -> bool:
        return self.status is CommandStatus.PASSED


@dataclass(frozen=True, slots=True)
class VerificationSummary:
    """Command results plus their policy-derived terminal state."""

    results: tuple[CommandResult, ...]
    terminal_state: VerificationTerminalState


class _BoundedCapture:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._stored = bytearray()
        self._hash = hashlib.sha256()
        self.truncated = False

    def add(self, chunk: bytes) -> None:
        self._hash.update(chunk)
        remaining = self._limit - len(self._stored)
        if remaining > 0:
            self._stored.extend(chunk[:remaining])
        if len(chunk) > max(remaining, 0):
            self.truncated = True

    @property
    def text(self) -> str:
        return self._stored.decode("utf-8", errors="replace")

    @property
    def sha256(self) -> str:
        return self._hash.hexdigest()


async def _drain(stream: asyncio.StreamReader | None, capture: _BoundedCapture) -> None:
    if stream is None:
        return
    while chunk := await stream.read(_READ_SIZE):
        capture.add(chunk)


async def _terminate(process: asyncio.subprocess.Process) -> None:
    """Terminate a process (and its POSIX process group) and reap it."""
    if process.returncode is not None:
        await process.wait()
        return

    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        pass

    try:
        await asyncio.wait_for(process.wait(), _TERMINATION_GRACE_SECONDS)
        return
    except TimeoutError:
        pass

    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        pass
    await process.wait()


def _command_hash(spec: CommandSpec) -> str:
    payload = b"\0".join(
        os.fsencode(part) for part in (*spec.argv, os.fspath(spec.cwd))
    )
    return hashlib.sha256(payload).hexdigest()


async def run_command(spec: CommandSpec) -> CommandResult:
    """Run one command with bounded output, timeout, and safe cancellation.

    Cancellation terminates and reaps the child before propagating
    :class:`asyncio.CancelledError` to the caller.
    """
    if not spec.cwd.is_dir():
        raise NotADirectoryError(spec.cwd)

    creationflags = 0
    start_new_session = os.name == "posix"
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    started = time.monotonic()
    creation = asyncio.create_task(
        asyncio.create_subprocess_exec(
            *spec.argv,
            cwd=spec.cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=start_new_session,
            creationflags=creationflags,
        )
    )
    try:
        process = await asyncio.shield(creation)
    except asyncio.CancelledError:
        # Process creation runs in an executor on some event loops. Shield it so a
        # cancellation in that small window cannot orphan a newly-created child.
        process = await creation
        await _terminate(process)
        raise
    stdout = _BoundedCapture(spec.output_limit_bytes)
    stderr = _BoundedCapture(spec.output_limit_bytes)
    readers = [
        asyncio.create_task(_drain(process.stdout, stdout)),
        asyncio.create_task(_drain(process.stderr, stderr)),
    ]
    timed_out = False

    try:
        try:
            await asyncio.wait_for(process.wait(), spec.timeout_seconds)
        except TimeoutError:
            timed_out = True
            await _terminate(process)
        await asyncio.gather(*readers)
    except asyncio.CancelledError:
        await _terminate(process)
        await asyncio.gather(*readers, return_exceptions=True)
        raise
    except BaseException:
        await _terminate(process)
        await asyncio.gather(*readers, return_exceptions=True)
        raise

    if timed_out:
        status = CommandStatus.TIMED_OUT
    elif process.returncode == 0:
        status = CommandStatus.PASSED
    else:
        status = CommandStatus.FAILED

    return CommandResult(
        spec=spec,
        status=status,
        exit_code=process.returncode,
        duration_seconds=time.monotonic() - started,
        stdout=stdout.text,
        stderr=stderr.text,
        stdout_sha256=stdout.sha256,
        stderr_sha256=stderr.sha256,
        command_sha256=_command_hash(spec),
        stdout_truncated=stdout.truncated,
        stderr_truncated=stderr.truncated,
    )


def evaluate_terminal_state(
    results: tuple[CommandResult, ...] | list[CommandResult],
) -> VerificationTerminalState:
    """Apply required/optional verification policy."""
    if any(result.spec.required and not result.passed for result in results):
        return VerificationTerminalState.FAILED
    if any(not result.spec.required and not result.passed for result in results):
        return VerificationTerminalState.PARTIALLY_VERIFIED
    return VerificationTerminalState.VERIFIED


async def run_verification(
    commands: tuple[CommandSpec, ...] | list[CommandSpec],
) -> VerificationSummary:
    """Run commands in declaration order and evaluate the terminal policy."""
    collected: list[CommandResult] = []
    for command in commands:
        collected.append(await run_command(command))
    results = tuple(collected)
    return VerificationSummary(results, evaluate_terminal_state(results))
