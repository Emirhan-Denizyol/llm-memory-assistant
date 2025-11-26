# app/services/pii_guard.py
from __future__ import annotations

import re
from typing import Callable

# Basit PII maskeleme kuralları.
# İleri seviye (NLP tabanlı) PII tespiti istenirse bu modül genişletilir.

# E-posta
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.UNICODE)
# Telefon (uluslararası gevşek desen, 7+ rakam)
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}\s?)?(?:\(?\d{2,4}\)?\s?)?[\d\s\-]{7,})")
# T.C. Kimlik / ulusal ID benzeri (11 rakam), çok gevşek tutuyoruz – gerçek doğrulama yapılmıyor
NATIONAL_ID_RE = re.compile(r"\b\d{11}\b")
# IBAN (TR/GENEL gevşek)
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b", re.IGNORECASE)
# Kredi kartı (13–19 rakam, boşluk/çizgi ayırıcılarla)
CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

MASK_EMAIL = lambda m: f"{m.group(1)[:2]}***@{m.group(2)}"
MASK_GENERIC = lambda s: "***"

def _mask_email(text: str) -> str:
    return EMAIL_RE.sub(MASK_EMAIL, text)

def _mask_phone(text: str) -> str:
    # Sadece rakam yoğun dizileri masker; tarihi/ID’leri yanlış pozitiflememek için uzunluk eşiği var.
    return PHONE_RE.sub(lambda m: "***" if len(re.sub(r"\D", "", m.group(0))) >= 7 else m.group(0), text)

def _mask_national_id(text: str) -> str:
    return NATIONAL_ID_RE.sub(MASK_GENERIC, text)

def _mask_iban(text: str) -> str:
    return IBAN_RE.sub(lambda m: f"{m.group(0)[:6]}***{m.group(0)[-4:]}", text)

def _mask_credit_card(text: str) -> str:
    return CREDIT_CARD_RE.sub(lambda m: f"{m.group(0)[:4]} **** **** {m.group(0)[-4:]}", text)

def scrub_text(text: str) -> str:
    """
    Metindeki temel PII ögelerini maskeleyip döndürür.
    Sıra önemlidir: önce e-posta, ardından daha geniş desenler.
    """
    if not text:
        return text
    out = str(text)
    out = _mask_email(out)
    out = _mask_phone(out)
    out = _mask_national_id(out)
    out = _mask_iban(out)
    out = _mask_credit_card(out)
    return out
