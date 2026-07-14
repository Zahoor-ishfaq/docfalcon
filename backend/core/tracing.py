"""Langfuse client — no-op if keys not set (dev without tracing still works)."""

import logging
from functools import lru_cache
from typing import Optional
from langfuse import Langfuse

from backend.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_langfuse() -> Optional[Langfuse]:
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.info("langfuse_disabled reason=missing_keys")
        return None
    return Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,
    )