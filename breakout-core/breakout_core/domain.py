"""Structural types describing the domain objects breakout-core operates on.

These are `Protocol`s, not classes to instantiate: any object with the right
attributes satisfies them. Breakout Billing's SQLAlchemy models satisfy them
today; the care platform's (multi-tenant) models will satisfy the same shapes.
This is how the shared logic stays free of any ORM.
"""
from datetime import date, datetime
from typing import Protocol


class PaymentLike(Protocol):
    amount: float
    servicer_fee: float | None
    is_refund: bool

    @property
    def signed_amount(self) -> float:
        """Amount as it affects totals: negative for a refund."""
        ...


class AppointmentLike(Protocol):
    status: str
    fee: float | None
    written_off: bool
    datetime: datetime
    cpt_code: str | None
    diagnosis_codes: str | None
    payments: list[PaymentLike]

    @property
    def modifiers(self) -> list[str]:
        """Non-empty CPT modifiers, in order."""
        ...


class ClientLike(Protocol):
    first_name: str
    last_name: str
    dob: date | None
    diagnosis_codes: str | None
    insurance_company: str | None
    insurance_id: str | None
    group_number: str | None

    @property
    def patient_name(self) -> str:
        """The identified patient's name, for the statement."""
        ...


class ProviderLike(Protocol):
    name: str | None
    credentials: str | None
    npi: str | None
    license_number: str | None
    tax_id: str | None
    address: str | None
    phone: str | None
    email: str | None
    practice_name: str | None
