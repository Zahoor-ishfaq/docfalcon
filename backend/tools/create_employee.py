"""Agent tool: insert a new employee record."""

from datetime import datetime, timezone
from bson import ObjectId
from backend.core.database import get_db


async def create_employee(company_id: str, fields: dict) -> str:
    """Inserts employee from extracted fields. Returns new employee_id string."""
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "company_id": ObjectId(company_id),
        "name_en": fields.get("name_en") or fields.get("full_name_en"),
        "name_ar": fields.get("name_ar") or fields.get("full_name_ar"),
        "iqama_number": fields.get("iqama_number"),
        "iqama_expiry": fields.get("iqama_expiry") or fields.get("expiry_date"),  # LLM returns expiry_date
        "passport_expiry": fields.get("passport_expiry"),
        "visa_expiry": fields.get("visa_expiry"),
        "nationality": fields.get("nationality"),
        "profession": fields.get("profession"),
        "created_at": now,
        "updated_at": now,
    }
    result = await db.employees.insert_one(doc)
    return str(result.inserted_id)