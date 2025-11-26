# app/core/errors.py
from __future__ import annotations

from typing import Any, Dict, Optional


class ApplicationError(Exception):
    """
    Uygulama içinde kontrollü olarak fırlatılacak temel hata tipi.

    main.py içinde bu hata tipi 400 (Bad Request) olarak JSONResponse'a
    map ediliyor.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "application_error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            data["details"] = self.details
        return data


class NotFoundError(ApplicationError):
    def __init__(self, message: str = "Kaynak bulunamadı", **kwargs: Any) -> None:
        super().__init__(message, code="not_found", **kwargs)


class AuthError(ApplicationError):
    def __init__(self, message: str = "Yetkilendirme hatası", **kwargs: Any) -> None:
        super().__init__(message, code="auth_error", **kwargs)


class ValidationAppError(ApplicationError):
    def __init__(self, message: str = "İş kuralı doğrulama hatası", **kwargs: Any) -> None:
        super().__init__(message, code="business_validation_error", **kwargs)
