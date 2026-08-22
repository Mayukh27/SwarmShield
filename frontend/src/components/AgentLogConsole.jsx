import { useEffect, useRef } from "react";
import { useScanStore } from "../store/scanStore";

const AGENT_COLOR = {
  planner: "text-amber",
  sentinel: "text-cyan",
  prompt_injection_specialist: "text-text-primary",
  jailbreak_specialist: "text-text-primary",
  tool_abuse_specialist: "text-text-primary",
  data_exfiltration_specialist: "text-text-primary",
  privilege_escalation_specialist: "text-text-primary",
};

const EVENT_PREFIX = {
  scan_status: "SYS",
  agent_action: "TX ",
  sentinel_verdict: "JDG",
  vulnerability_found: "HIT",
};

function Line({ event }) {
  const agentColor = AGENT_COLOR[event.agent_type] || "text-text-muted";
  const isHit = event.event_type === "vulnerability_found";
  const time = new Date(event.timestamp).toLocaleTimeString("en-US", { hour12: false });

  return (
    <div
      className={`flex gap-3 py-0.5 leading-relaxed ${
        isHit ? "bg-critical-dim/40 -mx-2 px-2 rounded" : ""
      }`}
    >
      <span className="text-text-muted shrink-0">{time}</span>
      <span
        className={`shrink-0 font-medium ${
          isHit ? "text-critical" : "text-text-muted"
        }`}
      >
        [{EVENT_PREFIX[event.event_type] || "???"}]
      </span>
      {event.agent_type && (
        <span className={`shrink-0 ${agentColor}`}>{event.agent_type}</span>
      )}
      <span className={isHit ? "text-critical" : "text-text-primary"}>
        {event.message}
      </span>
    </div>
  );
}

export default function AgentLogConsole() {
  const events = useScanStore((s) => s.events);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length]);

  return (
    <div className="flex h-full flex-col rounded-lg border border-grid bg-panel">
      <div className="flex items-center justify-between border-b border-grid px-4 py-2.5">
        <span className="font-display text-xs font-semibold tracking-widest text-text-muted">
          LIVE CONSOLE
        </span>
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
          events.map((e, i) => <Line key={i} event={e} />)
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
