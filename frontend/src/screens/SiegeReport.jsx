import { useScanStore } from "../store/scanStore";
import VulnerabilityTable from "../components/VulnerabilityTable";
import RiskBreakdownPanel from "../components/RiskBreakdownPanel";
import { structureFor, SEVERITY_TONE } from "../theme/coc";

export default function SiegeReport({ onNavigate }) {
  const vulnerabilities = useScanStore((s) => s.vulnerabilities);
  const activeScan = useScanStore((s) => s.activeScan);

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-4 overflow-y-auto px-5 py-6">
      <div>
        <h1 className="font-display text-lg font-bold text-text-primary">📜 Siege Report</h1>
        <p className="font-mono text-[11px] text-text-muted">
          Every confirmed vulnerability from this siege — real findings, real evidence,
          real OWASP LLM Top-10 category.
        </p>
      </div>

      <RiskBreakdownPanel />

      {vulnerabilities.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {vulnerabilities.map((v) => {
            const s = structureFor(v.owasp_category);
            const tone = SEVERITY_TONE[v.severity] || SEVERITY_TONE.medium;
            return (
              <span
                key={v.id}
                className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] ${tone.text}`}
                style={{ borderColor: "currentColor" }}
                title={v.owasp_category}
              >
                {s.icon} {s.structure}
              </span>
            );
          })}
        </div>
      )}

      {/* Real table, real expand/patch-generate flow — unchanged logic */}
      <VulnerabilityTable />

      {activeScan?.status === "completed" && vulnerabilities.length > 0 && (
        <button
          onClick={() => onNavigate("forge")}
          className="self-start rounded border border-gold/40 bg-gold-dim px-3 py-2 font-mono text-xs font-semibold text-gold hover:bg-gold/20"
        >
          🔨 Head to the Remediation Forge
        </button>
      )}
    </div>
  );
}
