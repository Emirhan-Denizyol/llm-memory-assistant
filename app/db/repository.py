# app/db/repository.py
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

# Config fallback
try:
    from app.core.config import settings  # type: ignore
except Exception:
    class _Fallback:
        DB_PATH = os.getenv("DB_PATH", "./data/memory.db")
    settings = _Fallback()  # type: ignore


# -----------------------------------------------------------------------------
# Connection & Pragmas
# -----------------------------------------------------------------------------
def _apply_pragmas(con: sqlite3.Connection) -> None:
    """
    Performans ve tutarlılık için önerilen PRAGMA ayarları.
    """
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA temp_store=MEMORY;")
    cur.execute("PRAGMA mmap_size=134217728;")  # 128MB
    cur.execute("PRAGMA busy_timeout=5000;")    # 5s
    cur.close()


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    RowFactory açık, pragmalar uygulanmış bağlantı döndürür.
    """
    path = db_path or getattr(settings, "DB_PATH", "./data/memory.db")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    _apply_pragmas(con)
    return con


@contextmanager
def get_conn(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    con = connect(db_path)
    try:
        yield con
        con.commit()
    except Exception:
        # Hata durumunda rollback
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        con.close()


# -----------------------------------------------------------------------------
# Schema Management
# -----------------------------------------------------------------------------
def _schema_file(schema_path: Optional[str] = None) -> Path:
    if schema_path:
        return Path(schema_path)
    # Varsayılan: bu dosyanın yanındaki schema.sql
    return Path(__file__).resolve().with_name("schema.sql")


def ensure_schema(path: Optional[str] = None, schema_path: Optional[str] = None) -> None:
    """
    Veritabanı şemasını (app/db/schema.sql) uygular / garanti eder.
    İdempotent olacak şekilde tasarlanmıştır (CREATE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).
    """
    sf = _schema_file(schema_path)
    if not sf.exists():
        raise FileNotFoundError(f"Schema file not found: {sf}")

    sql = sf.read_text(encoding="utf-8")

    with get_conn(path) as con:
        con.executescript(sql)


# -----------------------------------------------------------------------------
# Query Helpers
# -----------------------------------------------------------------------------
def execute(
    sql: str,
    params: Iterable[Any] | None = None,
    *,
    db_path: Optional[str] = None,
) -> int:
    """
    INSERT/UPDATE/DELETE gibi değişiklik yapan işlemler için.
    Dönüş: etkilenen satır sayısı.
    """
    with get_conn(db_path) as con:
        cur = con.cursor()
        cur.execute(sql, tuple(params or []))
        rowcount = cur.rowcount
        cur.close()
        return int(rowcount)


def executescript(
    script: str,
    *,
    db_path: Optional[str] = None,
) -> None:
    """
    Birden fazla SQL komutunu tek seferde çalıştırmak için.
    """
    with get_conn(db_path) as con:
        con.executescript(script)


def fetchone(
    sql: str,
    params: Iterable[Any] | None = None,
    *,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Tek satır döndüren SELECT yardımcı fonksiyonu.
    """
    with get_conn(db_path) as con:
        cur = con.cursor()
        cur.execute(sql, tuple(params or []))
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None


def fetchall(
    sql: str,
    params: Iterable[Any] | None = None,
    *,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Çok satırlı SELECT yardımcı fonksiyonu.
    """
    with get_conn(db_path) as con:
        cur = con.cursor()
        cur.execute(sql, tuple(params or []))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]


# -----------------------------------------------------------------------------
# Convenience: seed helpers (opsiyonel)
# -----------------------------------------------------------------------------
def ensure_user(user_id: str, *, db_path: Optional[str] = None) -> None:
    """
    users tablosunda user_id yoksa ekler.
    """
    with get_conn(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO users(user_id, created_at) VALUES (?, strftime('%s','now'))",
                (user_id,),
            )
        cur.close()


def ensure_session(session_id: str, user_id: str, title: str = "", *, db_path: Optional[str] = None) -> None:
    """
    sessions tablosunda session_id yoksa ekler.
    """
    with get_conn(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO sessions(session_id, user_id, title, created_at) VALUES (?, ?, ?, strftime('%s','now'))",
                (session_id, user_id, title),
            )
        cur.close()
