"""Shield routes are read-only proxies to the SwarmShield gateway; mock the HTTP layer."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import shield
from app.core.config import settings


@pytest.fixture()
def client(monkeypatch):
    calls: list[str] = []

    async def fake_get_json(url, *, headers=None):
        calls.append(url)
        if url.endswith("/health") and "9100" in url:
            return {"patched": False, "shield": {"enabled": True}}
        if url.endswith("/health"):
            return {"status": "ok", "counters": {"block": 2}}
        if "/v1/events" in url:
            return {"events": [{"verdict": "block"}], "counters": {}}
        return {"agents": [{"agent_id": "rag:kb-004", "status": "quarantined"}], "conversations": []}

    monkeypatch.setattr(shield, "_get_json", fake_get_json)
    monkeypatch.setattr(settings, "SWARMSHIELD_GATEWAY_URL", "http://gw:8100")
    monkeypatch.setattr(settings, "CONTROLLED_TARGET_URL", "http://target:9100")
    app = FastAPI()
    app.include_router(shield.router, prefix="/api")
    tc = TestClient(app)
    tc.calls = calls  # type: ignore[attr-defined]
    return tc


def test_status_combines_gateway_and_target(client):
    body = client.get("/api/shield/status").json()
    assert body["gateway"]["reachable"] is True and body["gateway"]["counters"] == {"block": 2}
    assert body["target"]["shield"] == {"enabled": True}


def test_events_and_agents_are_proxied(client):
    assert client.get("/api/shield/events?limit=10").json()["events"][0]["verdict"] == "block"
    assert client.get("/api/shield/agents").json()["agents"][0]["status"] == "quarantined"
    assert any("limit=10" in u for u in client.calls)


def test_503_when_gateway_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "SWARMSHIELD_GATEWAY_URL", "")
    assert client.get("/api/shield/events").status_code == 503
