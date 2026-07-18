from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path

_SENSITIVE_NAME = re.compile(
    r"(?:secret|token|key|password|auth|credential)", re.IGNORECASE
)
_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret|auth|credential)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_AUTHORIZATION = re.compile(
    r"(?i)\b(authorization\s*[:=]\s*(?:bearer\s+)?|bearer\s+)([^\s,;]+)"
)
_TOKEN = re.compile(
    r"(?i)\b(?:sk-[a-z0-9_-]{8,}|gh[pousr]_[a-z0-9_]{8,}|github_pat_[a-z0-9_]{8,})\b"
)
_DEFAULT_LIMIT = 8_192


def _nontrivial(value: str) -> bool:
    return len(value) >= 8 and len(set(value)) >= 4 and not value.isspace()


def sanitize_output(
    output: str, *, paths: Iterable[Path] = (), limit: int = _DEFAULT_LIMIT
) -> str:
    sanitized = output
    redacted_paths = (*paths, Path.home())
    for path in redacted_paths:
        resolved = Path(path).resolve()
        representations = {str(resolved), resolved.as_posix()}
        for representation in sorted(representations, key=len, reverse=True):
            sanitized = re.sub(
                re.escape(representation), "<fixture>", sanitized, flags=re.IGNORECASE
            )

    sensitive_values = {
        value
        for name, value in os.environ.items()
        if _SENSITIVE_NAME.search(name) and _nontrivial(value)
    }
    for value in sorted(sensitive_values, key=len, reverse=True):
        sanitized = sanitized.replace(value, "<redacted>")

    sanitized = _ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}{match.group(2)}<redacted>", sanitized
    )
    sanitized = _AUTHORIZATION.sub(
        lambda match: f"{match.group(1)}<redacted>", sanitized
    )
    sanitized = _TOKEN.sub("<redacted>", sanitized)
    return sanitized[:limit]


__all__ = ["sanitize_output"]
