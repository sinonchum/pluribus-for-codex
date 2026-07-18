import asyncio

from app.adapters.codex import CodexConfig, build_preflight_args, run_preflight


class FakeProcess:
    def __init__(self, stdout=b"codex 1.2.3\n", stderr=b"", returncode=0, delay=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.delay = delay
        self.killed = False

    async def communicate(self):
        await asyncio.sleep(self.delay)
        return self.stdout, self.stderr

    def kill(self):
        self.killed = True
        self.returncode = -9

    async def wait(self):
        return self.returncode


def test_preflight_argument_builder():
    assert build_preflight_args() == ("--version",)


def test_missing_executable_is_actionable():
    result = asyncio.run(run_preflight(CodexConfig(), resolver=lambda _: None))
    assert not result.available
    assert result.error_code == "executable_missing"
    assert "CODEX_EXECUTABLE" in result.error_message


def test_successful_and_nonzero_probe(monkeypatch):
    seen = []

    async def success(*args, **kwargs):
        seen.append((args, kwargs))
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", success)
    result = asyncio.run(run_preflight(CodexConfig(), resolver=lambda _: "/bin/codex"))
    assert result.available and result.version == "codex 1.2.3"
    assert seen[0][0] == ("/bin/codex", "--version")

    async def failure(*args, **kwargs):
        return FakeProcess(stderr=b"bad probe", returncode=7)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", failure)
    result = asyncio.run(run_preflight(CodexConfig(), resolver=lambda _: "/bin/codex"))
    assert not result.available
    assert result.exit_code == 7
    assert result.error_code == "probe_failed"


def test_probe_timeout_kills_process(monkeypatch):
    process = FakeProcess(delay=0.1)

    async def create(*args, **kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    result = asyncio.run(
        run_preflight(
            CodexConfig(preflight_timeout_seconds=0.01),
            resolver=lambda _: "/bin/codex",
        )
    )
    assert result.error_code == "timeout"
    assert process.killed
    assert result.stdout == "codex 1.2.3\n"


def test_cannot_start_and_authentication_failures_are_distinct(monkeypatch):
    async def cannot_start(*args, **kwargs):
        raise OSError("secret local details")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", cannot_start)
    result = asyncio.run(run_preflight(CodexConfig(), resolver=lambda _: "/bin/codex"))
    assert result.error_code == "cannot_start"
    assert "secret local details" not in result.error_message

    async def auth_failure(*args, **kwargs):
        return FakeProcess(stderr=b"authentication required", returncode=1)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", auth_failure)
    result = asyncio.run(run_preflight(CodexConfig(), resolver=lambda _: "/bin/codex"))
    assert result.error_code == "authentication_failed"
    assert "login" in result.error_message.lower()

    async def packaged_binary_missing(*args, **kwargs):
        return FakeProcess(stderr=b"Error: spawn /package/codex ENOENT", returncode=1)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", packaged_binary_missing)
    result = asyncio.run(run_preflight(CodexConfig(), resolver=lambda _: "/bin/codex"))
    assert result.error_code == "cannot_start"
    assert "Reinstall" in result.error_message


def test_preflight_cancellation_kills_child_and_returns_state(monkeypatch):
    process = FakeProcess(delay=10)

    async def create(*args, **kwargs):
        return process

    async def cancel_probe():
        monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
        task = asyncio.create_task(
            run_preflight(CodexConfig(), resolver=lambda _: "/bin/codex")
        )
        await asyncio.sleep(0)
        task.cancel()
        return await task

    result = asyncio.run(cancel_probe())
    assert result.error_code == "cancelled"
    assert process.killed
