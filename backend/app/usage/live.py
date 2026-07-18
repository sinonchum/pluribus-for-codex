from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Protocol

from app.usage import UsageProof, UsageReceipt, build_usage_receipt
from app.usage.verification import run_coordinator_verification
from app.verification.runner import CommandSpec, CommandStatus, run_command

_MEMORY_ID = "mem_billing_audit_handoff_v1"
_EXPECTED_CHANGED_FILES = ("billing/invoices.py",)
_EXCLUDED_DIRECTORIES = {".venv", ".pytest_cache", "__pycache__"}
_ADAPTER_OUTPUT_LIMIT_BYTES = 16_384
_ADAPTER_TIMEOUT_SECONDS = 180
_CODEX_RESULT_KEYS = {
    "memory_id",
    "matched_trigger",
    "injected_into_codex",
    "codex_reported_use",
    "effect",
    "changed_files",
}


def _require_text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def _require_safe_paths(value: object) -> tuple[str, ...]:
    if type(value) is not tuple or not value:
        raise ValueError("changed_files must be a non-empty tuple")
    for item in value:
        _require_text(item, "changed_files")
        posix_path = PurePosixPath(item)
        windows_path = PureWindowsPath(item)
        if (
            posix_path.is_absolute()
            or windows_path.is_absolute()
            or ".." in posix_path.parts
            or ".." in windows_path.parts
            or "\\" in item
        ):
            raise ValueError("changed_files must contain safe relative paths")
    return value


@dataclass(frozen=True, slots=True)
class CodexUseResult:
    memory_id: str
    matched_trigger: str
    injected_into_codex: bool
    codex_reported_use: bool
    effect: str
    changed_files: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.memory_id, "memory_id")
        _require_text(self.matched_trigger, "matched_trigger")
        _require_text(self.effect, "effect")
        if not isinstance(self.injected_into_codex, bool):
            raise ValueError("injected_into_codex must be a boolean")
        if not isinstance(self.codex_reported_use, bool):
            raise ValueError("codex_reported_use must be a boolean")
        _require_safe_paths(self.changed_files)


class CodexUsageAdapter(Protocol):
    async def use_installed_memory(
        self, installed_memory_root: Path, workspace: Path
    ) -> CodexUseResult: ...


@dataclass(frozen=True, slots=True)
class CommandCodexUsageAdapter:
    command: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.command) is not tuple or not self.command:
            raise ValueError("command must be a non-empty tuple of strings")
        if any(not isinstance(part, str) or not part for part in self.command):
            raise ValueError("command must be a non-empty tuple of strings")

    async def use_installed_memory(
        self, installed_memory_root: Path, workspace: Path
    ) -> CodexUseResult:
        result = await run_command(
            CommandSpec(
                executable=self.command[0],
                args=(
                    *self.command[1:],
                    str(installed_memory_root),
                    str(workspace),
                ),
                cwd=workspace,
                timeout_seconds=_ADAPTER_TIMEOUT_SECONDS,
                output_limit_bytes=_ADAPTER_OUTPUT_LIMIT_BYTES,
                name="codex-usage-adapter",
            )
        )
        if (
            result.status is not CommandStatus.PASSED
            or result.exit_code != 0
            or result.stdout_truncated
        ):
            raise RuntimeError("Codex usage adapter failed")

        try:
            payload = json.loads(result.stdout)
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError("Codex usage adapter returned invalid JSON") from error
        if not isinstance(payload, dict) or set(payload) != _CODEX_RESULT_KEYS:
            raise ValueError("Codex usage adapter returned an invalid result shape")
        if type(payload["changed_files"]) is not list:
            raise ValueError("Codex usage adapter changed_files must be a list")
        payload["changed_files"] = tuple(payload["changed_files"])
        try:
            return CodexUseResult(**payload)
        except (TypeError, ValueError) as error:
            raise ValueError("Codex usage adapter returned invalid proof") from error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(64 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot(workspace: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for root, directories, files in os.walk(workspace, followlinks=False):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in _EXCLUDED_DIRECTORIES
            and not (Path(root) / directory).is_symlink()
        )
        for filename in sorted(files):
            path = Path(root) / filename
            if filename.endswith(".pyc") or path.is_symlink() or not path.is_file():
                continue
            relative_path = path.relative_to(workspace).as_posix()
            snapshot[relative_path] = _sha256(path)
    return snapshot


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes
    except AttributeError:
        return False
    return bool(attributes & 0x400)


def _reject_workspace_links(workspace: Path) -> None:
    for root, directories, files in os.walk(workspace, followlinks=False):
        directories[:] = [
            directory
            for directory in directories
            if directory not in _EXCLUDED_DIRECTORIES
        ]
        for name in (*directories, *files):
            path = Path(root) / name
            if path.is_symlink() or _is_reparse_point(path):
                raise ValueError(
                    "workspace must not contain symlinks or reparse points"
                )


def _changed_files(before: dict[str, str], after: dict[str, str]) -> tuple[str, ...]:
    paths = set(before) | set(after)
    return tuple(sorted(path for path in paths if before.get(path) != after.get(path)))


async def run_live_usage(
    *,
    adapter: CodexUsageAdapter,
    installed_memory_root: Path,
    workspace: Path,
    receipt_id: str,
    consumer: str,
    created_at: datetime,
    verification_command: tuple[str, ...],
) -> UsageReceipt:
    installed_memory_root = Path(installed_memory_root)
    workspace = Path(workspace)
    if not installed_memory_root.is_dir():
        raise NotADirectoryError(installed_memory_root)
    if not workspace.is_dir():
        raise NotADirectoryError(workspace)
    if installed_memory_root.is_symlink() or _is_reparse_point(installed_memory_root):
        raise ValueError("installed_memory_root must not be a symlink or reparse point")
    if workspace.is_symlink() or _is_reparse_point(workspace):
        raise ValueError("workspace must not contain symlinks or reparse points")
    installed_memory_root = installed_memory_root.resolve()
    workspace = workspace.resolve()
    _require_text(receipt_id, "receipt_id")
    _require_text(consumer, "consumer")
    if not isinstance(created_at, datetime) or created_at.tzinfo is None:
        raise ValueError("created_at must be a timezone-aware datetime")
    if type(verification_command) is not tuple or not verification_command:
        raise ValueError("verification_command must be a non-empty tuple of strings")
    if any(not isinstance(part, str) or not part for part in verification_command):
        raise ValueError("verification_command must be a non-empty tuple of strings")

    _reject_workspace_links(workspace)
    before = _snapshot(workspace)
    result = await adapter.use_installed_memory(installed_memory_root, workspace)
    _reject_workspace_links(workspace)
    after = _snapshot(workspace)

    if type(result) is not CodexUseResult:
        raise ValueError("adapter must return an exact CodexUseResult")
    if result.memory_id != _MEMORY_ID:
        raise ValueError("adapter returned an unexpected memory_id")
    if result.injected_into_codex is not True:
        raise ValueError("memory injection confirmation is required")
    if result.codex_reported_use is not True:
        raise ValueError("Codex-reported use is required")
    actual_changed_files = _changed_files(before, after)
    if result.changed_files != actual_changed_files:
        raise ValueError("reported changed_files must equal the actual workspace delta")
    if actual_changed_files != _EXPECTED_CHANGED_FILES:
        raise ValueError("the live change must be exactly billing/invoices.py")

    verification = await run_coordinator_verification(workspace, verification_command)
    return build_usage_receipt(
        UsageProof(
            receipt_id=receipt_id,
            memory_id=result.memory_id,
            consumer=consumer,
            matched_trigger=result.matched_trigger,
            injected_memory_id=result.memory_id,
            codex_reported_use=result.codex_reported_use,
            effect=result.effect,
            changed_files=actual_changed_files,
            verification=verification,
            created_at=created_at,
        )
    )


__all__ = [
    "CodexUsageAdapter",
    "CodexUseResult",
    "CommandCodexUsageAdapter",
    "run_live_usage",
]
