# app/services/retriever.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.core.config import settings

# --- Config / Constants (güvenli varsayılanlar) -------------------------------
try:
    STM_MAX_TURNS_DEFAULT: int = getattr(settings, "STM_MAX_TURNS_DEFAULT", 8)
    TOPK_LOCAL_DEFAULT: int = getattr(settings, "TOPK_LOCAL_DEFAULT", 8)
    TOPK_GLOBAL_DEFAULT: int = getattr(settings, "TOPK_GLOBAL_DEFAULT", 8)
    RETRIEVAL_BUDGET_TOKENS: int = getattr(
        settings, "RETRIEVAL_BUDGET_TOKENS", 400
    )
    # Varsayılan eşiği yumuşak tuttuk; özellikle Local LTM için kullanıyoruz.
    RETRIEVAL_MIN_SIMILARITY: float = getattr(
        settings, "RETRIEVAL_MIN_SIMILARITY", 0.50
    )
    # Local / Global skor ağırlıkları
    LOCAL_LTM_SCORE_WEIGHT: float = getattr(
        settings, "LOCAL_LTM_SCORE_WEIGHT", 0.90
    )
    GLOBAL_LTM_SCORE_WEIGHT: float = getattr(
        settings, "GLOBAL_LTM_SCORE_WEIGHT", 1.10
    )
except Exception:
    STM_MAX_TURNS_DEFAULT = 8
    TOPK_LOCAL_DEFAULT = 8
    TOPK_GLOBAL_DEFAULT = 8
    RETRIEVAL_BUDGET_TOKENS = 400
    RETRIEVAL_MIN_SIMILARITY = 0.50
    LOCAL_LTM_SCORE_WEIGHT = 0.90
    GLOBAL_LTM_SCORE_WEIGHT = 1.10

# --- Opsiyonel servis importları ---------------------------------------------
try:
    from app.services import stm_store
except Exception:
    stm_store = None  # type: ignore

try:
    from app.services import ltm_local_store, ltm_global_store
except Exception:
    ltm_local_store = None  # type: ignore
    ltm_global_store = None  # type: ignore

try:
    from app.services import summarizer
except Exception:
    summarizer = None  # type: ignore

# Reranker opsiyonel
try:
    from app.services.reranker import mmr_rerank  # type: ignore
except Exception:
    mmr_rerank = None  # type: ignore


# --------------------------- Yardımcılar --------------------------------------
def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _load_prompt_file(filename: str) -> str:
    base = Path(__file__).resolve().parent.parent / "prompts"
    return _read_text_file(base / filename)


def _fmt_turn(role: str, text: str) -> str:
    return f"{role.upper()}: {text.strip()}"


def _dedupe_by_text(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for it in items:
        txt = (it.get("snippet") or it.get("text") or "").strip()
        key = txt.lower()
        if key and key not in seen:
            out.append(it)
            seen.add(key)
    return out


def _truncate(items: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    return items[:k] if k and k > 0 else items


def _mk_source(
    scope: str,
    *,
    id=None,
    session_id=None,
    score=None,
    snippet=None,
    meta=None,
) -> Dict[str, Any]:
    return {
        "scope": scope,
        "id": id,
        "session_id": session_id,
        "score": score,
        "snippet": snippet,
        "meta": meta or {},
    }


def _filter_by_similarity(
    items: List[Dict[str, Any]],
    min_sim: float,
) -> List[Dict[str, Any]]:
    """
    meta.similarity < min_sim olan kayıtları filtreler.
    similarity yoksa (eski kayıt vs.) güvenli tarafta kalmak için bırakıyoruz.
    """
    if not items:
        return items
    if min_sim <= 0:
        # Eşik 0 veya altı ise filtreleme yapma
        return items

    filtered: List[Dict[str, Any]] = []
    for it in items:
        meta = it.get("meta")
        sim = None
        if isinstance(meta, dict):
            sim = meta.get("similarity")
        # similarity yoksa güvenli tarafta kal (filtreleme)
        if sim is None or sim >= min_sim:
            filtered.append(it)
    return filtered


# --------------------------- Ana Giriş Noktası --------------------------------
def retrieve_context(
    user_id: str,
    session_id: str,
    query_text: str,
    topk_local: int = TOPK_LOCAL_DEFAULT,
    topk_global: int = TOPK_GLOBAL_DEFAULT,
    stm_max_turns: int = STM_MAX_TURNS_DEFAULT,
) -> Dict[str, Any]:
    """
    Kullanıcının sorgusu için STM + Local LTM + Global LTM'den bağlam derler,
    prompt metnini üretir, kaynakları (sources) ve kullanılan STM tur sayısını döndürür.

    Tasarım:
    - STM         : Sadece bu session içindeki son turlar.
    - Local LTM   : Bu session'a ait kalıcı kayıtlar (session_id filtreli).
    - Global LTM  : Kullanıcı genelinde önemli kayıtlar (user_id bazlı, tüm session'lar).
    """

    # 1) STM (son N tur)
    stm_turns: List[Dict[str, Any]] = []
    if stm_store is not None and hasattr(stm_store, "get_context"):
        try:
            stm_turns = stm_store.get_context(  # type: ignore
                session_id, max_turns=stm_max_turns
            )
        except Exception:
            stm_turns = []
    used_stm_turns = len(stm_turns or [])

    # 2) Local LTM arama (session bazlı)
    local_hits: List[Dict[str, Any]] = []
    if ltm_local_store is not None:
        try:
            if hasattr(ltm_local_store, "search_embed"):
                local_hits, _ = ltm_local_store.search_embed(  # type: ignore
                    user_id=user_id,
                    session_id=session_id,
                    query_text=query_text,
                    topk=topk_local,
                )
            else:
                local_hits, _ = ltm_local_store.search_text(  # type: ignore
                    user_id=user_id,
                    session_id=session_id,
                    q=query_text,
                    topk=topk_local,
                )
        except Exception:
            local_hits = []

    # Local LTM için similarity filtresi uyguluyoruz
    if local_hits:
        local_hits = _filter_by_similarity(local_hits, RETRIEVAL_MIN_SIMILARITY)

    local_sources = [
        _mk_source(
            "local",
            id=hit.get("id"),
            session_id=hit.get("session_id"),
            score=(hit.get("meta") or {}).get("similarity"),
            snippet=hit.get("text"),
            meta=hit.get("meta"),
        )
        for hit in local_hits or []
    ]

    # 3) Global LTM arama (user profili / oturumdan bağımsız)
    global_hits: List[Dict[str, Any]] = []
    if ltm_global_store is not None:
        try:
            if hasattr(ltm_global_store, "search_embed"):
                global_hits, _ = ltm_global_store.search_embed(  # type: ignore
                    user_id=user_id,
                    query_text=query_text,
                    topk=topk_global,
                )
            else:
                global_hits, _ = ltm_global_store.search_text(  # type: ignore
                    user_id=user_id,
                    q=query_text,
                    topk=topk_global,
                )
        except Exception:
            global_hits = []

    # Global LTM tarafında similarity filtresini uygulamıyoruz.
    global_sources = [
        _mk_source(
            "global",
            id=hit.get("id"),
            session_id=None,
            score=(hit.get("meta") or {}).get("similarity"),
            snippet=hit.get("text"),
            meta=hit.get("meta"),
        )
        for hit in global_hits or []
    ]

    # 4) Skor ağırlıklandırma (Local vs Global)
    for src in local_sources:
        score = src.get("score")
        if isinstance(score, (int, float)):
            weighted = float(score) * LOCAL_LTM_SCORE_WEIGHT
            src["score"] = weighted
            # meta içine de istersen iz bırak
            meta = src.get("meta") or {}
            meta.setdefault("raw_similarity", score)
            meta["weighted_score"] = weighted
            meta["score_weight"] = LOCAL_LTM_SCORE_WEIGHT
            src["meta"] = meta

    for src in global_sources:
        score = src.get("score")
        if isinstance(score, (int, float)):
            weighted = float(score) * GLOBAL_LTM_SCORE_WEIGHT
            src["score"] = weighted
            meta = src.get("meta") or {}
            meta.setdefault("raw_similarity", score)
            meta["weighted_score"] = weighted
            meta["score_weight"] = GLOBAL_LTM_SCORE_WEIGHT
            src["meta"] = meta

    # 5) Rerank + dedupe
    combined = local_sources + global_sources
    combined = _dedupe_by_text(combined)

    if mmr_rerank is not None and combined:
        try:
            combined = mmr_rerank(  # type: ignore
                combined, query=query_text, topk=len(combined)
            )
        except Exception:
            pass

    # 6) Distillation (özet)
    distilled_sections: List[str] = []
    if summarizer is not None and combined:
        try:
            distilled = summarizer.distill(  # type: ignore
                combined,
                budget_tokens=RETRIEVAL_BUDGET_TOKENS,
            )
            if isinstance(distilled, str):
                distilled_sections = [distilled]
            elif isinstance(distilled, list):
                distilled_sections = [str(x) for x in distilled]
        except Exception:
            distilled_sections = []

    # summarizer yoksa / hata varsa: en iyi snippet’leri doğrudan kullan
    if not distilled_sections:
        distilled_sections = [
            f"- {src.get('snippet')}"
            for src in _truncate(combined, topk_local + topk_global)
        ]

    # 7) Prompt derleme
    system_prompt = (
        _load_prompt_file("system.txt")
        or "You are a helpful assistant with multi-layer memory."
    )
    retrieval_instructions = _load_prompt_file("retrieval_instructions.txt") or (
        "Use STM (session), Local LTM (user's past interactions) and Global LTM "
        "(user profile and long-term facts) wisely. "
        "Prefer STM > Local > Global when conflicts arise; choose the most recent facts."
    )

    stm_text = "\n".join(
        _fmt_turn(t.get("role", "user"), t.get("text", ""))
        for t in (stm_turns or [])
    )
    local_text = "\n".join(f"- {h.get('text')}" for h in (local_hits or []))
    global_text = "\n".join(f"- {h.get('text')}" for h in (global_hits or []))
    distilled_text = "\n".join(distilled_sections)

    prompt = f"""[SYSTEM]
{system_prompt}

[INSTRUCTIONS]
{retrieval_instructions}

[CONTEXT: STM (last {used_stm_turns} turns)]
{stm_text if stm_text else "(empty)"}

[CONTEXT: Local LTM]
{local_text if local_text else "(empty)"}

[CONTEXT: Global LTM]
{global_text if global_text else "(empty)"}

[CONTEXT: Distilled Memory]
{distilled_text if distilled_text else "(empty)"}

[USER MESSAGE]
{query_text}
"""

    return {
        "prompt": prompt,
        "used_stm_turns": used_stm_turns,
        "sources": combined,
    }
