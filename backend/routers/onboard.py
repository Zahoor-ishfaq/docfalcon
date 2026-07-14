"""Onboarding agent router — ZIP upload + SSE streaming."""

import io
import json
import logging
import zipfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.core.dependencies import get_current_user
from backend.core.files import validate_magic, sanitize_filename
from backend.services.ocr import extract_text
from backend.services.agent import run_agent

router = APIRouter(prefix="/onboard", tags=["onboard"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

MAX_ZIP_SIZE = 20 * 1024 * 1024  # 20MB
MAX_FILES = 20
MAX_UNCOMPRESSED = 60 * 1024 * 1024  # zip-bomb guard: total inflated size
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
EXTENSION_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
}


@router.post("")
@limiter.limit("5/minute")
async def onboard(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Accept a ZIP, stream SSE progress events as agent processes each file."""
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Only .zip files accepted")

    contents = await file.read()
    if len(contents) > MAX_ZIP_SIZE:
        raise HTTPException(400, "ZIP exceeds 20MB limit")

    validate_magic(contents[:8], "application/zip")

    try:
        zf = zipfile.ZipFile(io.BytesIO(contents))
    except zipfile.BadZipFile:
        raise HTTPException(400, "Invalid ZIP file")

    entries = [
        e for e in zf.infolist()
        if not e.is_dir() and not e.filename.startswith("__MACOSX")
    ]

    # Reject absolute paths / traversal before reading anything out of the archive.
    for e in entries:
        if e.filename.startswith("/") or ".." in e.filename.replace("\\", "/").split("/"):
            raise HTTPException(400, "ZIP contains unsafe file paths")

    if sum(e.file_size for e in entries) > MAX_UNCOMPRESSED:
        raise HTTPException(400, "ZIP uncompressed size too large")

    valid = []
    for e in entries:
        ext = "." + e.filename.rsplit(".", 1)[-1].lower() if "." in e.filename else ""
        if ext in ALLOWED_EXTENSIONS:
            valid.append((e, ext))

    if not valid:
        raise HTTPException(400, "ZIP contains no supported files (jpg, png, pdf)")

    if len(valid) > MAX_FILES:
        raise HTTPException(400, f"ZIP contains {len(valid)} files — max {MAX_FILES}")

    # Read bytes + OCR upfront so the agent has raw_text immediately.
    files = []
    ocr_errors = []
    for entry, ext in valid:
        safe_name = sanitize_filename(entry.filename)
        file_bytes = zf.read(entry.filename)
        content_type = EXTENSION_MIME[ext]

        # An .png that is really an executable must never reach OCR.
        try:
            validate_magic(file_bytes[:8], content_type)
        except HTTPException:
            logger.warning("magic_mismatch file=%s", safe_name)
            ocr_errors.append(safe_name)
            continue

        try:
            raw_text = extract_text(file_bytes, content_type)
        except Exception as e:
            logger.error("ocr_failed file=%s error=%s", safe_name, str(e)[:200])
            ocr_errors.append(safe_name)
            continue

        files.append({
            "name": safe_name,
            "contents": file_bytes,
            "content_type": content_type,
            "raw_text": raw_text,
        })

    if not files:
        raise HTTPException(422, "No valid files could be processed from ZIP")

    company_id = current_user["company_id"]
    user_id = str(current_user["_id"])

    async def event_stream():
        for name in ocr_errors:
            yield _sse({"type": "tool_error", "tool": "ocr", "file": name, "error": "File rejected or OCR failed"})

        async for event in run_agent(files, company_id, user_id):
            yield _sse(event)

        yield _sse({"type": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # disables Nginx buffering on Render
    })


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"