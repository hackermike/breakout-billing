"""Bookkeeping report aggregations.

Revenue is recognized when a session is **completed** (its fee becomes charged).
"Collected" is all cash received (any payment). Outstanding balance (A/R) is
completed-session charges minus payments on those sessions, per client — the same
`app.finances.balance_on_services` used by the client detail page.

The pure `_*` helpers work off an already-loaded list of appointments so a single
dashboard render only queries the database once (see `dashboard`).
"""
from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from app.finances import CHARGEABLE_STATUS, balance_on_services, total_collected
from app.models.appointment import Appointment


def _appointments(db: Session) -> list[Appointment]:
    return (
        db.query(Appointment)
        .options(joinedload(Appointment.client), joinedload(Appointment.payments))
        .all()
    )


def _summary(appts: list[Appointment]) -> dict:
    services = balance_on_services(appts)
    return {
        "charged": services["charged"],
        "collected": total_collected(appts),   # all cash received (cash-flow view)
        "outstanding": services["outstanding"],  # A/R, completed-scoped (matches _outstanding)
    }


def _by_month(appts: list[Appointment]) -> list[dict]:
    charged = defaultdict(float)
    collected = defaultdict(float)
    for a in appts:
        if a.status == CHARGEABLE_STATUS:
            charged[a.datetime.strftime("%Y-%m")] += a.fee or 0
        for p in a.payments:
            collected[p.payment_date.strftime("%Y-%m")] += p.amount

    months = sorted(set(charged) | set(collected))
    return [
        {"month": m, "charged": round(charged[m], 2), "collected": round(collected[m], 2)}
        for m in months
    ]


def _by_payer(appts: list[Appointment]) -> list[dict]:
    totals = defaultdict(float)
    for a in appts:
        for p in a.payments:
            totals[p.payer or "unknown"] += p.amount
    return [
        {"payer": payer, "total": round(total, 2)}
        for payer, total in sorted(totals.items(), key=lambda kv: -kv[1])
    ]


def _outstanding(appts: list[Appointment]) -> list[dict]:
    by_client: dict[int, list[Appointment]] = defaultdict(list)
    names: dict[int, str] = {}
    for a in appts:
        by_client[a.client_id].append(a)
        names[a.client_id] = a.client.full_name

    rows = []
    for cid, client_appts in by_client.items():
        # Same completed-scoped balance the client detail page shows.
        bal = balance_on_services(client_appts)
        if bal["outstanding"] > 0.005:
            rows.append({
                "client": names[cid],
                "charged": bal["charged"],
                "paid": bal["paid"],
                "balance": bal["outstanding"],
            })
    return sorted(rows, key=lambda r: -r["balance"])


def dashboard(db: Session) -> dict:
    """Load appointments once and derive every report view from that snapshot."""
    appts = _appointments(db)
    return {
        "summary": _summary(appts),
        "by_month": _by_month(appts),
        "by_payer": _by_payer(appts),
        "outstanding": _outstanding(appts),
    }


# Thin per-view wrappers (handy in tests that assert one aggregation at a time).
def income_summary(db: Session) -> dict:
    return _summary(_appointments(db))


def income_by_month(db: Session) -> list[dict]:
    return _by_month(_appointments(db))


def income_by_payer(db: Session) -> list[dict]:
    return _by_payer(_appointments(db))


def outstanding_by_client(db: Session) -> list[dict]:
    return _outstanding(_appointments(db))
