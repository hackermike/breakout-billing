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


def _appt_with(payments, status="completed", fee=150.0, written_off=False):
    a = Appointment(datetime=datetime(2026, 7, 1, 9, 0), status=status,
                    fee=fee, cpt_code="90837", written_off=written_off)
    a.payments = payments
    return a


def test_refund_reduces_paid_and_collected():
    from app.models.payment import Payment as P
    appt = _appt_with([
        P(amount=150, payment_date=date(2026, 7, 1)),
        P(amount=40, payment_date=date(2026, 7, 2), is_refund=True),
    ])
    assert appt_paid(appt) == 110
    assert total_collected([appt]) == 110


def test_written_off_fee_excluded_from_ar():
    appts = [_appt_with([], fee=150.0, written_off=True)]
    bal = balance_on_services(appts)
    assert bal["charged"] == 0
    assert bal["outstanding"] == 0


def test_overpayment_shows_as_negative_balance_credit():
    appt = _appt_with([Payment(amount=200, payment_date=date(2026, 7, 1))], fee=150.0)
    bal = balance_on_services([appt])
    assert bal["outstanding"] == -50  # a $50 account credit


def test_total_servicer_fees_sums_processor_fees():
    from app.finances import total_servicer_fees
    from app.models.payment import Payment as P
    appt = _appt_with([
        P(amount=100, payment_date=date(2026, 7, 1), servicer_fee=2.90),
        P(amount=50, payment_date=date(2026, 7, 1), servicer_fee=1.45),
    ])
    assert total_servicer_fees([appt]) == 4.35
