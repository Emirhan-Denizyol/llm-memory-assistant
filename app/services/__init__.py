# app/services/__init__.py
from __future__ import annotations

"""
Service paketinin işaret dosyası.

Bilerek çok sade bırakıldı. Alt modüller (llm_client, retriever, stm_store, vb.)
doğrudan `from app.services import retriever` şeklinde import edildiğinde
Python otomatik olarak ilgili alt modülü yükleyecektir.

Burada ağır import veya yan etki yok → import hataları engellenir.
"""
