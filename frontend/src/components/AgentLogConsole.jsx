import { useEffect, useMemo, useRef, useState } from "react";
import { useScanStore } from "../store/scanStore";

const AGENT_COLOR = {
  planner: "text-amber",
  sentinel: "text-cyan",
  prompt_injection_specialist: "text-text-primary",
  jailbreak_specialist: "text-text-primary",
  tool_abuse_specialist: "text-text-primary",
  data_exfiltration_specialist: "text-text-primary",
  privilege_escalation_specialist: "text-text-primary",
  capability_intelligence: "text-gold",
};

const EVENT_PREFIX = {
  scan_status: "SYS",
  agent_action: "TX ",
  sentinel_verdict: "JDG",
  vulnerability_found: "HIT",
  memory_consulted: "MEM",
  dna_mutation: "DNA",
  strategy_skipped: "SKP",
  capability_scan_started: "CAP",
  capability_unknown_discovered: "UNK",
  capability_scan_completed: "CAP",
  capability_coverage_updated: "COV",
};

// Which event types carry real evidence worth expanding — everything else
// (agent_action, scan_status) is already fully expressed by its message.
const EXPANDABLE = new Set(["sentinel_verdict", "vulnerability_found", "dna_mutation", "memory_consulted"]);

function EvidenceRow({ label, value }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div className="flex gap-2">
      <span className="shrink-0 text-text-muted">{label}:</span>
      <span className="break-words text-text-primary">
        {typeof value === "object" ? JSON.stringify(value) : String(value)}
      </span>
    </div>
  );
}

function Evidence({ event, vulnerability }) {
  const d = event.data || {};
  if (event.event_type === "sentinel_verdict") {
    return (
      <div className="ml-16 mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 rounded border border-grid bg-void/60 px-3 py-2 font-mono text-[11px]">
        <EvidenceRow label="Violation detected" value={d.violation_detected} />
        <EvidenceRow label="Violation type" value={d.violation_type} />
        <EvidenceRow label="Confidence" value={d.confidence} />
        <EvidenceRow label="Mutation hint" value={d.mutation_hint} />
        {d.reasoning && (
          <div className="col-span-full">
            <span className="text-text-muted">Reasoning: </span>
            <span className="text-text-primary">{d.reasoning}</span>
          </div>
        )}
      </div>
    );
  }
  if (event.event_type === "vulnerability_found") {
    return (
      <div className="ml-16 mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 rounded border border-critical/30 bg-critical-dim/40 px-3 py-2 font-mono text-[11px]">
        {vulnerability ? (
          <>
            <EvidenceRow label="Title" value={vulnerability.title} />
            <EvidenceRow label="Category" value={vulnerability.owasp_category} />
            <EvidenceRow label="Severity" value={vulnerability.severity} />
            <EvidenceRow label="Status" value={vulnerability.status} />
          </>
        ) : (
          <span className="col-span-full text-text-muted">Finding record not loaded yet.</span>
        )}
      </div>
    );
  }
  if (event.event_type === "dna_mutation") {
    return (
      <div className="ml-16 mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 rounded border border-grid bg-void/60 px-3 py-2 font-mono text-[11px]">
        <EvidenceRow label="Vector" value={d.vector_id} />
        <EvidenceRow label="Generation" value={d.generation} />
        <EvidenceRow label="Mutation" value={d.mutation} />
      </div>
    );
  }
  if (event.event_type === "memory_consulted") {
    return (
      <div className="ml-16 mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 rounded border border-grid bg-void/60 px-3 py-2 font-mono text-[11px]">
        <EvidenceRow label="Strategy" value={d.strategy} />
        <EvidenceRow label="Confidence" value={d.confidence} />
        <EvidenceRow label="Used" value={d.used} />
      </div>
    );
  }
  return null;
}

function Line({ event, vulnerability, expanded, onToggle }) {
  const agentColor = AGENT_COLOR[event.agent_type] || "text-text-muted";
  const isHit = event.event_type === "vulnerability_found";
  const canExpand = EXPANDABLE.has(event.event_type);
  const time = new Date(event.timestamp).toLocaleTimeString("en-US", { hour12: false });

  return (
    <div className={isHit ? "-mx-2 rounded bg-critical-dim/40 px-2" : ""}>
      <div
        onClick={canExpand ? onToggle : undefined}
        className={`flex gap-3 py-0.5 leading-relaxed ${canExpand ? "cursor-pointer hover:opacity-80" : ""}`}
      >
        <span className="shrink-0 text-text-muted">{time}</span>
        <span className={`shrink-0 font-medium ${isHit ? "text-critical" : "text-text-muted"}`}>
          [{EVENT_PREFIX[event.event_type] || "???"}]
        </span>
        {event.agent_type && <span className={`shrink-0 ${agentColor}`}>{event.agent_type}</span>}
        <span className={isHit ? "text-critical" : "text-text-primary"}>{event.message}</span>
        {canExpand && <span className="ml-auto shrink-0 text-text-muted">{expanded ? "▲" : "▼"}</span>}
      </div>
      {canExpand && expanded && <Evidence event={event} vulnerability={vulnerability} />}
    </div>
  );
}

export default function AgentLogConsole() {
  const events = useScanStore((s) => s.events);
  const vulnerabilities = useScanStore((s) => s.vulnerabilities);
  const bottomRef = useRef(null);
  const [expandedIdx, setExpandedIdx] = useState(null);

  const vulnById = useMemo(() => {
    const m = new Map();
    vulnerabilities.forEach((v) => m.set(v.id, v));
    return m;
  }, [vulnerabilities]);

  // Cap what actually mounts in the DOM — the store already caps to 500,
  // but rendering all 500 rows on every tick is unnecessary work once the
  // console is this deep. The most recent 200 stay live; expandedIdx is a
  // raw store index so it still resolves correctly regardless of the slice.
  const VISIBLE_LIMIT = 200;
  const visibleStart = Math.max(0, events.length - VISIBLE_LIMIT);
  const visibleEvents = useMemo(() => events.slice(visibleStart), [events, visibleStart]);

  useEffect(() => {
    if (expandedIdx === null) bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length, expandedIdx]);

  return (
    <div className="flex h-full flex-col rounded-lg border border-grid bg-panel">
      <div className="flex items-center justify-between border-b border-grid px-4 py-2.5">
        <span className="font-display text-xs font-semibold tracking-widest text-text-muted">BATTLE LOG</span>
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-cyan" />
          <span className="font-mono text-[11px] text-text-muted">streaming</span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-3 font-mono text-[13px]">
        {events.length === 0 ? (
          <p className="text-text-muted">
            Waiting for the swarm to begin. Start a scan to see agents work in real time.
          </p>
        ) : (
          <>
            {visibleStart > 0 && (
              <p className="pb-1 text-[10px] text-text-muted">
                {visibleStart} earlier {visibleStart === 1 ? "entry" : "entries"} not shown — see War Log for
                the full timeline.
              </p>
            )}
            {visibleEvents.map((e, i) => {
              const idx = visibleStart + i;
              return (
                <Line
                  key={idx}
                  event={e}
                  vulnerability={e.data?.vulnerability_id ? vulnById.get(e.data.vulnerability_id) : undefined}
                  expanded={expandedIdx === idx}
                  onToggle={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
                />
              );
            })}
          </>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
