from __future__ import annotations

from typing import Dict, Any

from agents import function_tool
from mail2mail.settings import get_settings


DEFAULT_RULES = {
    "invoices": {"to": ["billing@example.com"], "subject_prefix": "[Billing]"},
    "hr": {"to": ["hr@example.com"], "subject_prefix": "[HR]"},
    "support": {"to": ["helpdesk@example.com"], "subject_prefix": "[Support]"},
    "sales": {"to": ["sales@example.com"], "subject_prefix": "[Sales]"},
    "personal": {"to": [], "subject_prefix": None},
}


@function_tool
def resolve(category: str) -> Dict[str, Any]:
    """Вернёт адреса назначения {to[], subject_prefix?} по category.

    Источник правил: settings.yaml -> routing_rules[]. При отсутствии совпадений — пустые списки.
    """
    try:
        settings = get_settings()
        rules = settings.routing_rules or []
        for rule in rules:
            if str(rule.get("category", "")).strip() == str(category).strip():
                to = rule.get("to") or []
                subject_prefix = rule.get("subject_prefix") if rule.get("subject_prefix") is not None else None
                # Normalize to lists of strings
                to = [str(x).strip() for x in to if str(x).strip()]
                return {"to": to, "subject_prefix": subject_prefix}
    except Exception:
        pass
    # Fallback: no routing
    return {"to": [], "subject_prefix": None}
