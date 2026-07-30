"""Bookkeeping report aggregations.

Revenue is recognized when a session is **completed** (its fee becomes charged).
Cash is counted when a **payment** is received. Outstanding balance (accounts
receivable) is charged minus collected, per client.
"""
from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from app.models.appointment import Appointment

CHARGEABLE_STATUS = "completed"


def _appointments(db: Session) -> list[Appointment]:
    return (
        db.query(Appointment)
        .options(joinedload(Appointment.client), joinedload(Appointment.payments))
        .all()
    )


def income_summary(db: Session) -> dict:
    appts = _appointments(db)
    charged = sum(a.fee or 0 for a in appts if a.status == CHARGEABLE_STATUS)
    collected = sum(p.amount for a in appts for p in a.payments)
    return {
        "charged": charged,
        "collected": collected,
        "outstanding": round(charged - collected, 2),
    }


def income_by_month(db: Session) -> list[dict]:
    charged = defaultdict(float)
    collected = defaultdict(float)
    for a in _appointments(db):
        if a.status == CHARGEABLE_STATUS:
            charged[a.datetime.strftime("%Y-%m")] += a.fee or 0
        for p in a.payments:
            collected[p.payment_date.strftime("%Y-%m")] += p.amount

    months = sorted(set(charged) | set(collected))
    return [
        {
            "month": m,
            "charged": round(charged[m], 2),
            "collected": round(collected[m], 2),
        }
        for m in months
    ]


def income_by_payer(db: Session) -> list[dict]:
    totals = defaultdict(float)
    for a in _appointments(db):
        for p in a.payments:
            totals[p.payer or "unknown"] += p.amount
    return [
        {"payer": payer, "total": round(total, 2)}
        for payer, total in sorted(totals.items(), key=lambda kv: -kv[1])
    ]


def outstanding_by_client(db: Session) -> list[dict]:
    charged = defaultdict(float)
    paid = defaultdict(float)
    names = {}
    for a in _appointments(db):
        names[a.client_id] = a.client.full_name
        if a.status == CHARGEABLE_STATUS:
            charged[a.client_id] += a.fee or 0
        for p in a.payments:
            paid[a.client_id] += p.amount

    rows = []
    for cid, name in names.items():
        balance = round(charged[cid] - paid[cid], 2)
        if balance > 0.005:
            rows.append(
                {
                    "client": name,
                    "charged": round(charged[cid], 2),
                    "paid": round(paid[cid], 2),
                    "balance": balance,
                }
            )
    return sorted(rows, key=lambda r: -r["balance"])
