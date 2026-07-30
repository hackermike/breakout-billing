from datetime import date, datetime

from app import cpt
from app.finances import appt_paid, balance_on_services, total_collected
from app.models.appointment import Appointment
from app.models.payment import Payment


def _appt(status="completed", fee=150.0, payments=()):
    a = Appointment(datetime=datetime(2026, 7, 1, 9, 0), status=status, fee=fee, cpt_code="90837")
    a.payments = [Payment(amount=p, payment_date=date(2026, 7, 1)) for p in payments]
    return a


def test_appt_paid_sums_payments():
    assert appt_paid(_appt(payments=[50, 25])) == 75


def test_balance_on_services_is_completed_scoped():
    appts = [_appt("completed", 150, [150]), _appt("scheduled", 200, [50])]
    bal = balance_on_services(appts)
    assert bal["charged"] == 150      # scheduled fee excluded
    assert bal["paid"] == 150         # payment on the scheduled appt excluded
    assert bal["outstanding"] == 0


def test_total_collected_counts_all_cash():
    appts = [_appt("completed", 150, [100]), _appt("scheduled", 200, [50])]
    assert total_collected(appts) == 150  # every payment, regardless of status


def test_cpt_catalog():
    assert cpt.default_fee("90837") == 150.0
    assert cpt.default_fee("unknown") == cpt.default_fee(cpt.DEFAULT_CODE)
    assert cpt.description("90834") == "Psychotherapy, 45 min"
    assert cpt.description("zzz") == "Psychotherapy"
    # The diagnostic-eval code exists for superbills but isn't a booking option.
    assert "90791" not in {c.code for c in cpt.BOOKABLE}
    assert "90791" in cpt.BY_CODE
