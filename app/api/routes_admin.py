# app/api/routes_admin.py
from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter
from starlette.responses import JSONResponse

# Opsiyonel metrik modülü
try:
    from app.observability.metrics import METRICS  # type: ignore
except Exception:
    class _DummyMetrics:
        start_ts = time.time()
        requests = 0
        avg_latency_ms = 0.0
        retrieval_hits = 0
        topk_local = 5
        topk_global = 5
    METRICS = _DummyMetrics()  # type: ignore

router = APIRouter()
_STARTED_AT = time.time()


@router.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "uptime_s": round(time.time() - _STARTED_AT, 3)}


@router.get("/stats")
async def stats() -> JSONResponse:
    data = {
        "uptime_s": round(time.time() - getattr(METRICS, "start_ts", _STARTED_AT), 3),
        "requests": int(getattr(METRICS, "requests", 0)),
        "avg_latency_ms": float(getattr(METRICS, "avg_latency_ms", 0.0)),
        "retrieval_hits": int(getattr(METRICS, "retrieval_hits", 0)),
        "topk_local": int(getattr(METRICS, "topk_local", 5)),
        "topk_global": int(getattr(METRICS, "topk_global", 5)),
    }
    return JSONResponse(data)
