"""Populate the database with demo data for July 2026."""
from datetime import date, datetime

import app.models  # noqa: F401 — registers models
from app.database import SessionLocal
from app.db_init import run_migrations
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.payment import Payment
from app.models.provider import Provider

CLIENTS = [
    dict(first_name="Sarah", last_name="Chen", dob=date(1988, 4, 12),
         email="s.chen@example.com", phone="(555) 234-5678",
         insurance_company="BlueCross BlueShield", insurance_id="BCB8812345",
         group_number="GRP001", diagnosis_codes="F41.1"),
    dict(first_name="Marcus", last_name="Thompson", dob=date(1975, 9, 23),
         email="m.thompson@example.com", phone="(555) 345-6789",
         insurance_company="Aetna", insurance_id="AET4456789",
         group_number="GRP002", diagnosis_codes="F33.0, F41.1"),
    dict(first_name="Elena", last_name="Rodriguez", dob=date(1992, 2, 7),
         email="e.rodriguez@example.com", phone="(555) 456-7890",
         insurance_company="UnitedHealthcare", insurance_id="UHC9934567",
         group_number="GRP003", diagnosis_codes="F43.10"),
    dict(first_name="James", last_name="Park", dob=date(1983, 11, 30),
         email="j.park@example.com", phone="(555) 567-8901",
         insurance_company="Cigna", insurance_id="CIG1123456",
         group_number="GRP004", diagnosis_codes="F32.1"),
    dict(first_name="Amara", last_name="Williams", dob=date(1990, 6, 18),
         email="a.williams@example.com", phone="(555) 678-9012",
         insurance_company="Humana", insurance_id="HUM7789012",
         group_number="GRP005", diagnosis_codes="F41.1, F32.1"),
    dict(first_name="David", last_name="Kim", dob=date(1967, 3, 5),
         email="d.kim@example.com", phone="(555) 789-0123",
         insurance_company="Medicare", insurance_id="MCD3345678",
         group_number="", diagnosis_codes="F33.0"),
]

PROVIDER = dict(
    name="Dr. Alex Morgan",
    credentials="PhD, LCSW",
    npi="1234567890",
    license_number="LCS-23456",
    practice_name="Mindful Path Therapy",
    address="123 Healing Way Suite 4, Portland OR 97201",
    phone="(503) 555-1234",
    email="dr.morgan@mindfulpath.com",
    tax_id="12-3456789",
)

# (day, hour, minute, client_index, status, cpt_code)
APPT_DATA = [
    # Week 1
    (1,   9,  0, 0, "completed", "90837"),
    (1,  10,  0, 1, "completed", "90834"),
    (1,  14,  0, 2, "completed", "90837"),
    (2,   9,  0, 3, "completed", "90837"),
    (2,  11,  0, 4, "completed", "90837"),
    (3,   9,  0, 5, "completed", "90834"),
    (3,  10,  0, 0, "completed", "90837"),
    # Week 2
    (7,   9,  0, 1, "completed", "90837"),
    (7,  10,  0, 2, "completed", "90837"),
    (7,  14,  0, 3, "completed", "90834"),
    (8,   9,  0, 4, "completed", "90837"),
    (8,  11,  0, 5, "completed", "90837"),
    (9,   9,  0, 0, "completed", "90837"),
    (9,  10, 30, 1, "completed", "90837"),
    (9,  14,  0, 2, "cancelled", "90837"),
    (10,  9,  0, 3, "completed", "90834"),
    (10, 11,  0, 4, "completed", "90837"),
    (11,  9,  0, 5, "completed", "90837"),
    (11, 13,  0, 0, "completed", "90837"),
    # Week 3
    (14,  9,  0, 1, "completed", "90837"),
    (14, 10,  0, 2, "completed", "90837"),
    (14, 14,  0, 3, "completed", "90834"),
    (15,  9,  0, 4, "completed", "90837"),
    (15, 11,  0, 5, "completed", "90837"),
    (16,  9,  0, 0, "completed", "90837"),
    (16, 10,  0, 1, "completed", "90837"),
    (17,  9,  0, 2, "no_show",   "90837"),
    (17, 11,  0, 3, "completed", "90837"),
    (17, 14,  0, 4, "completed", "90834"),
    (18,  9,  0, 5, "completed", "90837"),
    # Week 4
    (21,  9,  0, 0, "completed", "90837"),
    (21, 11,  0, 1, "completed", "90837"),
    (22,  9,  0, 2, "completed", "90837"),
    (22, 10,  0, 3, "completed", "90834"),
    (23,  9,  0, 4, "completed", "90837"),
    (23, 14,  0, 5, "completed", "90837"),
    (24,  9,  0, 0, "completed", "90837"),
    (24, 11,  0, 1, "cancelled", "90837"),
    (25,  9,  0, 2, "completed", "90837"),
    (25, 13,  0, 3, "completed", "90834"),
    # Week 5 — today (29) and upcoming
    (28,  9,  0, 4, "completed", "90837"),
    (28, 11,  0, 5, "completed", "90837"),
    (29,  9,  0, 0, "scheduled", "90837"),
    (29, 10,  0, 1, "scheduled", "90837"),
    (29, 14,  0, 2, "scheduled", "90834"),
    (30,  9,  0, 3, "scheduled", "90837"),
    (30, 11,  0, 4, "scheduled", "90837"),
    (31,  9,  0, 5, "scheduled", "90837"),
    (31, 14,  0, 0, "scheduled", "90834"),
]


def main():
    run_migrations()
    db = SessionLocal()

    if db.query(Client).count() > 0:
        print("Already seeded — skipping.")
        db.close()
        return

    provider = Provider(**PROVIDER)
    db.add(provider)
    db.flush()

    clients = []
    for data in CLIENTS:
        c = Client(**data)
        db.add(c)
        clients.append(c)
    db.flush()

    # Opt a few clients into email reminders so the Reminders panel has data.
    for c in clients[:4]:
        c.reminder_channel = "email"
        c.email_consent_at = datetime(2026, 7, 1, 9, 0)

    fee_for = {"90837": 150.0, "90834": 125.0, "90832": 100.0, "90847": 175.0, "90853": 80.0}

    appointments = []
    for i, (day, hour, minute, cidx, status, cpt) in enumerate(APPT_DATA):
        appt = Appointment(
            client_id=clients[cidx].id,
            datetime=datetime(2026, 7, day, hour, minute),
            duration_minutes=50 if cpt == "90837" else 45,
            cpt_code=cpt,
            fee=fee_for.get(cpt, 150.0),
            status=status,
            # Some sessions are telehealth; give them a demo video link.
            telehealth_url="https://meet.example.com/room/mindfulpath" if i % 4 == 0 else None,
        )
        db.add(appt)
        appointments.append(appt)
    db.flush()

    # Pay most completed sessions, but leave a few unpaid or partially paid and
    # mix payers, so bookkeeping reports show realistic A/R and payer splits.
    completed = [a for a in appointments if a.status == "completed"]
    for i, appt in enumerate(completed):
        if i % 9 == 4:
            continue  # unpaid -> shows as outstanding balance
        ratio = 0.5 if i % 9 == 7 else 1.0  # some partial payments
        payer = "client" if i % 3 == 0 else "insurance"
        db.add(Payment(
            appointment_id=appt.id,
            amount=round(appt.fee * ratio, 2),
            payment_date=appt.datetime.date(),
            payment_method="card" if payer == "client" else "insurance",
            payer=payer,
        ))

    db.commit()
    print(f"Seeded {len(clients)} clients and {len(appointments)} appointments.")
    db.close()


if __name__ == "__main__":
    main()
