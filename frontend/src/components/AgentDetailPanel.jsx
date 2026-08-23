import { troopFor } from "../theme/coc";
import { useScanStore } from "../store/scanStore";

/**
 * Clicking a troop (specialist agent) on the battlefield opens this panel.
 * Shows the agent's most recent real AttackLog row — payload, target
 * response, Sentinel verdict, generation, lineage, outcome. No invented
 * activity: if the agent hasn't attempted anything yet, we say so.
 */
export default function AgentDetailPanel({ agentType, onClose }) {
  const attackLogs = useScanStore((s) => s.attackLogs);
  const t = troopFor(agentType);

  const logsForAgent = attackLogs
    .filter((l) => l.agent_type === agentType)
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  const latest = logsForAgent[0];
  const verdict = latest?.sentinel_verdict;

  return (
    <div className="absolute inset-y-0 right-0 z-20 flex w-full max-w-xs flex-col gap-3 overflow-y-auto border-l border-gold/30 bg-panel/95 p-3 backdrop-blur sm:w-72">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-display text-sm font-bold text-text-primary">{t.troop}</div>
          <div className="font-mono text-[10px] text-text-muted">{t.role}</div>
        </div>
        <button onClick={onClose} className="font-mono text-xs text-text-muted hover:text-text-primary">
          ✕
        </button>
      </div>

      <div className="rounded border border-grid bg-panel-raised px-2.5 py-1.5 font-mono text-[10px] text-text-muted">
        Attempts this siege: <span className="text-text-primary">{logsForAgent.length}</span>
      </div>

      {!latest ? (
        <p className="font-mono text-[11px] text-text-muted">NOT YET ATTACKED — standing by.</p>
      ) : (
        <div className="flex flex-col gap-2 font-mono text-[11px]">
          <div className="rounded border border-grid bg-panel px-2.5 py-2">
            <div className="mb-1 text-text-muted">Generation / lineage</div>
            <div className="text-text-primary">
              G{latest.generation}
              {latest.parent_attempt_id ? ` — mutated from a prior attempt` : " — root attempt"}
            </div>
          </div>

          <div className="rounded border border-grid bg-panel px-2.5 py-2">
            <div className="mb-1 text-text-muted">Target capability / category</div>
            <div className="text-text-primary">{latest.owasp_category || "—"}</div>
          </div>

          <div className="rounded border border-grid bg-panel px-2.5 py-2">
            <div className="mb-1 text-text-muted">Payload sent</div>
            <div className="max-h-24 overflow-y-auto whitespace-pre-wrap break-words text-text-primary">
              {latest.payload}
            </div>
          </div>

          {latest.target_response && (
            <div className="rounded border border-grid bg-panel px-2.5 py-2">
              <div className="mb-1 text-text-muted">Target response</div>
              <div className="max-h-24 overflow-y-auto whitespace-pre-wrap break-words text-text-primary">
                {latest.target_response}
              </div>
            </div>
          )}

          <div
            className={`rounded border px-2.5 py-2 ${
              latest.succeeded
                ? "border-critical/40 bg-critical-dim text-critical"
                : "border-hp/40 bg-hp-dim text-hp"
            }`}
          >
            <div className="mb-1 opacity-80">Sentinel result</div>
            <div className="font-semibold">{latest.succeeded ? "VIOLATION" : "BLOCKED / NO VIOLATION"}</div>
            {verdict?.confidence !== undefined && (
              <div className="mt-0.5 opacity-80">confidence {verdict.confidence}</div>
            )}
            {verdict?.mutation_hint && (
              <div className="mt-0.5 opacity-80">mutation hint: {verdict.mutation_hint}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
