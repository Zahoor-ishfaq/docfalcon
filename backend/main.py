import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.core.database import ping_db
from backend.routers.extract import router as extract_router
from backend.routers.employees import router as employees_router
from backend.routers.auth import router as auth_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("docfalcon")

app = FastAPI(title="DocFalcon API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(extract_router)
app.include_router(employees_router)


# Log full trace server-side, return clean JSON to client (no stack traces leaked).
@app.exception_handler(Exception)
async def unhandled_exc(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health():
    ok, err = await ping_db()
    return {"status": "ok", "db": "connected" if ok else "disconnected", "error": err}