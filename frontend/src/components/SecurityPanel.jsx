import { useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, { Background, MarkerType } from "reactflow";
import "reactflow/dist/style.css";
import { create } from "zustand";
import { useScanStore } from "../store/scanStore";

/**
 * A2A Security panel: the SwarmShield runtime gateway next to the autonomous red team.
 *
 *  - Live topology + feed: polled from the REAL gateway (via /api/shield/*), so it shows scan
 *    monitoring traffic, the security demo, and target-side blocks alike.
 *  - "Run Security Demo": opens /api/shield/demo/stream, the backend fires real attack scenarios
 *    at the gateway and streams each real 200/403/429 back as `security_event` (same SSE shape as
 *    the rest of the telemetry), which lands in scanStore and therefore also in the Battle Log.
 */

export const useShieldStore = create((set) => ({
  status: null, // /shield/status
  agents: [], // gateway agent registry
  events: [], // recent gateway decisions
  error: null,
  setShield: (patch) => set(patch),
}));

async function getJson(path) {
  const res = await fetch(`/api/shield${path}`);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

function useShieldPolling(intervalMs = 1500) {
  const setShield = useShieldStore((s) => s.setShield);
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      const [st, ag, ev] = await Promise.allSettled([
        getJson("/status"),
        getJson("/agents"),
        getJson("/events?limit=60"),
      ]);
      if (!alive) return;
      setShield({
        status: st.status === "fulfilled" ? st.value : null,
        agents: ag.status === "fulfilled" ? ag.value.agents || [] : [],
        events: ev.status === "fulfilled" ? (ev.value.events || []).filter((e) => e.type === "a2a_transfer") : [],
        error: st.status === "rejected" ? "SwarmShield gateway is not configured or unreachable" : null,
      });
    };
    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [intervalMs, setShield]);
}

const STATUS = {
  normal: { dot: "🟢", label: "NORMAL", color: "#34d399" },
  inspected: { dot: "🟡", label: "INSPECTED", color: "#facc15" },
  quarantined: { dot: "🔴", label: "QUARANTINED", color: "#ff5c5c" },
};

export function ShieldBadge({ status }) {
  const s = STATUS[status];
  if (!s) return null;
  return (
    <span title={`SwarmShield: ${s.label}`} className="ml-2 text-[10px]" style={{ color: s.color }}>
      {s.dot}
    </span>
  );
}

const httpColor = (code) => (code === 429 ? "#ff5c5c" : code === 403 ? "#ff5c5c" : "#34d399");

function buildGraph(agents, events) {
  const shown = agents.filter((a) => !a.agent_id.startsWith("tool:")).slice(0, 16);
  const ids = new Set(shown.map((a) => a.agent_id));
  const n = Math.max(shown.length, 1);
  const nodes = shown.map((a, i) => {
    const st = STATUS[a.status] || STATUS.normal;
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    return {
      id: a.agent_id,
      position: { x: 380 + Math.cos(angle) * 330, y: 170 + Math.sin(angle) * 150 },
      data: {
        label: (
          <div style={{ fontSize: 10, lineHeight: 1.3 }}>
            <div>
              {st.dot} {a.agent_id}
            </div>
            {a.status === "quarantined" && (
              <div style={{ color: st.color, fontWeight: 700 }}>QUARANTINED BY SWARMSHIELD</div>
            )}
          </div>
        ),
      },
      style: {
        background: "#0b0f14",
        color: "#e6edf3",
        border: `2px solid ${st.color}`,
        borderRadius: 10,
        padding: 6,
        boxShadow: a.status === "quarantined" ? "0 0 18px rgba(255,92,92,0.55)" : "none",
      },
    };
  });

  const last = new Map();
  for (const e of events) last.set(`${e.sender_id}>${e.receiver_id}`, e);
  const now = Date.now() / 1000;
  const edges = [];
  for (const [key, e] of last) {
    if (!ids.has(e.sender_id) || !ids.has(e.receiver_id)) continue;
    const bad = e.http_status >= 400;
    edges.push({
      id: key,
      source: e.sender_id,
      target: e.receiver_id,
      animated: now - e.ts < 8,
      label: bad ? String(e.http_status) : undefined,
      labelStyle: { fill: "#fff", fontSize: 10, fontWeight: 700 },
      labelBgStyle: { fill: bad ? "#ff5c5c" : "#34d399" },
      style: { stroke: bad ? "#ff5c5c" : e.verdict === "flag" ? "#facc15" : "#34d399", strokeWidth: bad ? 2.5 : 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: bad ? "#ff5c5c" : "#34d399" },
    });
  }
  return { nodes, edges };
}

let demoSource = null; // module-level so navigating between screens never kills a running demo

export default function SecurityPanel() {
  useShieldPolling();
  const { status, agents, events, error } = useShieldStore();
  const storeEvents = useScanStore((s) => s.events);
  const [running, setRunning] = useState(Boolean(demoSource));
  const [demoError, setDemoError] = useState(null);
  const mounted = useRef(true);
  useEffect(() => () => (mounted.current = false), []);

  const reachable = status?.gateway?.reachable;
  const graph = useMemo(() => buildGraph(agents, events), [agents, events]);

  // Latest demo run, taken from the shared telemetry store (real gateway responses).
  const demoRows = useMemo(() => {
    const start = storeEvents.map((e) => e.event_type).lastIndexOf("security_demo_started");
    if (start < 0) return { rows: [], done: null };
    const slice = storeEvents.slice(start + 1);
    return {
      rows: slice.filter((e) => e.event_type === "security_event" && e.data?.mode === "demo"),
      done: slice.find((e) => e.event_type === "security_demo_done") || null,
    };
  }, [storeEvents]);

  const runDemo = () => {
    if (demoSource) return;
    setDemoError(null);
    setRunning(true);
    const push = useScanStore.getState().pushEvent;
    const es = new EventSource("/api/shield/demo/stream");
    demoSource = es;
    const finish = () => {
      es.close();
      demoSource = null;
      if (mounted.current) setRunning(false);
    };
    for (const type of ["security_demo_started", "security_event", "security_demo_done", "security_demo_error"]) {
      es.addEventListener(type, (e) => {
        const data = JSON.parse(e.data);
        push({ ...data, event_type: type });
        if (type === "security_demo_error" && mounted.current) setDemoError(data.message);
        if (type === "security_demo_done" || type === "security_demo_error") finish();
      });
    }
    es.onerror = finish; // stream closes when the simulation ends; never auto-reconnect (would re-run it)
  };

  return (
    <div className="glass overflow-hidden rounded-2xl">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 p-5">
        <div>
          <h2 className="font-medium text-text-primary">A2A Runtime Security · SwarmShield Gateway</h2>
          <p className="mt-1 text-[11px] text-white/35">
            Agent-to-agent messages and tool calls are inspected by the gateway.{" "}
            <span style={{ color: STATUS.normal.color }}>🟢 normal</span> ·{" "}
            <span style={{ color: STATUS.inspected.color }}>🟡 inspected</span> ·{" "}
            <span style={{ color: STATUS.quarantined.color }}>🔴 blocked / quarantined</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] tracking-widest" style={{ color: reachable ? "#34d399" : "#ff5c5c" }}>
            {reachable ? "GATEWAY ONLINE" : "GATEWAY OFFLINE"}
          </span>
          <button
            onClick={runDemo}
            disabled={running || !reachable}
            className="rounded-lg border border-red-400/40 bg-red-500/10 px-4 py-2 text-xs font-semibold tracking-wide text-red-300 transition hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {running ? "Running simulation…" : "▶ Run Security Demo"}
          </button>
        </div>
      </div>

      {(error || demoError) && (
        <div className="border-b border-red-400/30 bg-red-500/10 px-5 py-2 text-[11px] text-red-300">⚠ {demoError || error}</div>
      )}

      <div className="grid gap-px bg-white/5 xl:grid-cols-3">
        <div className="h-[340px] bg-[#07090d] xl:col-span-2">
          {graph.nodes.length === 0 ? (
            <p className="p-5 text-xs text-white/35">
              No agent traffic yet. Start a red-team scan, or click “Run Security Demo”.
            </p>
          ) : (
            <ReactFlow nodes={graph.nodes} edges={graph.edges} fitView nodesDraggable={false} proOptions={{ hideAttribution: true }}>
              <Background color="#1c232c" gap={24} />
            </ReactFlow>
          )}
        </div>

        <div className="h-[340px] overflow-y-auto bg-[#07090d] p-4 font-mono text-[11px]">
          <p className="mb-2 text-[10px] tracking-widest text-white/30">LIVE GATEWAY DECISIONS</p>
          {events.length === 0 && <p className="text-white/30">Waiting for traffic…</p>}
          {[...events].reverse().slice(0, 30).map((e) => (
            <div key={e.event_id} className="mb-1.5 leading-snug">
              <span style={{ color: httpColor(e.http_status), fontWeight: 700 }}>{e.http_status}</span>{" "}
              <span className="text-white/70">
                {e.sender_id} → {e.receiver_id}
                {e.target_tool ? ` [${e.target_tool}]` : ""}
              </span>
              {e.http_status >= 400 && <div className="pl-6 text-red-300/80">{e.reason}</div>}
              {e.verdict === "flag" && <div className="pl-6 text-yellow-300/80">inspected: {e.reason}</div>}
            </div>
          ))}
        </div>
      </div>

      {demoRows.rows.length > 0 && (
        <div className="border-t border-white/10 p-5">
          <p className="mb-3 text-[10px] tracking-widest text-white/30">SECURITY DEMO · REAL GATEWAY RESPONSES</p>
          <div className="space-y-2">
            {demoRows.rows.map((e, i) => {
              const d = e.data;
              const color = d.http_status === 200 ? (d.ui_state === "inspected" ? "#facc15" : "#34d399") : "#ff5c5c";
              return (
                <div key={i} className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-[11px]">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded px-1.5 py-0.5 font-bold text-black" style={{ background: color }}>
                      {d.http_status}
                    </span>
                    <span className="text-white/80">{d.label}</span>
                    <span className="text-white/35">
                      {d.sender_id} → {d.receiver_id}
                      {d.target_tool ? ` [${d.target_tool}]` : ""}
                    </span>
                  </div>
                  {d.http_status !== 200 && <div className="mt-1 text-red-300/90">{d.reason}</div>}
                  {d.ui_state === "inspected" && <div className="mt-1 text-yellow-300/90">{d.reason} (risk {d.risk_score})</div>}
                  {d.rules?.length > 0 && d.http_status !== 200 && (
                    <div className="mt-1 text-white/40">rules: {d.rules.join(", ")}</div>
                  )}
                  {d.http_status === 429 && (
                    <div className="mt-1 text-white/50">
                      evidence: {d.gateway_evidence?.kind} · {d.gateway_evidence?.transfers} transfers · ~
                      {d.gateway_evidence?.est_tokens} tokens · cooldown {d.gateway_evidence?.cooldown_s}s
                    </div>
                  )}
                  {d.quarantined_agents?.length > 0 && (
                    <div className="mt-1 font-semibold text-red-400">🔴 QUARANTINED: {d.quarantined_agents.join(", ")}</div>
                  )}
                </div>
              );
            })}
          </div>
          {demoRows.done && (
            <p className="mt-3 text-[11px] text-emerald-300">
              ✓ {demoRows.done.data.blocked_403} blocked (403) · {demoRows.done.data.tripped_429} circuit-breaker trip (429) ·
              quarantined: {demoRows.done.data.quarantined_agents.join(", ") || "none"}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
