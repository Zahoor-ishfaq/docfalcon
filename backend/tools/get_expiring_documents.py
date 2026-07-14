from datetime import datetime, timedelta
from backend.core.database import get_db
from backend.models.employee import compute_status

async def get_expiring_documents(company_id: str, days: int) -> list[dict]:
    """Find employees with any doc expiring within `days` from today."""
    db = get_db()
    cutoff = datetime.utcnow() + timedelta(days=days)
    today = datetime.utcnow()

    cursor = db.employees.find({"company_id": company_id})
    results = []

    async for emp in cursor:
        checks = {
            "iqama":    emp.get("iqama_expiry"),
            "passport": emp.get("passport_expiry"),
            "visa":     emp.get("visa_expiry"),
        }
        for doc_type, expiry in checks.items():
            if not expiry:
                continue
            # normalize — Motor returns datetime, but handle string too
            if isinstance(expiry, str):
                expiry = datetime.fromisoformat(expiry)
            if today <= expiry <= cutoff:
                results.append({
                    "employee_id": str(emp["_id"]),
                    "name":        emp.get("name_en") or emp.get("name_ar", "Unknown"),
                    "iqama_number": emp.get("iqama_number"),
                    "doc_type":    doc_type,
                    "expiry_date": expiry.date().isoformat(),
                    "days_left":   (expiry.date() - datetime.utcnow().date()).days,
                })

    return sorted(results, key=lambda x: x["days_left"])