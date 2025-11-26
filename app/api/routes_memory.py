# app/api/routes_memory.py
from __future__ import annotations

from typing import List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from app.api.schemas import (
    ChatResponse,
    ListQuery,
    ListResponse,
    MemoryDeleteResponse,
    MemoryItem,
    MemorySearchRequest,
    MemoryWriteRequest,
    Scope,
)

router = APIRouter()

# --- Opsiyonel importlar (servis katmanı boş olsa da router ayağa kalksın) ---
try:
    from app.services import ltm_local_store
except Exception:
    ltm_local_store = None  # type: ignore

try:
    from app.services import ltm_global_store
except Exception:
    ltm_global_store = None  # type: ignore

try:
    from app.services import stm_store
except Exception:
    stm_store = None  # type: ignore


# -----------------------------
# Yardımcılar
# -----------------------------
def _require(cond: bool, msg: str, status_code: int = 400):
    if not cond:
        raise HTTPException(status_code=status_code, detail=msg)


def _paginate(
    items: List[MemoryItem], total: int, page: int, page_size: int
) -> ListResponse[MemoryItem]:
    return ListResponse[MemoryItem](page=page, page_size=page_size, total=total, items=items)


# -----------------------------
# LISTELEME (LOCAL/GLOBAL)
# -----------------------------
@router.get("/memory/local", response_model=ListResponse[MemoryItem])
async def list_local_memories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user_id: str = Query(...),
    session_id: str = Query(...),
    q: Optional[str] = Query(None),
):
    _require(ltm_local_store is not None, "Local LTM servisi yapılandırılmamış.", 501)
    offset = (page - 1) * page_size
    try:
        items, total = ltm_local_store.list(user_id=user_id, session_id=session_id, q=q, offset=offset, limit=page_size)  # type: ignore
    except AttributeError:
        raise HTTPException(500, "ltm_local_store.list(...) fonksiyonu eksik.")
    return _paginate(items, total, page, page_size)


@router.get("/memory/global", response_model=ListResponse[MemoryItem])
async def list_global_memories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user_id: str = Query(...),
    q: Optional[str] = Query(None),
):
    _require(ltm_global_store is not None, "Global LTM servisi yapılandırılmamış.", 501)
    offset = (page - 1) * page_size
    try:
        items, total = ltm_global_store.list(user_id=user_id, q=q, offset=offset, limit=page_size)  # type: ignore
    except AttributeError:
        raise HTTPException(500, "ltm_global_store.list(...) fonksiyonu eksik.")
    return _paginate(items, total, page, page_size)


# -----------------------------
# EKLE / GÜNCELLE (LOCAL/GLOBAL)
# -----------------------------
@router.post("/memory/local", response_model=MemoryItem)
async def add_local_memory(req: MemoryWriteRequest):
    _require(req.scope == Scope.LOCAL, "Bu uç yalnızca scope=local içindir.")
    _require(req.session_id is not None, "Local LTM için session_id zorunludur.")
    _require(ltm_local_store is not None, "Local LTM servisi yapılandırılmamış.", 501)

    try:
        item = ltm_local_store.add(  # type: ignore
            session_id=req.session_id,
            user_id=req.user_id,
            text=req.text,
            meta=req.meta or {},
        )
    except AttributeError:
        raise HTTPException(500, "ltm_local_store.add(...) fonksiyonu eksik.")
    return item


@router.post("/memory/global", response_model=MemoryItem)
async def add_global_memory(req: MemoryWriteRequest):
    _require(req.scope == Scope.GLOBAL, "Bu uç yalnızca scope=global içindir.")
    _require(ltm_global_store is not None, "Global LTM servisi yapılandırılmamış.", 501)

    try:
        item = ltm_global_store.add(  # type: ignore
            user_id=req.user_id,
            text=req.text,
            meta=req.meta or {},
        )
    except AttributeError:
        raise HTTPException(500, "ltm_global_store.add(...) fonksiyonu eksik.")
    return item


# -----------------------------
# SİL (scope + id)
# -----------------------------
@router.delete("/memory/{scope}/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory(scope: Scope, memory_id: int):
    if scope == Scope.LOCAL:
        _require(ltm_local_store is not None, "Local LTM servisi yapılandırılmamış.", 501)
        try:
            deleted = ltm_local_store.delete(memory_id)  # type: ignore
        except AttributeError:
            raise HTTPException(500, "ltm_local_store.delete(...) fonksiyonu eksik.")
    elif scope == Scope.GLOBAL:
        _require(ltm_global_store is not None, "Global LTM servisi yapılandırılmamış.", 501)
        try:
            deleted = ltm_global_store.delete(memory_id)  # type: ignore
        except AttributeError:
            raise HTTPException(500, "ltm_global_store.delete(...) fonksiyonu eksik.")
    else:
        # STM kalıcı değil; tekil id ile silme desteklenmez
        raise HTTPException(400, "STM için tekil silme desteklenmez.")
    return MemoryDeleteResponse(deleted=int(deleted))


# -----------------------------
# ARAMA (embedding veya metin)
# -----------------------------
@router.post("/memory/search", response_model=ListResponse[MemoryItem])
async def search_memory(req: MemorySearchRequest):
    _require(ltm_local_store is not None or ltm_global_store is not None, "LTM servisleri yapılandırılmamış.", 501)

    items: List[MemoryItem] = []
    total = 0

    def _extend(result: Tuple[List[MemoryItem], int]):
        nonlocal items, total
        lst, tot = result
        items.extend(lst)
        total += tot

    if req.scope in (None, Scope.LOCAL):
        _require(req.session_id is not None, "Local arama için session_id zorunludur.")
        if ltm_local_store is not None:
            try:
                _extend(ltm_local_store.search_text(user_id=req.user_id, session_id=req.session_id, q=req.q, topk=req.topk))  # type: ignore
            except AttributeError:
                raise HTTPException(500, "ltm_local_store.search_text(...) fonksiyonu eksik.")

    if req.scope in (None, Scope.GLOBAL):
        if ltm_global_store is not None:
            try:
                _extend(ltm_global_store.search_text(user_id=req.user_id, q=req.q, topk=req.topk))  # type: ignore
            except AttributeError:
                raise HTTPException(500, "ltm_global_store.search_text(...) fonksiyonu eksik.")

    # Basit kırpma (karma listeleme durumunda)
    items = items[: req.topk]
    total = max(total, len(items))
    return _paginate(items, total, page=1, page_size=req.topk)


# -----------------------------
# TEMİZLE (STM / LOCAL / GLOBAL)
# -----------------------------
@router.post("/memory/clear", response_model=MemoryDeleteResponse)
async def clear_memory(
    scope: Scope = Query(..., description="stm | local | global"),
    user_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
):
    if scope == Scope.STM:
        _require(stm_store is not None, "STM store yapılandırılmamış.", 501)
        _require(session_id is not None, "STM temizlemek için session_id gereklidir.")
        try:
            stm_store.clear(session_id)  # type: ignore
            return MemoryDeleteResponse(deleted=1)
        except AttributeError:
            raise HTTPException(500, "stm_store.clear(...) fonksiyonu eksik.")

    elif scope == Scope.LOCAL:
        _require(ltm_local_store is not None, "Local LTM servisi yapılandırılmamış.", 501)
        _require(user_id is not None and session_id is not None, "Local temizlemek için user_id ve session_id gereklidir.")
        try:
            deleted = ltm_local_store.clear(user_id=user_id, session_id=session_id)  # type: ignore
            return MemoryDeleteResponse(deleted=int(deleted))
        except AttributeError:
            raise HTTPException(500, "ltm_local_store.clear(...) fonksiyonu eksik.")

    elif scope == Scope.GLOBAL:
        _require(ltm_global_store is not None, "Global LTM servisi yapılandırılmamış.", 501)
        _require(user_id is not None, "Global temizlemek için user_id gereklidir.")
        try:
            deleted = ltm_global_store.clear(user_id=user_id)  # type: ignore
            return MemoryDeleteResponse(deleted=int(deleted))
        except AttributeError:
            raise HTTPException(500, "ltm_global_store.clear(...) fonksiyonu eksik.")

    else:
        raise HTTPException(400, "Geçersiz scope.")
