from backend.core.database import get_db
from difflib import SequenceMatcher
import unicodedata, re

def _normalize(name: str) -> str:
    """Arabic yeh/kaf normalization + lowercase."""
    name = name.replace("ى", "ي").replace("ك", "ك")
    return re.sub(r"\s+", " ", name.strip().lower())

def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()

async def check_name_mismatch(company_id: str) -> list[dict]:
    """
    For each employee, compare iqama name vs contract name pulled from extracted_fields.
    Returns employees where similarity < 0.82.
    """
    db = get_db()
    results = []

    async for emp in db.employees.find({"company_id": company_id}):
        emp_id = str(emp["_id"])
        iqama_name = emp.get("name_en") or emp.get("name_ar", "")

        # find the most recent contract doc for this employee
        contract = await db.documents.find_one(
            {"company_id": company_id, "employee_id": emp_id, "doc_type": "contract"},
            sort=[("created_at", -1)],
        )
        if not contract:
            continue

        contract_name = (contract.get("extracted_fields") or {}).get("employee_name", "")
        if not contract_name:
            continue

        score = _similar(iqama_name, contract_name)
        if score < 0.82:
            results.append({
                "employee_id":   emp_id,
                "iqama_name":    iqama_name,
                "contract_name": contract_name,
                "similarity":    round(score, 3),
            })

    return results