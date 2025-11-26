# app/services/memory_policy.py
from __future__ import annotations

import json
import time
from typing import Any, Dict, List

# Opsiyonel PII filtresi
try:
    from app.services.pii_guard import scrub_text  # type: ignore
except Exception:
    def scrub_text(x: str) -> str:  # fallback
        return x

# LLM client (Gemini / benzetimi) – opsiyonel import
try:
    from app.services import llm_client  # type: ignore
except Exception:
    llm_client = None  # type: ignore


def _clean(s: str) -> str:
    """Basit whitespace temizliği + opsiyonel PII maskesi."""
    s = (s or "").strip()
    return scrub_text(" ".join(s.split()))


def _build_prompt(user_message: str, assistant_reply: str) -> str:
    """
    LLM'den gelecekte hatırlamaya değer memory kayıtları isteyen sistem prompt'u.
    """
    return f"""
You are a memory extraction module for an AI assistant.

Your job:
- Look at the latest user message and assistant reply.
- Decide what is worth remembering for the FUTURE.
- Extract 0 to 5 short memory items.
- Each item MUST have:
  - "scope": "global" or "local"
    * "global": user profile, preferences, long-term facts (name, job, hobbies, projects…)
    * "local": this conversation's decisions, tasks, constraints, plans
  - "text": short and self-contained, in Turkish
  - "reason": why it is useful to remember

Rules:
- If nothing important, return: []
- DO NOT invent facts.
- Max text length: 200 chars
- Output ONLY VALID JSON LIST.

[USER_MESSAGE]
{user_message}

[ASSISTANT_REPLY]
{assistant_reply}
""".strip()


def _llm_propose_memories(
    user_message: str,
    assistant_reply: str,
) -> List[Dict[str, Any]]:
    """LLM’den memory önerileri alır (JSON list)."""
    if llm_client is None:
        return []

    prompt = _build_prompt(user_message, assistant_reply)

    try:
        llm_out = llm_client.generate(prompt=prompt)  # type: ignore
    except Exception:
        return []

    raw_text = (
        llm_out.get("text")
        if isinstance(llm_out, dict)
        else str(llm_out)
    )

    if not raw_text:
        return []

    # JSON bekleniyor
    try:
        data = json.loads(raw_text)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    candidates: List[Dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        scope = str(item.get("scope", "")).lower().strip()
        text = _clean(str(item.get("text", "")))
        reason = _clean(str(item.get("reason", "")))

        if scope not in ("local", "global"):
            continue
        if not text:
            continue

        candidates.append({
            "scope": scope,
            "text": text,
            "reason": reason or None,
        })

    return candidates


def extract_writebacks(
    *,
    user_id: str,
    session_id: str,
    user_message: str,
    assistant_reply: str,
    sources: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Kullanıcı mesajı + asistan yanıtından Local/Global memory çıkarımı.
    """
    results: List[Dict[str, Any]] = []

    # 1) LLM adayları
    candidates = _llm_propose_memories(
        user_message=user_message,
        assistant_reply=assistant_reply,
    )

    if not candidates:
        return results

    # 2) Dedup + meta ekle
    seen = set()
    now_ts = int(time.time())

    for c in candidates:
        scope = c.get("scope")
        txt = _clean(c.get("text", ""))

        if not txt or scope not in ("local", "global"):
            continue

        key = f"{scope}:{txt.lower()}"
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "scope": scope,
            "text": txt,
            "meta": {
                "reason": c.get("reason"),
                "ts": now_ts,
            },
        })

    return results
