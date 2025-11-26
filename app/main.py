# app/main.py
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Iterable, List

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

# --- Config & Logging ---------------------------------------------------------
try:
    # Beklenen: app/core/config.py içinde pydantic BaseSettings -> settings
    from app.core.config import settings  # type: ignore
except Exception:
    # Emniyetli varsayılanlar (config hazır olmasa da dev ortamında çalışsın)
    class _FallbackSettings:
        PROJECT_NAME = "Jetlink Memory Bot"
        API_PREFIX = "/api"
        ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")
        LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        DB_PATH = os.getenv("DB_PATH", "./data/memory.db")

    settings = _FallbackSettings()  # type: ignore

logging.basicConfig(
    level=getattr(logging, getattr(settings, "LOG_LEVEL", "INFO")),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("app.main")

# --- Rate limit (SlowAPI entegrasyonu) ---------------------------------------
limiter = None
rate_limit_handler = None
try:
    # Beklenen: app/api/rate_limit.py -> limiter, rate_limit_exceeded_handler
    from app.api.rate_limit import limiter as _limiter, rate_limit_exceeded_handler as _rl_handler  # type: ignore

    limiter = _limiter
    rate_limit_handler = _rl_handler
except Exception:
    log.warning("Rate limit modülü yüklenemedi; hız sınırı devre dışı.")

# --- Auth dependency ----------------------------------------------------------
require_api_key = None
try:
    # Beklenen: app/api/auth.py -> require_api_key (FastAPI Depends ile kullanılacak)
    from app.api.auth import require_api_key as _require_api_key  # type: ignore

    require_api_key = _require_api_key
except Exception:
    log.warning("Auth modülü yüklenemedi; API anahtarı doğrulaması devre dışı.")

# --- Repository / DB init -----------------------------------------------------
ensure_schema = None
try:
    from app.db.repository import ensure_schema as _ensure_schema  # type: ignore

    ensure_schema = _ensure_schema
except Exception:
    log.warning("DB repository.ensure_schema bulunamadı; uygulama DB şemasını garanti etmeyecek.")

# --- Routers ------------------------------------------------------------------
from app.api.routes_chat import router as chat_router  # type: ignore
from app.api.routes_admin import router as admin_router  # type: ignore
try:
    from app.api.routes_memory import router as memory_router  # type: ignore
except Exception:
    memory_router = None
    log.warning("routes_memory.py bulunamadı; /memory uçları devre dışı kalacak.")


def _as_iter(x: Iterable[str] | str) -> List[str]:
    if isinstance(x, str):
        return [x]
    return list(x)


def create_app() -> FastAPI:
    app = FastAPI(
        title=getattr(settings, "PROJECT_NAME", "Jetlink Memory Bot"),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- CORS ---
    origins = getattr(settings, "ALLOWED_ORIGINS", ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_as_iter(origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Rate limit middleware/handler (varsa) ---
    if limiter is not None:
        # SlowAPI 0.1.x tarzı
        try:
            from slowapi import _rate_limit_exceeded_handler  # noqa: F401
            from slowapi.middleware import SlowAPIMiddleware  # type: ignore
            from slowapi.errors import RateLimitExceeded  # type: ignore

            app.state.limiter = limiter
            app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # type: ignore
            app.add_middleware(SlowAPIMiddleware)
            log.info("Rate limiting etkin.")
        except Exception as e:
            log.warning("Rate limiting middleware bağlanamadı: %s", e)

    # --- Global hata eşleyiciler ---
    # Uygulamaya özel Exception -> JSONResponse
    try:
        from app.core.errors import ApplicationError  # type: ignore
    except Exception:
        ApplicationError = RuntimeError  # type: ignore

    @app.exception_handler(ApplicationError)
    async def _app_error_handler(_, exc: Exception):
        log.exception("ApplicationError: %s", exc)
        return JSONResponse(status_code=400, content={"code": "application_error", "message": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"code": "validation_error", "errors": exc.errors()},
        )

    # --- Lifespan: ilk açılışta data klasörü/DB şeması ---
    @app.on_event("startup")
    async def _on_startup():
        data_dir = Path(getattr(settings, "DB_PATH", "./data/memory.db")).parent
        data_dir.mkdir(parents=True, exist_ok=True)
        if ensure_schema:
            try:
                ensure_schema(path=getattr(settings, "DB_PATH", "./data/memory.db"))  # type: ignore
                log.info("DB şeması garanti edildi.")
            except Exception as e:
                log.exception("DB şema garantisi başarısız: %s", e)

    # --- Router montajı ---
    api_prefix = getattr(settings, "API_PREFIX", "/api")

    # Auth zorunluysa, chat/memory/admin router'larına dependency olarak uygula
    deps = [Depends(require_api_key)] if require_api_key else []

    app.include_router(chat_router, prefix=api_prefix, tags=["chat"], dependencies=deps)
    if memory_router is not None:
        app.include_router(memory_router, prefix=api_prefix, tags=["memory"], dependencies=deps)
    app.include_router(admin_router, prefix=api_prefix, tags=["admin"], dependencies=deps)

    # Basit kök endpoint
    @app.get("/")
    async def root():
        return {
            "name": getattr(settings, "PROJECT_NAME", "Jetlink Memory Bot"),
            "docs": "/docs",
            "api_prefix": api_prefix,
            "status": "ok",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
