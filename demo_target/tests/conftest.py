"""Starts the REAL SwarmShield gateway in-process (same policy file the rest of the repo
uses) so demo_target tests exercise real injection detection / RBAC / circuit-breaker
behavior. No LLM, no external network."""
from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import pytest

POLICY = Path(__file__).resolve().parents[2] / "swarmshield" / "policies" / "controlled_target_policy.yaml"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def gateway_url():
    uvicorn = pytest.importorskip("uvicorn")
    os.environ["SWARMSHIELD_POLICY"] = str(POLICY)
    os.environ["SWARMSHIELD_NO_QUARANTINE"] = "user,support_assistant,target,planner"
    os.environ.pop("SWARMSHIELD_API_KEY", None)
    from swarmshield.gateway import app

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "gateway did not start"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture()
def client(gateway_url, monkeypatch):
    """A TestClient for demo_target.app, pointed at the real in-process gateway above."""
    monkeypatch.setenv("SWARMSHIELD_GATEWAY_URL", gateway_url)
    monkeypatch.delenv("SWARMSHIELD_API_KEY", raising=False)
    import importlib

    import demo_target.gateway_client as gc
    import demo_target.app as app_module

    importlib.reload(gc)  # pick up the monkeypatched env for GATEWAY singleton
    app_module.GATEWAY = gc.GATEWAY

    from fastapi.testclient import TestClient

    with TestClient(app_module.app) as c:
        c.post("/admin/reset_state")
        yield c
