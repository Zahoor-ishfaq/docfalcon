"""Unified LLM client — Claude Haiku primary, Groq fallback."""

import json
import logging

from anthropic import Anthropic, APIError as AnthropicError
from groq import Groq, APIError as GroqError

from core.config import settings

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
GROQ_MODEL = "llama-3.3-70b-versatile"


class ExtractionError(Exception):
    """Raised when LLM fails to produce valid output."""
    pass


def _call_claude(prompt: str) -> tuple:
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text, resp.usage.input_tokens, resp.usage.output_tokens


def _call_groq(prompt: str) -> tuple:
    client = Groq(api_key=settings.GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content, resp.usage.prompt_tokens, resp.usage.completion_tokens


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences if LLM wraps JSON in them."""
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        clean = clean.rsplit("```", 1)[0]
    return clean.strip()

def _calc_cost(provider: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate cost per call. Haiku: $0.25/1M in, $1.25/1M out. Groq: free."""
    if provider == "groq":
        return 0.0
    return (tokens_in * 0.25 / 1_000_000) + (tokens_out * 1.25 / 1_000_000)

def extract(text: str, doc_type: str) -> dict:
    """OCR text + doc_type → validated dict. Retries once on malformed output."""
    from models.extraction import EXTRACTION_MODELS

    if doc_type not in EXTRACTION_MODELS:
        raise ValueError(f"Unknown doc_type: {doc_type}")

    model_cls = EXTRACTION_MODELS[doc_type]
    prompt = _build_prompt(text, doc_type)
    provider = settings.LLM_PROVIDER.lower()
    last_error = None

    for attempt in range(2):
        tokens_in, tokens_out = 0, 0

        try:
            if provider == "claude":
                raw, tokens_in, tokens_out = _call_claude(prompt)
            else:
                raw, tokens_in, tokens_out = _call_groq(prompt)
        except (AnthropicError, Exception) as e:
            if provider != "claude":
                raise
            logger.warning("claude_failed error=%s, falling_back=groq", str(e)[:100])
            provider = "groq"
            raw, tokens_in, tokens_out = _call_groq(prompt)

        logger.info("llm_call provider=%s attempt=%d tokens_in=%d tokens_out=%d", provider, attempt + 1, tokens_in, tokens_out)

        try:
            parsed = json.loads(_strip_fences(raw))
            validated = model_cls(**parsed)
            result = validated.model_dump()
            cost = _calc_cost(provider, tokens_in, tokens_out)
            logger.info("llm_extract provider=%s doc_type=%s tokens_in=%d tokens_out=%d cost_usd=%.6f", provider, doc_type, tokens_in, tokens_out, cost)
            result["_meta"] = {"provider": provider, "tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd": cost}
            return result
        except (json.JSONDecodeError, Exception) as e:
            last_error = str(e)
            logger.warning("validation_failed attempt=%d error=%s", attempt + 1, last_error[:100])
            prompt = (
                f"{prompt}\n\n"
                f"YOUR PREVIOUS RESPONSE WAS INVALID: {last_error}\n"
                f"Return ONLY valid JSON matching the schema. No markdown, no explanation, no code fences."
            )

    raise ExtractionError(f"LLM output invalid after 2 attempts: {last_error}")


def _build_prompt(text: str, doc_type: str) -> str:
    """Prompt template per doc type — enforces strict JSON, nulls for missing fields."""
    schemas = {
        "iqama": {
            "fields": '{"name_en": str|null, "name_ar": str|null, "iqama_number": str|null, "nationality": str|null, "profession": str|null, "expiry_date": "YYYY-MM-DD"|null, "employer": str|null}',
            "hint": "Saudi residence permit (Iqama). Text may be bilingual Arabic/English. Use the GREGORIAN date (not Hijri) for expiry_date.",
        },
        "visa": {
            "fields": '{"name_en": str|null, "name_ar": str|null, "passport_number": str|null, "visa_number": str|null, "visa_type": str|null, "expiry_date": "YYYY-MM-DD"|null, "sponsor": str|null}',
            "hint": "Saudi visa document. Text may be bilingual Arabic/English. Use the GREGORIAN date (not Hijri) for expiry_date.",
        },
        "contract": {
            "fields": '{"employee_name": str|null, "employer": str|null, "position": str|null, "start_date": "YYYY-MM-DD"|null, "end_date": "YYYY-MM-DD"|null, "salary": str|null}',
            "hint": "Employment contract. Salary should include currency if visible.",
        },
    }

    schema = schemas[doc_type]

    return (
        f"You are a document data extractor for Saudi HR documents.\n"
        f"Document type: {doc_type}. {schema['hint']}\n\n"
        f"RULES:\n"
        f"- Return ONLY a valid JSON object. No markdown, no explanation, no code fences.\n"
        f"- Use null for any field you cannot confidently extract.\n"
        f"- Dates must be YYYY-MM-DD format.\n"
        f"- Do not guess or hallucinate values.\n"
        f"- Arabic names go in name_ar, English transliterations in name_en.\n\n"
        f"EXPECTED SCHEMA:\n{schema['fields']}\n\n"
        f"OCR TEXT:\n{text}"
    )