"""Thin, self-contained client for the real SwarmShield gateway.

This is intentionally the same shape as ``controlled_target/shield_hook.py``: demo_target
does not reimplement any security logic (no injection scoring, no RBAC table, no loop
detection). Every decision below comes from a live ``POST /a2a/transfer`` call to the
gateway container (``swarmshield/gateway.py``). This file only turns that HTTP response
into a small Python object the FastAPI app can render as JSON.

Configured via env vars (same names used elsewhere in the repo):
    SWARMSHIELD_GATEWAY_URL   e.g. http://swarmshield-gateway:8100
    SWARMSHIELD_API_KEY       optional
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx


@dataclass
class Decision:
    action: str  # allow | flag | block | trip | unavailable
    http_status: int
    reason: str = ""
    risk_score: float = 0.0
    violation_type: Optional[str] = None
    rules: list[str] = field(default_factory=list)
    quarantined_agents: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def blocks(self) -> bool:
        return self.action in {"block", "trip", "unavailable"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "http_status": self.http_status,
            "reason": self.reason,
            "risk_score": self.risk_score,
            "violation_type": self.violation_type,
            "rules": self.rules,
            "quarantined_agents": self.quarantined_agents,
            "evidence": self.evidence,
        }


class GatewayClient:
    def __init__(self) -> None:
        self.url = (os.environ.get("SWARMSHIELD_GATEWAY_URL") or "").rstrip("/")
        self.api_key = os.environ.get("SWARMSHIELD_API_KEY") or ""
        self.timeout = float(os.environ.get("GATEWAY_TIMEOUT", "3.0"))
        self._http = httpx.Client(timeout=self.timeout)

    @property
    def configured(self) -> bool:
        return bool(self.url)

    def health(self) -> Optional[dict[str, Any]]:
        if not self.configured:
            return None
        try:
            r = self._http.get(f"{self.url}/health")
            return r.json() if r.status_code == 200 else None
        except httpx.HTTPError:
            return None

    def transfer(
        self,
        *,
        message: str,
        sender_id: str,
        sender_role: str,
        receiver_id: str,
        receiver_role: str,
        provenance: Optional[list[str]] = None,
        conversation_id: Optional[str] = None,
        target_tool: Optional[str] = None,
        tool_args: Optional[dict[str, Any]] = None,
        hop_count: int = 0,
    ) -> Decision:
        """Calls the real gateway's ``POST /a2a/transfer``. Never scores anything locally."""
        if not self.configured:
            return Decision("unavailable", 503, "SWARMSHIELD_GATEWAY_URL is not set")

        body: dict[str, Any] = {
            "message": message,
            "sender_id": sender_id,
            "sender_role": sender_role,
            "receiver_id": receiver_id,
            "receiver_role": receiver_role,
            "provenance": provenance or [],
            "hop_count": hop_count,
            "tool_args": tool_args or {},
        }
        if conversation_id:
            body["conversation_id"] = conversation_id
        if target_tool:
            body["target_tool"] = target_tool

        headers = {"X-SwarmShield-Key": self.api_key} if self.api_key else {}
        try:
            resp = self._http.post(f"{self.url}/a2a/transfer", json=body, headers=headers)
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            return Decision("unavailable", 503, f"gateway unreachable: {type(exc).__name__}")

        if resp.status_code == 200:
            action = "flag" if data.get("verdict") == "flag" else "allow"
        elif resp.status_code == 403:
            action = "block"
        elif resp.status_code == 429:
            action = "trip"
        else:
            action = "unavailable"

        return Decision(
            action=action,
            http_status=resp.status_code,
            reason=str(data.get("reason", "")),
            risk_score=float(data.get("risk_score", 0.0)),
            violation_type=data.get("violation_type"),
            rules=[f.get("rule", "") for f in data.get("findings", [])],
            quarantined_agents=list(data.get("quarantined_agents", [])),
            evidence=dict(data.get("evidence") or {}),
            raw=data,
        )

    def release(self, agent_id: str) -> None:
        """Best-effort: clears a quarantine set earlier in this same gateway (existing admin route)."""
        if not self.configured:
            return
        headers = {"X-SwarmShield-Key": self.api_key} if self.api_key else {}
        try:
            self._http.post(f"{self.url}/v1/agents/{agent_id}/release", headers=headers)
        except httpx.HTTPError:
            pass


GATEWAY = GatewayClient()
