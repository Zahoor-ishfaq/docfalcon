from backend.core.database import get_db
from backend.models.employee import compute_status
from bson import ObjectId

async def get_employee_summary(company_id: str, name_or_iqama: str) -> dict | None:
    """Return all doc fields + computed status for one employee (name or iqama lookup)."""
    db = get_db()

    # try iqama number first, then name substring
    query = {"company_id": company_id, "iqama_number": name_or_iqama}
    emp = await db.employees.find_one(query)

    if not emp:
        emp = await db.employees.find_one({
            "company_id": company_id,
            "name_en": {"$regex": name_or_iqama, "$options": "i"},
        })

    if not emp:
        return None

    emp["_id"] = str(emp["_id"])
    status = compute_status(emp)
    return {
        "id":               emp["_id"],
        "name_en":          emp.get("name_en"),
        "name_ar":          emp.get("name_ar"),
        "iqama_number":     emp.get("iqama_number"),
        "nationality":      emp.get("nationality"),
        "profession":       emp.get("profession"),
        "iqama_expiry":     emp.get("iqama_expiry"),
        "passport_expiry":  emp.get("passport_expiry"),
        "visa_expiry":      emp.get("visa_expiry"),
        "status":           status,
    }