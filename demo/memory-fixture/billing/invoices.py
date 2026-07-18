from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"


@dataclass(slots=True)
class Invoice:
    invoice_id: str
    status: InvoiceStatus = InvoiceStatus.PENDING


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    invoice_id: str
    from_status: InvoiceStatus
    to_status: InvoiceStatus
    reason: str


def transition_invoice(
    invoice: Invoice,
    *,
    to_status: InvoiceStatus,
    ledger: list[LedgerEvent],
    reason: str,
) -> None:
    """Alice's audit-safe transition primitive used by every billing state change."""

    ledger.append(
        LedgerEvent(
            invoice_id=invoice.invoice_id,
            from_status=invoice.status,
            to_status=to_status,
            reason=reason,
        )
    )
    invoice.status = to_status
