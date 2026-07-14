"""Shared file validation — magic bytes, filename sanitization, path traversal."""

import re
from fastapi import HTTPException

MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/zip",
}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")


def validate_magic(header: bytes, claimed: str) -> None:
    """Reject files whose real format contradicts the declared content type."""
    for sig, mime in MAGIC.items():
        if header.startswith(sig):
            if mime != claimed:
                raise HTTPException(400, "File content doesn't match its extension")
            return
    raise HTTPException(400, "Unrecognized file format")


def sanitize_filename(name: str) -> str:
    """Strip directory components and unsafe chars — blocks ../../etc/passwd."""
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = _SAFE_NAME.sub("_", base).lstrip(".")
    if not cleaned:
        raise HTTPException(400, "Invalid filename")
    return cleaned[:120]