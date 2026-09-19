import { useEffect, useMemo, useState } from "react";

const INSPECTED_MS = 5_000;
const QUARANTINED_MS = 12_000;

export const SECURITY_EVENT_TYPES = new Set(["security_blocked", "security_circuit_breaker"]);

export function useAgentSecurityStates(events) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  return useMemo(() => {
    const lastInspectedAt = new Map();
    const lastQuarantine = new Map();

    for (const e of events) {
      if (!e.agent_type) continue;
      const ts = new Date(e.timestamp).getTime();
      if (Number.isNaN(ts)) continue;

      if (e.event_type === "agent_action") {
        lastInspectedAt.set(e.agent_type, ts);
      } else if (SECURITY_EVENT_TYPES.has(e.event_type)) {
        const prev = lastQuarantine.get(e.agent_type);
        if (!prev || ts >= prev.ts) lastQuarantine.set(e.agent_type, { ts, event: e });
      }
    }

    const states = {};
    const allTypes = new Set([...lastInspectedAt.keys(), ...lastQuarantine.keys()]);
    for (const type of allTypes) {
      const quarantine = lastQuarantine.get(type);
      const inspectedAt = lastInspectedAt.get(type);

      if (quarantine && now - quarantine.ts < QUARANTINED_MS) {
        states[type] = { state: "quarantined", since: quarantine.ts, event: quarantine.event };
      } else if (inspectedAt && now - inspectedAt < INSPECTED_MS) {
        states[type] = { state: "inspected", since: inspectedAt, event: null };
      } else {
        states[type] = {
          state: "normal",
          since: Math.max(quarantine?.ts || 0, inspectedAt || 0) || null,
          event: null,
        };
      }
    }
    return states;
  }, [events, now]);
}