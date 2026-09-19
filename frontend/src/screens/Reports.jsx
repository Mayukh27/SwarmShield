import { useMemo, useState } from "react";
import { useScanStore } from "../store/scanStore";
import { integrityFromRisk } from "../theme/coc";

const FILTERS = [
  { id: "all", label: "ALL" },
  { id: "agent_action", label: "ATTACK" },
  { id: "sentinel_verdict", label: "SENTINEL" },
  { id: "vulnerability_found", label: "FINDINGS" },
  { id: "memory_consulted", label: "MEMORY" },
  { id: "dna_mutation", label: "DNA" },
  { id: "scan_status", label: "SYSTEM" },
];

function matchesFilter(event, filterId) {
  if (filterId === "all") return true;
  return event.event_type === filterId;
}

export default function Reports() {
  const events = useScanStore((s) => s.events);
  const activeScan = useScanStore((s) => s.activeScan);
  const vulnerabilities = useScanStore((s) => s.vulnerabilities);
  const [filter, setFilter] = useState("all");

  const filtered = useMemo(() => events.filter((e) => matchesFilter(e, filter)), [events, filter]);
  const VISIBLE_LIMIT = 300;
  const hiddenCount = Math.max(0, filtered.length - VISIBLE_LIMIT);
  const visible = filtered.slice(hiddenCount);

  const integrity = integrityFromRisk(activeScan?.risk_score);
  const fixedCount = activeScan?.risk_breakdown?.fixed_count ?? 0;

  return (
    <div className="mx-auto flex h-full max-w-4xl flex-col gap-4 overflow-y-auto px-6 py-8 lg:px-8">
      <div>
        <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">SECURITY OPERATIONS</p>
        <h1 className="mt-1 text-xl font-semibold text-text-primary">Reports</h1>
        <p className="mt-1 text-xs text-white/30">
          {activeScan
            ? "Real scan summary and full event timeline for the current scan."
            : "No scan yet — start one from Targets to build a report."}
        </p>
      </div>

      {activeScan && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            ["Security Score", integrity !== null ? `${integrity}%` : "—"],
            ["Attack Attempts", activeScan.total_attempts ?? 0],
            ["Vulnerabilities", vulnerabilities.length],
            ["Fixed", fixedCount],
          ].map(([label, value]) => (
            <div key={label} className="glass flex flex-col items-center gap-1 rounded-2xl px-4 py-4">
              <span className="text-2xl font-bold text-text-primary">{value}</span>
              <span className="text-[10px] tracking-widest text-white/30">{label}</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`rounded-lg border px-2.5 py-1 text-[10px] font-medium transition-colors ${
              filter === f.id
                ? "border-amber-400/40 bg-amber-400/10 text-amber-300"
                : "border-white/10 bg-white/5 text-white/40 hover:text-white"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="glass scroll-thin flex-1 overflow-y-auto rounded-2xl">
        {filtered.length === 0 ? (
          <p className="p-6 text-xs text-white/25">No events yet for this filter.</p>
        ) : (
          <ol className="divide-y divide-white/5">
            {hiddenCount > 0 && (
              <li className="px-4 py-2 text-[10px] text-white/25">
                {hiddenCount} earlier {hiddenCount === 1 ? "entry" : "entries"} not shown.
              </li>
            )}
            {visible.map((e, i) => (
              <li key={hiddenCount + i} className="flex flex-wrap gap-2 px-4 py-2.5 text-xs sm:flex-nowrap sm:gap-3">
                <span className="shrink-0 text-[10px] text-white/25">
                  {new Date(e.timestamp).toLocaleTimeString("en-US", { hour12: false })}
                </span>
                <div className="min-w-0">
                  {e.agent_type && <span className="mr-2 text-[10px] text-cyan-300/60">{e.agent_type}</span>}
                  <span className="text-white/60">{e.message}</span>
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
