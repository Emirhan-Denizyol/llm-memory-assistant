# app/services/stm_store.py
from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional


class _STMStore:
    """
    Process içi (in-memory) kısa süreli bellek.
    - Her session_id için sıralı "turn" listesi tutar.
    - Uygulama yeniden başlatılınca sıfırlanır (kalıcı değildir).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._by_session: Dict[str, List[dict]] = {}

    def append_turn(self, session_id: str, role: str, text: str) -> None:
        """STM'e bir konuşma turu ekle (role: user/assistant/system)."""
        if not session_id or not text:
            return
        item = {
            "role": str(role or "user"),
            "text": str(text).strip(),
            "ts": int(time.time()),
        }
        with self._lock:
            self._by_session.setdefault(session_id, []).append(item)

    def get_context(self, session_id: str, max_turns: int = 8) -> List[dict]:
        """STM içinden son N turu döndür (kopya)."""
        if not session_id:
            return []
        with self._lock:
            turns = self._by_session.get(session_id, [])
            if max_turns and max_turns > 0:
                turns = turns[-max_turns:]
            # kopya döndür ki dışarıda mutasyona uğramasın
            return [dict(t) for t in turns]

    def clear(self, session_id: str) -> None:
        """Belirli bir oturumun STM'ini temizle."""
        if not session_id:
            return
        with self._lock:
            self._by_session.pop(session_id, None)

    def clear_all(self) -> None:
        """Tüm STM içeriklerini temizle (uygulama içi reset)."""
        with self._lock:
            self._by_session.clear()


# Tekil (singleton) örnek
_store = _STMStore()

# Modül düzeyi kısayollar
append_turn = _store.append_turn
get_context = _store.get_context
clear = _store.clear
clear_all = _store.clear_all
