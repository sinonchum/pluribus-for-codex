"""Tests for shell-free, bounded verification execution."""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from app.verification import (
    CommandResult,
    CommandSpec,
    CommandStatus,
    VerificationTerminalState,
    evaluate_terminal_state,
    run_command,
    run_verification,
)


def _python(
    cwd: Path,
    code: str,
    *args: str,
    required: bool = True,
    timeout: float = 2.0,
    cap: int = 65_536,
) -> CommandSpec:
    return CommandSpec(
        executable=sys.executable,
        args=("-c", code, *args),
        cwd=cwd,
        timeout_seconds=timeout,
        required=required,
        output_limit_bytes=cap,
        name="helper",
    )


def test_pass_fail_explicit_cwd_and_hashes(tmp_path: Path) -> None:
    cwd = tmp_path / "working path with spaces"
    cwd.mkdir()
    passed = asyncio.run(
        run_command(
            _python(
                cwd,
                "import os,sys; print(os.getcwd()); print('warning', file=sys.stderr)",
            )
        )
    )
    failed = asyncio.run(run_command(_python(cwd, "raise SystemExit(7)")))

    assert passed.status is CommandStatus.PASSED
    assert passed.exit_code == 0
    assert str(cwd) in passed.stdout
    expected_stderr = f"warning{os.linesep}"
    assert passed.stderr == expected_stderr
    assert passed.stdout_sha256 == hashlib.sha256(passed.stdout.encode()).hexdigest()
    assert passed.stderr_sha256 == hashlib.sha256(expected_stderr.encode()).hexdigest()
    assert len(passed.command_sha256) == 64
    assert passed.duration_seconds >= 0
    assert failed.status is CommandStatus.FAILED
    assert failed.exit_code == 7


def test_argument_is_not_interpreted_by_a_shell(tmp_path: Path) -> None:
    marker = tmp_path / "injected"
    malicious = f"; touch {marker} ; $(touch {marker})"
    result = asyncio.run(
        run_command(_python(tmp_path, "import sys; print(sys.argv[1])", malicious))
    )

    assert result.stdout.strip() == malicious
    assert not marker.exists()


def test_stdout_and_stderr_are_capped_but_hash_full_streams(tmp_path: Path) -> None:
    stdout = b"a" * 10_000
    stderr = b"b" * 12_000
    result = asyncio.run(
        run_command(
            _python(
                tmp_path,
                "import sys; sys.stdout.write('a'*10000); sys.stderr.write('b'*12000)",
                cap=128,
            )
        )
    )

    assert len(result.stdout.encode()) == 128
    assert len(result.stderr.encode()) == 128
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True
    assert result.stdout_sha256 == hashlib.sha256(stdout).hexdigest()
    assert result.stderr_sha256 == hashlib.sha256(stderr).hexdigest()


def test_timeout_terminates_process_and_preserves_partial_output(
    tmp_path: Path,
) -> None:
    result = asyncio.run(
        run_command(
            _python(
                tmp_path,
                "import time; print('started', flush=True); time.sleep(5)",
                timeout=0.1,
            )
        )
    )

    assert result.status is CommandStatus.TIMED_OUT
    assert result.exit_code is not None
    assert result.stdout == f"started{os.linesep}"
    assert result.duration_seconds < 2


def test_cancellation_terminates_and_reaps_child(tmp_path: Path) -> None:
    marker = tmp_path / "child-finished"

    async def exercise() -> None:
        task = asyncio.create_task(
            run_command(
                _python(
                    tmp_path,
                    "import pathlib,sys,time; time.sleep(.4); "
                    "pathlib.Path(sys.argv[1]).touch()",
                    str(marker),
                    timeout=5,
                )
            )
        )
        await asyncio.sleep(0.08)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0.5)

    asyncio.run(exercise())
    assert not marker.exists()


def _result(tmp_path: Path, *, required: bool, status: CommandStatus) -> CommandResult:
    spec = _python(tmp_path, "pass", required=required)
    return CommandResult(
        spec=spec,
        status=status,
        exit_code=0 if status is CommandStatus.PASSED else 1,
        duration_seconds=0.1,
        stdout="",
        stderr="",
        stdout_sha256=hashlib.sha256(b"").hexdigest(),
        stderr_sha256=hashlib.sha256(b"").hexdigest(),
        command_sha256="0" * 64,
    )


def test_required_optional_terminal_policy(tmp_path: Path) -> None:
    required_pass = _result(tmp_path, required=True, status=CommandStatus.PASSED)
    optional_pass = _result(tmp_path, required=False, status=CommandStatus.PASSED)
    optional_fail = replace(optional_pass, status=CommandStatus.FAILED, exit_code=1)
    required_timeout = replace(
        required_pass, status=CommandStatus.TIMED_OUT, exit_code=-1
    )

    assert (
        evaluate_terminal_state([required_pass, optional_pass])
        is VerificationTerminalState.VERIFIED
    )
    assert (
        evaluate_terminal_state([required_pass, optional_fail])
        is VerificationTerminalState.PARTIALLY_VERIFIED
    )
    assert (
        evaluate_terminal_state([required_timeout, optional_pass])
        is VerificationTerminalState.FAILED
    )


def test_run_verification_keeps_declaration_order(tmp_path: Path) -> None:
    commands = [
        _python(tmp_path, "print('first')"),
        _python(tmp_path, "print('second')", required=False),
    ]
    summary = asyncio.run(run_verification(commands))

    assert [result.stdout.strip() for result in summary.results] == ["first", "second"]
    assert summary.terminal_state is VerificationTerminalState.VERIFIED


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"executable": ""}, "executable"),
        ({"timeout_seconds": 0}, "timeout_seconds"),
        ({"output_limit_bytes": -1}, "output_limit_bytes"),
    ],
)
def test_invalid_command_specs_are_rejected(
    tmp_path: Path, kwargs: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "executable": sys.executable,
        "args": (),
        "cwd": tmp_path,
    }
    values.update(kwargs)
    with pytest.raises(ValueError, match=message):
        CommandSpec(**values)  # type: ignore[arg-type]


def test_missing_cwd_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        asyncio.run(run_command(_python(tmp_path / "missing", "pass")))
