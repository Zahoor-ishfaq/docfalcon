"""Agent tool: patch existing employee fields."""

from datetime import datetime, timezone
from bson import ObjectId
from backend.core.database import get_db


async def update_employee(employee_id: str, fields: dict) -> bool:
    """Patches non-null fields onto an existing employee. Returns True if found."""
    db = get_db()
    # Normalize expiry_date → iqama_expiry
    if fields.get("expiry_date") and not fields.get("iqama_expiry"):
        fields["iqama_expiry"] = fields.pop("expiry_date")
    patch = {k: v for k, v in fields.items() if v is not None}
    patch["updated_at"] = datetime.now(timezone.utc)
    result = await db.employees.update_one(
        {"_id": ObjectId(employee_id)},
        {"$set": patch},
    )
    return result.matched_count > 0