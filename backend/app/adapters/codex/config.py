"""Configuration for bounded Codex CLI execution."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _environment_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


def _environment_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


@dataclass(frozen=True, slots=True)
class CodexConfig:
    """Runtime limits and executable selection for Codex."""

    executable: str = "codex"
    default_timeout_seconds: float = 120.0
    preflight_timeout_seconds: float = 30.0
    termination_grace_seconds: float = 2.0
    max_stdout_bytes: int = 1_000_000
    max_stderr_bytes: int = 250_000

    def __post_init__(self) -> None:
        if not self.executable.strip():
            raise ValueError("Codex executable must not be empty.")
        for field_name in (
            "default_timeout_seconds",
            "preflight_timeout_seconds",
            "termination_grace_seconds",
        ):
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be positive.")
        if self.max_stdout_bytes <= 0 or self.max_stderr_bytes <= 0:
            raise ValueError("Codex output limits must be positive.")

    @classmethod
    def from_environment(cls) -> CodexConfig:
        """Build configuration from optional ``CODEX_*`` variables."""

        return cls(
            executable=os.getenv("CODEX_EXECUTABLE", "codex"),
            default_timeout_seconds=_environment_float("CODEX_TIMEOUT_SECONDS", 120.0),
            preflight_timeout_seconds=_environment_float(
                "CODEX_PREFLIGHT_TIMEOUT_SECONDS", 30.0
            ),
            termination_grace_seconds=_environment_float(
                "CODEX_TERMINATION_GRACE_SECONDS", 2.0
            ),
            max_stdout_bytes=_environment_int("CODEX_MAX_STDOUT_BYTES", 1_000_000),
            max_stderr_bytes=_environment_int("CODEX_MAX_STDERR_BYTES", 250_000),
        )
