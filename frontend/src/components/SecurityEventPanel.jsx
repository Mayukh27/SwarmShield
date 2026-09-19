import { SECURITY_EVENT_TYPES } from "../hooks/useAgentSecurityStates";

const EVENT_META = {
  security_blocked: { httpStatus: 403, label: "BLOCKED" },
  security_circuit_breaker: { httpStatus: 429, label: "CIRCUIT BREAKER" },
};

const AGENT_LABEL = {
  prompt_injection_specialist: "Prompt Injection Agent",
  jailbreak_specialist: "Jailbreak Agent",
  tool_abuse_specialist: "Tool Abuse Agent",
  data_exfiltration_specialist: "Data Exfiltration Agent",
  privilege_escalation_specialist: "Privilege Escalation Agent",
};

function EventRow({ event }) {
  const meta = EVENT_META[event.event_type] || { httpStatus: "—", label: event.event_type };
  const d = event.data || {};
  const time = new Date(event.timestamp).toLocaleTimeString("en-US", { hour12: false });

  return (
    <div className="px-4 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded border border-critical/40 bg-critical-dim px-1.5 py-0.5 font-mono text-[10px] uppercase text-critical">
          {meta.label}
        </span>
        <span className="rounded border border-grid bg-panel-raised px-1.5 py-0.5 font-mono text-[10px] text-text-muted">
          HTTP {meta.httpStatus}
        </span>
        <span className="ml-auto font-mono text-[10px] text-text-muted">{time}</span>
      </div>
      <div className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-0.5 font-mono text-[11px]">
        <div className="col-span-2 flex gap-2">
          <span className="shrink-0 text-text-muted">sender →</span>
          <span className="text-text-primary">{AGENT_LABEL[event.agent_type] || event.agent_type || "—"}</span>
          <span className="text-text-muted">receiver →</span>
          <span className="text-text-primary">Target System</span>
        </div>
        {d.violation_type && (
          <div className="col-span-2 flex gap-2">
            <span className="shrink-0 text-text-muted">violation:</span>
            <span className="text-text-primary">{d.violation_type}</span>
          </div>
        )}
        {typeof d.risk_score === "number" && (
          <div className="flex gap-2">
            <span className="text-text-muted">risk score:</span>
            <span className="text-text-primary">{d.risk_score}</span>
          </div>
        )}
        {typeof d.retry_after === "number" && (
          <div className="flex gap-2">
            <span className="text-text-muted">retry after:</span>
            <span className="text-text-primary">{d.retry_after}s</span>
          </div>
        )}
      </div>
      <p className="mt-1.5 text-sm text-text-primary">{event.message}</p>
    </div>
  );
}

export default function SecurityEventPanel({ events }) {
  const securityEvents = events.filter((e) => SECURITY_EVENT_TYPES.has(e.event_type)).slice(-30).reverse();

  return (
    <div className="rounded-lg border border-grid bg-panel">
      <div className="flex items-center justify-between border-b border-grid px-4 py-2.5">
        <span className="font-display text-xs font-semibold tracking-widest text-text-muted">
          SECURITY EVENTS
        </span>
        {securityEvents.length > 0 && (
          <span className="rounded border border-critical/40 bg-critical-dim px-1.5 py-0.5 font-mono text-[10px] text-critical">
            {securityEvents.length}
          </span>
        )}
      </div>
      <div className="max-h-64 overflow-y-auto divide-y divide-grid">
        {securityEvents.length === 0 ? (
          <p className="px-4 py-3 text-sm text-text-muted">
            No SwarmShield gateway blocks yet — a specialist that trips the injection
            scan, RBAC policy, or circuit breaker will show up here.
          </p>
        ) : (
          securityEvents.map((e, i) => <EventRow key={`${e.timestamp}-${i}`} event={e} />)
        )}
      </div>
    </div>
  );
}