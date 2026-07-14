"""Security headers on every response."""

from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.config import settings

HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for k, v in HEADERS.items():
            response.headers.setdefault(k, v)
        # HSTS is meaningless (and harmful) over plain HTTP in dev.
        if settings.ENVIRONMENT == "production":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response