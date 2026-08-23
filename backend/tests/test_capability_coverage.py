from app.capability.attack_paths import derive_attack_paths
from app.capability.classifier import classify_all
from app.capability.coverage import compute_coverage
from app.capability.extractor import extract_tool_frames
from app.capability.fingerprint import compute_target_fingerprint
from app.capability.graph import build_capability_graph
from app.capability.hypotheses import generate_hypotheses
from app.capability.runtime import classify_observed, extract_observed_tool_frames, reconcile


class _FakeAgentType:
    def __init__(self, value):
        self.value = value


class _FakeLog:
    def __init__(self, target_response, agent_type_value, succeeded=False):
        self.target_response = target_response
        self.agent_type = _FakeAgentType(agent_type_value)
        self.succeeded = succeeded


class _FakeTarget:
    name = "demo-agent"
    endpoint_url = "http://localhost:9100/chat"
    permission_map = {}

    def __init__(self, tools):
        self.declared_tools = tools


def _pipeline(declared_tools, attack_logs=None):
    declared = classify_all(extract_tool_frames(declared_tools).tool_frames)
    observed = []
    if attack_logs:
        obs_result = extract_observed_tool_frames(attack_logs)
        observed = classify_observed(obs_result.tool_frames)
    merged = reconcile(declared, observed)
    graph = build_capability_graph(merged)
    paths = derive_attack_paths(merged, graph)
    hyps = generate_hypotheses(merged, paths)
    return merged, paths, hyps


def test_coverage_all_not_tested_with_no_logs():
    frames, paths, hyps = _pipeline([{"name": "search_documents", "description": "search kb"}])
    cov = compute_coverage(frames, paths, hyps, [])
    assert cov["summary"]["operation_coverage_pct"] == 0.0
    assert all(v == "not_tested" for v in cov["operations"].values())
    assert all(v == "not_tested" for v in cov["specialists"].values())


def test_coverage_reflects_real_attack_logs():
    log = _FakeLog(
        "TOOL_CALL: internal_admin_update(action=grant)",
        "tool_abuse_specialist",
        succeeded=True,
    )
    frames, paths, hyps = _pipeline(
        [{"name": "search_documents", "description": "search kb"}], attack_logs=[log]
    )
    cov = compute_coverage(frames, paths, hyps, [log])
    assert cov["specialists"]["tool_abuse"] == "passed"
    assert cov["specialists"]["jailbreak"] == "not_tested"
    assert cov["operations"]["update"] == "tested"


def test_undeclared_capability_detected_and_high_risk_hypothesis_emitted():
    log = _FakeLog("TOOL_CALL: internal_admin_update(action=grant)", "tool_abuse_specialist")
    frames, paths, hyps = _pipeline(
        [{"name": "search_documents", "description": "search kb"}], attack_logs=[log]
    )
    undeclared = [f for f in frames if f.status.value == "undeclared_observed"]
    assert len(undeclared) == 1
    assert undeclared[0].name == "internal_admin_update"
    # spec section 8: undeclared-observed capabilities get a risk bump and
    # must surface as a hypothesis, not be silently dropped
    matching_hyps = [h for h in hyps if "internal_admin_update" in h.capabilities_involved or undeclared[0].capability_id in h.capabilities_involved]
    assert matching_hyps, "undeclared capability must produce at least one hypothesis"


def test_fingerprint_stable_for_same_capability_set():
    tools = [{"name": "search_documents", "description": "search kb"}]
    frames_a, _, _ = _pipeline(tools)
    frames_b, _, _ = _pipeline(tools)
    fp_a = compute_target_fingerprint(_FakeTarget(tools), frames_a)
    fp_b = compute_target_fingerprint(_FakeTarget(tools), frames_b)
    assert fp_a["fingerprint"] == fp_b["fingerprint"]


def test_fingerprint_changes_when_capability_set_changes():
    tools_a = [{"name": "search_documents", "description": "search kb"}]
    tools_b = [{"name": "search_documents", "description": "search kb"}, {"name": "read_file", "description": "read a file"}]
    frames_a, _, _ = _pipeline(tools_a)
    frames_b, _, _ = _pipeline(tools_b)
    fp_a = compute_target_fingerprint(_FakeTarget(tools_a), frames_a)
    fp_b = compute_target_fingerprint(_FakeTarget(tools_b), frames_b)
    assert fp_a["fingerprint"] != fp_b["fingerprint"]
