"""Agent tool: find an employee by iqama number within a company."""

from bson import ObjectId
from backend.core.database import get_db


async def search_employees(iqama_number: str, company_id: str) -> dict | None:
    """Returns serialized employee dict or None if not found."""
    db = get_db()
    emp = await db.employees.find_one({
        "iqama_number": iqama_number,
        "company_id": ObjectId(company_id),
    })
    if not emp:
        return None
    emp["id"] = str(emp.pop("_id"))
    emp["company_id"] = str(emp["company_id"])
    return emp