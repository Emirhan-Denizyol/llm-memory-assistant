# app/services/ltm_local_store.py
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import builtins  # <-- yerleşik list()'e erişmek için

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

# Embedding istemcisi (opsiyonel import; yoksa naive fallback)
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
        """
        Basit/naive fallback: sabit boyutlu (EMB_DIM) çok küçük değerler.
        Gerçek embed_client hazır olduğunda bu kısım override edilir.
        """
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
# Yardımcılar
# ---------------------------
def _conn() -> sqlite3.Connection:
    Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(settings.DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _now() -> int:
    return int(time.time())


def _to_blob(vec: Iterable[float]) -> bytes:
    # Burada özellikle yerleşik list() fonksiyonunu kullanıyoruz,
    # modül içindeki list(...) fonksiyonunu değil.
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
    return {
        "id": row["id"],
        "scope": "local",
        "user_id": row["user_id"],
        "session_id": row["session_id"],
        "text": row["text"],
        "meta": json.loads(row["meta"]) if row["meta"] else None,
        "emb_version": row["emb_version"] if "emb_version" in row.keys() else None,
        "model": row["model"] if "model" in row.keys() else None,
        "dim": row["dim"] if "dim" in row.keys() else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ---------------------------
# CRUD
# ---------------------------
def add(
    session_id: str,
    user_id: str,
    text: str,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    text = _norm_text(text)
    emb = embed_encode([text])[0]
    ts = _now()

    with _conn() as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO local_memories (
                session_id, user_id, text, embedding, meta,
                emb_version, model, dim, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id,
                text,
                _to_blob(emb),
                json.dumps(meta or {}, ensure_ascii=False),
                EMB_VERSION,
                EMB_MODEL,
                EMB_DIM,
                ts,
                None,
            ),
        )
        mem_id = cur.lastrowid
        con.commit()

        cur.execute("SELECT * FROM local_memories WHERE id = ?", (mem_id,))
        row = cur.fetchone()
        return _row_to_item(row)


def list(
    user_id: str,
    session_id: str,
    q: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[Dict[str, Any]], int]:
    params: List[Any] = [user_id, session_id]
    where = "WHERE user_id = ? AND session_id = ?"
    if q:
        where += " AND text LIKE ?"
        params.append(f"%{q}%")

    with _conn() as con:
        cur = con.cursor()
        cur.execute(f"SELECT COUNT(1) AS c FROM local_memories {where}", params)
        total = int(cur.fetchone()["c"])

        cur.execute(
            f"""
            SELECT id, session_id, user_id, text, meta,
                   emb_version, model, dim, created_at, updated_at
            FROM local_memories
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
        cur.execute("DELETE FROM local_memories WHERE id = ?", (memory_id,))
        con.commit()
        return cur.rowcount


def clear(user_id: str, session_id: str) -> int:
    with _conn() as con:
        cur = con.cursor()
        cur.execute(
            "DELETE FROM local_memories WHERE user_id = ? AND session_id = ?",
            (user_id, session_id),
        )
        con.commit()
        return cur.rowcount


# ---------------------------
# ARAMA
# ---------------------------
def search_text(
    user_id: str,
    session_id: str,
    q: str,
    topk: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Basit LIKE tabanlı arama (embed istemcisi gerekmez).
    """
    q = _norm_text(q)
    with _conn() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, session_id, user_id, text, meta,
                   emb_version, model, dim, created_at, updated_at
            FROM local_memories
            WHERE user_id = ? AND session_id = ? AND text LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, session_id, f"%{q}%", topk),
        )
        rows = cur.fetchall()
        items = [_row_to_item(r) for r in rows]
        return items, len(items)


def search_embed(
    user_id: str,
    session_id: str,
    query_text: str,
    topk: int = 10,
    candidate_limit: int = 500,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Embedding tabanlı benzerlik araması (cosine).
    """
    query_text = _norm_text(query_text)
    q_emb = np.asarray(embed_encode([query_text])[0], dtype=np.float32)

    with _conn() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, session_id, user_id, text, meta, embedding,
                   emb_version, model, dim, created_at, updated_at
            FROM local_memories
            WHERE user_id = ? AND session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, session_id, candidate_limit),
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
        if items[i]["meta"] is None:
            items[i]["meta"] = {}
        items[i]["meta"]["similarity"] = float(s)

    return items, len(items)
