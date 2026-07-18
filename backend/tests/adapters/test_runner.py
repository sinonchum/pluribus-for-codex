import asyncio
import json

import pytest

from backend.app.adapters.codex import CodexConfig, CodexRunRequest, CodexRunner
from backend.app.adapters.codex.runner import build_agent_args


class FakeProcess:
    def __init__(self, stdout=b"", stderr=b"", returncode=0, delay=0):
        self.stdout_data = stdout
        self.stderr_data = stderr
        self.returncode = None
        self.final_returncode = returncode
        self.delay = delay
        self.terminated = False
        self.killed = False
        self.input = None

    async def communicate(self, value):
        self.input = value
        await asyncio.sleep(self.delay)
        self.returncode = self.final_returncode
        return self.stdout_data, self.stderr_data

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    async def wait(self):
        return self.returncode


def request(tmp_path, **overrides):
    values = dict(
        prompt="hello",
        working_directory=tmp_path,
        timeout_seconds=1,
        role="scout",
        mission_id="m1",
        agent_id="a1",
    )
    values.update(overrides)
    return CodexRunRequest(**values)


def test_runner_uses_exec_argument_array_and_captures_output(monkeypatch, tmp_path):
    payload = json.dumps({"status": "completed", "summary": "ok"})
    process = FakeProcess(payload.encode(), "héllo".encode(), returncode=3)
    captured = []

    async def create(*args, **kwargs):
        captured.append((args, kwargs))
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    result = asyncio.run(CodexRunner(CodexConfig()).run(request(tmp_path)))
    assert captured[0][0] == ("codex", "exec", "-")
    assert "shell" not in captured[0][1]
    assert process.input == b"hello"
    assert result.exit_code == 3
    assert result.stderr == "héllo"
    assert result.structured_handoff is not None
    assert result.duration_seconds >= 0


def test_runner_enforces_timeout_and_preserves_partial_compatible_output(monkeypatch, tmp_path):
    process = FakeProcess(b"partial", b"warning", delay=0.1)

    async def create(*args, **kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    result = asyncio.run(
        CodexRunner(CodexConfig()).run(request(tmp_path, timeout_seconds=0.01))
    )
    assert result.timed_out
    assert process.terminated
    assert result.stdout == "partial"
    assert result.stderr == "warning"


def test_runner_handles_cancellation_and_invalid_directory(monkeypatch, tmp_path):
    process = FakeProcess(delay=10)

    async def create(*args, **kwargs):
        return process

    async def cancel_run():
        monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
        task = asyncio.create_task(
            CodexRunner(CodexConfig(termination_grace_seconds=0.01)).run(request(tmp_path))
        )
        await asyncio.sleep(0)
        task.cancel()
        return await task

    result = asyncio.run(cancel_run())
    assert result.cancelled
    assert process.terminated

    with pytest.raises(ValueError, match="does not exist"):
        asyncio.run(
            CodexRunner(CodexConfig()).run(request(tmp_path / "missing"))
        )


def test_output_is_bounded_and_invalid_utf8_is_replaced(monkeypatch, tmp_path):
    process = FakeProcess(b"12345\xff", b"abcdef")

    async def create(*args, **kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    config = CodexConfig(max_stdout_bytes=6, max_stderr_bytes=3)
    result = asyncio.run(CodexRunner(config).run(request(tmp_path)))
    assert "�" in result.stdout
    assert result.stderr == "abc"
    assert not result.stdout_truncated
    assert result.stderr_truncated


def test_argument_builder_places_extra_args_before_stdin_sentinel(tmp_path):
    assert build_agent_args(request(tmp_path, extra_args=("--model", "x"))) == (
        "exec",
        "--model",
        "x",
        "-",
    )


def test_runner_reports_actionable_start_failure(monkeypatch, tmp_path):
    async def cannot_start(*args, **kwargs):
        raise OSError("sensitive local path")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", cannot_start)
    result = asyncio.run(CodexRunner(CodexConfig()).run(request(tmp_path)))
    assert result.exit_code is None
    assert "could not be started" in result.start_error
    assert "sensitive local path" not in result.start_error
