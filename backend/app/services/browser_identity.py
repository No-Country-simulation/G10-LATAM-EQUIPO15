"""Identidad opaca de navegador; el secreto nunca se devuelve en JSON ni en URLs."""

from hashlib import sha256
from datetime import datetime, timezone
import re
import secrets
from urllib.parse import urlsplit

from fastapi.responses import JSONResponse

from app.core.config import settings

COOKIE = "nuevamente_historial"


async def browser_identity(request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    origin = request.headers.get("origin")
    try:
        foreign_origin = bool(origin) and (origin == "null" or urlsplit(origin).netloc.lower() != request.headers.get("host", "").lower())
    except ValueError:
        foreign_origin = True
    if foreign_origin:
        return JSONResponse(status_code=403, content={"detail": {
            "codigo": "ORIGEN_NO_PERMITIDO", "mensaje": "La solicitud debe realizarse desde esta aplicación.",
        }}, headers={"Cache-Control": "no-store"})
    token = request.cookies.get(COOKIE, "")
    is_new = re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None
    if is_new:
        token = secrets.token_urlsafe(32)
    request.state.history_owner = sha256(token.encode()).hexdigest()
    request.state.history_identity_new = is_new
    request.state.history_started = datetime.now(timezone.utc)
    response = await call_next(request)
    if is_new:
        response.set_cookie(COOKIE, token, max_age=365 * 24 * 60 * 60, httponly=True,
                            secure=settings.HISTORY_COOKIE_SECURE or request.url.scheme == "https", samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Cookie"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
