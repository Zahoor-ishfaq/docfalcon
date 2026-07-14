import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.routers.dashboard import router as dashboard_router
from backend.core.config import settings
from backend.core.database import get_db, ping_db
from backend.core.middleware import SecurityHeadersMiddleware
from backend.services.vector_store import ensure_index
from backend.routers.extract import router as extract_router
from backend.routers.employees import router as employees_router
from backend.routers.auth import router as auth_router
from backend.routers.chat import router as chat_router
from backend.routers.onboard import router as onboard_router
from backend.routers.compliance import router as compliance_router


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("docfalcon")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ensure_index()
    except Exception as e:
        log.error("vector_index_init_failed error=%s", str(e)[:200])

    # TTL index expires consumed/stale refresh tokens without a cron job.
    try:
        db = get_db()
        await db.refresh_tokens.create_index("jti", unique=True)
        await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
    except Exception as e:
        log.error("refresh_token_index_failed error=%s", str(e)[:200])

    yield


# Swagger exposes the full API surface — keep it out of production.
_docs = "/docs" if settings.ENVIRONMENT == "development" else None

app = FastAPI(title="DocFalcon API", version="0.1.0", lifespan=lifespan, docs_url=_docs, redoc_url=None)

# slowapi resolves the limiter from app.state at request time; routers declare their own decorators.
app.state.limiter = Limiter(key_func=get_remote_address)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

app.include_router(auth_router)
app.include_router(extract_router)
app.include_router(employees_router)
app.include_router(dashboard_router)
app.include_router(chat_router)
app.include_router(onboard_router)
app.include_router(compliance_router)


@app.exception_handler(Exception)
async def unhandled_exc(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health():
    ok, err = await ping_db()
    return {"status": "ok", "db": "connected" if ok else "disconnected", "error": err}