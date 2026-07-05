FROM python:3.11-slim

# system deps (optional but handy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy code
COPY app ./app
COPY web ./web

# App Runner uses PORT env; default to 8000
ENV PORT=8000
# Gunicorn with uvicorn workers (prod-ready)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

