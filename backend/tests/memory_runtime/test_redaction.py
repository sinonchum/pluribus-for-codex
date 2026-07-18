from __future__ import annotations

from app.memory_runtime.redaction import redact_sensitive_text


def test_redacts_bearer_tokens() -> None:
    source = "Authorization: Bearer fake-token-1234567890"

    redacted = redact_sensitive_text(source)

    assert "fake-token" not in redacted
    assert "Bearer [REDACTED]" in redacted


def test_redacts_common_api_key_assignments() -> None:
    source = 'OPENAI_API_KEY="sk-fake-1234567890"\ntoken: fake_token_987654321'

    redacted = redact_sensitive_text(source)

    assert "sk-fake" not in redacted
    assert "fake_token" not in redacted
    assert redacted.count("[REDACTED]") == 2


def test_redacts_posix_and_windows_home_paths() -> None:
    source = (
        "See /Users/alice/private/project/log.txt and "
        "/home/bob/work/repro.py and /root/private/trace.log and "
        "C:\\Users\\carol\\secret\\trace.txt"
    )

    redacted = redact_sensitive_text(source)

    assert "alice" not in redacted
    assert "bob" not in redacted
    assert "/root" not in redacted
    assert "carol" not in redacted
    assert redacted.count("[HOME]") == 4


def test_redacts_standalone_provider_token_formats() -> None:
    tokens = [
        "sk-" + "a" * 32,
        "ghp_" + "b" * 36,
        "github_pat_" + "c" * 36,
    ]
    source = "tokens: " + " ".join(tokens)

    redacted = redact_sensitive_text(source)

    assert all(token not in redacted for token in tokens)
    assert redacted.count("[REDACTED]") == 3
