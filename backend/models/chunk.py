from datetime import datetime
from typing import Optional
from pydantic import Field
from .base import MongoModel, utcnow


class Chunk(MongoModel):
    company_id: str                       # multi-tenant filter — every vector search scoped to this
    document_id: str
    doc_type: str                         # denormalized for filter without join
    chunk_index: int
    text: str
    embedding: Optional[list[float]] = None  # 384-dim; set by rag.py after encode
    # Denormalized metadata for rich citations without extra queries at retrieval time.
    employee_label: Optional[str] = None  # e.g. "Ahmed Khan" or falls back to iqama/passport number
    iqama_number: Optional[str] = None
    expiry_date: Optional[str] = None     # kept as string — Ragas/JSON friendly, comes as-is from extraction
    created_at: datetime = Field(default_factory=utcnow)