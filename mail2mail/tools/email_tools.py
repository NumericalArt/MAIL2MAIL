from __future__ import annotations

import email
import os
from email import policy
from email.parser import BytesParser
from typing import Any, Dict, List, Optional

from agents import function_tool
from imapclient import IMAPClient

from mail2mail.settings import get_imap_config, get_smtp_config
import smtplib
from email.message import EmailMessage


def _extract_links_from_text(text: str) -> List[str]:
    import re

    url_pattern = re.compile(r"https?://\S+")
    return url_pattern.findall(text or "")


def _parse_eml(file_path: str) -> Dict[str, Any]:
    with open(file_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    headers = dict(msg.items())
    text_plain: Optional[str] = None
    text_html: Optional[str] = None
    attachments_meta: List[Dict[str, Any]] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = part.get_content_disposition()
            content_type = part.get_content_type()
            if content_disposition == "attachment":
                attachments_meta.append(
                    {
                        "filename": part.get_filename() or "attachment",
                        "mime": content_type,
                        "size_bytes": len(part.get_payload(decode=True) or b""),
                    }
                )
            elif content_type == "text/plain" and text_plain is None:
                text_plain = part.get_content()
            elif content_type == "text/html" and text_html is None:
                text_html = part.get_content()
    else:
        ctype = msg.get_content_type()
        if ctype == "text/plain":
            text_plain = msg.get_content()
        elif ctype == "text/html":
            text_html = msg.get_content()

    links: List[str] = []
    if text_plain:
        links += _extract_links_from_text(text_plain)
    if text_html:
        links += _extract_links_from_text(text_html)

    return {
        "headers": headers,
        "text_plain": text_plain,
        "text_html": text_html,
        "links": list(dict.fromkeys(links)),
        "attachments_meta": attachments_meta,
    }


@function_tool
def read_message(account_id: str, message_id: str) -> Dict[str, Any]:
    """Вернёт нормализованное письмо.

    headers, text_plain, text_html, links[], attachments_meta[{filename, mime, size_bytes}]

    Для базового локального теста `message_id` может быть абсолютным путём к .eml файлу.
    """
    # Basic stub: if message_id is a path to a local EML, parse it
    if os.path.isfile(message_id) and message_id.endswith(".eml"):
        return _parse_eml(message_id)

    # IMAP support: message_id may be "imap:latest_unseen" or "imap:UID"
    if message_id.startswith("imap:"):
        cfg = get_imap_config(account_id)
        if not cfg:
            raise ValueError("IMAP config not found for account")

        uid_to_fetch: Optional[int] = None
        mode = message_id.split(":", 1)[1]
        with IMAPClient(cfg.host, port=cfg.port, ssl=cfg.use_ssl) as client:
            client.login(cfg.username, cfg.password)
            client.select_folder(cfg.mailbox)
            if mode == "latest_unseen":
                uids = client.search(["UNSEEN"]) or client.search(["ALL"])
                if not uids:
                    raise ValueError("No messages found")
                uid_to_fetch = max(uids)
            else:
                try:
                    uid_to_fetch = int(mode)
                except ValueError:
                    raise ValueError("Unsupported imap message_id. Use imap:latest_unseen or imap:<UID>")

            raw = client.fetch([uid_to_fetch], [b'RFC822'])
            msg_bytes = raw[uid_to_fetch][b'RFC822']
            # Parse bytes and reuse the .eml parser
            msg = BytesParser(policy=policy.default).parsebytes(msg_bytes)
            headers = dict(msg.items())
            text_plain: Optional[str] = None
            text_html: Optional[str] = None
            attachments_meta: List[Dict[str, Any]] = []
            if msg.is_multipart():
                for part in msg.walk():
                    content_disposition = part.get_content_disposition()
                    content_type = part.get_content_type()
                    if content_disposition == "attachment":
                        attachments_meta.append(
                            {
                                "filename": part.get_filename() or "attachment",
                                "mime": content_type,
                                "size_bytes": len(part.get_payload(decode=True) or b""),
                            }
                        )
                    elif content_type == "text/plain" and text_plain is None:
                        text_plain = part.get_content()
                    elif content_type == "text/html" and text_html is None:
                        text_html = part.get_content()
            else:
                ctype = msg.get_content_type()
                if ctype == "text/plain":
                    text_plain = msg.get_content()
                elif ctype == "text/html":
                    text_html = msg.get_content()

            links: List[str] = []
            if text_plain:
                links += _extract_links_from_text(text_plain)
            if text_html:
                links += _extract_links_from_text(text_html)

            return {
                "headers": headers,
                "text_plain": text_plain,
                "text_html": text_html,
                "links": list(dict.fromkeys(links)),
                "attachments_meta": attachments_meta,
            }

    # Otherwise, not supported
    raise NotImplementedError("read_message supports local .eml path or imap:latest_unseen/imap:<UID>")


from email.message import EmailMessage


def send_email_smtp(
    from_account_id: str,
    to: List[str],
    subject: str,
    body: str,
    attach_paths: List[str],
) -> Dict[str, Any]:
    """Internal helper to send email via SMTP (STARTTLS), returns {sent_message_id} or mock."""
    # Single global sender: if from_account_id is "__default__" use admin_smtp.json
    cfg = None
    if from_account_id == "__default__":
        # read admin_smtp.json
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        smtp_store = os.path.join(base, "admin_smtp.json")
        data = {}
        if os.path.isfile(smtp_store):
            import json
            try:
                data = json.loads(open(smtp_store, "r", encoding="utf-8").read() or "{}")
            except Exception:
                data = {}
        if data:
            # build cfg-like
            class _Cfg:
                pass
            c = _Cfg()
            c.host = data.get("host")
            c.port = int(data.get("port") or 587)
            c.starttls = bool(data.get("starttls", True))
            c.username = data.get("username")
            c.from_addr = data.get("from") or c.username
            # password from .env via get_smtp_config using username/from as account_id
            env_cfg = get_smtp_config(c.username or c.from_addr or "")
            c.password = env_cfg.password if env_cfg else None
            cfg = c
    else:
        cfg = get_smtp_config(from_account_id)
    if not cfg:
        mock_id = f"sent://{from_account_id}/to={len(to)}"
        return {"sent_message_id": mock_id}

    # Sanitize subject to avoid header injection
    safe_subject = (subject or "").replace("\r", " ").replace("\n", " ")[:998]

    msg = EmailMessage()
    msg["From"] = cfg.from_addr
    msg["To"] = ", ".join(to)
    msg["Subject"] = safe_subject
    msg.set_content(body)

    for path in attach_paths or []:
        try:
            with open(path, "rb") as f:
                data = f.read()
            import mimetypes

            mime, _ = mimetypes.guess_type(path)
            maintype, subtype = (mime.split("/", 1) if mime else ("application", "octet-stream"))
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(path))
        except Exception:
            continue

    with smtplib.SMTP(cfg.host, cfg.port, timeout=30) as s:
        if cfg.starttls:
            s.starttls()
        s.login(cfg.username, cfg.password)
        s.send_message(msg)
    return {"sent_message_id": f"smtp://{cfg.host}:{cfg.port}/{len(to)}"}


@function_tool
def send(from_account_id: str, to: List[str], subject: str, body: str, attach_paths: List[str]) -> Dict[str, Any]:
    """Отправит письмо и вернёт {sent_message_id: str}. Tool wrapper."""
    return send_email_smtp(from_account_id, to, subject, body, attach_paths)
