"""
Attack path derivation (spec: sequences of capabilities an attacker could
chain to reach a sensitive outcome). Deterministic graph walk over
CAN_CHAIN/CROSSES_BOUNDARY edges -- no LLM call.

Spec section 15 explicitly calls out 3+ hop chains as first-class attack
paths ("SEARCH -> READ -> SEND forms an exfiltration path"), so beyond the
pairwise 2-hop logic below, `_walk_multi_hop` does a bounded-depth DFS over
the same CAN_CHAIN adjacency to surface longer chains a purely-pairwise
scan would miss. Depth is capped by settings.CAPABILITY_MAX_DEPTH so this
stays a bounded search over a small graph, not a combinatorial blow-up
(spec section 38: "do not generate thousands of brute-force combinations").
"""
from __future__ import annotations

from app.capability.enums import GraphEdgeType
from app.capability.models import AttackPath, CapabilityFrame, CapabilityGraph
from app.core.config import settings

_HIGH_SENSITIVITY = {"pii", "credentials", "secrets", "financial", "health", "source_code", "system_config"}


def _walk_multi_hop(
    by_tool_name: dict[str, CapabilityFrame],
    adjacency: dict[str, list[str]],
    max_depth: int,
    max_results: int,
) -> list[AttackPath]:
    """DFS from every tool node, following CAN_CHAIN edges, collecting
    simple paths (no repeated node) of length 3..max_depth hops. Only
    chains where the combined path is actually interesting -- crosses a
    trust boundary somewhere along the way, or accumulates enough risk --
    are kept, same bar as the 2-hop logic below."""
    results: list[AttackPath] = []
    seen_sequences: set[tuple[str, ...]] = set()

    def dfs(path: list[str], visited: set[str]):
        if len(results) >= max_results:
            return
        if len(path) >= 3:
            seq = tuple(path)
            if seq not in seen_sequences:
                seen_sequences.add(seq)
                nodes = [by_tool_name[n] for n in path]
                crosses = any(n.trust_boundary for n in nodes)
                combined_risk = round(min(100.0, sum(n.risk_score for n in nodes) / len(nodes) * 0.85), 1)
                if crosses or combined_risk >= 45:
                    results.append(AttackPath(
                        capability_ids=[n.capability_id for n in nodes],
                        operations=[n.operation for n in nodes],
                        crosses_trust_boundary=crosses,
                        description=f"{len(nodes)}-hop chain: " + " -> ".join(f"{n.name} ({n.operation.value})" for n in nodes),
                        risk_score=combined_risk,
                    ))
        if len(path) >= max_depth:
            return
        for neighbor in adjacency.get(path[-1], []):
            if neighbor in visited or neighbor not in by_tool_name:
                continue
            visited.add(neighbor)
            path.append(neighbor)
            dfs(path, visited)
            path.pop()
            visited.remove(neighbor)

    for start in by_tool_name:
        if len(results) >= max_results:
            break
        dfs([start], {start})

    results.sort(key=lambda p: p.risk_score, reverse=True)
    return results[:max_results]


def derive_attack_paths(frames: list[CapabilityFrame], graph: CapabilityGraph, max_paths: int | None = None) -> list[AttackPath]:
    max_paths = max_paths if max_paths is not None else settings.CAPABILITY_MAX_PATHS
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

    # Multi-hop (3+) chains: build a directed adjacency from the same
    # CAN_CHAIN edges and walk it bounded by CAPABILITY_MAX_DEPTH, to
    # surface chains like SEARCH -> READ -> SEND that the pairwise pass
    # above can't express (spec section 15).
    if len(by_tool_name) >= 3 and settings.CAPABILITY_MAX_DEPTH > 2:
        adjacency: dict[str, list[str]] = {}
        for edge in chain_edges:
            src_name = edge.source_id.removeprefix("tool:")
            dst_name = edge.target_id.removeprefix("tool:")
            adjacency.setdefault(src_name, []).append(dst_name)
            adjacency.setdefault(dst_name, []).append(src_name)  # resource-sharing is symmetric for traversal purposes
        remaining = max(0, max_paths - len(paths))
        if remaining:
            paths.extend(_walk_multi_hop(by_tool_name, adjacency, settings.CAPABILITY_MAX_DEPTH, remaining))

    paths.sort(key=lambda p: p.risk_score, reverse=True)
    return paths[:max_paths]
