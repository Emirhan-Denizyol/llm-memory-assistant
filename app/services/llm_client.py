# app/services/llm_client.py
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from app.core.config import settings

# LangChain & Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# -------------------------
# Fallback kontrolü
# -------------------------
LLM_FALLBACK_ENABLED = os.getenv("LLM_FALLBACK_ENABLED", "true").lower() == "true"


# -------------------------
# Model başlangıcı
# -------------------------
def _load_model() -> ChatGoogleGenerativeAI:
    """
    Tekil LangChain ChatGoogleGenerativeAI örneğini yükler.
    Eğer API anahtarı yoksa fallback'e düşer.
    """
    api_key = settings.GEMINI_API_KEY
    model_name = settings.GEMINI_MODEL

    if not api_key:
        # Fallback: API anahtarı yok → fonksiyon generate(...) içinde eko üretir.
        return None  # type: ignore

    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.4,
        max_output_tokens=512,
        google_api_key=api_key,
    )


_MODEL = _load_model()


# -------------------------
# Yardımcı
# -------------------------
def _fallback_response(prompt: str) -> str:
    """
    API anahtarı yoksa veya model yüklenemezse fallback yanıt üretir.
    """
    if not prompt:
        return "(fallback) Boş prompt alındı."
    return f"(fallback) {prompt[:400]}"


# -------------------------
# Ana API
# -------------------------
def generate(
    prompt: str,
    *,
    system: Optional[str] = None,
    temperature: float = 0.4,
    max_output_tokens: int = 512,
) -> Dict[str, Any]:
    """
    routes_chat.py tarafından kullanılan ana giriş noktası.
    Dönüş biçimi: {"text": "..."}  (zorunlu)
    """
    # Fallback gerekli mi?
    if _MODEL is None:
        if LLM_FALLBACK_ENABLED:
            return {"text": _fallback_response(prompt)}
        else:
            return {"text": ""}

    # Model mesajlarını hazırla
    msgs = []
    if system:
        msgs.append(SystemMessage(content=system))
    msgs.append(HumanMessage(content=prompt))

    try:
        response = _MODEL.invoke(msgs)
        text = response.content or ""
    except Exception:
        if LLM_FALLBACK_ENABLED:
            text = _fallback_response(prompt)
        else:
            text = ""

    return {"text": text}
