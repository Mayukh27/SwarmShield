import { useScanStore } from "../store/scanStore";

const SEVERITY_COLOR = {
  critical: "bg-critical",
  high: "bg-critical/70",
  medium: "bg-amber",
  low: "bg-cyan",
};

export default function RiskBreakdownPanel() {
  const activeScan = useScanStore((s) => s.activeScan);
  const breakdown = activeScan?.risk_breakdown;

  if (!breakdown || !breakdown.vulnerability_count) {
    const allFixed = breakdown?.fixed_count > 0;
    return (
      <div className="rounded-2xl border border-grid/80 bg-panel/70 p-4 text-sm text-text-muted backdrop-blur-xl">
        {allFixed ? (
          <span className="text-cyan">
            ✓ All {breakdown.fixed_count} confirmed finding{breakdown.fixed_count === 1 ? "" : "s"} re-validated as fixed. Risk score: 0/100.
          </span>
        ) : (
          "Risk breakdown appears once the scan completes and findings are scored (severity + exposure weighted, not a flat attempt ratio)."
        )}
      </div>
    );
  }

  const bySeverity = breakdown.by_severity || {};
  const total = Object.values(bySeverity).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="rounded-2xl border border-grid/80 bg-panel/70 p-4 backdrop-blur-xl">
      <div className="font-display text-xs font-semibold tracking-widest text-text-muted">
        RISK BREAKDOWN
      </div>

      <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-panel-raised">
        {Object.entries(bySeverity).map(([sev, count]) => (
          <div
            key={sev}
            className={SEVERITY_COLOR[sev] || "bg-text-muted"}
            style={{ width: `${(count / total) * 100}%` }}
            title={`${sev}: ${count}`}
          />
        ))}
      </div>

      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[11px] text-text-muted">
        {Object.entries(bySeverity).map(([sev, count]) => (
          <span key={sev}>
            {sev}: {count}
          </span>
        ))}
      </div>

      <div className="mt-3 border-t border-grid pt-3">
        <div className="font-mono text-[11px] text-text-muted">by OWASP category</div>
        {Object.entries(breakdown.by_category || {}).map(([cat, score]) => (
          <div key={cat} className="mt-1 flex items-center justify-between text-xs">
            <span className="truncate text-text-primary">{cat}</span>
            <span className="ml-2 shrink-0 font-mono text-amber">{score}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
