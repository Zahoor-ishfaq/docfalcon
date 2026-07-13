from typing import Any, Literal
from pydantic import Field
from .base import MongoModel, PyObjectId


class Document(MongoModel):
    company_id: PyObjectId
    employee_id: PyObjectId | None = None  # linked to an employee later
    doc_type: Literal["iqama", "visa", "contract"]
    file_hash: str = Field(min_length=64, max_length=64)  # SHA-256 hex; original file NOT stored
    extracted_fields: dict[str, Any]
    confidence: float | None = Field(default=None, ge=0, le=1)
    llm_provider: Literal["claude", "groq"]
    tokens_used: int = Field(ge=0)
    cost_usd: float = Field(ge=0)