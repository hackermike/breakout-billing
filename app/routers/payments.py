from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.crud import day_detail_context
from app.database import get_db
from app.models.appointment import Appointment
from app.models.payment import Payment
from app.templates_config import templates

router = APIRouter()


def _get_appointment(db: Session, appointment_id: int) -> Appointment:
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.get("/appointments/{appointment_id}/payment-form")
async def payment_form(request: Request, appointment_id: int, db: Session = Depends(get_db)):
    appt = _get_appointment(db, appointment_id)
    paid = sum(p.amount for p in appt.payments)
    return templates.TemplateResponse(
        request,
        "partials/payment_form.html",
        {
            "appointment": appt,
            "balance": round(appt.fee - paid, 2),
            "today": date.today().isoformat(),
        },
    )


@router.post("/appointments/{appointment_id}/payments")
async def create_payment(
    request: Request,
    appointment_id: int,
    amount: float = Form(...),
    payment_date: str = Form(...),
    payment_method: str = Form("card"),
    payer: str = Form("client"),
    db: Session = Depends(get_db),
):
    appt = _get_appointment(db, appointment_id)
    try:
        pay_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid payment date") from exc

    db.add(
        Payment(
            appointment_id=appt.id,
            amount=amount,
            payment_date=pay_date,
            payment_method=payment_method,
            payer=payer,
        )
    )
    db.commit()

    # Re-render the day detail for the appointment's day.
    return templates.TemplateResponse(
        request,
        "partials/day_detail.html",
        day_detail_context(db, appt.datetime),
    )
