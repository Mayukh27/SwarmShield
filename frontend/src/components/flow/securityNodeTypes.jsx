import { Handle, Position } from "reactflow";

const STATE_STYLE = {
  normal: { dot: "🟢", tone: "border-hp/40 bg-hp-dim text-hp", label: "Normal" },
  inspected: { dot: "🟡", tone: "border-amber/60 bg-amber-dim text-amber", label: "Inspected" },
  quarantined: {
    dot: "🔴",
    tone: "border-critical bg-critical-dim text-critical shadow-glow-critical",
    label: "Quarantined",
  },
};

export function SecurityAgentNode({ data }) {
  const style = STATE_STYLE[data.state] || STATE_STYLE.normal;
  const pulsing = data.state !== "normal";

  return (
    <div className={`w-[178px] rounded-md border px-3 py-2 font-mono text-[11px] transition-colors ${style.tone}`}>
      <Handle type="source" position={Position.Right} className="!bg-grid !border-0" />
      <div className="flex items-center justify-between">
        <span className="truncate text-[10px] uppercase tracking-wide opacity-70">{data.group}</span>
        <span className={pulsing ? "animate-pulseDot" : ""}>{style.dot}</span>
      </div>
      <div className="mt-1 truncate text-text-primary">{data.name}</div>
      <div className="mt-1 text-[10px] font-medium">{style.label}</div>
    </div>
  );
}

export function SecurityTargetNode({ data }) {
  return (
    <div className="w-[168px] rounded-md border border-grid bg-panel-raised px-3 py-2 font-mono text-[11px]">
      <Handle type="target" position={Position.Left} className="!bg-grid !border-0" />
      <div className="text-[10px] uppercase tracking-wide text-text-muted">Under test</div>
      <div className="mt-1 truncate text-text-primary">{data.label}</div>
      {typeof data.quarantinedCount === "number" && data.quarantinedCount > 0 && (
        <div className="mt-1 text-[10px] font-medium text-critical">
          {data.quarantinedCount} quarantined edge{data.quarantinedCount === 1 ? "" : "s"}
        </div>
      )}
    </div>
  );
}

export const securityNodeTypes = {
  securityAgentNode: SecurityAgentNode,
  securityTargetNode: SecurityTargetNode,
};