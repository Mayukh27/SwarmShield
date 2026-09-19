import { useScanStore } from "../store/scanStore";

const STATUS_LABEL = {
  pending: "Queued",
  planning: "Planning",
  attacking: "Attacking",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

function riskTone(score) {
  if (score === null || score === undefined) return "text-text-muted";
  if (score >= 50) return "text-critical";
  if (score >= 20) return "text-amber";
  return "text-cyan";
}

export default function ScorecardCard() {
  const activeScan = useScanStore((s) => s.activeScan);
  const vulnerabilities = useScanStore((s) => s.vulnerabilities);

  const status = activeScan?.status;
  const risk = activeScan?.risk_score;

  return (
    <div className="rounded-lg border border-grid bg-panel p-4">
      <div className="font-display text-xs font-semibold tracking-widest text-text-muted">
        RISK SCORECARD
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className={`font-display text-4xl font-bold ${riskTone(risk)}`}>
          {risk !== null && risk !== undefined ? risk : "—"}
        </span>
        <span className="text-sm text-text-muted">/ 100</span>
      </div>

      <div className="mt-3 flex items-center gap-2 font-mono text-xs">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            status === "attacking" || status === "planning"
              ? "animate-pulseDot bg-amber"
              : status === "completed"
              ? "bg-cyan"
              : status === "failed"
              ? "bg-critical"
              : "bg-text-muted"
          }`}
        />
        <span className="text-text-muted">
          {activeScan ? STATUS_LABEL[status] || status : "No active scan"}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 border-t border-grid pt-3">
        <div>
          <div className="font-mono text-lg text-text-primary">
            {activeScan?.total_attempts ?? 0}
          </div>
          <div className="text-[11px] text-text-muted">attempts</div>
        </div>
        <div>
          <div className="font-mono text-lg text-critical">{vulnerabilities.length}</div>
          <div className="text-[11px] text-text-muted">confirmed findings</div>
        </div>
      </div>
    </div>
  );
}
