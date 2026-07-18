from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


class GitCommandError(RuntimeError):
    """A Git process failed, timed out, or could not be started."""

    def __init__(
        self,
        command: tuple[str, ...],
        *,
        returncode: int | None = None,
        stderr: bytes = b"",
    ) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        detail = stderr.decode("utf-8", errors="replace").strip()
        message = f"Git command failed: {command!r}"
        if returncode is not None:
            message += f" (exit {returncode})"
        if detail:
            message += f": {detail}"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class GitResult:
    command: tuple[str, ...]
    stdout: bytes
    stderr: bytes
    returncode: int

    def text(self, *, strip: bool = True) -> str:
        value = self.stdout.decode("utf-8", errors="strict")
        return value.strip() if strip else value


@dataclass(frozen=True, slots=True)
class GitRunner:
    executable: str = "git"
    timeout_seconds: float = 30

    def run(
        self,
        repository: Path,
        arguments: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        environment: Mapping[str, str] | None = None,
        check: bool = True,
        timeout_seconds: float | None = None,
    ) -> GitResult:
        if isinstance(arguments, (str, bytes)):
            raise TypeError("Git arguments must be a sequence of individual strings")
        args = tuple(arguments)
        if not all(isinstance(argument, str) for argument in args):
            raise TypeError("Every Git argument must be a string")

        command = (self.executable, "-C", str(repository), *args)
        process_environment = os.environ.copy()
        if environment:
            process_environment.update(environment)
        try:
            completed = subprocess.run(
                command,
                input=input_bytes,
                capture_output=True,
                check=False,
                shell=False,
                env=process_environment,
                timeout=timeout_seconds or self.timeout_seconds,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as error:
            stderr = getattr(error, "stderr", None) or b""
            raise GitCommandError(command, stderr=stderr) from error

        result = GitResult(
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
        )
        if check and result.returncode != 0:
            raise GitCommandError(
                command,
                returncode=result.returncode,
                stderr=result.stderr,
            )
        return result

    def text(
        self,
        repository: Path,
        arguments: Sequence[str],
        **kwargs: object,
    ) -> str:
        return self.run(repository, arguments, **kwargs).text()
