# MAIL2MAIL

Mail2Mail is a local agentic mail orchestrator that triages incoming messages, extracts context from attachments, and forwards relevant messages to configured recipients. It includes a minimal admin UI for configuration (mailboxes, SMTP, prompts/routing).

## Features
- FastAPI admin UI (login required)
- IMAP monitor for one or multiple mailboxes
- LLM-based triage + compose using OpenAI (configurable models)
- Attachment processing via external/Documents_processor
- Outgoing via a single global SMTP configuration

## Quick start (Docker Compose)

Prerequisites:
- Docker and Docker Compose
- OpenAI API key

Steps:
1. Copy env file and set secrets:
   ```bash
   cd /path/to/mail2mail
   cp env.example .env
   # edit .env: ADMIN_PASSWORD, OPENAI_API_KEY, SMTP_*
   ```
2. Start services:
   ```bash
   docker compose up -d --build
   ```
3. Open admin UI:
   - URL: `http://localhost:8000`
   - Login: `ADMIN_USER` / `ADMIN_PASSWORD`

## Admin UI
- Variables: shows masked `.env` variables
- Mailboxes: manage mailbox entries used by the monitor manager
- SMTP: set the single global SMTP sender (used by workers)
- Prompts/Models/Routing: tune LLM behavior and forwarding rules
- Queue: shows last processing results from `admin_queue.json`

## Monitoring
Two modes are wired in `docker-compose.yml`:
- `admin`: FastAPI admin on port 8000
- `manager`: multi-mailbox monitor; reads `admin_mailboxes.json` and processes UNSEEN messages

To run single-mailbox monitor manually:
```bash
docker compose run --rm admin python -m cli --account your_account monitor
```

## Volumes and data
Mounted from host for persistence and inspection:
- `admin_mailboxes.json`, `admin_smtp.json`, `admin_queue.json`
- `images/`, `media_for_processing/`, `tables/`, `processed_documents/`
- `settings.yaml` (read-only by default)

## Environment variables
See `env.example`. Key ones:
- `OPENAI_API_KEY`: required
- `ADMIN_USER`, `ADMIN_PASSWORD`, `ADMIN_SESSION_SECRET`: admin UI
- `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`: outgoing mail

## Build without compose
```bash
docker build -t mail2mail:latest .
# Admin UI
docker run --rm -p 8000:8000 --env-file .env mail2mail:latest
```

## Local development
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn mail2mail.admin.app:app --reload --port 8000
```

## Testing
```bash
pytest -q
```

## Security notes
- Never commit real `.env` or `admin_*.json` with secrets
- Use `ADMIN_PASSWORD_HASH` if you prefer hashed password injection
- Restrict access to the admin UI behind a reverse proxy with HTTPS in production
