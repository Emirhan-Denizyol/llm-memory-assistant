# app/scripts/init_db.py
from __future__ import annotations

import argparse
import sys
from typing import Optional

try:
    from app.db.repository import ensure_schema, ensure_user, ensure_session  # type: ignore
except Exception as e:
    print(f"[init_db] Import error: {e}", file=sys.stderr)
    raise

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize SQLite schema and seed basic records.")
    parser.add_argument("--db", dest="db_path", default=None, help="Path to SQLite DB (default from settings.DB_PATH)")
    parser.add_argument("--user", dest="user_id", default=None, help="Seed a user_id into 'users' table")
    parser.add_argument("--session", dest="session_id", default=None, help="Seed a session_id into 'sessions' table (requires --user)")
    parser.add_argument("--title", dest="title", default="", help="Optional session title")
    args = parser.parse_args(argv)

    # Şemayı uygula
    ensure_schema(path=args.db_path)

    # Opsiyonel seed
    if args.user_id:
        ensure_user(args.user_id, db_path=args.db_path)
    if args.session_id and args.user_id:
        ensure_session(args.session_id, args.user_id, title=args.title, db_path=args.db_path)

    print("[init_db] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
