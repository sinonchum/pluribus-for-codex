from __future__ import annotations

import sys
from pathlib import Path

from app.usage import VerificationProof
from app.usage.sanitization import sanitize_output
from app.verification.runner import CommandSpec, CommandStatus, run_command

_OUTPUT_LIMIT_BYTES = 16_384
_TIMEOUT_SECONDS = 30


async def run_coordinator_verification(
    fixture_root: Path, command: tuple[str, ...]
) -> VerificationProof:
    if type(command) is not tuple or not command:
        raise ValueError("command must be a non-empty tuple of strings")
    if any(not isinstance(part, str) or not part for part in command):
        raise ValueError("command must be a non-empty tuple of strings")

    fixture_root = Path(fixture_root).resolve()
    executable = command[0]
    args = command[1:]
    if executable == "pytest":
        executable = sys.executable
        args = ("-m", "pytest", *args)
    result = await run_command(
        CommandSpec(
            executable=executable,
            args=args,
            cwd=fixture_root,
            timeout_seconds=_TIMEOUT_SECONDS,
            output_limit_bytes=_OUTPUT_LIMIT_BYTES,
            name="coordinator-verification",
        )
    )
    if result.status is not CommandStatus.PASSED or result.exit_code != 0:
        raise RuntimeError("Coordinator verification failed")

    output = f"{result.stdout}\n{result.stderr}"
    return VerificationProof(
        command=command,
        exit_code=result.exit_code,
        output_excerpt=sanitize_output(output, paths=(fixture_root,)),
    )


__all__ = ["run_coordinator_verification"]
