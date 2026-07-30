from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["zeropad"] = lambda v, w=2: str(int(v)).zfill(w)
