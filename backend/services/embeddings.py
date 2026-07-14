"""Local sentence-transformers embeddings. Multilingual (Arabic + English), 384-dim, free."""

from functools import lru_cache
from sentence_transformers import SentenceTransformer

from backend.core.config import settings


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    # Lazy singleton — model (~90MB) loads once on first call, stays in memory.
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def encode(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts → list of 384-dim vectors."""
    if not texts:
        return []
    vectors = _model().encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return vectors.tolist()