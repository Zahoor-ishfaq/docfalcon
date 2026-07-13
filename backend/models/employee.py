from datetime import date, datetime, timedelta
from pydantic import Field
from .base import MongoModel, PyObjectId, utcnow


class Employee(MongoModel):
    company_id: PyObjectId
    name_en: str = Field(min_length=1, max_length=200)
    name_ar: str | None = Field(default=None, max_length=200)
    iqama_number: str | None = Field(default=None, max_length=20)
    iqama_expiry: date | None = None
    passport_expiry: date | None = None
    visa_expiry: date | None = None
    nationality: str | None = Field(default=None, max_length=100)
    profession: str | None = Field(default=None, max_length=200)
    updated_at: datetime = Field(default_factory=utcnow)


def compute_status(emp: dict) -> str:
    """expired if any expiry < today, expiring_30d if within 30d, else valid."""
    today = date.today()
    horizon = today + timedelta(days=30)

    def _to_date(v):
        if isinstance(v, datetime): return v.date()
        if isinstance(v, date): return v
        if isinstance(v, str):
            try: return date.fromisoformat(v[:10])
            except ValueError: return None
        return None

    expiries = [_to_date(emp.get(k)) for k in ("iqama_expiry", "passport_expiry", "visa_expiry")]
    expiries = [e for e in expiries if e is not None]
    if not expiries:
        return "valid"
    if any(e < today for e in expiries):
        return "expired"
    if any(e <= horizon for e in expiries):
        return "expiring_30d"
    return "valid"