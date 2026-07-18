"""Safe execution of typed verification commands."""

from .runner import (
    CommandResult,
    CommandSpec,
    CommandStatus,
    VerificationSummary,
    VerificationTerminalState,
    evaluate_terminal_state,
    run_command,
    run_verification,
)

__all__ = [
    "CommandResult",
    "CommandSpec",
    "CommandStatus",
    "VerificationSummary",
    "VerificationTerminalState",
    "evaluate_terminal_state",
    "run_command",
    "run_verification",
]
