"""Actionable Codex adapter errors."""


class CodexError(Exception):
    """Base error for the Codex adapter."""


class CodexExecutableNotFoundError(CodexError):
    """Raised when the configured CLI cannot be resolved."""


class CodexStartError(CodexError):
    """Raised when the CLI exists but cannot be started."""


class CodexProbeError(CodexError):
    """Raised when a bounded preflight probe fails."""


class CodexAuthenticationError(CodexProbeError):
    """Raised when a probe reports an authentication problem."""


class CodexTimeoutError(CodexError):
    """Raised when an operation exceeds its explicit timeout."""


class CodexCancelledError(CodexError):
    """Raised when an operation is cancelled."""


class CodexNonZeroExitError(CodexError):
    """Raised when Codex exits unsuccessfully."""


class CodexMalformedOutputError(CodexError):
    """Raised when structured output cannot be parsed."""
