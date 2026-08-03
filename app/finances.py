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
    """Net payments recorded against one appointment (refunds count negatively)."""
    return sum(p.signed_amount for p in appt.payments)


def completed(appts: list[Appointment]) -> list[Appointment]:
    return [a for a in appts if a.status == CHARGEABLE_STATUS]


def appt_charged(appt: Appointment) -> float:
    """The fee a completed session bills — zero once the fee is written off."""
    if appt.status != CHARGEABLE_STATUS or appt.written_off:
        return 0.0
    return appt.fee or 0.0


def total_collected(appts: list[Appointment]) -> float:
    """All cash received across the given appointments, net of refunds."""
    return sum(appt_paid(a) for a in appts)


def total_servicer_fees(appts: list[Appointment]) -> float:
    """Card-processor fees paid across the given appointments' payments."""
    return round(sum(p.servicer_fee or 0 for a in appts for p in a.payments), 2)


def balance_on_services(appts: list[Appointment]) -> dict:
    """Charged / paid / outstanding scoped to completed, non-written-off sessions."""
    charged = sum(appt_charged(a) for a in appts)
    paid = sum(appt_paid(a) for a in completed(appts))
    return {"charged": charged, "paid": paid, "outstanding": round(charged - paid, 2)}
