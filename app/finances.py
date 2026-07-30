"""Shared money math, so charged/paid/balance is computed one way everywhere.

Two intentional notions of "paid":

- **Cash collected** (`total_collected`): every payment received, regardless of
  appointment status — the cash-flow view used by the Reports "Collected" figure.
- **Balance on services** (`balance_on_services`): fees for **completed** sessions
  minus payments on those sessions — the accounts-receivable view used by the
  client detail page and the outstanding-balances report.

They differ only when a payment is recorded against a non-completed appointment
(e.g. a prepayment); keeping both explicit avoids the two views quietly disagreeing.
"""
from app.models.appointment import Appointment

CHARGEABLE_STATUS = "completed"


def appt_paid(appt: Appointment) -> float:
    """Total payments recorded against one appointment."""
    return sum(p.amount for p in appt.payments)


def completed(appts: list[Appointment]) -> list[Appointment]:
    return [a for a in appts if a.status == CHARGEABLE_STATUS]


def total_collected(appts: list[Appointment]) -> float:
    """All cash received across the given appointments."""
    return sum(appt_paid(a) for a in appts)


def balance_on_services(appts: list[Appointment]) -> dict:
    """Charged / paid / outstanding scoped to completed sessions."""
    done = completed(appts)
    charged = sum(a.fee or 0 for a in done)
    paid = sum(appt_paid(a) for a in done)
    return {"charged": charged, "paid": paid, "outstanding": round(charged - paid, 2)}
