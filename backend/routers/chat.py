"""Chat routes — company-wide RAG Q&A with conversation history."""

import logging
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Literal
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.services.chat import answer

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=4000)


class ChatQuery(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    doc_type: Optional[Literal["iqama", "visa", "contract"]] = None
    document_id: Optional[str] = None
    history: list[HistoryMessage] = Field(default_factory=list, max_length=10)  # last 5 exchanges


@router.post("")
@limiter.limit("30/minute")
async def chat(
    request: Request,
    body: ChatQuery,
    current_user: dict = Depends(get_current_user),
):
    """Ask a question across all company documents. Optional filters: doc_type, document_id."""
    company_oid = ObjectId(current_user["company_id"])

    if body.document_id:
        try:
            doc_oid = ObjectId(body.document_id)
        except InvalidId:
            raise HTTPException(400, "Invalid document id")
        db = get_db()
        doc = await db.documents.find_one({"_id": doc_oid, "company_id": company_oid}, {"_id": 1})
        if not doc:
            raise HTTPException(404, "Document not found")

    try:
        return await answer(
            body.query,
            str(company_oid),
            doc_type=body.doc_type,
            document_id=body.document_id,
            history=[m.model_dump() for m in body.history],
        )
    except Exception as e:
        logger.error("chat_error error=%s", str(e)[:200])
        raise HTTPException(500, "Chat failed")


@router.get("/debug/counts")
async def debug_counts(current_user: dict = Depends(get_current_user)):
    db = get_db()
    company_oid = ObjectId(current_user["company_id"])
    docs = await db.documents.count_documents({"company_id": company_oid})
    chunks = await db.chunks.count_documents({"company_id": company_oid})
    doc_types = await db.chunks.distinct("doc_type", {"company_id": company_oid})
    return {"company_id": str(company_oid), "documents": docs, "chunks": chunks, "doc_types": doc_types}