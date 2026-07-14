"""Reusable Pydantic validators — blocks NoSQL operator injection in user strings."""

from typing import Annotated
from pydantic import AfterValidator


def _no_mongo_operators(v: str) -> str:
    """Mongo treats leading $ as an operator and . as a path separator — neither is valid in a name."""
    if v.startswith("$") or v.startswith("."):
        raise ValueError("Value must not start with '$' or '.'")
    return v.strip()


SafeStr = Annotated[str, AfterValidator(_no_mongo_operators)]