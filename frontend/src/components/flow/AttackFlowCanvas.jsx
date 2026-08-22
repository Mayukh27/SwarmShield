import { useMemo } from "react";
import ReactFlow, { Background, Controls, MarkerType } from "reactflow";
import "reactflow/dist/style.css";
import { nodeTypes } from "./nodeTypes";
import { useScanStore } from "../../store/scanStore";

const LANE_HEIGHT = 110;
const GEN_WIDTH = 240;
const ROOT_X = 40;

/**
 * Builds React Flow nodes/edges from the Planner's attack_plan (roots,
 * one per vector) plus the flat AttackLog list (which carries
 * parent_attempt_id -> a natural mutation lineage). Each vector gets its
 * own horizontal lane; generations flow left to right within a lane.
 */
function buildGraph(plan, attackLogs) {
  const vectors = plan?.vectors || [];
  const nodes = [];
  const edges = [];

  vectors.forEach((vector, laneIndex) => {
    const y = laneIndex * LANE_HEIGHT;

    nodes.push({
      id: `root-${vector.vector_id}`,
      type: "rootNode",
      position: { x: ROOT_X, y },
      data: { vectorId: vector.vector_id, priority: vector.priority },
    });

    const laneLogs = attackLogs
      .filter((l) => l.owasp_category === vector.owasp_category)
      .sort((a, b) => a.generation - b.generation);

    let prevNodeId = `root-${vector.vector_id}`;

    laneLogs.forEach((log) => {
      const nodeId = log.id;
      nodes.push({
        id: nodeId,
        type: "attackNode",
        position: { x: ROOT_X + 220 + log.generation * GEN_WIDTH, y },
        data: {
          agentType: log.agent_type,
          generation: log.generation,
          succeeded: log.succeeded,
          owaspCategory: log.owasp_category,
        },
      });

      edges.push({
        id: `e-${prevNodeId}-${nodeId}`,
        source: prevNodeId,
        target: nodeId,
        animated: !log.succeeded && laneLogs.at(-1)?.id !== log.id ? false : false,
        style: {
          stroke: log.succeeded ? "#FF5C5C" : "#1E2731",
          strokeWidth: log.succeeded ? 2 : 1.5,
          strokeDasharray: log.succeeded ? undefined : "4 3",
        },
        markerEnd: { type: MarkerType.ArrowClosed, color: log.succeeded ? "#FF5C5C" : "#3A4552" },
      });

      prevNodeId = nodeId;
    });
  });

  return { nodes, edges };
}

export default function AttackFlowCanvas() {
  const activeScan = useScanStore((s) => s.activeScan);
  const attackLogs = useScanStore((s) => s.attackLogs);

  const { nodes, edges } = useMemo(
    () => buildGraph(activeScan?.attack_plan, attackLogs),
    [activeScan?.attack_plan, attackLogs]
  );

  if (!activeScan?.attack_plan) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 rounded-lg border border-grid bg-panel text-text-muted">
        <span className="font-mono text-xs">NO ACTIVE SCAN</span>
        <span className="text-sm">Start a scan to watch the attack lineage build live.</span>
      </div>
    );
  }

  return (
    <div className="h-full overflow-hidden rounded-lg border border-grid bg-panel">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.4}
      >
        <Background color="#1E2731" gap={24} size={1} />
        <Controls className="!bg-panel-raised !border-grid [&_button]:!bg-panel-raised [&_button]:!border-grid [&_button]:!fill-text-muted" />
      </ReactFlow>
    </div>
  );
}
