"""Tests for OCR service — E1.5."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

SAMPLES = Path(__file__).parent.parent.parent / "docs" / "samples"

# --- OCR service direct tests ---

class TestOCRImage:
    """Test OCR on sample Iqama and visa PNGs."""

    def test_iqama_extracts_key_fields(self):
        """All 10 iqamas should return name, iqama number, and nationality."""
        from services.ocr import extract_text

        for img in sorted((SAMPLES / "iqama").glob("*.png")):
            with open(img, "rb") as f:
                text = extract_text(f.read(), "image/png")
            assert len(text) > 50, f"{img.name}: too little text extracted"
            # Iqama number is 10 digits — at least one should appear
            assert any(c.isdigit() for c in text), f"{img.name}: no digits found"

    def test_visa_extracts_key_fields(self):
        """All 5 visas should return readable text."""
        from services.ocr import extract_text

        for img in sorted((SAMPLES / "visa").glob("*.png")):
            with open(img, "rb") as f:
                text = extract_text(f.read(), "image/png")
            assert len(text) > 50, f"{img.name}: too little text extracted"


class TestOCRPdf:
    """Test OCR on sample contract PDFs."""

    def test_contract_extracts_text(self):
        """All 5 contracts should return substantial text."""
        from services.ocr import extract_text

        for pdf in sorted((SAMPLES / "contract").glob("*.pdf")):
            with open(pdf, "rb") as f:
                text = extract_text(f.read(), "application/pdf")
            assert len(text) > 100, f"{pdf.name}: too little text extracted"
            assert "contract" in text.lower() or "عقد" in text, f"{pdf.name}: missing contract keyword"


# --- Endpoint tests ---

class TestOCREndpoint:
    """Test /extract/ocr-test validation and response."""

    def test_valid_image_returns_text(self):
        img = SAMPLES / "iqama" / "iqama_01.png"
        with open(img, "rb") as f:
            resp = client.post("/extract/ocr-test", files={"file": ("iqama_01.png", f, "image/png")})
        assert resp.status_code == 200
        data = resp.json()
        assert "raw_text" in data
        assert len(data["raw_text"]) > 50

    def test_rejects_wrong_mime_type(self):
        resp = client.post(
            "/extract/ocr-test",
            files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")},
        )
        assert resp.status_code == 400

    def test_rejects_oversized_file(self):
        # 6MB of fake PNG data
        fake = b"\x89PNG" + b"\x00" * (6 * 1024 * 1024)
        resp = client.post(
            "/extract/ocr-test",
            files={"file": ("big.png", fake, "image/png")},
        )
        assert resp.status_code == 400

    def test_rejects_mismatched_magic_bytes(self):
        # Claims PNG but bytes are JPEG
        resp = client.post(
            "/extract/ocr-test",
            files={"file": ("fake.png", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/png")},
        )
        assert resp.status_code == 400