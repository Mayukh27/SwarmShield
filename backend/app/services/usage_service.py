"""
LLM token-usage bookkeeping: record one provider call, aggregate per scan.

Honesty rules (Phase 1):
  * Only real provider-reported counters are stored. Nothing is estimated
    from characters/words. A counter the provider did not report stays NULL.
  * If a call reported NO usable counter at all, no row is written (there is
    nothing real to record).
  * Recording is best-effort: a bookkeeping failure must never break a scan.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.llm_usage import LLMUsageRecord
from app.models.scan import ScanRun

logger = logging.getLogger(__name__)


def _clean_counter(value: Any) -> int | None:
    """Return ``value`` as a non-negative int, or None if the provider did not
    report a usable number. 0 is a legitimate reported value and is kept."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def record_llm_call(
    db: Session,
    scan_id: uuid.UUID | str,
    *,
    provider: str,
    model: str,
    input_tokens: Any,
    output_tokens: Any,
    agent_type: str | None = None,
) -> LLMUsageRecord | None:
    """Persist one real LLM call. Returns the row, or None when nothing was
    recorded (no usable counters, or a swallowed DB failure).

    ``total_tokens`` is the sum of the counters that WERE reported, so with
    both counters present it is exactly input + output.
    """
    inp = _clean_counter(input_tokens)
    out = _clean_counter(output_tokens)
    if inp is None and out is None:
        return None  # provider reported nothing -> record nothing, invent nothing

    row = LLMUsageRecord(
        scan_id=scan_id,
        agent_type=agent_type,
        provider=provider,
        model=model,
        input_tokens=inp,
        output_tokens=out,
        total_tokens=(inp or 0) + (out or 0),
    )
    try:
        # SAVEPOINT: if only this insert fails (e.g. the scan row vanished),
        # the caller's pending work in the shared scan session is untouched.
        with db.begin_nested():
            db.add(row)
    except Exception:
        logger.warning("Could not record LLM usage for scan %s", scan_id, exc_info=True)
        return None
    try:
        db.commit()  # same pattern as the LLM cache: make the row visible to /usage right away
    except Exception:
        logger.warning("Could not commit LLM usage for scan %s", scan_id, exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return None
    return row


def get_scan_usage(db: Session, scan_id: uuid.UUID | str) -> dict[str, Any]:
    """Aggregate all recorded usage for a scan.

    Returns SUMs of the stored counters and the number of recorded calls.
    A scan with nothing recorded yields zeros, ``llm_calls == 0`` and
    ``provider``/``model`` of None -- i.e. "no recorded usage".
    """
    totals = (
        db.query(
            func.coalesce(func.sum(LLMUsageRecord.input_tokens), 0),
            func.coalesce(func.sum(LLMUsageRecord.output_tokens), 0),
            func.coalesce(func.sum(LLMUsageRecord.total_tokens), 0),
            func.count(LLMUsageRecord.id),
        )
        .filter(LLMUsageRecord.scan_id == scan_id)
        .one()
    )
    input_tokens, output_tokens, total_tokens, llm_calls = (int(x) for x in totals)

    by_model_rows = (
        db.query(
            LLMUsageRecord.provider,
            LLMUsageRecord.model,
            func.coalesce(func.sum(LLMUsageRecord.input_tokens), 0),
            func.coalesce(func.sum(LLMUsageRecord.output_tokens), 0),
            func.coalesce(func.sum(LLMUsageRecord.total_tokens), 0),
            func.count(LLMUsageRecord.id),
        )
        .filter(LLMUsageRecord.scan_id == scan_id)
        .group_by(LLMUsageRecord.provider, LLMUsageRecord.model)
        .all()
    )
    by_model = sorted(
        (
            {
                "provider": p, "model": m,
                "input_tokens": int(i), "output_tokens": int(o),
                "total_tokens": int(t), "llm_calls": int(c),
            }
            for p, m, i, o, t, c in by_model_rows
        ),
        key=lambda r: (-r["llm_calls"], r["provider"], r["model"]),
    )

    by_agent_rows = (
        db.query(
            LLMUsageRecord.agent_type,
            func.coalesce(func.sum(LLMUsageRecord.input_tokens), 0),
            func.coalesce(func.sum(LLMUsageRecord.output_tokens), 0),
            func.coalesce(func.sum(LLMUsageRecord.total_tokens), 0),
            func.count(LLMUsageRecord.id),
        )
        .filter(LLMUsageRecord.scan_id == scan_id)
        .group_by(LLMUsageRecord.agent_type)
        .all()
    )
    by_agent = sorted(
        (
            {
                "agent_type": a or "unattributed",
                "input_tokens": int(i), "output_tokens": int(o),
                "total_tokens": int(t), "llm_calls": int(c),
            }
            for a, i, o, t, c in by_agent_rows
        ),
        key=lambda r: (-r["total_tokens"], r["agent_type"]),
    )

    # Calls where the provider reported only one of the two counters: the
    # total is then a lower bound. Surfaced so the UI never overstates.
    partial_calls = (
        db.query(func.count(LLMUsageRecord.id))
        .filter(
            LLMUsageRecord.scan_id == scan_id,
            (LLMUsageRecord.input_tokens.is_(None)) | (LLMUsageRecord.output_tokens.is_(None)),
        )
        .scalar()
    ) or 0

    top = by_model[0] if by_model else None
    return {
        "scan_id": str(scan_id),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "llm_calls": llm_calls,
        "partial_calls": int(partial_calls),
        "provider": top["provider"] if top else None,
        "model": top["model"] if top else None,
        "by_model": by_model,
        "by_agent": by_agent,
    }


def scan_exists(db: Session, scan_id: uuid.UUID | str) -> bool:
    return db.query(ScanRun.id).filter(ScanRun.id == scan_id).first() is not None
