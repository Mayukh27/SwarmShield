"""
Attack path derivation (spec: sequences of capabilities an attacker could
chain to reach a sensitive outcome). Deterministic graph walk over
CAN_CHAIN/CROSSES_BOUNDARY edges -- no LLM call.
"""
from __future__ import annotations

from app.capability.enums import GraphEdgeType
from app.capability.models import AttackPath, CapabilityFrame, CapabilityGraph

_HIGH_SENSITIVITY = {"pii", "credentials", "secrets", "financial", "health", "source_code", "system_config"}


def derive_attack_paths(frames: list[CapabilityFrame], graph: CapabilityGraph, max_paths: int = 15) -> list[AttackPath]:
    by_tool_name = {f.name: f for f in frames}
    chain_edges = [e for e in graph.edges if e.edge_type == GraphEdgeType.CAN_CHAIN]

    paths: list[AttackPath] = []
    seen_pairs: set[tuple[str, str]] = set()

    # Single-capability paths: anything that alone crosses a trust boundary
    # and touches sensitive data or is destructive is worth flagging on its own.
    for f in frames:
        if f.trust_boundary and (f.data_sensitivity.value in _HIGH_SENSITIVITY or f.destructive.value in ("possible", "likely")):
            paths.append(AttackPath(
                capability_ids=[f.capability_id],
                operations=[f.operation],
                crosses_trust_boundary=True,
                description=f"Direct access: {f.name} ({f.operation.value}) touches {f.data_sensitivity.value} data with no chaining required.",
                risk_score=f.risk_score,
            ))

    # Two-hop chains: tool A shares a resource with tool B, and together
    # they cross into higher-sensitivity or external-effect territory.
    for edge in chain_edges:
        src_name = edge.source_id.removeprefix("tool:")
        dst_name = edge.target_id.removeprefix("tool:")
        pair = tuple(sorted((src_name, dst_name)))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        src, dst = by_tool_name.get(src_name), by_tool_name.get(dst_name)
        if not src or not dst:
            continue

        crosses = src.trust_boundary or dst.trust_boundary
        combined_risk = round(min(100.0, (src.risk_score + dst.risk_score) * 0.6), 1)
        if not crosses and combined_risk < 40:
            continue  # not interesting enough to report as a chained path

        paths.append(AttackPath(
            capability_ids=[src.capability_id, dst.capability_id],
            operations=[src.operation, dst.operation],
            crosses_trust_boundary=crosses,
            description=f"Chain: {src.name} ({src.operation.value}) -> {dst.name} ({dst.operation.value}), sharing a resource.",
            risk_score=combined_risk,
        ))

    paths.sort(key=lambda p: p.risk_score, reverse=True)
    return paths[:max_paths]
