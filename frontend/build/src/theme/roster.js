/**
 * The autonomous swarm's real roster — one entry per `agent_type` the
 * backend actually emits on the SSE stream (see AGENT_TO_TROOP in
 * theme/coc.js and hooks/useScanStream.js). Nothing here is placeholder
 * data: the roster is the fixed set of backend agent roles, and every
 * per-agent field shown on screen (status/current action) is derived at
 * render time from real `events` in the store, never hardcoded.
 */
export const AGENT_ROSTER = [
  { type: "capability_intelligence", name: "Recon Agent", group: "DISCOVERY" },
  { type: "planner", name: "Planning Agent", group: "DISCOVERY" },
  { type: "prompt_injection_specialist", name: "Prompt Injection Agent", group: "VALIDATION" },
  { type: "jailbreak_specialist", name: "Jailbreak Agent", group: "VALIDATION" },
  { type: "tool_abuse_specialist", name: "Tool Abuse Agent", group: "VALIDATION" },
  { type: "data_exfiltration_specialist", name: "Data Exfiltration Agent", group: "VALIDATION" },
  { type: "privilege_escalation_specialist", name: "Privilege Escalation Agent", group: "VALIDATION" },
  { type: "sentinel", name: "Vulnerability Agent", group: "ANALYSIS" },
];

/**
 * Derives each roster agent's live state purely from real data already in
 * the store: the most recent event of that agent_type (message + timestamp)
 * and whether the scan is currently running. No fabricated progress values.
 */
export function deriveAgentStates(events, scanInFlight, scanStatus) {
  const latestByType = new Map();
  for (const e of events) {
    if (e.agent_type) latestByType.set(e.agent_type, e);
  }

  return AGENT_ROSTER.map((agent) => {
    const latest = latestByType.get(agent.type);
    const recentlyActive =
      latest && Date.now() - new Date(latest.timestamp).getTime() < 60_000;
    const status = scanInFlight && recentlyActive ? "ACTIVE" : scanInFlight ? "STANDBY" : "IDLE";
    return {
      ...agent,
      status,
      currentAction: latest?.message || (scanStatus ? "Awaiting deployment" : "No scan running"),
      lastEventAt: latest?.timestamp || null,
    };
  });
}
