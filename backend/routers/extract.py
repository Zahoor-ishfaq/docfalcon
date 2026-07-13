"""Extraction routes — OCR + LLM pipeline."""

import hashlib
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from bson import ObjectId

from services.ocr import extract_text
from services.llm_client import extract, ExtractionError
from core.config import settings
from core.database import get_db

router = APIRouter(prefix="/extract", tags=["extract"])
logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
DOC_TYPES = {"iqama", "visa", "contract"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB

# Placeholder until Epic 4 auth attaches a real company_id.
DEV_COMPANY_ID = "000000000000000000000001"

MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"%PDF": "application/pdf",
}


def _validate_magic(header: bytes, claimed: str) -> None:
    for sig, mime in MAGIC.items():
        if header.startswith(sig):
            if mime != claimed:
                raise HTTPException(400, "File content doesn't match extension")
            return
    raise HTTPException(400, "Unrecognized file format")


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
async def extract_document(
    file: UploadFile = File(...),
    doc_type: str = Query(..., description="iqama | visa | contract"),
):
    """Upload a document, get structured JSON back. Idempotent by file hash."""
    if doc_type not in DOC_TYPES:
        raise HTTPException(400, f"doc_type must be one of: {', '.join(DOC_TYPES)}")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Allowed types: jpg, png, pdf. Got: {file.content_type}")

    contents = await file.read()

    if len(contents) > MAX_SIZE:
        raise HTTPException(400, f"File exceeds 5MB limit ({len(contents)} bytes)")

    _validate_magic(contents[:8], file.content_type)

    file_hash = hashlib.sha256(contents).hexdigest()
    db = get_db()
    company_oid = ObjectId(DEV_COMPANY_ID)

    # Idempotency: same file + same company → return prior extraction, skip LLM call.
    existing = await db.documents.find_one({"file_hash": file_hash, "company_id": company_oid})
    if existing:
        return _serialize_doc(existing)

    try:
        raw_text = extract_text(contents, file.content_type)
        result = extract(raw_text, doc_type)
    except ExtractionError as e:
        raise HTTPException(422, f"Extraction failed: {e}")
    except Exception as e:
        logger.error("extract_error doc_type=%s error=%s", doc_type, str(e)[:200])
        raise HTTPException(500, "Internal extraction error")

    meta = result.pop("_meta", {})
    tokens_used = (meta.get("tokens_in") or 0) + (meta.get("tokens_out") or 0)

    # Store hash + extracted JSON only. Original file bytes are discarded.
    doc = {
        "company_id": company_oid,
        "employee_id": None,  # linked later via employees API
        "doc_type": doc_type,
        "file_hash": file_hash,
        "extracted_fields": result,
        "llm_provider": meta.get("provider"),
        "tokens_used": tokens_used,
        "cost_usd": meta.get("cost_usd"),
    }
    await db.documents.insert_one(doc)

    return {
        "doc_type": doc_type,
        "fields": result,
        "llm_provider": meta.get("provider"),
        "tokens_used": tokens_used,
        "cost_usd": meta.get("cost_usd"),
        "file_hash": file_hash,
        "cached": False,
    }


@router.post("/ocr-test")
async def ocr_test(file: UploadFile = File(...)):
    """Dev-only: upload image/PDF, get raw OCR text back."""
    if settings.ENVIRONMENT != "development":
        raise HTTPException(403, "This endpoint is disabled in production")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Allowed types: jpg, png, pdf. Got: {file.content_type}")

    contents = await file.read()

    if len(contents) > MAX_SIZE:
        raise HTTPException(400, f"File exceeds 5MB limit ({len(contents)} bytes)")

    _validate_magic(contents[:8], file.content_type)

    raw_text = extract_text(contents, file.content_type)

    return {"filename": file.filename, "content_type": file.content_type, "raw_text": raw_text}