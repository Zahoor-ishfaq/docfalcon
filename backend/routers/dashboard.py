import json
from fastapi import APIRouter, Depends
from bson import ObjectId

from backend.core.dependencies import get_current_user
from backend.core.database import get_db
from backend.models.employee import compute_status
from backend.services.cache import cache_get, cache_set

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

TTL_STATS = 60  # short TTL — writes invalidate explicitly, this is just the backstop


def _stats_key(company_id: str) -> str:
    return f"stats:{company_id}"


@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    company_id = str(current_user["company_id"])
    key = _stats_key(company_id)

    cached = await cache_get(key)
    if cached:
        return json.loads(cached)

    db = get_db()
    oid = ObjectId(company_id)

    total_employees = await db.employees.count_documents({"company_id": oid})
    total_documents = await db.documents.count_documents({"company_id": oid})

    # Status is computed at read-time, never stored — cannot aggregate in Mongo.
    counts = {"expired": 0, "expiring_30d": 0, "valid": 0}
    async for emp in db.employees.find({"company_id": oid}):
        counts[compute_status(emp)] = counts.get(compute_status(emp), 0) + 1

    result = {
        "total_employees": total_employees,
        "total_documents": total_documents,
        "expired": counts["expired"],
        "expiring_soon": counts["expiring_30d"],
        "valid": counts["valid"],
    }

    await cache_set(key, json.dumps(result), TTL_STATS)
    return result