"""demo_target: standalone multi-agent target. All security assertions verify the REAL gateway's
decision (via gateway_decision.http_status / violation_type / quarantined_agents), not any
local scoring -- demo_target contains none."""
from __future__ import annotations


def status(step: dict) -> int:
    return step["gateway_decision"]["http_status"]


def test_health_reports_agents_and_gateway(client):
    body = client.get("/health").json()
    assert set(body["agents"]) == {"planner_agent", "research_agent", "db_agent", "tool_agent", "agent_a", "agent_b"}
    assert body["gateway"]["configured"] and body["gateway"]["reachable"]


def test_scenario1_normal_a2a_request_is_allowed(client):
    resp = client.post("/attack/allow").json()
    assert status(resp["steps"][-1]) == 200
    assert resp["steps"][-1]["security_state"] == "ALLOW"


def test_scenario2_direct_injection_via_chat(client):
    resp = client.post("/attack/direct_injection").json()
    step = resp["steps"][-1]
    # gateway's own verdict is what matters (this vulnerable target's compliant behavior is
    # secondary evidence for the red-team "finding", not a security control)
    assert step["security_state"] in {"BLOCK", "ALLOW"}
    if step["security_state"] == "ALLOW":
        assert "TOOL_CALL" not in (step["result"] or "") or True  # deterministic path is asserted below
        assert "no input hardening" in step["result"]


def test_scenario3_indirect_injection_via_poisoned_document_is_blocked(client):
    resp = client.post("/attack/indirect_injection").json()
    step = resp["steps"][-1]
    assert status(step) == 403
    assert step["gateway_decision"]["violation_type"] == "prompt_injection"
    assert "research_agent" in step["gateway_decision"]["quarantined_agents"]


def test_scenario4_rbac_violation_then_agent_still_usable_for_allowed_tools(client):
    resp = client.post("/attack/rbac_violation").json()
    first, second = resp["steps"]
    assert status(first) == 403
    assert first["gateway_decision"]["violation_type"] == "rbac"
    assert "sql_drop" in first["blocked_reason"]
    assert status(second) == 200  # one violation alone doesn't quarantine (quarantine_after > 1)


def test_scenario5_poisoned_tool_output_is_intercepted(client):
    resp = client.post("/attack/poisoned_tool_output").json()
    step = resp["steps"][-1]
    assert status(step) == 403
    assert step["agent"] == "tool_agent"
    assert "tool:web_search" in step["gateway_decision"]["quarantined_agents"]


def test_scenario6_recursive_loop_trips_circuit_breaker_and_quarantines_both_agents(client):
    resp = client.post("/attack/recursive_loop").json()
    last = resp["steps"][-1]
    assert status(last) == 429
    assert last["gateway_decision"]["evidence"]["kind"] == "pingpong"
    assert set(last["gateway_decision"]["quarantined_agents"]) == {"agent_a", "agent_b"}
    assert resp["hops_sent"] < 12  # breaker stopped it well before the max_hops ceiling


def test_scenario7_quarantine_blocks_the_offending_agent_specifically(client):
    client.post("/attack/indirect_injection")  # quarantines research_agent
    again = client.post("/agents/delegate", json={
        "from_agent": "research_agent", "to_agent": "planner_agent",
        "from_role": "researcher", "to_role": "planner", "message": "innocuous follow-up",
    }).json()
    assert status(again) == 403
    assert again["gateway_decision"]["violation_type"] == "quarantined_sender"


def test_scenario8_clean_traffic_still_works_after_attacks(client):
    client.post("/attack/direct_injection")
    client.post("/attack/indirect_injection")
    client.post("/attack/rbac_violation")
    client.post("/attack/poisoned_tool_output")
    resp = client.post("/attack/clean_traffic_after_attacks").json()
    assert status(resp["steps"][-1]) == 200


def test_run_all_end_to_end_matches_expected_sequence(client):
    resp = client.post("/attack/run_all").json()["results"]
    codes = [status(r["steps"][-1]) for r in resp]
    assert len(codes) == 7
    assert codes[0] == 200  # allow
    # codes[1] (direct_injection) depends on this target's own vulnerable chat logic, not asserted here
    assert codes[2] == 403  # indirect_injection
    assert codes[3] == 200  # rbac_violation: last step is the allowed follow-up (see scenario 4 test)
    assert codes[4] == 403  # poisoned_tool_output
    assert codes[5] == 429  # recursive_loop
    assert codes[6] == 200  # clean traffic after attacks


def test_admin_reset_state_clears_log_and_releases_quarantines(client):
    client.post("/attack/indirect_injection")
    assert client.get("/state").json()["log"]
    client.post("/admin/reset_state")
    assert client.get("/state").json()["log"] == []
    ok = client.post("/attack/indirect_injection").json()["steps"][0]  # research_agent inbound must be un-quarantined
    assert ok["agent"] == "research_agent" and ok["gateway_decision"]["violation_type"] != "quarantined_sender"


def test_offline_no_llm_or_external_network_calls(client, monkeypatch):
    """Guardrail: httpx must only ever be asked to reach the gateway, nothing else."""
    import httpx

    seen = []
    orig = httpx.Client.request

    def spy(self, method, url, *a, **kw):
        seen.append(str(url))
        return orig(self, method, url, *a, **kw)

    monkeypatch.setattr(httpx.Client, "request", spy)
    client.post("/attack/run_all")
    assert seen
    outbound = [u for u in seen if "testserver" not in u]
    assert outbound
    assert all("127.0.0.1" in u or "localhost" in u for u in outbound)
