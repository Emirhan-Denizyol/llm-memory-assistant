# app/api/auth.py
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, APIKeyQuery

try:
    from app.core.config import settings  # type: ignore
except Exception:
    class _Fallback:
        API_KEY: Optional[str] = None
    settings = _Fallback()  # type: ignore

# Desteklenen iki alınış yöntemi
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_api_key(
    header_key: Optional[str] = Depends(_api_key_header),
    query_key: Optional[str] = Depends(_api_key_query),
) -> Optional[str]:
    """İstekten API anahtarını (header veya query) alır; yoksa None döner."""
    return header_key or query_key


async def require_api_key(api_key: Optional[str] = Depends(get_api_key)) -> None:
    """
    Router/endpoint dependency:
      - settings.API_KEY yoksa (None/boş), doğrulama devre dışı (açık mod).
      - Varsa, header/query'den gelen anahtar ile birebir eşleşme zorunlu.
    """
    expected = (settings.API_KEY or "").strip() if hasattr(settings, "API_KEY") else ""
    if not expected:
        # Açık mod (geliştirme/yerel ortam): doğrulama devre dışı
        return

    supplied = (api_key or "").strip()
    if not supplied or supplied != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: invalid or missing API key.",
        )
    # Başarılı doğrulama → None döner (FastAPI dependency sözleşmesi)
    return
