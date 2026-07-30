"""Email sending for appointment reminders.

Configured entirely from environment variables so no secret ever lands in the
database or the repo. With SMTP unset (local/dev, tests) it runs in **console
mode**: it logs the message and reports success without contacting a server.

Reminders carry minimal PHI — the practice name, date, and time only; never a
diagnosis or note.
"""
import os
import smtplib
from email.message import EmailMessage

from app.models.appointment import Appointment
from app.models.provider import Provider


def email_configured() -> bool:
    return bool(os.getenv("SMTP_HOST"))


def email_from() -> str:
    return os.getenv("SMTP_FROM", "reminders@localhost")


def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email; return True on success. Console mode when SMTP is unset."""
    host = os.getenv("SMTP_HOST")
    if not host:
        # Preview mode: log nothing sensitive (no recipient or subject/timing).
        print("[email:console] preview generated")
        return True

    msg = EmailMessage()
    msg["From"] = email_from()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as server:
            server.starttls()
            user = os.getenv("SMTP_USER")
            if user:
                server.login(user, os.getenv("SMTP_PASSWORD", ""))
            server.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        print(f"[email:error] {exc}")
        return False


def render_reminder(appt: Appointment, provider: Provider) -> tuple[str, str]:
    """Minimal-PHI reminder subject/body for one appointment."""
    practice = provider.practice_name or provider.name or "your therapist"
    when = appt.datetime.strftime("%A, %B %-d at %-I:%M %p")
    subject = f"Appointment reminder — {when}"
    # Generic greeting: keep the body to practice + date/time, no client-identifying info.
    body = (
        "Hello,\n\n"
        f"This is a reminder of your upcoming appointment with {practice} on {when}.\n\n"
        "If you need to reschedule, please reply to this email or call the office.\n\n"
        "To stop receiving these reminders, let us know and we'll turn them off."
    )
    return subject, body
