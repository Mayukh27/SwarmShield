"""
Capability Intelligence entrypoint (spec sections 1-5): discovers what a
target CAN DO from declared_tools + permission_map + (optionally) runtime
tool-call observations from a scan's AttackLogs, and reconciles them into
a single set of CapabilityFrames, flagging anything observed at runtime
that wasn't declared.
"""
from app.capability.attack_paths import derive_attack_paths
from app.capability.classifier import classify_all
from app.capability.coverage import compute_coverage
from app.capability.extractor import extract_permission_map_frames, extract_tool_frames
from app.capability.fingerprint import compute_target_fingerprint
from app.capability.graph import build_capability_graph
from app.capability.hypotheses import generate_hypotheses
from app.capability.runtime import classify_observed, extract_observed_tool_frames, reconcile


def analyze_target_capabilities(target, attack_logs: list | None = None) -> dict:
    declared_result = extract_tool_frames(target.declared_tools)
    declared_names = {t.tool_name for t in declared_result.tool_frames}

    perm_result = extract_permission_map_frames(target.permission_map, existing_names=declared_names)

    warnings = list(declared_result.warnings) + list(perm_result.warnings)
    declared_frames = classify_all(declared_result.tool_frames + perm_result.tool_frames)

    observed_frames = []
    if attack_logs:
        observed_result = extract_observed_tool_frames(attack_logs)
        warnings += observed_result.warnings
        observed_frames = classify_observed(observed_result.tool_frames)

    merged = reconcile(declared_frames, observed_frames)
    graph = build_capability_graph(merged)
    attack_paths = derive_attack_paths(merged, graph)
    hypotheses = generate_hypotheses(merged, attack_paths)
    coverage = compute_coverage(merged, attack_paths, hypotheses, attack_logs)

    return {
        "capabilities": [f.to_dict() for f in merged],
        "warnings": warnings,
        "declared_count": sum(1 for f in merged if f.declared),
        "observed_count": sum(1 for f in merged if f.observed),
        "undeclared_observed_count": sum(1 for f in merged if f.status.value == "undeclared_observed"),
        "graph": graph.to_dict(),
        "attack_paths": [p.to_dict() for p in attack_paths],
        "hypotheses": [h.to_dict() for h in hypotheses],
        "coverage": coverage,
        "fingerprint": compute_target_fingerprint(target, merged),
    }


def summarize_hypotheses_for_planner(analysis: dict, limit: int = 8) -> list[dict]:
    """Compact projection handed to the existing Planner prompt as extra
    context -- title/objective/priority/specialists only, so the Planner
    can weigh dynamic hypotheses alongside its own reasoning without the
    prompt ballooning in size (spec: 'utilize the analysis to derive
    hypotheses ... existing Planner/Specialists' remain the executors)."""
    top = analysis.get("hypotheses", [])[:limit]
    return [
        {
            "title": h["title"],
            "objective": h["objective"],
            "priority": h["priority"],
            "required_specialists": h["required_specialists"],
            "reason": h["reason"],
        }
        for h in top
    ]
