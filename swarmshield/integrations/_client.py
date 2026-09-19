"""Minimal gateway client shared by the LangChain and LangGraph integrations.

Maps gateway HTTP semantics to Python:
    200 -> ``GatewayVerdict`` (may have ``requires_human_review=True``)
    403 -> ``SwarmShieldSecurityException``
    429 -> ``SwarmShieldCircuitBreakerException``
    unreachable / 5xx -> ``SwarmShieldUnavailableError`` (fail closed) or a degraded
                         "allow" verdict (fail open), depending on ``fail_mode``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Optional, Sequence

import httpx

from swarmshield.exceptions import (
    SwarmShieldCircuitBreakerException,
    SwarmShieldError,
    SwarmShieldSecurityException,
    SwarmShieldUnavailableError,
)

logger = logging.getLogger("swarmshield.client")

FailMode = Literal["closed", "open"]


@dataclass(frozen=True)
class GatewayVerdict:
    """Successful (HTTP 200) gateway answer."""

    verdict: str
    risk_score: float
    reason: str = ""
    findings: tuple[dict[str, Any], ...] = ()
    requires_human_review: bool = False
    message_id: str = ""
    degraded: bool = False  # True when the gateway was offline and we failed open
    raw: Mapping[str, Any] = field(default_factory=dict)


def build_payload(
    *,
    message: str,
    sender_id: str,
    receiver_id: str,
    sender_role: str,
    receiver_role: Optional[str] = None,
    target_tool: Optional[str] = None,
    tool_args: Optional[Mapping[str, Any]] = None,
    conversation_id: Optional[str] = None,
    hop_count: int = 0,
    provenance: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    """Build the JSON body for ``POST /a2a/transfer`` (omits unset optional fields)."""
    payload: dict[str, Any] = {
        "message": message,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "target_tool": target_tool,
        "tool_args": dict(tool_args or {}),
        "hop_count": hop_count,
        "provenance": list(provenance or []),
    }
    if conversation_id:
        payload["conversation_id"] = conversation_id
    return {k: v for k, v in payload.items() if v is not None}


class GatewayClient:
    """Sync + async client for the SwarmShield gateway."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        timeout: float = 5.0,
        fail_mode: FailMode = "closed",
    ) -> None:
        self.base_url = (base_url or os.getenv("SWARMSHIELD_URL", "http://localhost:8000")).rstrip("/")
        self._api_key = api_key or os.getenv("SWARMSHIELD_API_KEY")
        self._timeout = timeout
        self.fail_mode: FailMode = fail_mode

    # ---- internals -------------------------------------------------------------------

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-SwarmShield-Key": self._api_key} if self._api_key else {}

    def _unavailable(self, cause: str) -> GatewayVerdict:
        if self.fail_mode == "open":
            logger.warning("SwarmShield gateway unavailable (%s): FAILING OPEN, traffic is NOT inspected", cause)
            return GatewayVerdict("allow", 0.0, f"gateway unavailable, fail-open ({cause})", degraded=True)
        raise SwarmShieldUnavailableError(f"SwarmShield gateway unavailable ({cause}); failing closed")

    def _interpret(self, resp: httpx.Response) -> GatewayVerdict:
        try:
            body: dict[str, Any] = resp.json()
        except ValueError:
            body = {}

        if resp.status_code == 200:
            return GatewayVerdict(
                verdict=str(body.get("verdict", "allow")),
                risk_score=float(body.get("risk_score", 0.0)),
                reason=str(body.get("reason", "")),
                findings=tuple(body.get("findings", [])),
                requires_human_review=bool(body.get("requires_human_review", False)),
                message_id=str(body.get("message_id", "")),
                raw=body,
            )
        if resp.status_code == 403:
            raise SwarmShieldSecurityException(body.get("reason") or "blocked by SwarmShield", detail=body)
        if resp.status_code == 429:
            retry = body.get("retry_after") or resp.headers.get("Retry-After")
            raise SwarmShieldCircuitBreakerException(
                body.get("reason") or "circuit breaker tripped",
                detail=body,
                retry_after=int(retry) if retry else None,
            )
        if resp.status_code >= 500:
            return self._unavailable(f"HTTP {resp.status_code}")
        raise SwarmShieldError(f"unexpected gateway response: HTTP {resp.status_code}", detail=body)

    # ---- public API ------------------------------------------------------------------

    def transfer(self, **kwargs: Any) -> GatewayVerdict:
        """Blocking call. See :func:`build_payload` for accepted keyword arguments."""
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(f"{self.base_url}/a2a/transfer", json=build_payload(**kwargs), headers=self._headers)
        except httpx.TransportError as exc:  # connect errors, timeouts, protocol errors
            return self._unavailable(type(exc).__name__)
        return self._interpret(resp)

    async def atransfer(self, **kwargs: Any) -> GatewayVerdict:
        """Async call. See :func:`build_payload` for accepted keyword arguments."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/a2a/transfer", json=build_payload(**kwargs), headers=self._headers
                )
        except httpx.TransportError as exc:
            return self._unavailable(type(exc).__name__)
        return self._interpret(resp)
