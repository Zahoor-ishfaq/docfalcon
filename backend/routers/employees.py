from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pydantic import BaseModel
from datetime import date, datetime, timezone

from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.models.employee import Employee, compute_status

router = APIRouter(prefix="/employees", tags=["employees"])


class EmployeeIn(BaseModel):
    name_en: str
    name_ar: str | None = None
    iqama_number: str | None = None
    iqama_expiry: date | None = None
    passport_expiry: date | None = None
    visa_expiry: date | None = None
    nationality: str | None = None
    profession: str | None = None


class EmployeeUpdate(EmployeeIn):
    name_en: str | None = None


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc["company_id"] = str(doc["company_id"])
    doc["status"] = compute_status(doc)
    return doc


def _oid(id_: str) -> ObjectId:
    if not ObjectId.is_valid(id_):
        raise HTTPException(400, "Invalid employee id")
    return ObjectId(id_)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_employee(payload: EmployeeIn, current_user: dict = Depends(get_current_user)):
    db = get_db()
    company_oid = ObjectId(current_user["company_id"])
    emp = Employee(company_id=current_user["company_id"], **payload.model_dump())
    doc = emp.model_dump(exclude={"id"}, mode="json")
    doc["company_id"] = company_oid
    res = await db.employees.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _serialize(doc)


VALID_STATUSES = {"expired", "expiring_30d", "valid"}


@router.get("")
async def list_employees(
    status: str | None = Query(None, description="expired | expiring_30d | valid"),
    current_user: dict = Depends(get_current_user),
):
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(400, f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")

    db = get_db()
    cursor = db.employees.find({"company_id": ObjectId(current_user["company_id"])})
    results = [_serialize(d) async for d in cursor]
    if status:
        results = [r for r in results if r["status"] == status]
    return results


@router.get("/{id}")
async def get_employee(id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.employees.find_one({"_id": _oid(id), "company_id": ObjectId(current_user["company_id"])})
    if not doc:
        raise HTTPException(404, "Employee not found")
    return _serialize(doc)


@router.put("/{id}")
async def update_employee(id: str, payload: EmployeeUpdate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    updates = payload.model_dump(exclude_unset=True, mode="json")
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc)
    res = await db.employees.find_one_and_update(
        {"_id": _oid(id), "company_id": ObjectId(current_user["company_id"])},
        {"$set": updates},
        return_document=True,
    )
    if not res:
        raise HTTPException(404, "Employee not found")
    return _serialize(res)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    res = await db.employees.delete_one({"_id": _oid(id), "company_id": ObjectId(current_user["company_id"])})
    if res.deleted_count == 0:
        raise HTTPException(404, "Employee not found")