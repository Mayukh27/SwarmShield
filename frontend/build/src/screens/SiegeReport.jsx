import { useScanStore } from "../store/scanStore";
import VulnerabilityTable from "../components/VulnerabilityTable";
import RiskBreakdownPanel from "../components/RiskBreakdownPanel";
import { structureFor, SEVERITY_TONE } from "../theme/coc";

export default function SiegeReport({ onNavigate }) {
  const vulnerabilities = useScanStore((s) => s.vulnerabilities);
  const activeScan = useScanStore((s) => s.activeScan);

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-4 overflow-y-auto px-6 py-8 lg:px-8">
      <div>
        <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">SECURITY OPERATIONS</p>
        <h1 className="mt-1 text-xl font-semibold text-text-primary">Vulnerabilities</h1>
        <p className="mt-1 text-xs text-white/30">
          Every confirmed vulnerability from this scan — real findings, real evidence, real OWASP LLM
          Top-10 category.
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
          onClick={() => onNavigate("patches")}
          className="self-start rounded-lg bg-cyan-400 px-4 py-2 text-xs font-semibold text-black transition hover:bg-cyan-300"
        >
          Go to Patch Center
        </button>
      )}
    </div>
  );
}
