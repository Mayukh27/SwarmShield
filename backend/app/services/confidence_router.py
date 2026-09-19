from __future__ import annotations
from typing import Any
from app.core.config import settings


def score(result: Any, *, retrieval_similarity: float = 0.0, evidence_strength: float = 0.5,
          historical_success: float = 0.5, output_validation: float = 1.0) -> float:
    model_confidence = result.get("confidence", 0.5) if isinstance(result, dict) else 0.5
    try: model_confidence = float(model_confidence)
    except (TypeError, ValueError): model_confidence = 0.5
    value = (.30 * max(0, min(1, model_confidence)) + .25 * max(0, min(1, retrieval_similarity))
             + .20 * max(0, min(1, evidence_strength)) + .15 * max(0, min(1, historical_success))
             + .10 * max(0, min(1, output_validation)))
    return round(value, 4)


def decision(confidence: float) -> str:
    if confidence >= settings.LLM_CONFIDENCE_THRESHOLD: return "accept"
    if confidence >= settings.LLM_MEDIUM_CONFIDENCE_THRESHOLD: return "retry_local"
    return "cloud"
