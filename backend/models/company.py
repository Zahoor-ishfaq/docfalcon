from pydantic import Field
from .base import MongoModel


class Company(MongoModel):
    name: str = Field(min_length=1, max_length=200)