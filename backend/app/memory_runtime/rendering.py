from __future__ import annotations

import base64
import json
import shlex
from collections.abc import Mapping
from typing import Any

from .redaction import redact_sensitive_text
from .validation import (
    validate_capsule,
    validate_memory_id,
    validate_slug,
    validate_version,
)

_MACHINE_START = "<!-- PLURIBUS_MEMORY_DATA_V1_START -->"
_MACHINE_END = "<!-- PLURIBUS_MEMORY_DATA_V1_END -->"
_MACHINE_FIELDS = {
    "id",
    "slug",
    "title",
    "problem",
    "triggers",
    "steps",
    "tags",
    "version",
}


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    return value


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def render_memory_markdown(capsule: Mapping[str, Any]) -> str:
    """Render deterministic, sanitized Markdown from a frozen Memory Capsule."""

    data = _redact_value(validate_capsule(capsule))
    machine_data = {
        key: data[key]
        for key in (
            "id",
            "slug",
            "title",
            "problem",
            "triggers",
            "steps",
            "tags",
            "version",
        )
    }
    serialized = json.dumps(
        machine_data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = base64.b64encode(serialized).decode("ascii")
    verification = data["verification"]
    command = shlex.join(verification["command"])
    return "\n".join(
        (
            _MACHINE_START,
            encoded,
            _MACHINE_END,
            "",
            f"# {data['title']}",
            "",
            f"- **Memory ID:** `{data['id']}`",
            f"- **Slug:** `{data['slug']}`",
            f"- **Version:** `{data['version']}`",
            f"- **Author:** {data['author']['display_name']} (`{data['author']['id']}`)",
            f"- **Status:** {data['status']}",
            "",
            "## Problem",
            "",
            data["problem"],
            "",
            "## Triggers",
            "",
            _bullets(data["triggers"]),
            "",
            "## Reusable steps",
            "",
            _numbered(data["steps"]),
            "",
            "## Tags",
            "",
            _bullets(data["tags"]),
            "",
            "## Compatibility",
            "",
            _bullets(data["compatibility"]),
            "",
            "## Verification evidence",
            "",
            f"- **Command:** `{command}`",
            f"- **Exit code:** {verification['exit_code']}",
            f"- **Passed:** {verification['passed']}",
            f"- **Evidence:** {verification['evidence_excerpt']}",
            "",
        )
    )


def parse_memory_markdown(markdown: str) -> dict[str, Any]:
    """Read the bounded machine-data block emitted by the renderer."""

    start = markdown.find(_MACHINE_START)
    end = markdown.find(_MACHINE_END)
    if start < 0 or end < 0 or end <= start:
        raise ValueError("MEMORY.md is missing Pluribus machine data")
    payload_start = start + len(_MACHINE_START)
    payload = markdown[payload_start:end].strip()
    try:
        decoded = base64.b64decode(payload, validate=True).decode("utf-8")
        data = json.loads(decoded)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Pluribus machine data is invalid") from error
    if not isinstance(data, dict) or set(data) != _MACHINE_FIELDS:
        raise ValueError("Pluribus machine data must match the frozen runtime fields")
    if not all(
        isinstance(data[key], str)
        for key in ("id", "slug", "title", "problem", "version")
    ):
        raise ValueError("Pluribus machine identity fields must be strings")
    for key in ("triggers", "steps", "tags"):
        if not isinstance(data[key], list) or not all(
            isinstance(item, str) and item for item in data[key]
        ):
            raise ValueError(f"Pluribus machine {key} must be a string array")
    validate_memory_id(data["id"])
    validate_slug(data["slug"])
    validate_version(data["version"])
    return data
