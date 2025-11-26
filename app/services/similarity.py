# app/services/similarity.py
from __future__ import annotations

import math
import unicodedata
from typing import Iterable, List, Sequence, Tuple

import numpy as np


# ---------------------------
# Metin normalizasyonu
# ---------------------------
def normalize_text(s: str) -> str:
    """
    Temel metin normalizasyonu: NFKC, trim, çoklu boşluk sıkıştırma, lower.
    (PII/anonimleştirme ayrı bir katmanda yapılmalıdır.)
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = " ".join(s.strip().split())
    return s.lower()


# ---------------------------
# Vektör işlemleri
# ---------------------------
def l2_normalize(x: np.ndarray, axis: int = -1, eps: float = 1e-12) -> np.ndarray:
    n = np.linalg.norm(x, axis=axis, keepdims=True)
    return x / (n + eps)


def cosine(a: np.ndarray, b: np.ndarray, eps: float = 1e-12) -> float:
    """
    Tekil vektörler için kosinüs benzerliği.
    """
    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    na = np.linalg.norm(a) + eps
    nb = np.linalg.norm(b) + eps
    return float(np.dot(a, b) / (na * nb))


def cosine_matrix(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """
    query: (D,) veya (Q,D)
    matrix: (N,D)
    dönüş: (N,) veya (Q,N) kosinüs skorları
    """
    q = np.asarray(query, dtype=np.float32)
    M = np.asarray(matrix, dtype=np.float32)

    if q.ndim == 1:
        q = q[None, :]
    qn = l2_normalize(q, axis=1)
    Mn = l2_normalize(M, axis=1)
    return qn @ Mn.T  # (Q,N)


# ---------------------------
# Top-K yardımcıları
# ---------------------------
def topk_indices(scores: Sequence[float], k: int) -> List[int]:
    """
    Küçük/orta N için basit top-K. Büyük N’de numpy.argpartition daha hızlıdır.
    """
    if k <= 0:
        return []
    k = min(k, len(scores))
    return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]


def topk_pairs(scores: Sequence[float], k: int) -> List[Tuple[int, float]]:
    idxs = topk_indices(scores, k)
    return [(i, float(scores[i])) for i in idxs]


def knn(query_vec: np.ndarray, matrix: np.ndarray, k: int) -> List[Tuple[int, float]]:
    """
    Embedding matrisinde kosinüs KNN.
    """
    sims = cosine_matrix(query_vec, matrix).ravel().tolist()
    return topk_pairs(sims, k)


# ---------------------------
# Çeşitlilik için basit MMR
# ---------------------------
def mmr(
    candidates: List[str],
    query: str,
    emb_fn,
    topk: int,
    lambda_: float = 0.5,
) -> List[int]:
    """
    Minimal MMR (Maximal Marginal Relevance) seçici.
    - candidates: metin listesi
    - emb_fn: metinleri vektöre çeviren fonksiyon (batch desteklemeli)
    Dönüş: seçilen indeksler.
    """
    if not candidates:
        return []
    topk = max(1, min(topk, len(candidates)))

    vecs = np.asarray(emb_fn(candidates), dtype=np.float32)  # (N,D)
    qvec = np.asarray(emb_fn([query])[0], dtype=np.float32)  # (D,)

    sims_to_q = cosine_matrix(qvec, vecs).ravel()  # (N,)
    selected: List[int] = []
    remaining = set(range(len(candidates)))

    while len(selected) < topk and remaining:
        if not selected:
            # ilk: sorguya en benzer
            i = int(np.argmax(sims_to_q[list(remaining)]))
            choice = list(remaining)[i]
        else:
            # her aday için: lambda*sim(q, i) - (1-lambda)*max_j sim(i, j)
            sel_vecs = vecs[selected]  # (S,D)
            # (1,N_remaining) - (S,N_remaining) -> broadcasting ile çeşitlilik
            div_terms = cosine_matrix(sel_vecs, vecs[list(remaining)])  # (S,R)
            max_div = np.max(div_terms, axis=0) if div_terms.size else np.zeros(len(remaining))
            cand_indices = list(remaining)
            mmr_scores = lambda_ * sims_to_q[cand_indices] - (1 - lambda_) * max_div
            choice = cand_indices[int(np.argmax(mmr_scores))]

        selected.append(choice)
        remaining.remove(choice)

    return selected
