from __future__ import annotations

import shutil
from typing import Dict, Any

from agents import function_tool


@function_tool
def cleanup(work_dir: str) -> Dict[str, Any]:
    """Удалит временный каталог; вернёт {ok: true}."""
    try:
        shutil.rmtree(work_dir, ignore_errors=True)
        return {"ok": True}
    except Exception:
        return {"ok": False}
