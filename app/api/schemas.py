# app/api/schemas.py
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, PositiveInt


# -----------------------------
# Ortak Enum/Tanımlar
# -----------------------------
class Scope(str, Enum):
    """Bellek kapsam türleri."""
    STM = "stm"         # kısa süreli, kalıcı değil (listeleme/silme için çoğunlukla UI amaçlı)
    LOCAL = "local"     # oturum (session) özelinde kalıcı bellek
    GLOBAL = "global"   # kullanıcı genelinde kalıcı bellek


# -----------------------------
# Chat (Sohbet) Şemaları
# -----------------------------
class ChatRequest(BaseModel):
    """Sohbet isteği."""
    user_id: str = Field(..., description="Kullanıcı kimliği")
    session_id: str = Field(..., description="Sohbet oturum kimliği")
    message: str = Field(..., min_length=1, description="Kullanıcı mesajı")

    # retrieval/STM parametreleri (isteğe bağlı override)
    topk_local: int = Field(5, ge=0, le=50, description="Local LTM'den getirilecek maksimum kayıt")
    topk_global: int = Field(5, ge=0, le=50, description="Global LTM'den getirilecek maksimum kayıt")
    stm_max_turns: int = Field(8, ge=0, le=50, description="STM içinden eklenecek son konuşma turu sayısı")
    return_sources: bool = Field(True, description="Yanıt ile birlikte kullanılan kaynak/snippet bilgilerini döndür")

    class Config:
        arbitrary_types_allowed = True


class SourceItem(BaseModel):
    """Modelin yanıt üretirken dayandığı kaynak/snippet bilgisi."""
    scope: Scope = Field(..., description="stm/local/global")
    id: Optional[int] = Field(None, description="Kayıt kimliği (STM için None olabilir)")
    session_id: Optional[str] = Field(None, description="Local LTM kaynağı ise ilgili session_id")
    score: Optional[float] = Field(None, ge=0, description="Benzerlik skoru (varsa)")
    snippet: Optional[str] = Field(None, description="Kısa içerik/özet")
    meta: Optional[Dict[str, Any]] = Field(None, description="Kaynak metaverisi (turn_id, created_at vb.)")


class ChatResponse(BaseModel):
    """Sohbet yanıtı."""
    reply: str = Field(..., description="Modelin üretimi")
    used_stm_turns: int = Field(0, ge=0, description="Prompta dahil edilen STM tur sayısı")
    sources: Optional[List[SourceItem]] = Field(None, description="Kullanılan kaynak/snippet listesi")


# -----------------------------
# Bellek (Memory) Şemaları
# -----------------------------
class MemoryItem(BaseModel):
    """Bellekteki tek bir kayıt (Local veya Global)."""
    id: Optional[int] = Field(None, description="Otomatik artan kimlik")
    scope: Scope = Field(..., description="local/global (STM kalıcı değildir)")
    user_id: str = Field(..., description="Kullanıcı kimliği")
    session_id: Optional[str] = Field(None, description="Local bellek için zorunlu; Global için boş")
    text: str = Field(..., min_length=1, description="Saklanan içerik")
    meta: Optional[Dict[str, Any]] = Field(None, description="Serbest biçimli metaveri (kaynak, turn_id vb.)")

    # Embedding metadata (sürümleme/uyumluluk için)
    emb_version: Optional[str] = Field(None, description="Embedding sürümü örn. ge-text-001")
    model: Optional[str] = Field(None, description="Embedding modeli")
    dim: Optional[int] = Field(None, description="Vektör boyutu")

    # Zaman bilgileri (epoch saniye)
    created_at: Optional[int] = Field(None, description="Oluşturulma zamanı")
    updated_at: Optional[int] = Field(None, description="Güncellenme zamanı")


class MemoryWriteRequest(BaseModel):
    """Belleğe yeni kayıt ekleme veya güncelleme talebi."""
    scope: Scope = Field(..., description="local veya global")
    user_id: str = Field(..., description="Kullanıcı kimliği")
    session_id: Optional[str] = Field(None, description="Local için gerekli")
    text: str = Field(..., min_length=1, description="Saklanacak metin")
    meta: Optional[Dict[str, Any]] = Field(None, description="İsteğe bağlı metaveri")


class MemorySearchRequest(BaseModel):
    """Embedding tabanlı veya metin arama talebi."""
    user_id: str = Field(..., description="Kullanıcı kimliği")
    q: str = Field(..., min_length=1, description="Arama ifadesi")
    scope: Optional[Scope] = Field(None, description="Belirtilmezse local+global birlikte aranır")
    session_id: Optional[str] = Field(None, description="Local aramada gerekli olabilir")
    topk: PositiveInt = Field(10, description="Döndürülecek en iyi sonuç sayısı")


class MemoryDeleteResponse(BaseModel):
    deleted: int = Field(..., ge=0, description="Silinen kayıt sayısı")


# -----------------------------
# Listeleme / Sayfalama
# -----------------------------
T = TypeVar("T")


class ListQuery(BaseModel):
    """Listeleme parametreleri."""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=200)
    q: Optional[str] = Field(None, description="Basit metin araması (LIKE)")
    scope: Optional[Scope] = Field(None, description="Filtre: local/global")
    user_id: Optional[str] = Field(None, description="Filtre: kullanıcı")
    session_id: Optional[str] = Field(None, description="Filtre: oturum")


class ListResponse(BaseModel, Generic[T]):
    """Genel amaçlı sayfalı liste yanıtı."""
    page: int
    page_size: int
    total: int
    items: List[T]


# -----------------------------
# Admin / Observability (ops.)
# -----------------------------
class StatsResponse(BaseModel):
    """/stats için basit örnek yanıt yapısı (isteğe bağlı)."""
    uptime_s: float
    requests: int
    avg_latency_ms: float
    retrieval_hits: int
    topk_local: int = 5
    topk_global: int = 5
