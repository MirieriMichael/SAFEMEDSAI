# backend/Dockerfile
FROM python:3.11-slim

# --- System deps for OCR/OpenCV ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng libgl1 \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Add app code
COPY . /app

# Render provides $PORT. Use gunicorn for production-like server.
CMD sh -c "python manage.py migrate && gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 2"