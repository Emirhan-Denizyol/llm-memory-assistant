# app/services/summarizer.py
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from app.services.similarity import normalize_text

# Opsiyonel LLM kullanımı (varsa daha derli toplu özet alınır)
try:
    from app.services.llm_client import generate as llm_generate  # type: ignore
except Exception:
    llm_generate = None  # type: ignore


def _estimate_tokens(text: str) -> int:
    """
    Yaklaşık token tahmini: kelime sayısı * 1.3
    (Model/Tokenizer bağımsız kaba tahmin.)
    """
    if not text:
        return 0
    return int(max(1, len(text.split())) * 1.3)


def _sent_split(text: str) -> List[str]:
    # Basit cümle bölücü (nokta/soru/ünlem)
    parts = re.split(r"(?<=[\.\!\?])\s+", text.strip())
    return [p for p in parts if p]


def _dedupe(snippets: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for s in snippets:
        key = normalize_text(s)
        if key and key not in seen:
            seen.add(key)
            out.append(s.strip())
    return out


def _rank_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Kaynakları basit skorla sırala: similarity(meta) → uzunluk cezası hafif uygulansın.
    """
    ranked = []
    for src in sources:
        txt = (src.get("snippet") or src.get("text") or "").strip()
        if not txt:
            continue
        sim = float((src.get("meta") or {}).get("similarity") or 0.0)
        length_penalty = 1.0 - min(0.4, max(0.0, len(txt) / 2000.0))  # çok uzunlara küçük penalti
        score = sim * 0.8 + length_penalty * 0.2
        ranked.append({"text": txt, "score": score})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


def distill(
    sources: List[Dict[str, Any]],
    *,
    budget_tokens: int = 400,
    prefer_llm: bool = True,
) -> str:
    """
    RAG bağlamını token bütçesine indirger.
    - Kaynakları skorlayıp benzersizleştirir.
    - LLM varsa sıkı bir "bullet summary" üretir, yoksa kural tabanlı özet yapar.
    Dönüş: tek bir metin (prompt’a yapıştırılacak).
    """
    if not sources:
        return ""

    ranked = _rank_sources(sources)
    snippets = _dedupe([r["text"] for r in ranked])

    # Kural tabanlı kısa madde işaretleri
    bullets: List[str] = []
    for s in snippets:
        sents = _sent_split(s)
        head = sents[0] if sents else s
        head = re.sub(r"\s+", " ", head).strip()
        if not head:
            continue
        bullets.append(f"- {head}")

    # Token bütçesine sığdır
    packed: List[str] = []
    total = 0
    for b in bullets:
        t = _estimate_tokens(b)
        if total + t > budget_tokens:
            break
        packed.append(b)
        total += t

    if not packed:
        return ""

    draft = "\n".join(packed)

    # LLM varsa kompakt özet iste
    if prefer_llm and llm_generate is not None:
        prompt = (
            "Aşağıdaki maddeleri 5-8 kısa madde halinde çok özlü bir özet haline getir. "
            "İsim/tercih/gerçekleri koru, tekrarları kaldır, max 400 token sınırına uy.\n\n"
            f"{draft}"
        )
        try:
            out = llm_generate(prompt).get("text", "").strip()  # type: ignore
            if out:
                return out
        except Exception:
            pass

    # Fallback: taslak halini döndür
    return draft
