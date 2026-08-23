"""
Capability Intelligence entrypoint (spec sections 1-5): discovers what a
target CAN DO from declared_tools + permission_map + (optionally) runtime
tool-call observations from a scan's AttackLogs, and reconciles them into
a single set of CapabilityFrames, flagging anything observed at runtime
that wasn't declared.

Phase 6 adds the two pieces Phase 5 flagged as still missing:
  - persistent memory actually informs hypothesis prioritization (spec
    section 25), not just fingerprint computation with nothing consuming it
  - a bounded number of the highest-priority hypotheses get RAG-sourced
    security context attached (spec section 26)

Both are optional and best-effort: `db` is an optional parameter, and any
failure reaching memory/RAG degrades to "no historical signal" / "no RAG
context" rather than failing the whole analysis (spec section 37).
"""
from __future__ import annotations

from app.capability.attack_paths import derive_attack_paths
from app.capability.classifier import classify_all
from app.capability.coverage import compute_coverage
from app.capability.extractor import extract_permission_map_frames, extract_tool_frames
from app.capability.fingerprint import compute_target_fingerprint
from app.capability.graph import build_capability_graph
from app.capability.hypotheses import CATEGORY_SPECIALISTS, generate_hypotheses
from app.capability.prioritizer import MemorySignal
from app.capability.runtime import classify_observed, extract_observed_tool_frames, reconcile
from app.core.config import settings


def _disabled_result(reason: str) -> dict:
    """Spec section 20/37: if Capability Intelligence is unavailable or
    disabled, the rest of the scan must still work. Callers check
    `enabled` before treating this as a real analysis."""
    return {
        "enabled": False,
        "reason": reason,
        "capabilities": [], "warnings": [reason], "declared_count": 0, "observed_count": 0,
        "undeclared_observed_count": 0, "graph": {"nodes": [], "edges": []}, "attack_paths": [],
        "hypotheses": [], "coverage": {}, "fingerprint": {},
    }


def _memory_signals_for_target(db, target, frames, attack_paths) -> dict[str, MemorySignal]:
    """Spec section 25: before generating hypotheses, retrieve relevant
    previous experience for this target and let it inform prioritization.
    Joins on the same `target_fingerprint` key the adaptive attack loop
    already writes (str(target.id) -- see orchestrator.py), which is a
    more reliable join than the capability-set hash for "have we tested
    this exact target before", since the hash shifts whenever the tool
    surface changes even slightly between scans.
    """
    if db is None or not settings.MEMORY_ENABLED:
        return {}
    try:
        from app.models.agent_memory import AgentMemory

        rows = (
            db.query(AgentMemory)
            .filter(AgentMemory.target_fingerprint == str(target.id))
            .limit(max(1, settings.CAPABILITY_MEMORY_LOOKBACK) * 20)
            .all()
        )
    except Exception:
        return {}
    if not rows:
        return {}

    by_namespace: dict[str, list] = {}
    for row in rows:
        by_namespace.setdefault(row.namespace, []).append(row)

    signals: dict[str, MemorySignal] = {}
    for frame in frames:
        specialists = CATEGORY_SPECIALISTS.get(frame.category, [])
        matches = []
        for spec in specialists:
            matches.extend(by_namespace.get(f"{spec.value}_specialist", []))
        if not matches:
            continue
        matches = matches[: settings.CAPABILITY_MEMORY_LOOKBACK]
        successes = sum(1 for m in matches if m.success == 1.0)
        failures = sum(1 for m in matches if m.success == 0.0)
        signals[frame.capability_id] = MemorySignal(
            previous_attempts=len(matches), prior_success_count=successes,
            prior_failure_count=failures, novel=False,
        )

    for path in attack_paths:
        involved_categories = {f.category for f in frames if f.capability_id in path.capability_ids}
        matches = []
        for cat in involved_categories:
            for spec in CATEGORY_SPECIALISTS.get(cat, []):
                matches.extend(by_namespace.get(f"{spec.value}_specialist", []))
        if not matches:
            continue
        matches = matches[: settings.CAPABILITY_MEMORY_LOOKBACK]
        successes = sum(1 for m in matches if m.success == 1.0)
        failures = sum(1 for m in matches if m.success == 0.0)
        signals[f"path:{path.path_id}"] = MemorySignal(
            previous_attempts=len(matches), prior_success_count=successes,
            prior_failure_count=failures, novel=False,
        )

    return signals


def _enrich_top_hypotheses_with_rag(db, hypotheses: list) -> None:
    """Spec section 26: for each high-value hypothesis, retrieve relevant
    security knowledge. Bounded to the top CAPABILITY_RAG_ENRICH_TOP_K
    hypotheses (already priority-sorted by the caller) so this never turns
    into an unbounded per-capability RAG sweep (spec section 38). Mutates
    the hypothesis objects in place; best-effort, never raises."""
    if db is None or not settings.RAG_ENABLED or not hypotheses:
        return
    try:
        from app.services import rag_service
    except Exception:
        return

    for h in hypotheses[: max(0, settings.CAPABILITY_RAG_ENRICH_TOP_K)]:
        try:
            query = f"{h.attack_surface} {h.security_property} {h.objective}"[:300]
            results = rag_service.search(db, query, limit=3)
        except Exception:
            continue
        if not results:
            continue
        titles = [r["title"] for r in results if r.get("title")]
        if titles:
            h.context_sources = list(dict.fromkeys(list(h.context_sources) + [f"rag:{t}" for t in titles]))
            h.evidence = list(h.evidence) + [f"Related security guidance on file: {t}" for t in titles[:2]]


def analyze_target_capabilities(target, attack_logs: list | None = None, db=None) -> dict:
    if not settings.CAPABILITY_INTELLIGENCE_ENABLED:
        return _disabled_result("Capability Intelligence is disabled (CAPABILITY_INTELLIGENCE_ENABLED=false).")

    declared_result = extract_tool_frames(target.declared_tools)
    declared_names = {t.tool_name for t in declared_result.tool_frames}

    perm_result = extract_permission_map_frames(target.permission_map, existing_names=declared_names)

    warnings = list(declared_result.warnings) + list(perm_result.warnings)
    declared_frames = classify_all(declared_result.tool_frames + perm_result.tool_frames)

    observed_frames = []
    if attack_logs and settings.CAPABILITY_RUNTIME_OBSERVATION:
        observed_result = extract_observed_tool_frames(attack_logs)
        warnings += observed_result.warnings
        observed_frames = classify_observed(observed_result.tool_frames)

    merged = reconcile(declared_frames, observed_frames)
    graph = build_capability_graph(merged)
    attack_paths = derive_attack_paths(merged, graph, max_paths=settings.CAPABILITY_MAX_PATHS)
    fingerprint = compute_target_fingerprint(target, merged)

    memory_signals = _memory_signals_for_target(db, target, merged, attack_paths)
    hypotheses = generate_hypotheses(
        merged, attack_paths,
        max_hypotheses=settings.CAPABILITY_MAX_HYPOTHESES,
        target_fingerprint=fingerprint.get("fingerprint", ""),
        memory_signals=memory_signals,
    )
    _enrich_top_hypotheses_with_rag(db, hypotheses)

    coverage = compute_coverage(merged, attack_paths, hypotheses, attack_logs)

    return {
        "enabled": True,
        "capabilities": [f.to_dict() for f in merged],
        "warnings": warnings,
        "declared_count": sum(1 for f in merged if f.declared),
        "observed_count": sum(1 for f in merged if f.observed),
        "undeclared_observed_count": sum(1 for f in merged if f.status.value == "undeclared_observed"),
        "graph": graph.to_dict(),
        "attack_paths": [p.to_dict() for p in attack_paths],
        "hypotheses": [h.to_dict() for h in hypotheses],
        "coverage": coverage,
        "fingerprint": fingerprint,
        "memory_informed_count": sum(1 for v in memory_signals.values() if not v.novel),
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
