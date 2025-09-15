from __future__ import annotations

import os
import shutil
from email import policy
from email.parser import BytesParser
from typing import Dict, Any, List, Optional

from agents import function_tool
from imapclient import IMAPClient

from mail2mail.settings import get_imap_config


def _extract_attachments_from_eml(eml_path: str, target_dir: str) -> List[str]:
    saved: List[str] = []
    with open(eml_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    if not os.path.isdir(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    dangerous_exts = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js", ".jar", ".com", ".scr", ".msi", ".dll", ".html", ".htm"}
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = part.get_filename() or "attachment"
            try:
                ext = os.path.splitext(filename)[1].lower()
                if ext in dangerous_exts:
                    continue
            except Exception:
                pass
            raw = part.get_payload(decode=True) or b""
            out_path = os.path.join(target_dir, filename)
            with open(out_path, "wb") as outf:
                outf.write(raw)
            saved.append(out_path)
    return saved


@function_tool
def save_attachments(account_id: str, message_id: str, target_dir: str) -> Dict[str, Any]:
    """Сохранит вложения письма в target_dir; вернёт {saved_paths: [str]}.

    В прототипе ожидаем, что message_id — путь к локальному .eml
    """
    if message_id.endswith(".eml") and os.path.isfile(message_id):
        paths = _extract_attachments_from_eml(message_id, target_dir)
        return {"saved_paths": paths}
    # IMAP variant: message_id may be imap:<UID> or imap:latest_unseen
    if message_id.startswith("imap:"):
        cfg = get_imap_config(account_id)
        if not cfg:
            raise ValueError("IMAP config not found for account")
        mode = message_id.split(":", 1)[1]
        uid_to_fetch: Optional[int] = None
        with IMAPClient(cfg.host, port=cfg.port, ssl=cfg.use_ssl) as client:
            client.login(cfg.username, cfg.password)
            client.select_folder(cfg.mailbox)
            if mode == "latest_unseen":
                uids = client.search(["UNSEEN"]) or client.search(["ALL"])
                if not uids:
                    return {"saved_paths": []}
                uid_to_fetch = max(uids)
            else:
                try:
                    uid_to_fetch = int(mode)
                except ValueError:
                    raise ValueError("Unsupported imap message_id for attachments")

            raw = client.fetch([uid_to_fetch], [b'RFC822'])
            msg_bytes = raw[uid_to_fetch][b'RFC822']
            msg = BytesParser(policy=policy.default).parsebytes(msg_bytes)

            if not os.path.isdir(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            saved: List[str] = []
            dangerous_exts = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js", ".jar", ".com", ".scr", ".msi", ".dll", ".html", ".htm"}
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    filename = part.get_filename() or "attachment"
                    try:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in dangerous_exts:
                            continue
                    except Exception:
                        pass
                    rawbin = part.get_payload(decode=True) or b""
                    out_path = os.path.join(target_dir, filename)
                    with open(out_path, "wb") as outf:
                        outf.write(rawbin)
                    saved.append(out_path)
            return {"saved_paths": saved}

    raise NotImplementedError("save_attachments supports local .eml path or imap:")
