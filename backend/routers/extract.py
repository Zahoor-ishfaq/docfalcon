"""Extraction routes — OCR + LLM pipeline."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request
from bson import ObjectId
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.services.ocr import extract_text
from backend.services.llm_client import extract, ExtractionError
from backend.services.rag import index_document
from backend.services.cache import cache_get, cache_set, cache_delete
from backend.tools.classify_document import classify_document
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.core.files import validate_magic, sanitize_filename

router = APIRouter(prefix="/extract", tags=["extract"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
DOC_TYPES = {"iqama", "visa", "contract"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB
TTL_EXTRACT = 86400  # 24h — extraction output for a given file hash is immutable


def _serialize_doc(d: dict) -> dict:
    return {
        "doc_type": d["doc_type"],
        "fields": d["extracted_fields"],
        "llm_provider": d.get("llm_provider"),
        "tokens_used": d.get("tokens_used"),
        "cost_usd": d.get("cost_usd"),
        "file_hash": d["file_hash"],
        "cached": True,
    }


@router.post("")
@limiter.limit("10/minute")
async def extract_document(
    request: Request,
    file: UploadFile = File(...),
    doc_type: str = Query(..., description="iqama | visa | contract"),
    current_user: dict = Depends(get_current_user),
):
    """Upload a document, get structured JSON back. Idempotent by file hash."""
    if doc_type not in DOC_TYPES:
        raise HTTPException(400, f"doc_type must be one of: {', '.join(DOC_TYPES)}")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Allowed types: jpg, png, pdf. Got: {file.content_type}")

    sanitize_filename(file.filename or "")

    contents = await file.read()

    if len(contents) > MAX_SIZE:
        raise HTTPException(400, f"File exceeds 5MB limit ({len(contents)} bytes)")

    validate_magic(contents[:8], file.content_type)

    file_hash = hashlib.sha256(contents).hexdigest()
    db = get_db()
    company_oid = ObjectId(current_user["company_id"])

    # Company-scoped key — the same file uploaded by two tenants must never cross over.
    cache_key = f"extract:{company_oid}:{file_hash}"
    hit = await cache_get(cache_key)
    if hit:
        return json.loads(hit)

    existing = await db.documents.find_one({"file_hash": file_hash, "company_id": company_oid})
    if existing:
        payload = _serialize_doc(existing)
        await cache_set(cache_key, json.dumps(payload), TTL_EXTRACT)
        return payload

    try:
        raw_text = extract_text(contents, file.content_type)
    except Exception as e:
        logger.error("ocr_error doc_type=%s error=%s", doc_type, str(e)[:200])
        raise HTTPException(500, "OCR failed")

    # Guard against mislabeled uploads before spending LLM tokens on extraction.
    try:
        classification = await classify_document(raw_text)
        detected = classification.get("doc_type")
        confidence = classification.get("confidence", 0)
        if detected and detected != doc_type and confidence >= 0.7:
            raise HTTPException(
                409,
                detail={
                    "detail": f"Document appears to be a '{detected}', not '{doc_type}'.",
                    "detected": detected,
                    "claimed": doc_type,
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        # Classifier failure must never block extraction — log and continue.
        logger.warning("classify_failed doc_type=%s error=%s", doc_type, str(e)[:200])

    try:
        result = extract(raw_text, doc_type)
    except ExtractionError as e:
        raise HTTPException(422, f"Extraction failed: {e}")
    except Exception as e:
        logger.error("extract_error doc_type=%s error=%s", doc_type, str(e)[:200])
        raise HTTPException(500, "Internal extraction error")

    meta = result.pop("_meta", {})
    tokens_used = (meta.get("tokens_in") or 0) + (meta.get("tokens_out") or 0)

    doc = {
        "company_id": company_oid,
        "employee_id": None,
        "doc_type": doc_type,
        "file_hash": file_hash,
        "extracted_fields": result,
        "raw_text": raw_text,
        "llm_provider": meta.get("provider"),
        "tokens_used": tokens_used,
        "cost_usd": meta.get("cost_usd"),
        "created_at": datetime.now(timezone.utc),
    }
    inserted = await db.documents.insert_one(doc)

    try:
        await index_document(str(inserted.inserted_id), str(company_oid), doc_type, raw_text, extracted_fields=result)
    except Exception as e:
        logger.error("rag_index_failed doc_id=%s error=%s", inserted.inserted_id, str(e)[:200])

    # New document changes total_documents — stats cache is now stale.
    await cache_delete(f"stats:{company_oid}")

    payload = {
        "doc_type": doc_type,
        "fields": result,
        "llm_provider": meta.get("provider"),
        "tokens_used": tokens_used,
        "cost_usd": meta.get("cost_usd"),
        "file_hash": file_hash,
        "cached": False,
    }
    # Store with cached=True so a replay reports correctly; this caller still sees False.
    await cache_set(cache_key, json.dumps({**payload, "cached": True}), TTL_EXTRACT)
    return payload