import json
from groq import AsyncGroq
from backend.core.config import settings

_client: AsyncGroq | None = None

def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _client

PROMPT = """You are a document classifier for Saudi HR documents.
Given OCR text, identify the document type.

Return ONLY valid JSON: {"doc_type": "<type>", "confidence": <0.0-1.0>}

doc_type must be exactly one of: "iqama", "visa", "contract"

Signals:
- iqama: رقم الإقامة, iqama number, residence permit, المهنة, الجنسية
- visa: تأشيرة, visa number, entry permit, مدة الإقامة
- contract: عقد عمل, employment contract, salary, طرف أول, طرف ثاني"""

async def classify_document(raw_text: str) -> dict:
    """Classify doc type before extraction to catch mislabeled uploads."""
    resp = await _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": raw_text[:3000]},
        ],
        max_tokens=60,
        temperature=0,
    )
    text = resp.choices[0].message.content.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)