import { useState } from "react";
import { useScanStore } from "../store/scanStore";

const PRIORITY_TONE = {
  critical: "text-critical bg-critical-dim border-critical/50",
  high: "text-critical bg-critical-dim border-critical/40",
  medium: "text-gold bg-gold-dim border-gold/40",
  low: "text-cyan bg-cyan-dim border-cyan/40",
};

/**
 * The Planner's own attack_plan is already on activeScan (see
 * backend/app/agents/orchestrator.py — set once at scan start), so this
 * is zero extra network calls: purely a new lens on data already in the
 * store. Represents the Planner as the strategic commander (spec §12)
 * without inventing anything it didn't actually output.
 */
export default function BattlePlanPanel() {
  const activeScan = useScanStore((s) => s.activeScan);
  const attackLogs = useScanStore((s) => s.attackLogs);
  const [expanded, setExpanded] = useState(false);

  const plan = activeScan?.attack_plan;
  const vectors = plan?.vectors || [];

  return (
    <div className="rounded-lg border border-grid bg-panel">
      <div className="border-b border-grid px-4 py-2.5 font-display text-xs font-semibold tracking-widest text-text-muted">
        BATTLE PLAN
      </div>
      {!plan ? (
        <p className="px-4 py-3 text-sm text-text-muted">
          The Scout hasn't reported a plan yet — this fills in once the Planner Agent finishes mapping the
          attack surface.
        </p>
      ) : (
        <div className="px-4 py-3">
          {plan.attack_surface_summary && (
            <p className="mb-2 text-sm text-text-primary">{plan.attack_surface_summary}</p>
          )}
          <p className="font-mono text-[11px] text-text-muted">
            {vectors.length} vector{vectors.length === 1 ? "" : "s"} planned
          </p>

          <div className="mt-2 flex flex-col gap-1.5">
            {vectors.map((v) => {
              const testedCount = attackLogs.filter(
                (l) => l.owasp_category === v.owasp_category
              ).length;
              return (
                <div key={v.vector_id} className="rounded border border-grid bg-panel-raised px-2.5 py-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-mono text-[11px] text-text-primary">{v.vector_id}</span>
                    <span
                      className={`shrink-0 rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase ${
                        PRIORITY_TONE[v.priority] || PRIORITY_TONE.medium
                      }`}
                    >
                      {v.priority}
                    </span>
                  </div>
                  <div className="mt-0.5 font-mono text-[10px] text-text-muted">
                    {v.specialist} · {v.owasp_category} · {testedCount} attempt{testedCount === 1 ? "" : "s"}
                  </div>
                  {expanded && v.rationale && (
                    <p className="mt-1 text-[11px] text-text-muted">{v.rationale}</p>
                  )}
                </div>
              );
            })}
          </div>

          {vectors.some((v) => v.rationale) && (
            <button
              onClick={() => setExpanded((e) => !e)}
              className="mt-2 font-mono text-[10px] text-cyan hover:underline"
            >
              {expanded ? "Hide reasoning" : "Show reasoning per vector"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
