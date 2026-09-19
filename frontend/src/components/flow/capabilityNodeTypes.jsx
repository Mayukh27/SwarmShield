import { Handle, Position } from "reactflow";

// GraphNodeType (backend/app/capability/enums.py) -> visual treatment.
// Colors are decoration on top of the plain node_type label, never a
// replacement for it (kept consistent with theme/coc.js's rule).
const TYPE_STYLE = {
  agent: { icon: "🧙", tone: "border-amber/50 bg-amber-dim text-amber" },
  tool: { icon: "🔧", tone: "border-cyan/50 bg-cyan-dim text-cyan" },
  capability: { icon: "⚙️", tone: "border-gold/50 bg-gold-dim text-gold" },
  resource: { icon: "🗄️", tone: "border-hp/50 bg-hp-dim text-hp" },
  data: { icon: "📄", tone: "border-hp/50 bg-hp-dim text-hp" },
  role: { icon: "🎭", tone: "border-grid bg-panel-raised text-text-primary" },
  permission: { icon: "🔑", tone: "border-grid bg-panel-raised text-text-primary" },
  trust_boundary: { icon: "🚧", tone: "border-critical/50 bg-critical-dim text-critical" },
  external_endpoint: { icon: "🌐", tone: "border-critical/50 bg-critical-dim text-critical" },
  internal_endpoint: { icon: "🏠", tone: "border-grid bg-panel-raised text-text-primary" },
  other_agent: { icon: "🧙", tone: "border-amber/50 bg-amber-dim text-amber" },
};
const DEFAULT_STYLE = { icon: "❔", tone: "border-grid bg-panel-raised text-text-muted" };

export function CapabilityGraphNode({ data }) {
  const style = TYPE_STYLE[data.nodeType] || DEFAULT_STYLE;
  const highRisk = data.highRisk;
  return (
    <div
      className={`w-[190px] rounded-md border px-3 py-2 font-mono text-[11px] ${style.tone} ${
        highRisk ? "shadow-glow-critical" : ""
      }`}
    >
      <Handle type="target" position={Position.Left} className="!bg-grid !border-0" />
      <div className="flex items-center gap-1.5">
        <span>{style.icon}</span>
        <span className="text-[9px] uppercase tracking-wide opacity-70">{data.nodeType}</span>
      </div>
      <div className="mt-1 truncate text-text-primary">{data.label}</div>
      <Handle type="source" position={Position.Right} className="!bg-grid !border-0" />
    </div>
  );
}

export const capabilityGraphNodeTypes = { capabilityNode: CapabilityGraphNode };
