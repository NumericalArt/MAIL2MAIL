from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from agents import function_tool
from pydantic import BaseModel, ConfigDict


def _run_documents_processor(path: str, work_dir: str, options: Optional[ProcessOptions]) -> Dict[str, Any]:
    """Invoke external/Documents_processor to process a file and return extracted pieces.

    We import its module directly to avoid spawning a process; fallback to simple stub if import fails.
    """
    try:
        import sys
        proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ext_dir = os.path.join(proj_root, "external", "Documents_processor")
        if ext_dir not in sys.path:
            sys.path.insert(0, ext_dir)

        from documents_processor import Document  # type: ignore

        # Configure page limits via env if provided
        if options and options.page_limits is not None:
            os.environ["MAX_DOCUMENT_PAGES"] = str(options.page_limits)
            os.environ["DISABLE_PAGE_LIMIT"] = "false"

        # Pass vision toggle via env for the downstream library
        if options and options.vision_descriptions is not None:
            os.environ["MAX_VISION_CALLS_PER_PAGE"] = "50" if options.vision_descriptions else "0"

        # Optional model routing for vision descriptions
        docs_vision_model = os.getenv("DOCS_VISION_MODEL")
        if docs_vision_model:
            os.environ["DOCS_VISION_MODEL"] = docs_vision_model

        doc = Document(path)
        doc.process()

        # Gather results
        text_content = getattr(doc, "text_content", "") or ""
        tables = getattr(doc, "tables", []) or []
        images = getattr(doc, "images", []) or []
        return {
            "extracted_text": text_content,
            "tables": tables,
            "images": images,
            "notes": [],
        }
    except Exception as e:  # fallback
        return {
            "extracted_text": f"[documents_processor error] {e}",
            "tables": [],
            "images": [],
            "notes": [f"documents_processor failure: {e}"],
        }


class ProcessOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_limits: Optional[int] = None
    vision_descriptions: Optional[bool] = None


@function_tool
def process_files(paths: List[str], options: Optional[ProcessOptions] = None) -> Dict[str, Any]:
    """Извлечёт текст/таблицы/описания изображений из файлов локально.

    Прототип: возвращает объединённый псевдо‑текст и пустые tables/images.
    В дальнейшем подключим NumericalArt/Documents_processor через CLI/SDK.
    """
    notes: List[str] = []
    combined_texts: List[str] = []
    all_tables: List[Dict[str, Any]] = []
    all_images: List[Dict[str, Any]] = []

    work_dir = os.getenv("TMP_ROOT", os.path.abspath(os.path.join(os.getcwd(), "tmp")))
    os.makedirs(work_dir, exist_ok=True)

    for p in paths or []:
        if not os.path.exists(p):
            notes.append(f"missing: {p}")
            continue
        result = _run_documents_processor(p, work_dir, options)
        if result.get("extracted_text"):
            combined_texts.append(str(result.get("extracted_text")))
        all_tables.extend(result.get("tables", []))
        all_images.extend(result.get("images", []))
        notes.extend(result.get("notes", []))

    return {
        "extracted_text": "\n\n".join(combined_texts),
        "tables": all_tables,
        "images": all_images,
        "notes": notes,
    }
