from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .rendering import parse_memory_markdown, render_memory_markdown
from .validation import (
    validate_capsule,
    validate_memory_id,
    validate_slug,
    validate_timestamp,
    validate_version,
)

_MANIFEST_FIELDS = {
    "memory_id",
    "slug",
    "version",
    "install_path",
    "content_sha256",
    "installed_at",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}\Z")
_DIRECTORY_FLAGS = (
    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
)
_FILE_READ_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
_FILE_WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _root_path(root: str | Path) -> Path:
    path = Path(root).expanduser()
    if not path.exists() or not path.is_dir():
        raise ValueError("caller-supplied root must be an existing directory")
    if path.is_symlink():
        raise ValueError("caller-supplied root must not be a symbolic link")
    return path.resolve()


def _open_directory_at(parent_fd: int, name: str, *, create: bool) -> int | None:
    if create:
        with suppress(FileExistsError):
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
    try:
        return os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            return None
        raise
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise ValueError(
                f"installed memory path component {name!r} must not be a symbolic link"
            ) from error
        raise


@contextmanager
def _installed_directory(root: Path, *, create: bool) -> Iterator[int | None]:
    root_fd = os.open(root, _DIRECTORY_FLAGS)
    pluribus_fd: int | None = None
    installed_fd: int | None = None
    try:
        pluribus_fd = _open_directory_at(root_fd, ".pluribus", create=create)
        if pluribus_fd is None:
            yield None
            return
        installed_fd = _open_directory_at(pluribus_fd, "installed", create=create)
        yield installed_fd
    finally:
        if installed_fd is not None:
            os.close(installed_fd)
        if pluribus_fd is not None:
            os.close(pluribus_fd)
        os.close(root_fd)


def _open_package_directory(
    installed_fd: int, slug: str, *, create: bool
) -> int | None:
    validate_slug(slug)
    return _open_directory_at(installed_fd, slug, create=create)


def _entry_exists(directory_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _read_regular_file(directory_fd: int, name: str) -> bytes:
    try:
        descriptor = os.open(name, _FILE_READ_FLAGS, dir_fd=directory_fd)
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise ValueError(f"{name} must not be a symbolic link") from error
        raise ValueError(f"unable to read installed {name}") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f"{name} must be a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(descriptor)


def _atomic_write_at(directory_fd: int, name: str, content: bytes) -> None:
    temporary = f".{name}.{secrets.token_hex(12)}"
    descriptor = os.open(
        temporary,
        _FILE_WRITE_FLAGS,
        0o600,
        dir_fd=directory_fd,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(
            temporary,
            name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        os.fsync(directory_fd)
    finally:
        os.close(descriptor)
        with suppress(FileNotFoundError):
            os.unlink(temporary, dir_fd=directory_fd)


def _parse_manifest(content: bytes, expected_slug: str) -> dict[str, Any]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid install manifest") from error
    if not isinstance(value, dict) or set(value) != _MANIFEST_FIELDS:
        raise ValueError("invalid install manifest contract")
    if not all(isinstance(value[field], str) for field in _MANIFEST_FIELDS):
        raise ValueError("invalid install manifest values")
    try:
        validate_memory_id(value["memory_id"], "manifest.memory_id")
        validate_slug(value["slug"])
        validate_version(value["version"])
        validate_timestamp(value["installed_at"], "manifest.installed_at")
    except ValueError as error:
        raise ValueError("invalid install manifest values") from error
    if value["slug"] != expected_slug:
        raise ValueError("install manifest location does not match its slug")
    expected_path = f".pluribus/installed/{expected_slug}/MEMORY.md"
    if value["install_path"] != expected_path or not _SHA256.fullmatch(
        value["content_sha256"]
    ):
        raise ValueError("invalid install manifest values")
    return value


def _read_package(
    package_fd: int, expected_slug: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _parse_manifest(
        _read_regular_file(package_fd, "manifest.json"), expected_slug
    )
    content = _read_regular_file(package_fd, "MEMORY.md")
    try:
        data = parse_memory_markdown(content.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError(f"invalid installed memory: {expected_slug}") from error
    if hashlib.sha256(content).hexdigest() != manifest["content_sha256"]:
        raise ValueError(f"installed memory integrity check failed: {expected_slug}")
    identity = (data.get("id"), data.get("slug"), data.get("version"))
    manifest_identity = (
        manifest["memory_id"],
        manifest["slug"],
        manifest["version"],
    )
    if identity != manifest_identity:
        raise ValueError(f"installed memory identity mismatch: {expected_slug}")
    return manifest, data


def _list_installations(
    root: str | Path,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    project_root = _root_path(root)
    installations: list[tuple[dict[str, Any], dict[str, Any]]] = []
    with _installed_directory(project_root, create=False) as installed_fd:
        if installed_fd is None:
            return []
        for slug in sorted(os.listdir(installed_fd)):
            if slug.startswith("."):
                continue
            try:
                validate_slug(slug)
            except ValueError as error:
                raise ValueError("invalid installed package directory") from error
            package_fd = _open_package_directory(installed_fd, slug, create=False)
            if package_fd is None:
                continue
            try:
                installations.append(_read_package(package_fd, slug))
            finally:
                os.close(package_fd)
    return sorted(
        installations,
        key=lambda item: (item[0]["installed_at"], item[0]["slug"]),
    )


def install_memory(root: str | Path, capsule: Mapping[str, Any]) -> dict[str, Any]:
    """Install one deterministic memory package beneath a supplied project root."""

    project_root = _root_path(root)
    data = validate_capsule(capsule)
    markdown = render_memory_markdown(capsule).encode("utf-8")
    digest = hashlib.sha256(markdown).hexdigest()
    manifest = {
        "memory_id": data["id"],
        "slug": data["slug"],
        "version": data["version"],
        "install_path": f".pluribus/installed/{data['slug']}/MEMORY.md",
        "content_sha256": digest,
        "installed_at": _utc_now(),
    }

    with _installed_directory(project_root, create=True) as installed_fd:
        if installed_fd is None:
            raise ValueError("unable to create installed memory directory")
        package_fd = _open_package_directory(installed_fd, data["slug"], create=True)
        if package_fd is None:
            raise ValueError("unable to create memory package directory")
        try:
            if _entry_exists(package_fd, "manifest.json"):
                existing, _ = _read_package(package_fd, data["slug"])
                if existing["version"] == data["version"]:
                    if existing["content_sha256"] == digest:
                        return existing
                    raise ValueError(
                        "memory version already installed with different content or integrity"
                    )
            _atomic_write_at(package_fd, "MEMORY.md", markdown)
            _atomic_write_at(
                package_fd,
                "manifest.json",
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            )
        finally:
            os.close(package_fd)
    return manifest


def list_installed_memories(root: str | Path) -> list[dict[str, Any]]:
    return [manifest for manifest, _ in _list_installations(root)]


def uninstall_memory(root: str | Path, slug: str) -> bool:
    project_root = _root_path(root)
    validate_slug(slug)
    with _installed_directory(project_root, create=False) as installed_fd:
        if installed_fd is None:
            return False
        package_fd = _open_package_directory(installed_fd, slug, create=False)
        if package_fd is None:
            return False
        try:
            entries = os.listdir(package_fd)
            unexpected = set(entries) - {"MEMORY.md", "manifest.json"}
            if unexpected:
                raise ValueError("memory package contains unexpected entries")
            for name in entries:
                os.unlink(name, dir_fd=package_fd)
            os.fsync(package_fd)
        finally:
            os.close(package_fd)
        os.rmdir(slug, dir_fd=installed_fd)
        os.fsync(installed_fd)
    return True
