from fastapi import APIRouter, Depends, HTTPException, Query, status
from bson import ObjectId
from pydantic import BaseModel, Field
from datetime import date, datetime, timezone
from typing import Literal

from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.core.validators import SafeStr
from backend.models.employee import Employee, compute_status
from backend.services.cache import cache_delete

router = APIRouter(prefix="/employees", tags=["employees"])

def _stats_key(company_id: str) -> str:
    return f"stats:{company_id}"


class EmployeeIn(BaseModel):
    name_en: SafeStr = Field(min_length=1, max_length=200)
    name_ar: SafeStr | None = Field(default=None, max_length=200)
    iqama_number: SafeStr | None = Field(default=None, max_length=20)
    iqama_expiry: date | None = None
    passport_expiry: date | None = None
    visa_expiry: date | None = None
    nationality: SafeStr | None = Field(default=None, max_length=100)
    profession: SafeStr | None = Field(default=None, max_length=200)


class EmployeeUpdate(EmployeeIn):
    name_en: SafeStr | None = Field(default=None, min_length=1, max_length=200)


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
    await cache_delete(_stats_key(str(current_user["company_id"])))
    return _serialize(doc)


@router.get("")
async def list_employees(
    status: Literal["expired", "expiring_30d", "valid"] | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
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
    await cache_delete(_stats_key(str(current_user["company_id"])))
    return _serialize(res)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    res = await db.employees.delete_one({"_id": _oid(id), "company_id": ObjectId(current_user["company_id"])})
    if res.deleted_count == 0:
        raise HTTPException(404, "Employee not found")
    await cache_delete(_stats_key(str(current_user["company_id"])))