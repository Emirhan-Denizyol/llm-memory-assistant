# app/api/routes_chat.py
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException

from app.api.schemas import ChatRequest, ChatResponse, Scope, SourceItem
from app.core.config import settings  # Backend defaultları için

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Servis importları: doğrudan modül bazlı, hata loglu ----------------------
try:
    import app.services.retriever as retriever  # type: ignore
except Exception as e:
    logger.exception("Retriever modülü yüklenemedi: %s", e)
    retriever = None  # type: ignore

try:
    import app.services.llm_client as llm_client  # type: ignore
except Exception as e:
    logger.exception("LLM client modülü yüklenemedi: %s", e)
    llm_client = None  # type: ignore

try:
    import app.services.stm_store as stm_store  # type: ignore
except Exception as e:
    logger.exception("STM store modülü yüklenemedi: %s", e)
    stm_store = None  # type: ignore

try:
    import app.services.ltm_local_store as ltm_local_store  # type: ignore
    import app.services.ltm_global_store as ltm_global_store  # type: ignore
except Exception as e:
    logger.exception("LTM store modülleri yüklenemedi: %s", e)
    ltm_local_store = None  # type: ignore
    ltm_global_store = None  # type: ignore

try:
    import app.services.memory_policy as memory_policy  # type: ignore
except Exception as e:
    logger.exception("Memory policy modülü yüklenemedi: %s", e)
    memory_policy = None  # type: ignore


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Ana sohbet endpoint'i.
    - STM + Local LTM + Global LTM'den bağlam toplar (retriever)
    - LLM'den yanıt alır (llm_client)
    - Gerekirse hafızaya write-back yapar (memory_policy + ltm_*_store)
    """
    # Ön-kontroller
    if retriever is None or llm_client is None:
        raise HTTPException(501, detail="Retriever veya LLM istemcisi yapılandırılmamış.")

    # --- topk / stm_defaults backend tarafında yönetilsin ---------------------
    try:
        default_topk_local = getattr(settings, "TOPK_LOCAL_DEFAULT", 8)
        default_topk_global = getattr(settings, "TOPK_GLOBAL_DEFAULT", 8)
        default_stm_max_turns = getattr(settings, "STM_MAX_TURNS_DEFAULT", 8)
    except Exception:
        default_topk_local = 8
        default_topk_global = 8
        default_stm_max_turns = 8

    resolved_topk_local = (
        req.topk_local if req.topk_local is not None else default_topk_local
    )
    resolved_topk_global = (
        req.topk_global if req.topk_global is not None else default_topk_global
    )
    resolved_stm_max_turns = (
        req.stm_max_turns if req.stm_max_turns is not None else default_stm_max_turns
    )
    # --------------------------------------------------------------------------

    # 0) Kullanıcı turunu STM'e yaz (aynı session içinde hafıza oluşsun)
    if stm_store is not None and hasattr(stm_store, "append_turn"):
        try:
            stm_store.append_turn(  # type: ignore
                req.session_id,
                role="user",
                text=req.message,
            )
        except Exception:
            logger.exception("STM user turn eklenemedi")

    # 1) Bağlamı derle (STM + Local LTM + Global LTM)
    try:
        ctx = retriever.retrieve_context(  # type: ignore
            user_id=req.user_id,
            session_id=req.session_id,
            query_text=req.message,
            topk_local=resolved_topk_local,
            topk_global=resolved_topk_global,
            stm_max_turns=resolved_stm_max_turns,
        )
    except Exception as e:
        # Gerçek hatayı logla ve tek bir genel hata mesajı dön
        logger.exception("Retriever çağrısı sırasında hata: %s", e)
        raise HTTPException(500, "Bağlam derlenirken iç hata oluştu.")

    # ctx beklenen alanlar: prompt, used_stm_turns, sources(list[SourceItem benzeri])
    prompt = ctx.get("prompt", None)
    used_stm_turns = int(ctx.get("used_stm_turns", 0))
    raw_sources = ctx.get("sources", []) or []

    if not prompt:
        raise HTTPException(500, "Retriever geçerli bir prompt üretemedi.")

    # 2) LLM’den yanıt al
    try:
        llm_out = llm_client.generate(prompt=prompt)  # type: ignore
    except AttributeError:
        raise HTTPException(500, "llm_client.generate(...) fonksiyonu eksik.")
    except Exception as e:
        logger.exception("LLM çağrısı sırasında hata: %s", e)
        raise HTTPException(500, "LLM yanıt üretirken hata oluştu.")

    reply: str = (
        llm_out.get("text") if isinstance(llm_out, dict) else str(llm_out)
    )

    # 2.5) Asistan turunu STM'e yaz (cevap da hafızaya girsin)
    if stm_store is not None and hasattr(stm_store, "append_turn"):
        try:
            stm_store.append_turn(  # type: ignore
                req.session_id,
                role="assistant",
                text=reply,
            )
        except Exception:
            logger.exception("STM assistant turn eklenemedi")

    # 3) Write-back (potansiyel uzun süreli hafıza yazımı)
    sources: List[SourceItem] = []
    for s in raw_sources:
        # dict -> SourceItem dönüştür (güçlü tip)
        try:
            sources.append(SourceItem(**s) if isinstance(s, dict) else s)
        except Exception:
            # toleranslı davran: minimum alanlarla doldur
            sources.append(
                SourceItem(
                    scope=Scope.LOCAL,
                    id=None,
                    score=None,
                    snippet=str(s),
                )
            )

    if memory_policy is not None:
        try:
            actions = memory_policy.extract_writebacks(  # type: ignore
                user_id=req.user_id,
                session_id=req.session_id,
                user_message=req.message,
                assistant_reply=reply,
                sources=[s.dict() for s in sources],
            )
        except AttributeError:
            actions = []
        except Exception as e:
            logger.exception("Memory policy extract_writebacks sırasında hata: %s", e)
            actions = []
    else:
        actions = []

    # 4) Aksiyonları uygula (Local / Global)
    for act in actions or []:
        scope = act.get("scope")
        text = act.get("text")
        meta = act.get("meta") or {}
        if not text or scope not in ("local", "global"):
            continue

        if scope == "local" and ltm_local_store is not None:
            try:
                ltm_local_store.add(  # type: ignore
                    session_id=req.session_id,
                    user_id=req.user_id,
                    text=text,
                    meta=meta,
                )
            except Exception as e:
                logger.exception("Local LTM write-back hatası: %s", e)
        elif scope == "global" and ltm_global_store is not None:
            try:
                ltm_global_store.add(  # type: ignore
                    user_id=req.user_id,
                    text=text,
                    meta=meta,
                )
            except Exception as e:
                logger.exception("Global LTM write-back hatası: %s", e)

    # 5) Yanıt modeli
    return ChatResponse(
        reply=reply,
        used_stm_turns=used_stm_turns,
        sources=sources if req.return_sources else None,
    )
