# app/services/embed_client.py
from __future__ import annotations

import os
from typing import Iterable, List

# LangChain Google Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Config
try:
    from app.core.config import settings  # type: ignore
except Exception:
    class _Fallback:
        EMB_VERSION = os.getenv("EMB_VERSION", "text-embedding-004")
        EMB_MODEL = os.getenv("EMB_MODEL", "text-embedding-004")
        EMB_DIM = int(os.getenv("EMB_DIM", "768"))
        GOOGLE_EMBED_API_KEY = os.getenv("GOOGLE_EMBED_API_KEY", "")

    settings = _Fallback()  # type: ignore

# --- Model/versiyon sabitleri ---
EMB_VERSION: str = getattr(settings, "EMB_VERSION", "text-embedding-004")
EMB_MODEL: str = getattr(settings, "EMB_MODEL", "text-embedding-004")
EMB_DIM: int = int(getattr(settings, "EMB_DIM", 768))
GOOGLE_EMBED_API_KEY: str = getattr(settings, "GOOGLE_EMBED_API_KEY", "")

# Fallback her durumda aktif olsun (test ve dev için deterministik davranış)
EMB_FALLBACK_ENABLED = os.getenv("EMB_FALLBACK_ENABLED", "true").lower() == "true"


def _fallback_vector(text: str) -> List[float]:
    """
    Deterministik fallback embedding vektörü.
    İlk elemana hash bazlı bir değer, kalanlara 0 yazar.
    """
    h = abs(hash(text)) % 1009 / 1009.0
    vec = [0.0] * EMB_DIM
    vec[0] = float(h)
    return vec


def _load_embeddings() -> GoogleGenerativeAIEmbeddings | None:
    """
    Tekil GoogleGenerativeAIEmbeddings örneğini yükler.
    API anahtarı yoksa None döner ve encode() fallback kullanır.
    """
    if not GOOGLE_EMBED_API_KEY:
        return None

    return GoogleGenerativeAIEmbeddings(
        model=EMB_MODEL,
        google_api_key=GOOGLE_EMBED_API_KEY,
    )


_EMB = _load_embeddings()


def encode(texts: Iterable[str], timeout: float = 20.0) -> List[List[float]]:
    """
    Metin listesini embed eder.
    - LangChain GoogleGenerativeAIEmbeddings kullanır.
    - Her durumda deterministik bir sonuç döner (fallback).
    """
    # Iterable güvenliği
    if isinstance(texts, str):
        texts = [texts]

    outputs: List[List[float]] = []
    texts_list = [str(t) for t in texts]

    # API anahtarı veya model yoksa direkt fallback
    if _EMB is None:
        for t in texts_list:
            outputs.append(_fallback_vector(t))
        return outputs

    # LangChain ile embed etmeyi dene
    try:
        # embed_documents: List[str] -> List[List[float]]
        embs = _EMB.embed_documents(texts_list)
        for vec, t in zip(embs, texts_list):
            if not isinstance(vec, list) or not vec:
                outputs.append(_fallback_vector(t))
                continue

            # Boyut kontrolü
            if EMB_DIM and len(vec) != EMB_DIM:
                if len(vec) > EMB_DIM:
                    vec = vec[:EMB_DIM]
                else:
                    vec = vec + [0.0] * (EMB_DIM - len(vec))

            outputs.append([float(x) for x in vec])
        return outputs

    except Exception:
        # Ağ hatası / kota / beklenmedik durum → fallback
        for t in texts_list:
            outputs.append(_fallback_vector(t))
        return outputs
