from backend.app.adapters.codex import CodexConfig


def test_config_supports_constructor_and_environment(monkeypatch):
    explicit = CodexConfig(executable="custom", default_timeout_seconds=5)
    assert explicit.executable == "custom"
    assert explicit.default_timeout_seconds == 5

    monkeypatch.setenv("CODEX_EXECUTABLE", "from-env")
    monkeypatch.setenv("CODEX_TIMEOUT_SECONDS", "9")
    monkeypatch.setenv("CODEX_MAX_STDOUT_BYTES", "123")
    configured = CodexConfig.from_environment()
    assert configured.executable == "from-env"
    assert configured.default_timeout_seconds == 9
    assert configured.max_stdout_bytes == 123
