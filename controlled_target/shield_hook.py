"""Optional SwarmShield gateway hook for the controlled target.

Self-contained on purpose (only ``httpx``): the target container does not need the
``swarmshield`` package. Everything is OFF unless ``SWARMSHIELD_GATEWAY_URL`` is set AND the
shield is switched on (``SHIELD_ENABLED_AT_START=true`` or ``POST /admin/enable_shield``), so
existing behaviour and tests are unchanged by default.

The target calls ``SHIELD.inspect`` at three choke points:
    1. the user's message                    (direct prompt injection)
    2. every retrieved RAG document          (indirect prompt injection)
    3. every tool call, before it executes   (RBAC, taint, restricted arguments)

Gateway unreachable -> ``SHIELD_FAIL_MODE`` decides: ``closed`` (default) blocks, ``open`` allows.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

log = logging.getLogger("swarmshield.controlled_target.shield")

BLOCK_MESSAGE = "[blocked by SwarmShield]"


@dataclass
class ShieldDecision:
    action: str  # allow | flag | block | trip | unavailable
    reason: str = ""
    risk_score: float = 0.0
    violation_type: Optional[str] = None
    rules: list[str] = field(default_factory=list)

    @property
    def blocks(self) -> bool:
        return self.action in {"block", "trip", "unavailable"}

    @property
    def suspicious(self) -> bool:
        return self.action in {"flag", "block", "trip", "unavailable"}


class ShieldClient:
    def __init__(self) -> None:
        self.url = (os.environ.get("SWARMSHIELD_GATEWAY_URL") or "").rstrip("/")
        self.api_key = os.environ.get("SWARMSHIELD_API_KEY") or ""
        self.timeout = float(os.environ.get("SHIELD_TIMEOUT", "3.0"))
        self.fail_mode = os.environ.get("SHIELD_FAIL_MODE", "closed").lower()
        self.enabled = os.environ.get("SHIELD_ENABLED_AT_START", "false").lower() in {"1", "true", "yes"}
        self._http = httpx.Client(timeout=self.timeout)

    @property
    def configured(self) -> bool:
        return bool(self.url)

    @property
    def active(self) -> bool:
        return self.configured and self.enabled

    def reachable(self) -> bool:
        if not self.configured:
            return False
        try:
            return self._http.get(f"{self.url}/health").status_code == 200
        except httpx.HTTPError:
            return False

    def inspect(
        self,
        *,
        message: str,
        sender_id: str,
        sender_role: str,
        receiver_id: str,
        receiver_role: str,
        provenance: list[str],
        conversation_id: str,
        target_tool: Optional[str] = None,
        tool_args: Optional[dict[str, Any]] = None,
    ) -> ShieldDecision:
        body: dict[str, Any] = {
            "message": message,
            "sender_id": sender_id,
            "sender_role": sender_role,
            "receiver_id": receiver_id,
            "receiver_role": receiver_role,
            "provenance": provenance,
            "conversation_id": conversation_id,
            "tool_args": tool_args or {},
        }
        if target_tool:
            body["target_tool"] = target_tool
        headers = {"X-SwarmShield-Key": self.api_key} if self.api_key else {}
        try:
            resp = self._http.post(f"{self.url}/a2a/transfer", json=body, headers=headers)
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("SwarmShield gateway unavailable (%s); fail_mode=%s", type(exc).__name__, self.fail_mode)
            if self.fail_mode == "open":
                return ShieldDecision("allow", "gateway unavailable (fail-open)")
            return ShieldDecision("unavailable", "gateway unavailable (fail-closed)")

        if resp.status_code in (401, 403, 429) or resp.status_code >= 500:
            action = "trip" if resp.status_code == 429 else "block"
            if resp.status_code >= 500 or resp.status_code == 401:
                action = "unavailable" if self.fail_mode != "open" else "allow"
            return ShieldDecision(
                action,
                str(data.get("reason") or f"HTTP {resp.status_code}"),
                float(data.get("risk_score", 0.0)),
                data.get("violation_type"),
                [f.get("rule", "") for f in data.get("findings", [])],
            )
        return ShieldDecision(
            str(data.get("verdict", "allow")),
            str(data.get("reason", "")),
            float(data.get("risk_score", 0.0)),
            data.get("violation_type"),
            [f.get("rule", "") for f in data.get("findings", [])],
        )


SHIELD = ShieldClient()
