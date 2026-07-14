from datetime import datetime
from typing import Optional, Literal
from pydantic import Field
from .base import MongoModel, utcnow

class Document(MongoModel):
    company_id: str
    employee_id: Optional[str] = None
    doc_type: Literal["iqama", "visa", "contract"]
    file_hash: str = Field(min_length=64, max_length=64)
    extracted_fields: dict = {}
    raw_text: Optional[str] = None          # OCR text — required for RAG chunking
    llm_provider: Optional[Literal["claude", "groq"]] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    created_at: datetime = Field(default_factory=utcnow)