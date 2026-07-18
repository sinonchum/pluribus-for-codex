from __future__ import annotations

import re

_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{6,}")
_ASSIGNMENT = re.compile(
    r"(?im)\b(?P<key>(?:[A-Z][A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD))|"
    r"(?:api[_-]?key|token|secret|password))\s*[:=]\s*"
    r"(?P<quote>['\"]?)(?P<value>[^\s'\"]{6,})(?P=quote)"
)
_STANDALONE_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_-])(?:"
    r"sk-[A-Za-z0-9_-]{20,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"AIza[A-Za-z0-9_-]{20,}"
    r")(?![A-Za-z0-9_-])"
)
_POSIX_HOME = re.compile(r"(?<![\w.-])(?:(?:/(?:Users|home)/[^/\s]+)|/root)(?=/|\s|$)")
_WINDOWS_HOME = re.compile(r"(?i)(?<![\w.-])[A-Z]:\\Users\\[^\\\s]+")


def _redact_assignment(match: re.Match[str]) -> str:
    separator = ":" if ":" in match.group(0).split(match.group("value"), 1)[0] else "="
    return f"{match.group('key')}{separator} [REDACTED]"


def redact_sensitive_text(value: str) -> str:
    """Remove common credentials and personal home-directory prefixes."""

    redacted = _BEARER.sub("Bearer [REDACTED]", value)
    redacted = _ASSIGNMENT.sub(_redact_assignment, redacted)
    redacted = _STANDALONE_TOKEN.sub("[REDACTED]", redacted)
    redacted = _POSIX_HOME.sub("[HOME]", redacted)
    return _WINDOWS_HOME.sub("[HOME]", redacted)
