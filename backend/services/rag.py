"""RAG pipeline: chunk + embed + store on ingest; embed + retrieve on query."""

import logging
from bson import ObjectId

from backend.services.chunker import chunk as chunk_text
from backend.services.embeddings import encode
from backend.services.vector_store import upsert_chunks, search

logger = logging.getLogger(__name__)


def _extract_metadata(extracted_fields: dict | None) -> dict:
    """Pull a stable, human-useful subset of fields for citation display.

    Different doc types name fields differently — we try common keys and fall back
    gracefully. Storing this on every chunk trades ~200 bytes for zero-lookup citations.
    """
    f = extracted_fields or {}
    label = (
        f.get("name_en")
        or f.get("full_name")
        or f.get("employee_name")
        or f.get("holder_name")
        or f.get("name")
        or f.get("iqama_number")
        or f.get("passport_number")
        or None
    )
    iqama = f.get("iqama_number") or f.get("id_number")
    expiry = (
        f.get("iqama_expiry")
        or f.get("visa_expiry")
        or f.get("expiry_date")
        or f.get("contract_end_date")
        or f.get("end_date")
    )
    return {
        "employee_label": str(label) if label else None,
        "iqama_number": str(iqama) if iqama else None,
        "expiry_date": str(expiry) if expiry else None,
    }


async def index_document(
    document_id: str,
    company_id: str,
    doc_type: str,
    raw_text: str,
    extracted_fields: dict | None = None,
) -> int:
    """Chunk → embed → store. Called after a document is inserted. Returns chunk count."""
    if not raw_text:
        return 0
    texts = chunk_text(raw_text, doc_type)
    if not texts:
        return 0
    embeddings = encode(texts)
    meta = _extract_metadata(extracted_fields)
    docs = [
        {
            "company_id": ObjectId(company_id),
            "document_id": ObjectId(document_id),
            "doc_type": doc_type,
            "chunk_index": i,
            "text": t,
            "embedding": e,
            **meta,
        }
        for i, (t, e) in enumerate(zip(texts, embeddings))
    ]
    n = await upsert_chunks(docs)
    logger.info("rag_indexed doc_id=%s chunks=%d label=%s", document_id, n, meta.get("employee_label"))
    return n


async def retrieve(
    query: str,
    company_id: str,
    document_id: str | None = None,
    doc_type: str | None = None,
    limit: int = 8,
) -> list[dict]:
    """Embed query → vector search. Always company-scoped; document_id and doc_type are optional narrowers."""
    if not query.strip():
        return []
    [qv] = encode([query])
    results = await search(qv, company_id, document_id=document_id, doc_type=doc_type, limit=limit)
    try:
        from backend.core.tracing import get_langfuse
        lf = get_langfuse()
        if lf:
            lf.trace(
                name="rag.retrieve",
                input={"query": query, "document_id": document_id, "doc_type": doc_type},
                output={"chunk_count": len(results)},
                metadata={"limit": limit},
            )
    except Exception as e:
        logger.debug("langfuse_trace_skipped err=%s", str(e)[:100])
    return results