"""Framework adapters for the SwarmShield gateway.

Thin wrappers only: every decision (injection scan, RBAC/taint, circuit breaker) is made by the
gateway. LangChain / LangGraph are OPTIONAL dependencies and are imported lazily, so
``import swarmshield`` and the gateway itself never require them.

    from swarmshield.integrations import SwarmShieldMiddleware      # needs: pip install "swarmshield[langchain]"
    from swarmshield.integrations import add_swarmshield_gate       # needs: pip install "swarmshield[langgraph]"

Accessing an adapter whose framework is not installed raises an ImportError that says what to install.
"""

from __future__ import annotations

import importlib
from typing import Any

_LAZY: dict[str, str] = {
    # LangChain
    "SwarmShieldMiddleware": "swarmshield.integrations.langchain",
    # LangGraph
    "SwarmState": "swarmshield.integrations.langgraph",
    "add_swarmshield_gate": "swarmshield.integrations.langgraph",
    "make_gatekeeper": "swarmshield.integrations.langgraph",
    "make_review_node": "swarmshield.integrations.langgraph",
    "swarmshield_quarantine": "swarmshield.integrations.langgraph",
    "swarmshield_gatekeeper": "swarmshield.integrations.langgraph",
    "GATEKEEPER_NODE": "swarmshield.integrations.langgraph",
    "REVIEW_NODE": "swarmshield.integrations.langgraph",
    "QUARANTINE_NODE": "swarmshield.integrations.langgraph",
    # Framework-independent
    "GatewayClient": "swarmshield.integrations._client",
    "GatewayVerdict": "swarmshield.integrations._client",
}

__all__ = sorted(_LAZY)


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module), name)
