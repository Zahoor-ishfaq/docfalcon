from datetime import datetime, timezone
from typing import Annotated
from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _validate_oid(v):
    if isinstance(v, ObjectId): return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v): return v
    raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[str, BeforeValidator(_validate_oid)]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MongoModel(BaseModel):
    # populate_by_name lets us read Mongo's `_id` into our `id` field
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    id: PyObjectId | None = Field(default=None, alias="_id")
    created_at: datetime = Field(default_factory=utcnow)