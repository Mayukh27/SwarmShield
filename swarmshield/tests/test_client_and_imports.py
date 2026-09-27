"""Framework-independent pieces: the gateway client and the optional-import behaviour."""
from __future__ import annotations

import subprocess
import sys

import pytest

from swarmshield.exceptions import (
    SwarmShieldCircuitBreakerException,
    SwarmShieldSecurityException,
    SwarmShieldUnavailableError,
)
from swarmshield.integrations._client import GatewayClient

from .conftest import INJECTION

BASE = dict(sender_id="a", sender_role="researcher", receiver_id="b", receiver_role="researcher")


def test_clean_message_is_allowed(gateway_url, uid):
    v = GatewayClient(gateway_url).transfer(message="Summarize Q3 sales", conversation_id=f"c-{uid}", **BASE)
    assert v.verdict == "allow" and not v.requires_human_review and not v.degraded


def test_injection_maps_to_403_exception(gateway_url, uid):
    with pytest.raises(SwarmShieldSecurityException) as e:
        GatewayClient(gateway_url).transfer(
            message=INJECTION, conversation_id=f"c-{uid}", provenance=["untrusted_web"],
            **{**BASE, "sender_id": f"web-{uid}"},
        )
    assert e.value.violation_type == "prompt_injection" and e.value.risk_score >= 0.7


def test_loop_maps_to_429_exception_with_evidence(gateway_url, uid):
    client, conv = GatewayClient(gateway_url), f"loop-{uid}"
    a, b = f"pa-{uid}", f"pb-{uid}"
    with pytest.raises(SwarmShieldCircuitBreakerException) as e:
        for hop in range(1, 12):
            s, r = (a, b) if hop % 2 else (b, a)
            client.transfer(message="Please delegate this task back and re-plan it.", sender_id=s, receiver_id=r,
                            sender_role="planner", receiver_role="planner", conversation_id=conv)
    assert e.value.evidence["kind"] == "pingpong" and e.value.retry_after
    assert set(e.value.quarantined_agents) == {a, b}


def test_outage_fail_closed_vs_fail_open(dead_url):
    kw = dict(message="hi", **BASE)
    with pytest.raises(SwarmShieldUnavailableError):
        GatewayClient(dead_url, timeout=0.5, fail_mode="closed").transfer(**kw)
    v = GatewayClient(dead_url, timeout=0.5, fail_mode="open").transfer(**kw)
    assert v.degraded and v.verdict == "allow"


@pytest.mark.asyncio
async def test_async_transfer(gateway_url, uid):
    v = await GatewayClient(gateway_url).atransfer(message="hello", conversation_id=f"c-{uid}", **BASE)
    assert v.verdict == "allow"


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)


def test_swarmshield_and_gateway_import_without_langchain_or_langgraph():
    r = _run(
        "import sys; sys.modules['langchain']=None; sys.modules['langgraph']=None\n"
        "import swarmshield, swarmshield.exceptions, swarmshield.integrations, swarmshield.gateway\n"
        "assert 'swarmshield.integrations.langchain' not in sys.modules\n"
        "assert 'swarmshield.integrations.langgraph' not in sys.modules\n"
        "print('ok')"
    )
    assert r.returncode == 0 and "ok" in r.stdout, r.stderr


def test_missing_framework_gives_install_hint():
    r = _run(
        "import sys; sys.modules['langchain']=None; sys.modules['langgraph']=None\n"
        "import swarmshield.integrations as i\n"
        "for name, hint in (('SwarmShieldMiddleware','swarmshield[langchain]'), ('add_swarmshield_gate','swarmshield[langgraph]')):\n"
        "    try: getattr(i, name); raise SystemExit('no error for '+name)\n"
        "    except ImportError as e: assert hint in str(e), str(e)\n"
        "print('ok')"
    )
    assert r.returncode == 0 and "ok" in r.stdout, r.stdout + r.stderr
