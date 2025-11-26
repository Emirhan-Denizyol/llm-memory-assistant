# app/services/ltm_global_store.py
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import builtins  # yerleşik list() fonksiyonuna erişmek için

# Config
try:
    from app.core.config import settings  # type: ignore
except Exception:

    class _Fallback:
        DB_PATH = os.getenv("DB_PATH", "./data/memory.db")
        EMB_VERSION = "text-embedding-004"
        EMB_MODEL = "text-embedding-004"
        EMB_DIM = 768

    settings = _Fallback()  # type: ignore


# Embedding client (opsiyonel import)
try:
    from app.services.embed_client import (  # type: ignore
        encode as embed_encode,
        EMB_VERSION,
        EMB_MODEL,
        EMB_DIM,
    )
except Exception:
    EMB_VERSION = getattr(settings, "EMB_VERSION", "text-embedding-004")
    EMB_MODEL = getattr(settings, "EMB_MODEL", "text-embedding-004")
    EMB_DIM = int(getattr(settings, "EMB_DIM", 768))

    def embed_encode(texts: Iterable[str]) -> List[List[float]]:  # type: ignore
        """Fallback embedding."""
        if isinstance(texts, str):
            texts = [texts]
        out: List[List[float]] = []
        for t in texts:
            h = float(abs(hash(t)) % 997) / 997.0
            v = np.zeros(EMB_DIM, dtype=np.float32)
            v[0] = h
            out.append(v.tolist())
        return out


# ---------------------------
# Helpers
# ---------------------------
def _conn() -> sqlite3.Connection:
    Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(settings.DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _now() -> int:
    return int(time.time())


def _to_blob(vec: Iterable[float]) -> bytes:
    arr = np.asarray(builtins.list(vec), dtype=np.float32)
    return arr.tobytes()


def _from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def _norm_text(s: str) -> str:
    return " ".join(s.strip().split())


def _cosine(a: np.ndarray, b: np.ndarray, eps: float = 1e-12) -> float:
    na = np.linalg.norm(a) + eps
    nb = np.linalg.norm(b) + eps
    return float(np.dot(a, b) / (na * nb))


def _row_to_item(row: sqlite3.Row) -> Dict[str, Any]:
    meta = json.loads(row["meta"]) if row["meta"] else {}

    return {
        "id": row["id"],
        "scope": "global",
        "user_id": row["user_id"],
        "session_id": None,  # Global LTM session bazlı değildir
        "text": row["text"],
        "meta": meta,
        "emb_version": row["emb_version"],
        "model": row["model"],
        "dim": row["dim"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ---------------------------
# CRUD
# ---------------------------
def add(
    user_id: str,
    text: str,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    text = _norm_text(text)
    meta = meta or {}
    emb = embed_encode([text])[0]
    ts = _now()

    with _conn() as con:
        cur = con.cursor()
        try:
            # Yeni kayıt ekle
            cur.execute(
                """
                INSERT INTO global_memories (
                    user_id, text, embedding, meta,
                    emb_version, model, dim, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    text,
                    _to_blob(emb),
                    json.dumps(meta, ensure_ascii=False),
                    EMB_VERSION,
                    EMB_MODEL,
                    EMB_DIM,
                    ts,
                    None,
                ),
            )
            mem_id = cur.lastrowid
            con.commit()

            cur.execute("SELECT * FROM global_memories WHERE id = ?", (mem_id,))
            return _row_to_item(cur.fetchone())

        except sqlite3.IntegrityError:
            # 🔥 Duplicate durumunda artık 500 atmayacak
            # Aynı user_id + text varsa → Mevcut kaydı sessizce döndür
            cur.execute(
                """
                SELECT id, user_id, text, meta,
                       emb_version, model, dim, created_at, updated_at
                FROM global_memories
                WHERE user_id = ? AND text = ?
                """,
                (user_id, text),
            )
            row = cur.fetchone()
            if row:
                return _row_to_item(row)

            # Çok istisnai durum (olmamalı) → hatayı yeniden fırlat
            raise

# ---------------------------
# LIST
# ---------------------------
def list(
    user_id: str,
    q: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[Dict[str, Any]], int]:

    params = [user_id]
    where = "WHERE user_id = ?"
    if q:
        where += " AND text LIKE ?"
        params.append(f"%{q}%")

    with _conn() as con:
        cur = con.cursor()
        cur.execute(f"SELECT COUNT(1) AS c FROM global_memories {where}", params)
        total = int(cur.fetchone()["c"])

        cur.execute(
            f"""
            SELECT id, user_id, text, meta,
                   emb_version, model, dim, created_at, updated_at
            FROM global_memories
            {where}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        rows = cur.fetchall()
        items = [_row_to_item(r) for r in rows]
        return items, total


def delete(memory_id: int) -> int:
    with _conn() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM global_memories WHERE id = ?", (memory_id,))
        con.commit()
        return cur.rowcount


def clear(user_id: str) -> int:
    with _conn() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM global_memories WHERE user_id = ?", (user_id,))
        con.commit()
        return cur.rowcount


# ---------------------------
# SEARCH
# ---------------------------
def search_text(
    user_id: str,
    q: str,
    topk: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:

    q = _norm_text(q)

    with _conn() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, user_id, text, meta,
                   emb_version, model, dim, created_at, updated_at
            FROM global_memories
            WHERE user_id = ? AND text LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, f"%{q}%", topk),
        )
        rows = cur.fetchall()
        items = [_row_to_item(r) for r in rows]
        return items, len(items)


def search_embed(
    user_id: str,
    query_text: str,
    topk: int = 10,
    candidate_limit: int = 500,
) -> Tuple[List[Dict[str, Any]], int]:

    query_text = _norm_text(query_text)
    q_emb = np.asarray(embed_encode([query_text])[0], dtype=np.float32)

    with _conn() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, user_id, text, meta, embedding,
                   emb_version, model, dim, created_at, updated_at
            FROM global_memories
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, candidate_limit),
        )
        rows = cur.fetchall()

    scored: List[Tuple[float, sqlite3.Row]] = []
    for r in rows:
        emb = _from_blob(r["embedding"])
        score = _cosine(q_emb, emb)
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)

    top = scored[:topk]
    items = [_row_to_item(r) for (s, r) in top]

    # skorları meta içine yaz
    for i, (s, _) in enumerate(top):
        items[i]["meta"]["similarity"] = float(s)

    return items, len(items)
