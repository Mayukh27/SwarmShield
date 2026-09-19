"""SwarmShield Python SDK.

The one public entry point most callers need: the ``@protect_agent``
decorator. It wraps any function that hands a message/tool-call off to
another agent (an A2A handoff, or an agent invoking a tool) and routes
that handoff through the SwarmShield gateway (``POST /a2a/transfer``)
before the wrapped function ever runs.

    from swarmshield.sdk import protect_agent
    from swarmshield.exceptions import SwarmShieldSecurityException, SwarmShieldCircuitBreakerException

    @protect_agent(sender_role="tool_abuse_specialist")
    async def send_to_target(payload: str, *, swarmshield=None) -> dict:
        # swarmshield=None -> a GatewayVerdict is injected here if the
        # wrapped function declares the ``swarmshield`` keyword param.
        return await target_client.send(payload)

    try:
        result = await send_to_target(
            payload, sender_id="specialist-1", receiver_id="target-1",
            target_tool="sql_select", conversation_id=str(scan_id),
        )
    except SwarmShieldSecurityException as exc:
        ...  # 403: injection / RBAC / taint violation
    except SwarmShieldCircuitBreakerException as exc:
        ...  # 429: loop circuit breaker tripped

Call-site kwargs consumed by the decorator (all optional except
``message``/``sender_id``/``receiver_id`` -- see below for how those are
resolved) are popped off before the wrapped function is called, so the
wrapped function never has to know about them:

    message, sender_id, receiver_id, sender_role, receiver_role,
    target_tool, tool_args, conversation_id, hop_count, provenance

If ``message`` is not passed explicitly, the decorator falls back to the
wrapped function's first positional argument (the common case: a
``send(payload, ...)``-shaped function). ``sender_role`` can be fixed at
decoration time (``@protect_agent(sender_role="planner")``) or supplied
per call; a per-call value always wins.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
from typing import Any, Callable, Optional, TypeVar

from swarmshield.integrations._client import GatewayClient, GatewayVerdict
from swarmshield.exceptions import SwarmShieldUnavailableError

logger = logging.getLogger("swarmshield.sdk")

F = TypeVar("F", bound=Callable[..., Any])

_REQUEST_KWARGS = (
    "message", "sender_id", "receiver_id", "sender_role", "receiver_role",
    "target_tool", "tool_args", "conversation_id", "hop_count", "provenance",
)


def protect_agent(
    *,
    sender_role: Optional[str] = None,
    receiver_role: Optional[str] = None,
    gateway_url: Optional[str] = None,
    api_key: Optional[str] = None,
    fail_mode: str = "closed",
    client: Optional[GatewayClient] = None,
) -> Callable[[F], F]:
    """Decorator: route this agent function's handoff through the SwarmShield gateway.

    ``fail_mode="closed"`` (default): if the gateway is unreachable, the
    call raises ``SwarmShieldUnavailableError`` rather than letting
    uninspected traffic through. Pass ``fail_mode="open"`` for demos /
    non-critical paths where availability matters more than inspection.
    """
    gw = client or GatewayClient(base_url=gateway_url, api_key=api_key, fail_mode=fail_mode)

    def decorator(func: F) -> F:
        sig = inspect.signature(func)
        wants_verdict = "swarmshield" in sig.parameters
        is_async = asyncio.iscoroutinefunction(func)

        def _build_kwargs(args: tuple, kwargs: dict) -> dict:
            req = {k: kwargs.pop(k) for k in _REQUEST_KWARGS if k in kwargs}
            req.setdefault("sender_role", sender_role)
            req.setdefault("receiver_role", receiver_role)
            if "message" not in req and args:
                req["message"] = args[0]
            if req.get("sender_role") is None:
                raise ValueError(
                    f"{func.__name__}: sender_role is required (pass it to @protect_agent(...) "
                    f"or as a call kwarg)"
                )
            for required in ("message", "sender_id", "receiver_id"):
                if required not in req:
                    raise ValueError(f"{func.__name__}: '{required}' is required to call SwarmShield")
            return req

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                req = _build_kwargs(args, kwargs)
                verdict = await gw.atransfer(**req)
                _warn_if_degraded(verdict, func.__name__)
                if wants_verdict:
                    kwargs["swarmshield"] = verdict
                return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            req = _build_kwargs(args, kwargs)
            verdict = gw.transfer(**req)
            _warn_if_degraded(verdict, func.__name__)
            if wants_verdict:
                kwargs["swarmshield"] = verdict
            return func(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _warn_if_degraded(verdict: GatewayVerdict, fn_name: str) -> None:
    if verdict.degraded:
        logger.warning("SwarmShield gateway offline for %s(); call proceeded UNINSPECTED (fail-open)", fn_name)
    elif verdict.requires_human_review:
        logger.info("SwarmShield flagged %s() for human review: %s", fn_name, verdict.reason)


async def check(
    *,
    message: str,
    sender_id: str,
    receiver_id: str,
    sender_role: str,
    gateway: Optional[GatewayClient] = None,
    gateway_url: Optional[str] = None,
    api_key: Optional[str] = None,
    fail_mode: str = "closed",
    **kwargs: Any,
) -> GatewayVerdict:
    """Imperative alternative to the decorator: call the gateway directly and
    get back a ``GatewayVerdict``, or have it raise
    ``SwarmShieldSecurityException`` / ``SwarmShieldCircuitBreakerException`` /
    ``SwarmShieldUnavailableError``. Useful inside an existing loop (like an
    orchestrator's retry loop) where wrapping a whole function is awkward.
    """
    gw = gateway or GatewayClient(base_url=gateway_url, api_key=api_key, fail_mode=fail_mode)
    verdict = await gw.atransfer(
        message=message, sender_id=sender_id, receiver_id=receiver_id, sender_role=sender_role, **kwargs
    )
    _warn_if_degraded(verdict, "swarmshield.sdk.check")
    return verdict


__all__ = ["protect_agent", "check", "GatewayClient", "GatewayVerdict", "SwarmShieldUnavailableError"]
