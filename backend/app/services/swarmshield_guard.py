"""Wires the existing orchestrator's specialist -> target handoff (the real
tool-execution path, ``TargetClient.send``) through the SwarmShield runtime
security gateway.

This is the ONE integration point: `orchestrator._run_specialist_against_vector`
calls `guard_specialist_send` immediately before it calls `client.send(payload)`.
Every specialist-crafted payload gets:
  - scanned for indirect prompt injection markers
  - checked against the specialist's RBAC policy for the tool/area it targets
  - fed into the stateful circuit breaker (keyed per scan, so a specialist that
    gets stuck generating near-duplicate payloads across mutation generations
    trips the breaker instead of burning the whole attempt budget)

Fails OPEN by default (SWARMSHIELD_FAIL_MODE=open): if the gateway is not
running, the existing scan behaves exactly as it did before this integration
existed -- it just isn't inspected. Set SWARMSHIELD_FAIL_MODE=closed to make
the gateway mandatory.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from swarmshield.exceptions import (
    SwarmShieldCircuitBreakerException,
    SwarmShieldSecurityException,
    SwarmShieldUnavailableError,
)
from swarmshield.sdk import check as swarmshield_check

_FAIL_MODE = os.getenv("SWARMSHIELD_FAIL_MODE", "open")


@dataclass
class GuardVerdict:
    allowed: bool
    blocked: bool = False          # True -> caller should surface this as a 403-style block
    tripped: bool = False          # True -> caller should surface this as a 429-style trip
    reason: str = ""
    violation_type: Optional[str] = None
    risk_score: float = 0.0
    findings: list[dict[str, Any]] | None = None
    retry_after: Optional[int] = None
    degraded: bool = False         # gateway was unreachable and we failed open


async def guard_specialist_send(
    *,
    scan_id: uuid.UUID,
    specialist_key: str,
    payload: str,
    target_tool_or_area: Optional[str],
    generation: int,
) -> GuardVerdict:
    """Runs one specialist payload through the SwarmShield gateway.

    sender = the specialist agent generating the attack payload (its RBAC role
    is its specialist key, e.g. 'tool_abuse_specialist'); receiver = the target
    system under test. conversation_id is pinned to the scan so the circuit
    breaker's repetition/velocity checks apply across the whole scan, and
    hop_count is the specialist's own DNA generation counter (its own
    delegation depth for this vector).
    """
    try:
        verdict = await swarmshield_check(
            message=payload,
            sender_id=specialist_key,
            receiver_id="target-under-test",
            sender_role=specialist_key,
            target_tool=target_tool_or_area or "general",
            conversation_id=f"scan-{scan_id}",
            hop_count=generation,
            provenance=["agent_generated"],
            fail_mode=_FAIL_MODE,
        )
    except SwarmShieldSecurityException as exc:
        return GuardVerdict(
            allowed=False, blocked=True, reason=str(exc), violation_type=exc.violation_type,
            risk_score=exc.risk_score, findings=exc.findings,
        )
    except SwarmShieldCircuitBreakerException as exc:
        return GuardVerdict(
            allowed=False, tripped=True, reason=str(exc), violation_type=exc.violation_type,
            risk_score=exc.risk_score, findings=exc.findings, retry_after=exc.retry_after,
        )
    except SwarmShieldUnavailableError as exc:
        # Only reachable when SWARMSHIELD_FAIL_MODE=closed.
        return GuardVerdict(allowed=False, blocked=True, reason=str(exc), violation_type="gateway_unavailable")

    return GuardVerdict(
        allowed=True,
        reason=verdict.reason,
        risk_score=verdict.risk_score,
        findings=list(verdict.findings),
        degraded=verdict.degraded,
    )
