"""Single source of truth for CPT (procedure) codes.

Booking (default fee/duration), the superbill (description), and the appointment
forms (dropdown options) all read from here instead of keeping their own copies.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Cpt:
    code: str
    label: str        # for form dropdowns, e.g. "90837 — 60 min psychotherapy"
    description: str  # for superbills, e.g. "Psychotherapy, 60 min"
    fee: float        # default session fee
    duration: int     # default duration in minutes
    bookable: bool = True  # shown in the booking/edit form dropdowns


CPT_CODES: list[Cpt] = [
    Cpt("90837", "90837 — 60 min psychotherapy", "Psychotherapy, 60 min", 150.0, 50),
    Cpt("90834", "90834 — 45 min psychotherapy", "Psychotherapy, 45 min", 125.0, 45),
    Cpt("90832", "90832 — 30 min psychotherapy", "Psychotherapy, 30 min", 100.0, 30),
    Cpt("90847", "90847 — family therapy", "Family psychotherapy w/ patient", 175.0, 50),
    Cpt("90853", "90853 — group therapy", "Group psychotherapy", 80.0, 45),
    Cpt("90791", "90791 — diagnostic evaluation", "Psychiatric diagnostic evaluation",
        200.0, 60, bookable=False),
]

BY_CODE: dict[str, Cpt] = {c.code: c for c in CPT_CODES}
BOOKABLE: list[Cpt] = [c for c in CPT_CODES if c.bookable]
DEFAULT_CODE = "90837"


def default_fee(code: str) -> float:
    cpt = BY_CODE.get(code)
    return cpt.fee if cpt else BY_CODE[DEFAULT_CODE].fee


def description(code: str) -> str:
    cpt = BY_CODE.get(code)
    return cpt.description if cpt else "Psychotherapy"
