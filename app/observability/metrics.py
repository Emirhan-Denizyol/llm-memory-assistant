# app/observability/metrics.py
from __future__ import annotations

import threading
import time
from contextlib import contextmanager


class _Metrics:
    """
    Çok basit metrik toplayıcı.
    - istek sayısı
    - ortalama gecikme (ms)
    - retrieval hit sayısı
    - topk varsayılanları (gözlem amaçlı)
    """
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.start_ts = time.time()
        self.requests = 0
        self.total_latency_ms = 0.0
        self.avg_latency_ms = 0.0
        self.retrieval_hits = 0
        self.topk_local = 5
        self.topk_global = 5

    def record_request(self, latency_ms: float | None = None) -> None:
        with self._lock:
            self.requests += 1
            if latency_ms is not None:
                self.total_latency_ms += float(latency_ms)
                self.avg_latency_ms = self.total_latency_ms / max(1, self.requests)

    def record_retrieval_hit(self, n: int = 1) -> None:
        with self._lock:
            self.retrieval_hits += int(max(0, n))

    def set_topk(self, local: int, global_: int) -> None:
        with self._lock:
            self.topk_local = int(local)
            self.topk_global = int(global_)


@contextmanager
def measure_request():
    """
    with measure_request(): blok sonunda METRICS.record_request(latency_ms) çağrılır.
    """
    t0 = time.time()
    try:
        yield
    finally:
        dt_ms = (time.time() - t0) * 1000.0
        METRICS.record_request(dt_ms)


# Tekil metrik nesnesi
METRICS = _Metrics()
