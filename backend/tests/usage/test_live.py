from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.usage.live import CodexUseResult, run_live_usage

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "demo" / "memory-fixture"


class ApplyingCodexAdapter:
    async def use_installed_memory(
        self, installed_memory_root: Path, workspace: Path
    ) -> CodexUseResult:
        assert installed_memory_root.is_dir()
        (workspace / "pyproject.toml").write_text(
            '[project]\nname = "live-fixture"\nversion = "0.1.0"\n'
            '[tool.pytest.ini_options]\naddopts = "--import-mode=importlib"\n',
            encoding="utf-8",
        )
        return CodexUseResult(
            memory_id="mem_pytest_importlib_v1",
            matched_trigger="import file mismatch",
            injected_into_codex=True,
            codex_reported_use=True,
            effect="Configured pytest importlib collection mode.",
            changed_files=("pyproject.toml",),
        )


def test_live_usage_connects_adapter_change_to_coordinator_verification(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE_ROOT, workspace, ignore=shutil.ignore_patterns(".venv"))
    (workspace / "pyproject.toml").unlink()
    installed_root = tmp_path / "installed"
    installed_root.mkdir()

    receipt = asyncio.run(
        run_live_usage(
            adapter=ApplyingCodexAdapter(),
            installed_memory_root=installed_root,
            workspace=workspace,
            receipt_id="use_live_001",
            consumer="dev_bob",
            created_at=datetime(2026, 7, 18, 10, 8, tzinfo=UTC),
            verification_command=("pytest", "-q"),
        )
    )

    assert receipt.id == "use_live_001"
    assert receipt.memory_id == "mem_pytest_importlib_v1"
    assert receipt.changed_files == ("pyproject.toml",)
    assert receipt.verification.exit_code == 0
    assert "2 passed" in receipt.verification.output_excerpt


def test_live_usage_rejects_workspace_symlinks_before_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE_ROOT, workspace, ignore=shutil.ignore_patterns(".venv"))
    (workspace / "pyproject.toml").unlink()
    suspicious = workspace / "external-link"
    suspicious.write_text("simulated symlink target", encoding="utf-8")
    installed_root = tmp_path / "installed"
    installed_root.mkdir()
    original_is_symlink = Path.is_symlink

    def simulated_is_symlink(path: Path) -> bool:
        return path == suspicious or original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", simulated_is_symlink)

    with pytest.raises(ValueError, match="workspace must not contain symlinks"):
        asyncio.run(
            run_live_usage(
                adapter=ApplyingCodexAdapter(),
                installed_memory_root=installed_root,
                workspace=workspace,
                receipt_id="use_live_001",
                consumer="dev_bob",
                created_at=datetime(2026, 7, 18, 10, 8, tzinfo=UTC),
                verification_command=("pytest", "-q"),
            )
        )
