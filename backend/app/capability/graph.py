"""
CapabilityGraph builder (spec: capability -> tool -> resource -> trust
boundary relationships). Deterministic, built directly from classified
CapabilityFrames -- no LLM call.
"""
from __future__ import annotations

from app.capability.enums import GraphEdgeType, GraphNodeType, ResourceType
from app.capability.models import CapabilityFrame, CapabilityGraph, GraphEdge, GraphNode

_OP_EDGE: dict[str, GraphEdgeType] = {
    "read": GraphEdgeType.CAN_READ, "read_file": GraphEdgeType.CAN_READ,
    "read_database": GraphEdgeType.CAN_READ, "read_secret": GraphEdgeType.CAN_READ,
    "write": GraphEdgeType.CAN_WRITE, "write_file": GraphEdgeType.CAN_WRITE,
    "write_database": GraphEdgeType.CAN_WRITE,
    "delete": GraphEdgeType.CAN_DELETE, "delete_file": GraphEdgeType.CAN_DELETE,
    "delete_database": GraphEdgeType.CAN_DELETE,
}


def build_capability_graph(frames: list[CapabilityFrame]) -> CapabilityGraph:
    graph = CapabilityGraph()
    graph.nodes.append(GraphNode(node_id="agent:target", node_type=GraphNodeType.AGENT, label="Target Agent"))

    resource_nodes: dict[str, str] = {}
    role_nodes: dict[str, str] = {}

    for f in frames:
        tool_id = f"tool:{f.name}"
        graph.nodes.append(GraphNode(node_id=tool_id, node_type=GraphNodeType.TOOL, label=f.display_name or f.name,
                                      metadata={"capability_id": f.capability_id, "status": f.status.value if f.status else None}))
        graph.edges.append(GraphEdge("agent:target", tool_id, GraphEdgeType.CAN_CALL))

        cap_id = f"capability:{f.capability_id}"
        graph.nodes.append(GraphNode(node_id=cap_id, node_type=GraphNodeType.CAPABILITY, label=f.operation.value,
                                      metadata={"category": f.category.value, "risk_score": f.risk_score}))
        graph.edges.append(GraphEdge(tool_id, cap_id, GraphEdgeType.CAN_TRIGGER))

        for res in f.resources:
            res_key = res.value
            res_id = resource_nodes.setdefault(res_key, f"resource:{res_key}")
            if res_id not in {n.node_id for n in graph.nodes}:
                graph.nodes.append(GraphNode(node_id=res_id, node_type=GraphNodeType.RESOURCE, label=res_key))
            edge_type = _OP_EDGE.get(f.operation.value, GraphEdgeType.CAN_ACCESS)
            graph.edges.append(GraphEdge(tool_id, res_id, edge_type))

        if f.required_role:
            role_id = role_nodes.setdefault(f.required_role, f"role:{f.required_role}")
            if role_id not in {n.node_id for n in graph.nodes}:
                graph.nodes.append(GraphNode(node_id=role_id, node_type=GraphNodeType.ROLE, label=f.required_role))
            graph.edges.append(GraphEdge(tool_id, role_id, GraphEdgeType.REQUIRES_ROLE))

        if f.trust_boundary:
            boundary_id = "trust_boundary:external"
            if boundary_id not in {n.node_id for n in graph.nodes}:
                graph.nodes.append(GraphNode(node_id=boundary_id, node_type=GraphNodeType.TRUST_BOUNDARY, label="Trust Boundary"))
            graph.edges.append(GraphEdge(tool_id, boundary_id, GraphEdgeType.CROSSES_BOUNDARY))

    # Chain edges: tools that touch the same resource can plausibly be
    # composed by an attacker (read here, exfiltrate there).
    by_resource: dict[str, list[str]] = {}
    for f in frames:
        for res in f.resources:
            by_resource.setdefault(res.value, []).append(f"tool:{f.name}")
    for tool_ids in by_resource.values():
        for i, src in enumerate(tool_ids):
            for dst in tool_ids[i + 1:]:
                if src != dst:
                    graph.edges.append(GraphEdge(src, dst, GraphEdgeType.CAN_CHAIN))

    return graph
