"""
Minimal in-memory pub/sub, keyed by scan_id, so the SSE route can stream
agent events to the frontend as they happen during `scan_manager.run_scan`.

Hackathon-appropriate: single-process only. For a multi-worker deployment,
swap this for Redis pub/sub without changing the route/manager interfaces.
"""
import asyncio
import uuid
from collections import defaultdict

from app.schemas.attack import AgentLogEvent

_queues: dict[uuid.UUID, list[asyncio.Queue]] = defaultdict(list)


def subscribe(scan_id: uuid.UUID) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _queues[scan_id].append(q)
    return q


def unsubscribe(scan_id: uuid.UUID, q: asyncio.Queue) -> None:
    if q in _queues.get(scan_id, []):
        _queues[scan_id].remove(q)


async def publish(scan_id: uuid.UUID, event: AgentLogEvent) -> None:
    for q in _queues.get(scan_id, []):
        await q.put(event)
