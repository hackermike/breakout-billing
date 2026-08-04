FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
# breakout-core is an editable path dependency in requirements.txt, so its
# sources must be present before the install step.
COPY breakout-core/ ./breakout-core/
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
