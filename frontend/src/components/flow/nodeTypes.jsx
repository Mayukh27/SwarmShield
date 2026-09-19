import { Handle, Position } from "reactflow";

const AGENT_LABEL = {
  prompt_injection_specialist: "Prompt Injection",
  jailbreak_specialist: "Jailbreak",
  tool_abuse_specialist: "Tool Abuse",
  data_exfiltration_specialist: "Data Exfil",
  privilege_escalation_specialist: "Privilege Esc.",
};

/**
 * AttackNode: a single attempt in the lineage. Amber + scanning sweep while
 * the Sentinel hasn't ruled yet is not representable statically (we only
 * get nodes once persisted), so state is derived from `succeeded`:
 *   - true  -> solid critical-red "confirmed" chip with glow
 *   - false -> dim cyan "cleared" chip (Sentinel found no violation)
 * This keeps red meaningful: it only ever means a proven vulnerability.
 */
export function AttackNode({ data }) {
  const { agentType, generation, succeeded, owaspCategory } = data;
  const hit = succeeded === true;

  return (
    <div
      className={`w-[200px] rounded-md border px-3 py-2.5 font-mono text-[11px] transition-shadow ${
        hit
          ? "border-critical bg-critical-dim shadow-glow-critical"
          : "border-grid bg-panel-raised shadow-glow-cyan"
      }`}
    >
      <Handle type="target" position={Position.Left} className="!bg-grid !border-0" />
      <div className="flex items-center justify-between">
        <span className={`font-display text-[10px] font-semibold tracking-wider ${hit ? "text-critical" : "text-cyan"}`}>
          GEN {generation}
        </span>
        {hit && <span className="h-1.5 w-1.5 rounded-full bg-critical" />}
      </div>
      <div className="mt-1 text-text-primary">{AGENT_LABEL[agentType] || agentType}</div>
      <div className="mt-1 truncate text-text-muted">{owaspCategory}</div>
      <div className={`mt-1.5 text-[10px] font-medium ${hit ? "text-critical" : "text-text-muted"}`}>
        {hit ? "VIOLATION CONFIRMED" : "no violation"}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-grid !border-0" />
    </div>
  );
}

/**
 * RootNode: the vector's starting point, sourced from the Planner's plan
 * rather than an AttackLog row. Anchors each lineage lane on the left.
 */
export function RootNode({ data }) {
  return (
    <div className="w-[180px] rounded-md border border-amber/40 bg-amber-dim px-3 py-2.5 font-mono text-[11px]">
      <div className="font-display text-[10px] font-semibold tracking-wider text-amber">
        VECTOR
      </div>
      <div className="mt-1 text-text-primary">{data.vectorId}</div>
      <div className="mt-1 truncate text-text-muted">{data.priority} priority</div>
      <Handle type="source" position={Position.Right} className="!bg-grid !border-0" />
    </div>
  );
}

export const nodeTypes = {
  attackNode: AttackNode,
  rootNode: RootNode,
};
