"""Lazy local embeddings with a deterministic no-download fallback."""
from __future__ import annotations

import hashlib
import math
import re
import threading

from app.core.config import settings

_embedding_model = None
_model_lock = threading.Lock()


def _fallback_embedding(text: str, dimension: int = 128) -> list[float]:
    # Hashing-vector representation keeps local RAG useful without pulling a
    # model at startup (or in constrained test/offline environments).
    values = [0.0] * dimension
    for token in re.findall(r"[a-z0-9_+-]{2,}", text.lower()):
        index = int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % dimension
        values[index] += 1.0
    magnitude = math.sqrt(sum(v * v for v in values))
    return [v / magnitude for v in values] if magnitude else values


def _get_model():
    global _embedding_model
    if _embedding_model is None:
        with _model_lock:
            if _embedding_model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    # local_files_only prevents an implicit multi-hundred-MB
                    # download. Operators obtain the configured model first.
                    _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL, local_files_only=True)
                except Exception:
                    _embedding_model = False
    return _embedding_model


def embed(text: str) -> list[float]:
    model = _get_model()
    if model is False:
        return _fallback_embedding(text)
    return [float(x) for x in model.encode(text, normalize_embeddings=True).tolist()]


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    denominator = math.sqrt(sum(x*x for x in left)) * math.sqrt(sum(y*y for y in right))
    return sum(x*y for x, y in zip(left, right)) / denominator if denominator else 0.0
