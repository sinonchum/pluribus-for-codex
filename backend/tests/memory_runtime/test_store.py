from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.memory_runtime.store import (
    install_memory,
    list_installed_memories,
    uninstall_memory,
)


def test_install_creates_markdown_and_frozen_manifest(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    manifest = install_memory(tmp_path, capsule)
    install_dir = tmp_path / ".pluribus/installed/fix-pytest-module-collisions"
    memory_path = install_dir / "MEMORY.md"
    manifest_path = install_dir / "manifest.json"

    assert memory_path.is_file()
    assert manifest_path.is_file()
    assert manifest == json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["memory_id"] == "mem_pytest_importlib_v1"
    assert manifest["install_path"] == (
        ".pluribus/installed/fix-pytest-module-collisions/MEMORY.md"
    )
    assert (
        manifest["content_sha256"]
        == hashlib.sha256(memory_path.read_bytes()).hexdigest()
    )
    assert set(manifest) == {
        "memory_id",
        "slug",
        "version",
        "install_path",
        "content_sha256",
        "installed_at",
    }


def test_reinstalling_same_version_is_idempotent(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    first = install_memory(tmp_path, capsule)
    first_markdown = (
        tmp_path / ".pluribus/installed/fix-pytest-module-collisions/MEMORY.md"
    ).read_bytes()

    second = install_memory(tmp_path, capsule)

    assert second == first
    assert (
        tmp_path / ".pluribus/installed/fix-pytest-module-collisions/MEMORY.md"
    ).read_bytes() == first_markdown


def test_same_version_with_changed_content_is_rejected(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)
    capsule["problem"] = "Changed without a version bump."

    with pytest.raises(ValueError, match="version already installed"):
        install_memory(tmp_path, capsule)


def test_list_and_uninstall_use_only_caller_supplied_root(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)

    installed = list_installed_memories(tmp_path)
    removed = uninstall_memory(tmp_path, "fix-pytest-module-collisions")

    assert [item["memory_id"] for item in installed] == ["mem_pytest_importlib_v1"]
    assert removed is True
    assert list_installed_memories(tmp_path) == []
    assert uninstall_memory(tmp_path, "fix-pytest-module-collisions") is False


def test_install_rejects_unsafe_slug(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    capsule["slug"] = "../escape"

    with pytest.raises(ValueError, match="slug"):
        install_memory(tmp_path, capsule)


def test_list_rejects_manifest_file_symlink(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)
    manifest_path = (
        tmp_path / ".pluribus/installed/fix-pytest-module-collisions/manifest.json"
    )
    external = tmp_path.parent / f"{tmp_path.name}-external-manifest.json"
    external.write_bytes(manifest_path.read_bytes())
    manifest_path.unlink()
    manifest_path.symlink_to(external)

    with pytest.raises(ValueError, match="symbolic link"):
        list_installed_memories(tmp_path)


def test_list_rejects_manifest_identity_that_disagrees_with_markdown(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)
    manifest_path = (
        tmp_path / ".pluribus/installed/fix-pytest-module-collisions/manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["memory_id"] = "mem_tampered_v1"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="identity"):
        list_installed_memories(tmp_path)


def test_list_rejects_malformed_manifest_values(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)
    manifest_path = (
        tmp_path / ".pluribus/installed/fix-pytest-module-collisions/manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["content_sha256"] = ["not", "a", "digest"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest"):
        list_installed_memories(tmp_path)


def test_install_rejects_symlinked_ancestor_directory(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    external = tmp_path.parent / f"{tmp_path.name}-external-install-root"
    external.mkdir()
    (tmp_path / ".pluribus").symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="symbolic link"):
        install_memory(tmp_path, capsule)


def test_list_rejects_manifest_copied_under_wrong_package_directory(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)
    installed_root = tmp_path / ".pluribus/installed"
    shutil.copytree(
        installed_root / "fix-pytest-module-collisions",
        installed_root / "copied-package",
    )

    with pytest.raises(ValueError, match="location"):
        list_installed_memories(tmp_path)
