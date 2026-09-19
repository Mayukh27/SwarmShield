"""Exception hierarchy shared by every SwarmShield client (SDK, LangChain, LangGraph)."""

from __future__ import annotations

from typing import Any, Optional


class SwarmShieldError(Exception):
    """Base class for all SwarmShield errors."""

    def __init__(self, message: str, *, detail: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        # Raw JSON body returned by the gateway (may be empty for transport errors).
        self.detail: dict[str, Any] = detail or {}

    @property
    def risk_score(self) -> float:
        return float(self.detail.get("risk_score", 0.0))

    @property
    def findings(self) -> list[dict[str, Any]]:
        return list(self.detail.get("findings", []))

    @property
    def violation_type(self) -> Optional[str]:
        return self.detail.get("violation_type")


class SwarmShieldSecurityException(SwarmShieldError):
    """Gateway answered 403: injection, RBAC/taint violation or quarantined sender."""


class SwarmShieldCircuitBreakerException(SwarmShieldError):
    """Gateway answered 429: the conversation tripped the loop circuit breaker."""

    def __init__(
        self,
        message: str,
        *,
        detail: Optional[dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message, detail=detail)
        self.retry_after = retry_after


class SwarmShieldUnavailableError(SwarmShieldError):
    """Gateway unreachable / 5xx while the client is configured to fail closed."""
