from fastapi.templating import Jinja2Templates

from app.cpt import BOOKABLE

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["zeropad"] = lambda v, w=2: str(int(v)).zfill(w)
# CPT dropdown options for the appointment forms (single source: app/cpt.py).
templates.env.globals["cpt_codes"] = BOOKABLE
