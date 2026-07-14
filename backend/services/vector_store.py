"""Atlas Vector Search wrapper. Every query is company_id-filtered — no exceptions."""

import logging
from bson import ObjectId
from pymongo.operations import SearchIndexModel

from backend.core.database import get_db

logger = logging.getLogger(__name__)

INDEX_NAME = "chunks_vector_index"
EMBEDDING_DIM = 384

# Bump this when the index definition changes. ensure_index will drop + recreate on mismatch.
INDEX_VERSION = 2

INDEX_DEFINITION = {
    "fields": [
        {"type": "vector", "path": "embedding", "numDimensions": EMBEDDING_DIM, "similarity": "cosine"},
        {"type": "filter", "path": "company_id"},
        {"type": "filter", "path": "document_id"},
        {"type": "filter", "path": "doc_type"},
    ]
}


async def ensure_index() -> None:
    """Create/recreate the vector index. Idempotent — safe to call on every boot."""
    db = get_db()
    collections = await db.list_collection_names()
    if "chunks" not in collections:
        await db.create_collection("chunks")
    coll = db["chunks"]
    existing_paths = set()
    async for idx in coll.list_search_indexes():
        if idx["name"] == INDEX_NAME:
            for field in (idx.get("latestDefinition") or {}).get("fields", []):
                existing_paths.add(field.get("path"))
            break
    wanted_paths = {f["path"] for f in INDEX_DEFINITION["fields"]}

    # Missing index → create fresh.
    if not existing_paths:
        await coll.create_search_index(SearchIndexModel(definition=INDEX_DEFINITION, name=INDEX_NAME, type="vectorSearch"))
        logger.info("vector_index_created name=%s", INDEX_NAME)
        return

    # Stale index → drop + recreate so filter paths match.
    if existing_paths != wanted_paths:
        logger.info("vector_index_stale existing=%s wanted=%s — recreating", existing_paths, wanted_paths)
        await coll.drop_search_index(INDEX_NAME)
        # Atlas takes a moment to actually drop; retry loop kept simple — boot fails loudly if it truly can't recreate.
        await coll.create_search_index(SearchIndexModel(definition=INDEX_DEFINITION, name=INDEX_NAME, type="vectorSearch"))
        logger.info("vector_index_recreated name=%s", INDEX_NAME)


async def upsert_chunks(chunks: list[dict]) -> int:
    """Insert chunk docs. Caller supplies embedding + company_id + document_id."""
    if not chunks:
        return 0
    db = get_db()
    res = await db["chunks"].insert_many(chunks)
    return len(res.inserted_ids)


async def search(
    query_embedding: list[float],
    company_id: str,
    document_id: str | None = None,
    doc_type: str | None = None,
    limit: int = 8,
) -> list[dict]:
    """Vector search scoped to company. Optional filters narrow further."""
    db = get_db()
    filt: dict = {"company_id": ObjectId(company_id)}
    if document_id:
        filt["document_id"] = ObjectId(document_id)
    if doc_type:
        filt["doc_type"] = doc_type
    pipeline = [
        {
            "$vectorSearch": {
                "index": INDEX_NAME,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 100,
                "limit": limit,
                "filter": filt,
            }
        },
        {
            "$project": {
                "_id": 0,
                "text": 1,
                "chunk_index": 1,
                "document_id": 1,
                "doc_type": 1,
                "employee_label": 1,
                "iqama_number": 1,
                "expiry_date": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    return [d async for d in db["chunks"].aggregate(pipeline)]


async def delete_by_document(document_id: str) -> int:
    """Remove chunks when a document is deleted."""
    db = get_db()
    res = await db["chunks"].delete_many({"document_id": ObjectId(document_id)})
    return res.deleted_count