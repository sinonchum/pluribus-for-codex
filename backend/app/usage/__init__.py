from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _require_string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple) or not value:
        raise ValueError(f"{field} must be a non-empty tuple")
    for item in value:
        _require_text(item, field)
    return value


def _require_relative_path(value: str) -> None:
    posix_path = PurePosixPath(value)
    windows_path = PureWindowsPath(value)
    if (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or ".." in posix_path.parts
        or ".." in windows_path.parts
        or "\\" in value
    ):
        raise ValueError("changed_files must contain safe relative paths")


@dataclass(frozen=True, slots=True)
class VerificationProof:
    command: tuple[str, ...]
    exit_code: int
    output_excerpt: str

    def __post_init__(self) -> None:
        _require_string_tuple(self.command, "command")
        if isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int):
            raise ValueError("exit_code must be an integer")
        _require_text(self.output_excerpt, "output_excerpt")


@dataclass(frozen=True, slots=True)
class UsageProof:
    receipt_id: str
    memory_id: str
    consumer: str
    matched_trigger: str
    injected_memory_id: str
    codex_reported_use: bool
    effect: str
    changed_files: tuple[str, ...]
    verification: VerificationProof
    created_at: datetime

    def __post_init__(self) -> None:
        for field in (
            "receipt_id",
            "memory_id",
            "consumer",
            "matched_trigger",
            "injected_memory_id",
            "effect",
        ):
            _require_text(getattr(self, field), field)
        if not isinstance(self.codex_reported_use, bool):
            raise ValueError("codex_reported_use must be a boolean")
        _require_string_tuple(self.changed_files, "changed_files")
        for path in self.changed_files:
            _require_relative_path(path)
        if not isinstance(self.verification, VerificationProof):
            raise ValueError("verification must be a VerificationProof")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be a timezone-aware datetime")


@dataclass(frozen=True, slots=True)
class UsageReceipt:
    id: str
    memory_id: str
    consumer: str
    matched_trigger: str
    injected_into_codex: bool
    codex_reported_use: bool
    effect: str
    changed_files: tuple[str, ...]
    verification: VerificationProof
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        created_at = self.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
        return {
            "id": self.id,
            "memory_id": self.memory_id,
            "consumer": self.consumer,
            "matched_trigger": self.matched_trigger,
            "injected_into_codex": self.injected_into_codex,
            "codex_reported_use": self.codex_reported_use,
            "effect": self.effect,
            "changed_files": list(self.changed_files),
            "verification": {
                "command": list(self.verification.command),
                "exit_code": self.verification.exit_code,
                "output_excerpt": self.verification.output_excerpt,
            },
            "created_at": created_at,
        }


def build_usage_receipt(proof: UsageProof) -> UsageReceipt:
    if not isinstance(proof, UsageProof):
        raise ValueError("proof must be a UsageProof")
    if proof.injected_memory_id != proof.memory_id:
        raise ValueError("injected_memory_id must match memory_id")
    if not proof.codex_reported_use:
        raise ValueError("Codex-reported use is required")
    if proof.verification.exit_code != 0:
        raise ValueError("Coordinator verification must pass")

    return UsageReceipt(
        id=proof.receipt_id,
        memory_id=proof.memory_id,
        consumer=proof.consumer,
        matched_trigger=proof.matched_trigger,
        injected_into_codex=True,
        codex_reported_use=proof.codex_reported_use,
        effect=proof.effect,
        changed_files=proof.changed_files,
        verification=proof.verification,
        created_at=proof.created_at,
    )


__all__ = [
    "UsageProof",
    "UsageReceipt",
    "VerificationProof",
    "build_usage_receipt",
]
