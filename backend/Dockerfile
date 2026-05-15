# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System build dependencies for psycopg2 / cryptography / argon2-cffi / pillow / etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so the layer caches independently of source changes
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Application source
COPY . .

# Runtime directories the app expects (also mounted as volumes in compose)
RUN mkdir -p logs uploads/profile_pictures

# Run as a non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

EXPOSE 8000

# Default command — docker-compose overrides this to run init_db first
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
