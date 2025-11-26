# app/api/rate_limit.py
from __future__ import annotations

import os
import logging
from typing import Optional

log = logging.getLogger("rate_limit")

# settings import (opsiyonel fallback)
try:
    from app.core.config import settings  # type: ignore
except Exception:
    class _Fallback:
        RATE_LIMIT: str = "60/minute"
    settings = _Fallback()  # type: ignore


# -----------------------------------------------------------------------------
# SlowAPI (Flask-Limiter tarzı FastAPI rate limit)
# -----------------------------------------------------------------------------
try:
    from slowapi import Limiter  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore
    from slowapi.errors import RateLimitExceeded  # type: ignore
    from fastapi.responses import JSONResponse
    from fastapi import Request

    # Ortak limiter nesnesi (IP tabanlı)
    limiter = Limiter(key_func=get_remote_address)

    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
        """Hız limiti aşıldığında dönecek standart yanıt."""
        return JSONResponse(
            status_code=429,
            content={
                "code": "rate_limit_exceeded",
                "message": "Too many requests. Please try again later.",
                "detail": {
                    "limit": str(exc.detail),
                    "path": str(request.url.path),
                },
            },
        )

    # Uygulama genelinde kullanılacak varsayılan limit (örn. 60/dakika)
    DEFAULT_LIMIT = getattr(settings, "RATE_LIMIT", "60/minute")

    # Örnek kullanım (router içinde):
    # from app.api.rate_limit import limiter
    # @router.get("/endpoint")
    # @limiter.limit("5/minute")
    # async def endpoint(): ...
    #
    # veya global: app.state.limiter = limiter

except Exception as e:
    # slowapi yüklü değilse fallback
    log.warning("SlowAPI bulunamadı veya başlatılamadı: %s", e)

    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    async def rate_limit_exceeded_handler(*_, **__):
        return None

    limiter = DummyLimiter()
    DEFAULT_LIMIT = "disabled"
