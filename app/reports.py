"""Bookkeeping report aggregations.

Revenue is recognized when a session is **completed** (its fee becomes charged);
a written-off fee recognizes nothing. "Collected" is all cash received, net of
refunds. Income views (charged / collected / card fees / net) can be scoped to a
date range and grouped by month, quarter, or year. Accounts receivable is a
*current* balance, so it is never date-scoped.

The pure `_*` helpers work off an already-loaded list of appointments so a single
dashboard render only queries the database once (see `dashboard`).
"""
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.finances import appt_charged, balance_on_services
from app.models.appointment import Appointment

GROUPS = ("month", "quarter", "year")


def _appointments(db: Session) -> list[Appointment]:
    return (
        db.query(Appointment)
        .options(joinedload(Appointment.client), joinedload(Appointment.payments))
        .all()
    )


def _in_range(d: date, start: date | None, end: date | None) -> bool:
    return (start is None or d >= start) and (end is None or d <= end)


def _period_key(d: date, group: str) -> str:
    if group == "year":
        return f"{d.year}"
    if group == "quarter":
        return f"{d.year}-Q{(d.month - 1) // 3 + 1}"
    return d.strftime("%Y-%m")


def _charged_in_range(appts, start, end) -> float:
    return round(sum(
        appt_charged(a) for a in appts if _in_range(a.datetime.date(), start, end)
    ), 2)


def _collected_in_range(appts, start, end) -> float:
    return round(sum(
        p.signed_amount for a in appts for p in a.payments
        if _in_range(p.payment_date, start, end)
    ), 2)


def _fees_in_range(appts, start, end) -> float:
    return round(sum(
        p.servicer_fee or 0 for a in appts for p in a.payments
        if _in_range(p.payment_date, start, end)
    ), 2)


def _summary(appts: list[Appointment], start=None, end=None) -> dict:
    charged = _charged_in_range(appts, start, end)
    collected = _collected_in_range(appts, start, end)
    fees = _fees_in_range(appts, start, end)
    return {
        "charged": charged,
        "collected": collected,          # cash received in range, net of refunds
        "servicer_fees": fees,           # card-processor fees paid out
        "net_collected": round(collected - fees, 2),
        # A/R is a current balance, not scoped to the selected range.
        "outstanding": balance_on_services(appts)["outstanding"],
    }


def _by_period(appts: list[Appointment], group: str, start=None, end=None) -> list[dict]:
    charged = defaultdict(float)
    collected = defaultdict(float)
    fees = defaultdict(float)
    for a in appts:
        billed = appt_charged(a)
        if billed and _in_range(a.datetime.date(), start, end):
            charged[_period_key(a.datetime.date(), group)] += billed
        for p in a.payments:
            if _in_range(p.payment_date, start, end):
                k = _period_key(p.payment_date, group)
                collected[k] += p.signed_amount
                fees[k] += p.servicer_fee or 0

    keys = sorted(set(charged) | set(collected))
    return [
        {
            "period": k,
            "charged": round(charged[k], 2),
            "collected": round(collected[k], 2),
            "servicer_fees": round(fees[k], 2),
            "net_collected": round(collected[k] - fees[k], 2),
        }
        for k in keys
    ]


def _by_month(appts: list[Appointment]) -> list[dict]:
    """Month-keyed income (kept for the per-view wrapper and its tests)."""
    return [{"month": r["period"], **r} for r in _by_period(appts, "month")]


def _by_payer(appts: list[Appointment], start=None, end=None) -> list[dict]:
    totals = defaultdict(float)
    for a in appts:
        for p in a.payments:
            if _in_range(p.payment_date, start, end):
                totals[p.payer or "unknown"] += p.signed_amount
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


def _by_client(appts: list[Appointment], start=None, end=None) -> list[dict]:
    """Per-client statement rows: sessions/charged/collected in the selected range,
    plus the client's current outstanding balance."""
    groups: dict[int, list[Appointment]] = defaultdict(list)
    names: dict[int, str] = {}
    for a in appts:
        groups[a.client_id].append(a)
        names[a.client_id] = a.client.full_name

    rows = []
    for cid, client_appts in groups.items():
        charged = _charged_in_range(client_appts, start, end)
        collected = _collected_in_range(client_appts, start, end)
        sessions = sum(
            1 for a in client_appts
            if appt_charged(a) and _in_range(a.datetime.date(), start, end)
        )
        balance = balance_on_services(client_appts)["outstanding"]
        if charged or collected or abs(balance) > 0.005:
            rows.append({
                "client_id": cid,
                "client": names[cid],
                "sessions": sessions,
                "charged": charged,
                "collected": collected,
                "balance": balance,
            })
    return sorted(rows, key=lambda r: (-r["balance"], r["client"]))


def dashboard(db: Session, group: str = "month", start=None, end=None) -> dict:
    """Load appointments once and derive every report view from that snapshot."""
    appts = _appointments(db)
    return {
        "summary": _summary(appts, start, end),
        "group": group,
        "by_period": _by_period(appts, group, start, end),
        "by_payer": _by_payer(appts, start, end),
        "outstanding": _outstanding(appts),
        "by_client": _by_client(appts, start, end),
        "start": start,
        "end": end,
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
