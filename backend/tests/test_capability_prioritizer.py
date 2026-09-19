"""
Unit tests for Phase 6 additions: the weighted prioritizer (spec section
21), multi-hop attack-path discovery (spec section 15), and
memory-informed hypothesis prioritization/novelty (spec section 25).
All pure-Python -- no DB required, consistent with the rest of the
capability test suite.
"""
from app.capability.attack_paths import derive_attack_paths
from app.capability.classifier import classify_all
from app.capability.enums import CapabilityCategory, DataSensitivity, DestructiveRisk, HypothesisPriority
from app.capability.extractor import extract_tool_frames
from app.capability.graph import build_capability_graph
from app.capability.hypotheses import generate_hypotheses
from app.capability.models import CapabilityFrame
from app.capability.prioritizer import MemorySignal, compute_priority


def _tool(name: str, description: str = "", permissions: list[str] | None = None) -> dict:
    return {"name": name, "description": description, "permissions": permissions or []}


def _declared(*tools: dict) -> dict:
    return {"tools": list(tools)}


# ---------- prioritizer ----------

def test_compute_priority_is_bounded_0_to_100():
    result = compute_priority(
        capability_risk=100, boundary_risk=100, data_sensitivity=DataSensitivity.SECRETS,
        coverage_gap=True, frame=None, memory=MemorySignal(prior_failure_count=50),
    )
    assert 0.0 <= result.score <= 100.0


def test_higher_capability_risk_yields_higher_or_equal_priority_score():
    low = compute_priority(capability_risk=10, boundary_risk=0, data_sensitivity=DataSensitivity.PUBLIC, coverage_gap=False)
    high = compute_priority(capability_risk=90, boundary_risk=0, data_sensitivity=DataSensitivity.PUBLIC, coverage_gap=False)
    assert high.score > low.score


def test_prior_success_increases_historical_signal_component():
    no_history = compute_priority(capability_risk=50, boundary_risk=0, data_sensitivity=DataSensitivity.INTERNAL, coverage_gap=False)
    with_success = compute_priority(
        capability_risk=50, boundary_risk=0, data_sensitivity=DataSensitivity.INTERNAL, coverage_gap=False,
        memory=MemorySignal(prior_success_count=2, novel=False),
    )
    assert with_success.breakdown["historical_signal"] > no_history.breakdown["historical_signal"]
    assert with_success.score >= no_history.score


def test_repeated_prior_failures_reduce_score_relative_to_no_history():
    baseline = compute_priority(capability_risk=50, boundary_risk=0, data_sensitivity=DataSensitivity.INTERNAL, coverage_gap=True)
    penalized = compute_priority(
        capability_risk=50, boundary_risk=0, data_sensitivity=DataSensitivity.INTERNAL, coverage_gap=True,
        memory=MemorySignal(prior_failure_count=4, novel=False),
    )
    assert penalized.breakdown["previous_failure_penalty"] > 0
    assert penalized.score <= baseline.score


def test_destructive_ungated_capability_scores_high_authorization_risk():
    frame = CapabilityFrame(name="delete_user", destructive=DestructiveRisk.LIKELY, required_role=None)
    result = compute_priority(capability_risk=40, boundary_risk=0, data_sensitivity=DataSensitivity.USER_DATA, coverage_gap=True, frame=frame)
    assert result.breakdown["authorization_risk"] >= 40


def test_priority_bucket_thresholds_are_monotonic():
    scores_to_priorities = []
    for cap_risk in (5, 30, 55, 85):
        r = compute_priority(capability_risk=cap_risk, boundary_risk=0, data_sensitivity=DataSensitivity.UNKNOWN, coverage_gap=False)
        scores_to_priorities.append((r.score, r.priority))
    order = [HypothesisPriority.LOW, HypothesisPriority.MEDIUM, HypothesisPriority.HIGH, HypothesisPriority.CRITICAL]
    seen_ranks = [order.index(p) for _, p in scores_to_priorities]
    assert seen_ranks == sorted(seen_ranks)


# ---------- multi-hop attack paths ----------

def test_three_hop_chain_discovered_for_search_read_send():
    result = extract_tool_frames(_declared(
        _tool("search_documents", "Search the document index"),
        _tool("read_file", "Read a file from disk"),
        _tool("send_email", "Send an email to a recipient"),
    ))
    frames = classify_all(result.tool_frames)
    # Force all three to share a resource so a chain edge exists between
    # every pair -- this mirrors what the classifier does for tools that
    # plausibly operate on the same document/file resource.
    from app.capability.enums import ResourceType
    for f in frames:
        if ResourceType.FILESYSTEM not in f.resources:
            f.resources = list(f.resources) + [ResourceType.FILESYSTEM]

    graph = build_capability_graph(frames)
    paths = derive_attack_paths(frames, graph, max_paths=50)
    multi_hop = [p for p in paths if len(p.capability_ids) >= 3]
    assert multi_hop, "expected at least one 3+ hop chain across search -> read -> send"


def test_max_paths_bound_is_respected():
    tools = [_tool(f"read_file_{i}", "Read a file from disk") for i in range(6)]
    result = extract_tool_frames(_declared(*tools))
    frames = classify_all(result.tool_frames)
    from app.capability.enums import ResourceType
    for f in frames:
        f.resources = [ResourceType.FILESYSTEM]
    graph = build_capability_graph(frames)
    paths = derive_attack_paths(frames, graph, max_paths=3)
    assert len(paths) <= 3


# ---------- memory-informed hypothesis generation ----------

def test_memory_signal_reduces_previous_attempts_when_novel():
    frame = CapabilityFrame(
        name="read_file", category=CapabilityCategory.FILESYSTEM,
        data_sensitivity=DataSensitivity.INTERNAL, risk_score=40,
    )
    hyps = generate_hypotheses([frame], [], target_fingerprint="fp123")
    assert hyps[0].previous_attempts == 0
    assert hyps[0].fingerprint == "fp123"
    assert hyps[0].priority_breakdown  # decision trace populated


def test_memory_signal_with_prior_failures_recorded_on_hypothesis():
    frame = CapabilityFrame(
        capability_id="cap-1", name="read_file", category=CapabilityCategory.FILESYSTEM,
        data_sensitivity=DataSensitivity.INTERNAL, risk_score=40,
    )
    signals = {"cap-1": MemorySignal(prior_failure_count=3, previous_attempts=3, novel=False)}
    hyps = generate_hypotheses([frame], [], memory_signals=signals)
    assert hyps[0].previous_attempts == 3
    assert hyps[0].mutation_context["prior_failures"] == 3


def test_authorization_requirements_explicit_when_ungated():
    frame = CapabilityFrame(name="delete_user", category=CapabilityCategory.IDENTITY, required_role=None, required_permissions=[])
    hyps = generate_hypotheses([frame], [])
    assert hyps[0].authorization_requirements == ["none_declared"]


def test_authorization_requirements_list_role_and_permissions():
    frame = CapabilityFrame(
        name="delete_user", category=CapabilityCategory.IDENTITY,
        required_role="admin", required_permissions=["users:delete"],
    )
    hyps = generate_hypotheses([frame], [])
    assert "role:admin" in hyps[0].authorization_requirements
    assert "permission:users:delete" in hyps[0].authorization_requirements


# ---------- memory bridge (capability_service) ----------

class _FakeMemoryRow:
    def __init__(self, namespace, success, target_fingerprint="target-1"):
        self.namespace = namespace
        self.success = success
        self.target_fingerprint = target_fingerprint


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def limit(self, _n):
        return self

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def query(self, _model):
        return _FakeQuery(self._rows)


class _FakeTarget:
    def __init__(self, target_id="target-1"):
        self.id = target_id


def test_memory_signals_for_target_counts_successes_and_failures():
    from app.services.capability_service import _memory_signals_for_target

    frame = CapabilityFrame(
        capability_id="cap-1", name="read_file", category=CapabilityCategory.FILESYSTEM,
        data_sensitivity=DataSensitivity.INTERNAL, risk_score=40,
    )
    rows = [
        _FakeMemoryRow("data_exfiltration_specialist", success=1.0),
        _FakeMemoryRow("data_exfiltration_specialist", success=0.0),
        _FakeMemoryRow("tool_abuse_specialist", success=0.0),
        _FakeMemoryRow("prompt_injection_specialist", success=1.0),  # unrelated namespace, should not count
    ]
    db = _FakeDB(rows)
    signals = _memory_signals_for_target(db, _FakeTarget(), [frame], [])
    assert "cap-1" in signals
    sig = signals["cap-1"]
    assert sig.prior_success_count == 1
    assert sig.prior_failure_count == 2
    assert sig.novel is False


def test_memory_signals_empty_when_no_db():
    from app.services.capability_service import _memory_signals_for_target

    frame = CapabilityFrame(capability_id="cap-1", name="read_file", category=CapabilityCategory.FILESYSTEM)
    assert _memory_signals_for_target(None, _FakeTarget(), [frame], []) == {}


def test_memory_signals_empty_when_no_matching_rows():
    from app.services.capability_service import _memory_signals_for_target

    frame = CapabilityFrame(capability_id="cap-1", name="read_file", category=CapabilityCategory.FILESYSTEM)
    db = _FakeDB([_FakeMemoryRow("jailbreak_specialist", success=1.0)])
    signals = _memory_signals_for_target(db, _FakeTarget(), [frame], [])
    # jailbreak isn't in FILESYSTEM's mapped specialists (data_exfiltration/tool_abuse), so no signal
    assert "cap-1" not in signals


# ---------- coordinated multi-specialist vector resolution (spec section 19) ----------

def test_resolve_specialists_prefers_plural_list():
    from app.agents.orchestrator import _resolve_specialists

    vector = {"specialist": "tool_abuse_specialist", "specialists": ["tool_abuse_specialist", "data_exfiltration_specialist"]}
    assert _resolve_specialists(vector) == ["tool_abuse_specialist", "data_exfiltration_specialist"]


def test_resolve_specialists_falls_back_to_singular():
    from app.agents.orchestrator import _resolve_specialists

    assert _resolve_specialists({"specialist": "jailbreak_specialist"}) == ["jailbreak_specialist"]


def test_resolve_specialists_drops_unknown_keys_without_crashing():
    from app.agents.orchestrator import _resolve_specialists

    vector = {"specialists": ["tool_abuse_specialist", "made_up_specialist"]}
    assert _resolve_specialists(vector) == ["tool_abuse_specialist"]


def test_resolve_specialists_empty_when_nothing_valid():
    from app.agents.orchestrator import _resolve_specialists

    assert _resolve_specialists({"specialists": ["nonexistent"]}) == []
    assert _resolve_specialists({}) == []
