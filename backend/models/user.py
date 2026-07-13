from typing import Literal
from pydantic import EmailStr, Field
from .base import MongoModel, PyObjectId


class User(MongoModel):
    email: EmailStr
    password_hash: str | None = None  # null for OAuth-only users
    company_id: PyObjectId
    auth_provider: Literal["local", "google"] = "local"