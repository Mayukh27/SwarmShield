import { useState } from "react";
import { useScanStore } from "../store/scanStore";
import { api } from "../lib/api";
import { splitPolicyViolation } from "../lib/policy";
import PatchSuggestionPanel from "../components/PatchSuggestionPanel";
import { structureFor, SEVERITY_TONE } from "../theme/coc";

const STATUS_BADGE = {
  open: { label: "Open breach", tone: "text-critical bg-critical-dim border-critical/40" },
  remediation_suggested: { label: "Patch drafted", tone: "text-gold bg-gold-dim border-gold/40" },
  revalidation_passed: { label: "Ward repaired ✓", tone: "text-hp bg-hp-dim border-hp/40" },
  revalidation_failed: { label: "Still vulnerable", tone: "text-critical bg-critical-dim border-critical/40" },
};

export default function RemediationForge() {
  const vulnerabilities = useScanStore((s) => s.vulnerabilities);
  const activeScan = useScanStore((s) => s.activeScan);
  const targets = useScanStore((s) => s.targets);
  const selectedTargetId = useScanStore((s) => s.selectedTargetId);
  const target = targets.find((t) => t.id === selectedTargetId);
  const [patchesByVuln, setPatchesByVuln] = useState({});
  const [loadingId, setLoadingId] = useState(null);
  const [expanded, setExpanded] = useState(null);

  const handleGeneratePatch = async (vulnId) => {
    setLoadingId(vulnId);
    setExpanded(vulnId);
    try {
      const patch = await api.generatePatch(vulnId);
      setPatchesByVuln((prev) => ({ ...prev, [vulnId]: [patch, ...(prev[vulnId] || [])] }));
    } catch (e) {
      console.error("Patch generation failed", e);
    } finally {
      setLoadingId(null);
    }
  };

  if (vulnerabilities.length === 0) {
    return (
      <div className="mx-auto flex h-full max-w-3xl items-center justify-center px-6">
        <p className="glass rounded-2xl p-8 text-center text-xs text-white/30">
          No confirmed vulnerabilities yet to remediate. Run a scan first.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-4 overflow-y-auto px-6 py-8 lg:px-8">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">SECURITY OPERATIONS</p>
            <h1 className="mt-1 text-xl font-semibold text-text-primary">Patch Center</h1>
            <p className="mt-1 text-xs text-white/30">
              Generate a real AI-drafted fix per finding, then route it by code access:
              public PR, private PR/branch, or read-only PDF suggestion.
            </p>
          </div>
          {activeScan?.id && (
            <a
              href={api.scanReportPdfUrl(activeScan.id)}
              className="shrink-0 rounded-lg border border-cyan-400/30 bg-cyan-400/5 px-3 py-1.5 text-xs font-medium text-cyan-300 transition hover:bg-cyan-400/10"
            >
              Download report PDF
            </a>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {vulnerabilities.map((v) => {
          const s = structureFor(v.owasp_category);
          const badge = STATUS_BADGE[v.status] || STATUS_BADGE.open;
          const tone = SEVERITY_TONE[v.severity] || SEVERITY_TONE.medium;
          const isOpen = expanded === v.id;
          return (
            <div key={v.id} className="glass overflow-hidden rounded-2xl">
              <button
                onClick={() => setExpanded(isOpen ? null : v.id)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-panel-raised"
              >
                <span className="text-xl">{s.icon}</span>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-display text-sm font-semibold text-text-primary">
                    {v.title}
                  </div>
                  <div className={`font-mono text-[10px] ${tone.text}`}>
                    {s.structure} &middot; {tone.label} severity
                  </div>
                </div>
                <span className={`shrink-0 rounded border px-2 py-0.5 font-mono text-[10px] ${badge.tone}`}>
                  {badge.label}
                </span>
              </button>

              {isOpen && (
                <div className="border-t border-grid bg-void/40 px-4 py-3">
                  {(() => {
                    const { policyLine, rest } = splitPolicyViolation(v.description);
                    return (
                      <>
                        {policyLine && (
                          <p className="rounded border border-gold/30 bg-gold-dim px-2.5 py-1.5 text-sm font-medium text-gold">
                            {policyLine}
                          </p>
                        )}
                        {rest && <p className="mt-2 text-sm text-text-primary">{rest}</p>}
                      </>
                    );
                  })()}
                  {v.evidence && (
                    <pre className="mt-2 overflow-x-auto rounded border border-grid bg-panel-raised p-2.5 font-mono text-[11px] text-text-muted">
                      {v.evidence}
                    </pre>
                  )}

                  <button
                    onClick={() => handleGeneratePatch(v.id)}
                    disabled={loadingId === v.id}
                    className="mt-3 rounded-xl border border-gold/40 bg-gold-dim px-3 py-1.5 font-mono text-xs font-medium text-gold transition-colors hover:bg-gold/20 hover:shadow-glow disabled:opacity-50"
                  >
                    {loadingId === v.id ? "Forging patch…" : "🔨 Forge a remediation patch"}
                  </button>

                  {(patchesByVuln[v.id] || []).map((patch) => (
                    <PatchSuggestionPanel key={patch.id} patch={patch} vulnerabilityId={v.id} target={target} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
