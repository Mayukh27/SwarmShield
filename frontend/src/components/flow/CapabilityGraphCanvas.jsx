import { useMemo } from "react";
import ReactFlow, { Background, Controls, MarkerType } from "reactflow";
import "reactflow/dist/style.css";
import { capabilityGraphNodeTypes } from "./capabilityNodeTypes";

// Column order: roughly trust-in to trust-out, matching spec §9's edge
// vocabulary (agent -> tool/capability -> resource, crossing trust
// boundaries toward external endpoints).
const COLUMN_ORDER = [
  "agent",
  "other_agent",
  "role",
  "permission",
  "tool",
  "capability",
  "trust_boundary",
  "resource",
  "data",
  "internal_endpoint",
  "external_endpoint",
];
const COL_WIDTH = 230;
const ROW_HEIGHT = 90;

const HIGH_RISK_EDGE_TYPES = new Set(["crosses_boundary", "can_delete", "can_execute"]);

function layout(graph) {
  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const byColumn = {};
  nodes.forEach((n) => {
    const col = COLUMN_ORDER.includes(n.type) ? COLUMN_ORDER.indexOf(n.type) : COLUMN_ORDER.length;
    byColumn[col] = byColumn[col] || [];
    byColumn[col].push(n);
  });

  const rfNodes = [];
  Object.entries(byColumn).forEach(([col, colNodes]) => {
    colNodes.forEach((n, row) => {
      rfNodes.push({
        id: n.id,
        type: "capabilityNode",
        position: { x: Number(col) * COL_WIDTH, y: row * ROW_HEIGHT },
        data: { label: n.label, nodeType: n.type, highRisk: n.metadata?.risk_score > 70 },
      });
    });
  });

  const rfEdges = edges.map((e, i) => {
    const risky = HIGH_RISK_EDGE_TYPES.has(e.type);
    return {
      id: `e${i}-${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      label: e.type,
      labelStyle: { fill: "#8A97A6", fontSize: 9, fontFamily: "monospace" },
      style: {
        stroke: risky ? "#FF5C5C" : "#3A4552",
        strokeWidth: risky ? 2 : 1,
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: risky ? "#FF5C5C" : "#3A4552" },
    };
  });

  return { nodes: rfNodes, edges: rfEdges };
}

export default function CapabilityGraphCanvas({ graph }) {
  const { nodes, edges } = useMemo(() => layout(graph), [graph]);

  if (!graph || nodes.length === 0) {
    return (
      <div className="flex h-72 flex-col items-center justify-center gap-1 rounded-lg border border-grid bg-panel text-text-muted">
        <span className="font-mono text-xs">NOT YET AVAILABLE</span>
        <span className="text-[11px]">No capability graph for this target yet.</span>
      </div>
    );
  }

  return (
    <div className="h-96 overflow-hidden rounded-lg border border-grid bg-panel">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={capabilityGraphNodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
      >
        <Background color="#1E2731" gap={24} size={1} />
        <Controls className="!bg-panel-raised !border-grid [&_button]:!bg-panel-raised [&_button]:!border-grid [&_button]:!fill-text-muted" />
      </ReactFlow>
    </div>
  );
}
