from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.crud import day_detail_context, get_or_create_provider
from app.database import get_db
from app.finances import appt_paid
from app.models.appointment import Appointment
from app.models.payment import Payment
from app.templates_config import templates

router = APIRouter()


def _get_appointment(db: Session, appointment_id: int) -> Appointment:
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


def _get_payment(db: Session, payment_id: int) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


def _day_detail_response(request: Request, db: Session, dt) -> "templates.TemplateResponse":
    return templates.TemplateResponse(
        request, "partials/day_detail.html", day_detail_context(db, dt)
    )


def _servicer_fee(method: str, is_refund: bool, amount: float, percent: float | None) -> float:
    """Card-processor fee for a payment: a share of a credit-card charge, nothing
    for other methods or refunds."""
    if is_refund or method != "credit" or not percent:
        return 0.0
    return round(amount * percent / 100, 2)


@router.get("/appointments/{appointment_id}/payment-form")
async def payment_form(request: Request, appointment_id: int, db: Session = Depends(get_db)):
    appt = _get_appointment(db, appointment_id)
    provider = get_or_create_provider(db)
    return templates.TemplateResponse(
        request,
        "partials/payment_form.html",
        {
            "appointment": appt,
            "balance": round((appt.fee or 0) - appt_paid(appt), 2),
            "today": date.today().isoformat(),
            "default_credit_percent": provider.credit_fee_percent
            if provider.credit_fee_percent is not None else 2.9,
        },
    )


@router.post("/appointments/{appointment_id}/payments")
async def create_payment(
    request: Request,
    appointment_id: int,
    amount: float = Form(...),
    payment_date: str = Form(...),
    payment_method: str = Form("credit"),
    payer: str = Form("client"),
    servicer_fee_percent: float = Form(None),
    is_refund: str = Form(""),
    db: Session = Depends(get_db),
):
    appt = _get_appointment(db, appointment_id)
    if amount < 0:
        raise HTTPException(status_code=400, detail="Amount cannot be negative")
    try:
        pay_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid payment date") from exc

    refund = bool(is_refund)
    fee = _servicer_fee(payment_method, refund, amount, servicer_fee_percent)
    db.add(
        Payment(
            appointment_id=appt.id,
            amount=amount,
            payment_date=pay_date,
            payment_method=payment_method,
            payer=payer,
            servicer_fee=fee,
            is_refund=refund,
        )
    )
    db.commit()

    # Re-render the day detail for the appointment's day.
    return templates.TemplateResponse(
        request,
        "partials/day_detail.html",
        day_detail_context(db, appt.datetime),
    )


@router.post("/appointments/{appointment_id}/write-off")
async def toggle_write_off(
    request: Request, appointment_id: int, db: Session = Depends(get_db)
):
    appt = _get_appointment(db, appointment_id)
    appt.written_off = not appt.written_off
    db.commit()
    return _day_detail_response(request, db, appt.datetime)


@router.get("/payments/{payment_id}/edit-form")
async def payment_edit_form(request: Request, payment_id: int, db: Session = Depends(get_db)):
    payment = _get_payment(db, payment_id)
    return templates.TemplateResponse(
        request, "partials/payment_edit_form.html", {"payment": payment}
    )


@router.post("/payments/{payment_id}/edit")
async def update_payment(
    request: Request,
    payment_id: int,
    amount: float = Form(...),
    payment_date: str = Form(...),
    payment_method: str = Form("credit"),
    payer: str = Form("client"),
    servicer_fee: float = Form(0.0),
    is_refund: str = Form(""),
    db: Session = Depends(get_db),
):
    payment = _get_payment(db, payment_id)
    if amount < 0:
        raise HTTPException(status_code=400, detail="Amount cannot be negative")
    try:
        pay_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid payment date") from exc

    refund = bool(is_refund)
    payment.amount = amount
    payment.payment_date = pay_date
    payment.payment_method = payment_method
    payment.payer = payer
    payment.is_refund = refund
    # Only a (non-refund) credit-card payment carries a processor fee.
    payment.servicer_fee = servicer_fee if (payment_method == "credit" and not refund) else 0.0
    day = payment.appointment.datetime
    db.commit()
    return _day_detail_response(request, db, day)


@router.post("/payments/{payment_id}/delete")
async def delete_payment(request: Request, payment_id: int, db: Session = Depends(get_db)):
    payment = _get_payment(db, payment_id)
    day = payment.appointment.datetime
    db.delete(payment)
    db.commit()
    return _day_detail_response(request, db, day)
