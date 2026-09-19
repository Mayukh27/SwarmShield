"""Read-only window into the SwarmShield runtime gateway.

The red-team platform (this backend) attacks a target; the SwarmShield gateway defends it. These
routes let the dashboard show both sides: is the shield on, what did it block, which agents or
data sources are quarantined. Turning the shield on for a target happens through the existing, permission-gated
apply-and-revalidate flow (APPLY_PATCH_MODE). The one action route, /demo/stream, only sends
synthetic agent traffic to the gateway; it never touches the target.
"""
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.core.config import settings
from app.services import shield_runtime

router = APIRouter(prefix="/shield", tags=["shield"])


async def _get_json(url: str, *, headers: dict[str, str] | None = None) -> Any:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url, headers=headers or {})
        resp.raise_for_status()
        return resp.json()


def _gateway() -> tuple[str, dict[str, str]]:
    if not settings.SWARMSHIELD_GATEWAY_URL:
        raise HTTPException(status_code=503, detail="SWARMSHIELD_GATEWAY_URL is not configured")
    headers = {"X-SwarmShield-Key": settings.SWARMSHIELD_API_KEY} if settings.SWARMSHIELD_API_KEY else {}
    return settings.SWARMSHIELD_GATEWAY_URL.rstrip("/"), headers


@router.get("/status")
async def shield_status() -> dict[str, Any]:
    """Gateway health + whether the controlled target is currently routed through it."""
    base, _ = _gateway()
    out: dict[str, Any] = {"gateway": {"url": base}, "target": {}}
    try:
        out["gateway"].update(await _get_json(f"{base}/health"), reachable=True)
    except httpx.HTTPError as exc:
        out["gateway"].update(reachable=False, error=str(exc))
    try:
        health = await _get_json(f"{settings.CONTROLLED_TARGET_URL.rstrip('/')}/health")
        out["target"] = {"patched": health.get("patched"), "shield": health.get("shield")}
    except httpx.HTTPError as exc:
        out["target"] = {"error": str(exc)}
    return out


@router.get("/events")
async def shield_events(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    """Most recent gateway decisions (allow / flag / block / trip)."""
    base, headers = _gateway()
    try:
        return await _get_json(f"{base}/v1/events?limit={limit}", headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"gateway error: {exc}") from exc


@router.get("/agents")
async def shield_agents() -> dict[str, Any]:
    """Agent / data-source statuses: normal, inspected, quarantined."""
    base, headers = _gateway()
    try:
        return await _get_json(f"{base}/v1/agents", headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"gateway error: {exc}") from exc


@router.get("/demo/stream")
async def security_demo_stream() -> EventSourceResponse:
    """Runs the security simulation and streams each REAL gateway response as an SSE `security_event`.

    GET because the browser's EventSource can only GET. The generator ends with `security_demo_done`
    (or `security_demo_error`); the frontend closes the stream on those.
    """
    async def gen():
        async for ev in shield_runtime.run_demo():
            yield {"event": ev.event_type, "data": ev.model_dump_json()}

    return EventSourceResponse(gen())
