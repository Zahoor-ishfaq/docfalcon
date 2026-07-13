"""OCR service: extract text from images and PDFs using Google Cloud Vision."""

import io
import logging
import os

from PIL import Image
from pdf2image import convert_from_bytes
from google.cloud import vision

logger = logging.getLogger(__name__)

# Set credentials path
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "google-vision-key.json"
)

# Eastern Arabic + Extended Arabic → Western digits
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = vision.ImageAnnotatorClient()
        logger.info("google_vision_initialized")
    return _client


def extract_text_from_image(image: Image.Image) -> str:
    """Run Google Cloud Vision on a PIL Image."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    content = buf.getvalue()

    gv_image = vision.Image(content=content)
    response = _get_client().text_detection(image=gv_image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    if response.text_annotations:
        return response.text_annotations[0].description.strip()
    return ""


def extract_text(file_bytes: bytes, content_type: str) -> str:
    """Route to image or PDF handler based on MIME type."""
    if content_type == "application/pdf":
        return _ocr_pdf(file_bytes)
    return _ocr_image(file_bytes)


def _ocr_image(file_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(file_bytes))
    text = extract_text_from_image(image)
    logger.info("ocr_complete type=image chars=%d", len(text))
    return text.translate(AR_DIGITS)


def _ocr_pdf(file_bytes: bytes) -> str:
    from backend.core.config import settings
    poppler = settings.POPPLER_PATH or None
    pages = convert_from_bytes(file_bytes, dpi=300, poppler_path=poppler)
    texts = [extract_text_from_image(page) for page in pages]
    combined = "\n\n".join(t for t in texts if t)
    logger.info("ocr_complete type=pdf pages=%d chars=%d", len(pages), len(combined))
    return combined.translate(AR_DIGITS)
