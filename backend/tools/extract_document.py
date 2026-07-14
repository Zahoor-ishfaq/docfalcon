"""Agent tool: run OCR + LLM extraction on a file's bytes."""

from backend.services.ocr import extract_text
from backend.services.llm_client import extract, ExtractionError


async def extract_document(contents: bytes, content_type: str, doc_type: str) -> dict:
    """Returns {fields, raw_text, tokens_used, cost_usd, provider} or raises."""
    raw_text = extract_text(contents, content_type)
    result = extract(raw_text, doc_type)
    meta = result.pop("_meta", {})
    return {
        "fields": result,
        "raw_text": raw_text,
        "tokens_used": (meta.get("tokens_in") or 0) + (meta.get("tokens_out") or 0),
        "cost_usd": meta.get("cost_usd"),
        "provider": meta.get("provider"),
    }