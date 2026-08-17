FROM python:3.12-slim

WORKDIR /app

# Install system deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ backend/
COPY frontend/ frontend/

# Cloud Run provides PORT env var, default 8080
ENV APP_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD exec gunicorn backend.wsgi:app \
    --workers=4 \
    --worker-class=sync \
    --bind=0.0.0.0:$PORT \
    --log-level=info \
    --access-logfile=-
