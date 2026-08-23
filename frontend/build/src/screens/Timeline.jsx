import { useMemo, useState } from "react";
import { useScanStore } from "../store/scanStore";

const FILTERS = [
  { id: "all", label: "ALL" },
  { id: "attack_action", label: "ATTACK" },
  { id: "sentinel_verdict", label: "SENTINEL" },
  { id: "vulnerability_found", label: "FINDINGS" },
  { id: "memory_consulted", label: "MEMORY" },
  { id: "dna_mutation", label: "DNA" },
  { id: "scan_status", label: "SYSTEM" },
];

const ICON = {
  scan_status: "🚩",
  agent_action: "⚔️",
  sentinel_verdict: "🛡️",
  vulnerability_found: "💥",
  memory_consulted: "🧠",
  dna_mutation: "🧬",
};

function matchesFilter(event, filterId) {
  if (filterId === "all") return true;
  if (filterId === "attack_action") return event.event_type === "agent_action";
  return event.event_type === filterId;
}

export default function Timeline() {
  const events = useScanStore((s) => s.events);
  const activeScan = useScanStore((s) => s.activeScan);
  const [filter, setFilter] = useState("all");

  const filtered = useMemo(() => events.filter((e) => matchesFilter(e, filter)), [events, filter]);

  // Same rendering cap as the Battle Log — avoid mounting hundreds of rows
  // at once (§30). The full set is still there; this only limits the DOM.
  const VISIBLE_LIMIT = 300;
  const hiddenCount = Math.max(0, filtered.length - VISIBLE_LIMIT);
  const visible = filtered.slice(hiddenCount);

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-4 overflow-hidden px-5 py-6">
      <div>
        <h1 className="font-display text-lg font-bold text-text-primary">📜 War Timeline</h1>
        <p className="font-mono text-[11px] text-text-muted">
          {activeScan
            ? "Chronological record of this siege, straight from the live event stream."
            : "No active or recently viewed siege — start one to build a timeline."}
        </p>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`rounded border px-2.5 py-1 font-mono text-[10px] font-medium transition-colors ${
              filter === f.id
                ? "border-gold/50 bg-gold-dim text-gold shadow-glow"
                : "border-grid/80 bg-panel/70 text-text-muted backdrop-blur-xl hover:text-text-primary"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto rounded-2xl border border-grid/80 bg-panel/70 backdrop-blur-xl scroll-thin">
        {filtered.length === 0 ? (
          <p className="p-4 font-mono text-[11px] text-text-muted">
            No events yet for this filter.
          </p>
        ) : (
          <ol className="divide-y divide-grid">
            {hiddenCount > 0 && (
              <li className="px-4 py-2 font-mono text-[10px] text-text-muted">
                {hiddenCount} earlier {hiddenCount === 1 ? "entry" : "entries"} not shown (scroll limit).
              </li>
            )}
            {visible.map((e, i) => (
              <li key={hiddenCount + i} className="flex flex-wrap gap-2 px-4 py-2.5 sm:flex-nowrap sm:gap-3">
                <span className="shrink-0 font-mono text-[10px] text-text-muted">
                  {new Date(e.timestamp).toLocaleTimeString("en-US", { hour12: false })}
                </span>
                <span className="shrink-0">{ICON[e.event_type] || "•"}</span>
                <div className="min-w-0">
                  {e.agent_type && (
                    <span className="mr-2 font-mono text-[10px] text-amber">{e.agent_type}</span>
                  )}
                  <span className="font-mono text-[12px] text-text-primary">{e.message}</span>
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
