from billing import invoices


def test_existing_paid_transition_records_audit_event() -> None:
    invoice = invoices.Invoice("inv_001")
    ledger: list[invoices.LedgerEvent] = []

    invoices.transition_invoice(
        invoice,
        to_status=invoices.InvoiceStatus.PAID,
        ledger=ledger,
        reason="payment_captured",
    )

    assert invoice.status is invoices.InvoiceStatus.PAID
    assert len(ledger) == 1
    assert ledger[0].from_status is invoices.InvoiceStatus.PENDING
    assert ledger[0].to_status is invoices.InvoiceStatus.PAID


def test_cancel_invoice_sets_cancelled_status() -> None:
    invoice = invoices.Invoice("inv_002")
    ledger: list[invoices.LedgerEvent] = []

    invoices.cancel_invoice(invoice, ledger)

    assert invoice.status is invoices.InvoiceStatus.CANCELLED


def test_cancel_invoice_preserves_append_only_audit_trail() -> None:
    invoice = invoices.Invoice("inv_003")
    ledger: list[invoices.LedgerEvent] = []

    invoices.cancel_invoice(invoice, ledger)

    assert ledger == [
        invoices.LedgerEvent(
            invoice_id="inv_003",
            from_status=invoices.InvoiceStatus.PENDING,
            to_status=invoices.InvoiceStatus.CANCELLED,
            reason="customer_request",
        )
    ]
