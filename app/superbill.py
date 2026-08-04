"""Compatibility shim — superbill/statement PDF generation now lives in the shared
`breakout_core` package. Import from here or from `breakout_core.superbill`.
"""
from breakout_core.superbill import (
    BILLABLE_STATUSES,
    STATEMENT_TITLE,
    build_superbill_pdf,
    payments_to,
    service_rows,
)

__all__ = [
    "BILLABLE_STATUSES", "STATEMENT_TITLE", "build_superbill_pdf",
    "payments_to", "service_rows",
]
