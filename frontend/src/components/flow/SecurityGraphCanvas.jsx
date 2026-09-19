import { useMemo } from "react";
import ReactFlow, { Background, Controls, MarkerType } from "reactflow";
import "reactflow/dist/style.css";
import { securityNodeTypes } from "./securityNodeTypes";
import { AGENT_ROSTER } from "../../theme/roster";

const GATED_AGENT_TYPES = new Set([
  "prompt_injection_specialist",
  "jailbreak_specialist",
  "tool_abuse_specialist",
  "data_exfiltration_specialist",
  "privilege_escalation_specialist",
]);

const ROW_HEIGHT = 76;
const TARGET_X = 300;

const EDGE_COLOR = { normal: "#3A4552", inspected: "#f2b84b", quarantined: "#f87171" };

function buildGraph(agentStates) {
  const nodes = AGENT_ROSTER.map((agent, i) => ({
    id: agent.type,
    type: "securityAgentNode",
    position: { x: 0, y: i * ROW_HEIGHT },
    data: {
      name: agent.name,
      group: agent.group,
      state: agentStates[agent.type]?.state || "normal",
    },
  }));

  const quarantinedCount = AGENT_ROSTER.filter(
    (a) => GATED_AGENT_TYPES.has(a.type) && agentStates[a.type]?.state === "quarantined"
  ).length;

  nodes.push({
    id: "target-under-test",
    type: "securityTargetNode",
    position: { x: TARGET_X, y: (ROW_HEIGHT * (AGENT_ROSTER.length - 1)) / 2 },
    data: { label: "Target System", quarantinedCount },
  });

  const edges = AGENT_ROSTER.filter((a) => GATED_AGENT_TYPES.has(a.type)).map((agent) => {
    const state = agentStates[agent.type]?.state || "normal";
    const color = EDGE_COLOR[state];
    return {
      id: `e-${agent.type}-target`,
      source: agent.type,
      target: "target-under-test",
      animated: state !== "normal",
      style: {
        stroke: color,
        strokeWidth: state === "quarantined" ? 2.5 : state === "inspected" ? 2 : 1,
        strokeDasharray: state === "quarantined" ? "3 3" : undefined,
      },
      markerEnd: { type: MarkerType.ArrowClosed, color },
    };
  });

  return { nodes, edges };
}

export default function SecurityGraphCanvas({ agentStates }) {
  const { nodes, edges } = useMemo(() => buildGraph(agentStates), [agentStates]);

  return (
    <div className="h-[420px] overflow-hidden rounded-lg border border-grid bg-panel">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={securityNodeTypes}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.4}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background color="#1E2731" gap={24} size={1} />
        <Controls
          showInteractive={false}
          className="!bg-panel-raised !border-grid [&_button]:!bg-panel-raised [&_button]:!border-grid [&_button]:!fill-text-muted"
        />
      </ReactFlow>
    </div>
  );
}