# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libmagic1 libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY mail2mail /app/mail2mail
COPY external /app/external
COPY settings.yaml /app/settings.yaml
COPY cli.py /app/cli.py

RUN useradd -m app && mkdir -p /data && chown -R app:app /app /data
USER app

EXPOSE 8000

ENV SETTINGS_YAML=/app/settings.yaml \
    DATA_DIR=/data \
    ADMIN_SESSION_COOKIE=m2m_admin_session \
    ADMIN_SESSION_HTTPS_ONLY=true

CMD ["uvicorn", "mail2mail.admin.app:app", "--host", "0.0.0.0", "--port", "8000"]
