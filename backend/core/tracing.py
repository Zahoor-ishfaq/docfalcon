from langfuse import Langfuse
from functools import lru_cache
from backend.core.config import settings

@lru_cache(maxsize=1)
def get_tracer() -> Langfuse | None:
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        return None
    try:
        return Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception:
        return None


def trace_generation(tracer: Langfuse | None, *, trace_name: str, model: str,
                     input, output: str, input_tokens: int, output_tokens: int,
                     cost_usd: float | None = None) -> None:
    """Best-effort — swallows all errors so tracing never breaks the request."""
    if not tracer:
        return
    try:
        trace = tracer.trace(name=trace_name)
        trace.generation(
            name=model,
            model=model,
            input=input,
            output=output,
            usage={"input": input_tokens, "output": output_tokens},
            metadata={"cost_usd": cost_usd} if cost_usd else {},
        )
        tracer.flush()
    except Exception:
        pass