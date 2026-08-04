from fastapi.templating import Jinja2Templates

from app import auth
from app.cpt import BOOKABLE
from app.database import SessionLocal

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["zeropad"] = lambda v, w=2: str(int(v)).zfill(w)
# CPT dropdown options for the appointment forms (single source: app/cpt.py).
templates.env.globals["cpt_codes"] = BOOKABLE


def _login_enabled() -> bool:
    """Whether a login password is set — templates use it to show/hide Sign out."""
    db = SessionLocal()
    try:
        return auth.is_configured(db)
    finally:
        db.close()


templates.env.globals["login_enabled"] = _login_enabled
