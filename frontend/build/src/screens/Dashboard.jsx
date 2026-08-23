import { useMemo } from "react";
import { useScanStore } from "../store/scanStore";
import { integrityFromRisk } from "../theme/coc";
import { deriveAgentStates } from "../theme/roster";

function severityStyle(severity) {
  if (severity === "critical") return "border-red-400/20 bg-red-400/5 text-red-400";
  if (severity === "high") return "border-orange-400/20 bg-orange-400/5 text-orange-400";
  return "border-yellow-400/20 bg-yellow-400/5 text-yellow-400";
}

function targetStatus(target, activeScan, integrity) {
  const isActiveTarget = activeScan && target.id === activeScan.target_id;
  if (isActiveTarget && integrity !== null) {
    if (integrity < 50) return { label: "CRITICAL", tone: "text-red-400", score: integrity };
    if (integrity < 80) return { label: "WARNING", tone: "text-yellow-400", score: integrity };
    return { label: "HEALTHY", tone: "text-emerald-400", score: integrity };
  }
  return { label: target.authorized ? "IDLE" : "UNAUTHORIZED", tone: "text-white/30", score: null };
}

function eventLevel(event) {
  if (event.event_type === "vulnerability_found") return "CRITICAL";
  if (event.event_type === "sentinel_verdict" && event.data?.violation_detected) return "WARNING";
  if (event.event_type === "scan_status" && (event.data?.status === "completed")) return "SUCCESS";
  return "INFO";
}

export default function Dashboard({ onNavigate, onDeclareWar, scanInFlight }) {
  const targets = useScanStore((s) => s.targets);
  const selectedTargetId = useScanStore((s) => s.selectedTargetId);
  const activeScan = useScanStore((s) => s.activeScan);
  const vulnerabilities = useScanStore((s) => s.vulnerabilities);
  const events = useScanStore((s) => s.events);

  const integrity = integrityFromRisk(activeScan?.risk_score);
  const agents = useMemo(
    () => deriveAgentStates(events, scanInFlight, activeScan?.status),
    [events, scanInFlight, activeScan?.status]
  );
  const activeAgentCount = agents.filter((a) => a.status === "ACTIVE").length;
  const criticalCount = vulnerabilities.filter((v) => v.severity === "critical").length;
  const byCategory = activeScan?.risk_breakdown?.by_category || {};

  const recentEvents = events.slice(-8).reverse();

  return (
    <div className="min-h-full">
      <div className="p-6 lg:p-8">
        {/* WELCOME */}
        <section className="glass-cyan relative mb-6 overflow-hidden rounded-2xl p-6">
          <div className="pointer-events-none absolute -right-20 -top-20 h-48 w-48 rounded-full bg-cyan-400/10 blur-3xl" />
          <div className="relative flex flex-col justify-between gap-5 md:flex-row md:items-center">
            <div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.8)]" />
                <span className="text-[10px] tracking-[0.25em] text-cyan-300">
                  {scanInFlight ? "AUTONOMOUS SECURITY ACTIVE — SCAN RUNNING" : "AUTONOMOUS SECURITY ACTIVE"}
                </span>
              </div>
              <h2 className="mt-3 text-2xl font-semibold text-text-primary">
                Your infrastructure is being protected.
              </h2>
              <p className="mt-2 max-w-2xl text-sm text-white/35">
                Autonomous AI agents are continuously discovering, validating, and analyzing
                security threats across your connected infrastructure.
              </p>
            </div>
            <button
              onClick={() => onNavigate("agents")}
              className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-white transition hover:bg-white/10"
            >
              View Live Activity
            </button>
          </div>
        </section>

        {/* KPI CARDS — every value pulled from the store, no mock numbers */}
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {[
            ["Security Score", integrity !== null ? `${integrity}` : "—", integrity !== null ? (integrity >= 80 ? "GOOD" : integrity >= 50 ? "FAIR" : "POOR") : "NO SCAN"],
            ["Active Agents", String(activeAgentCount).padStart(2, "0"), scanInFlight ? "RUNNING" : "IDLE"],
            ["Targets", String(targets.length).padStart(2, "0"), "MONITORED"],
            ["Vulnerabilities", String(vulnerabilities.length), "DETECTED"],
            ["Critical", String(criticalCount), "ACTION"],
          ].map(([title, value, label]) => (
            <div key={title} className="group glass glass-hover rounded-2xl p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs text-white/40">{title}</p>
                <span className="text-[8px] tracking-[0.2em] text-white/20">{label}</span>
              </div>
              <div className="mt-5 flex items-end justify-between">
                <p className="text-3xl font-semibold text-text-primary">{value}</p>
              </div>
            </div>
          ))}
        </section>

        {/* AGENTS + SCORE */}
        <section className="mt-6 grid gap-6 xl:grid-cols-3">
          {/* AGENT SWARM */}
          <div className="glass overflow-hidden rounded-2xl xl:col-span-2">
            <div className="flex items-center justify-between border-b border-white/10 p-5">
              <div>
                <h2 className="font-medium text-text-primary">Autonomous Agent Swarm</h2>
                <p className="mt-1 text-xs text-white/30">Live intelligence across your security network</p>
              </div>
              <span className="flex items-center gap-2 text-[9px] tracking-widest text-emerald-400">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                LIVE
              </span>
            </div>

            <div className="grid gap-px bg-white/5 md:grid-cols-2">
              {agents.map((agent) => (
                <button
                  key={agent.type}
                  onClick={() => onNavigate("agents")}
                  className="group bg-[#07090d] p-5 text-left transition hover:bg-white/[0.025]"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-cyan-400/20 bg-cyan-400/5 text-cyan-300">
                        ◈
                      </div>
                      <div>
                        <p className="text-sm font-medium text-text-primary">{agent.name}</p>
                        <p className="text-[9px] tracking-widest text-white/25">{agent.group}</p>
                      </div>
                    </div>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[9px] tracking-widest ${
                        agent.status === "ACTIVE"
                          ? "border-emerald-400/30 text-emerald-400"
                          : agent.status === "STANDBY"
                          ? "border-yellow-400/30 text-yellow-400"
                          : "border-white/10 text-white/25"
                      }`}
                    >
                      {agent.status}
                    </span>
                  </div>

                  <div className="mt-4 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2">
                    <p className="text-[9px] tracking-widest text-white/20">CURRENT ACTION</p>
                    <p className="mt-1 truncate text-xs text-white/60">{agent.currentAction}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* SECURITY SCORE GAUGE */}
          <div className="glass-dark relative overflow-hidden rounded-2xl p-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[10px] tracking-[0.2em] text-white/30">SECURITY SCORE</p>
                <p className="mt-0.5 text-[9px] text-white/20">GLOBAL INFRASTRUCTURE HEALTH</p>
              </div>
            </div>

            <div className="relative mx-auto mt-6 flex h-48 w-48 items-center justify-center">
              <svg viewBox="0 0 200 200" className="h-full w-full -rotate-90">
                <circle cx="100" cy="100" r="88" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
                <circle
                  cx="100"
                  cy="100"
                  r="88"
                  fill="none"
                  stroke="#22d3ee"
                  strokeWidth="10"
                  strokeLinecap="round"
                  strokeDasharray={2 * Math.PI * 88}
                  strokeDashoffset={2 * Math.PI * 88 * (1 - (integrity ?? 0) / 100)}
                  style={{ transition: "stroke-dashoffset 0.6s ease" }}
                />
              </svg>
              <div className="absolute flex flex-col items-center">
                <span className="text-4xl font-bold text-text-primary">
                  {integrity !== null ? integrity : "—"}
                </span>
                <span className="mt-1 text-[10px] tracking-widest text-white/30">
                  {integrity !== null ? (integrity >= 80 ? "GOOD" : integrity >= 50 ? "FAIR" : "POOR") : "NO SCAN YET"}
                </span>
              </div>
            </div>

            <div className="mt-6 space-y-3">
              {Object.keys(byCategory).length === 0 ? (
                <p className="text-center text-[10px] text-white/25">
                  Category breakdown appears once a scan completes.
                </p>
              ) : (
                Object.entries(byCategory).map(([name, score]) => (
                  <div key={name}>
                    <div className="mb-2 flex justify-between text-xs">
                      <span className="truncate text-white/35">{name}</span>
                      <span className="text-white/70">{score}</span>
                    </div>
                    <div className="h-1 rounded-full bg-white/5">
                      <div
                        className="h-full rounded-full bg-cyan-400/70"
                        style={{ width: `${Math.min(100, score)}%` }}
                      />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        {/* TARGETS */}
        <section className="glass mt-6 rounded-2xl">
          <div className="flex items-center justify-between border-b border-white/10 p-5">
            <div>
              <h2 className="font-medium text-text-primary">Monitored Targets</h2>
              <p className="mt-1 text-xs text-white/30">Infrastructure currently protected by the swarm</p>
            </div>
            <button
              onClick={() => onNavigate("targets")}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white transition hover:bg-white/10"
            >
              Manage Targets
            </button>
          </div>

          {targets.length === 0 ? (
            <p className="p-8 text-center text-xs text-white/25">
              No targets registered yet. Add one from the Targets page to begin.
            </p>
          ) : (
            <div className="grid gap-px bg-white/5 md:grid-cols-3">
              {targets.map((target) => {
                const status = targetStatus(target, activeScan, integrity);
                return (
                  <button
                    key={target.id}
                    onClick={() => onNavigate("targets")}
                    className="bg-[#07090d] p-5 text-left transition hover:bg-white/[0.025]"
                  >
                    <div className="flex items-start justify-between">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-text-primary">{target.name}</p>
                        <p className="mt-1 truncate text-[10px] text-white/25">{target.endpoint_url}</p>
                      </div>
                      <span className={`shrink-0 text-[9px] tracking-widest ${status.tone}`}>{status.label}</span>
                    </div>

                    <div className="mt-6">
                      <div className="mb-2 flex justify-between text-[9px]">
                        <span className="text-white/20">SECURITY SCORE</span>
                        <span>{status.score !== null ? `${status.score}%` : "—"}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-white/5">
                        <div
                          className={`h-full rounded-full ${
                            status.label === "HEALTHY"
                              ? "bg-emerald-400"
                              : status.label === "WARNING"
                              ? "bg-yellow-400"
                              : status.label === "CRITICAL"
                              ? "bg-red-400"
                              : "bg-white/15"
                          }`}
                          style={{ width: `${status.score ?? 0}%` }}
                        />
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </section>

        {/* VULNERABILITIES */}
        <section className="glass mt-6 overflow-hidden rounded-2xl">
          <div className="flex items-center justify-between border-b border-white/10 p-5">
            <div>
              <h2 className="font-medium text-text-primary">Recent Vulnerabilities</h2>
              <p className="mt-1 text-xs text-white/30">Latest findings discovered by autonomous agents</p>
            </div>
            <button
              onClick={() => onNavigate("vulnerabilities")}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white transition hover:bg-white/10"
            >
              View All
            </button>
          </div>

          {vulnerabilities.length === 0 ? (
            <p className="p-8 text-center text-xs text-white/25">
              No confirmed vulnerabilities yet. They'll appear here as the swarm finds them.
            </p>
          ) : (
            <div>
              {vulnerabilities.slice(0, 5).map((v) => (
                <div
                  key={v.id}
                  className="flex flex-col justify-between gap-4 border-b border-white/5 p-5 transition hover:bg-white/[0.025] last:border-b-0 md:flex-row md:items-center"
                >
                  <div className="flex items-center gap-4">
                    <span
                      className={`h-2 w-2 shrink-0 rounded-full ${
                        v.severity === "critical"
                          ? "bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.6)]"
                          : v.severity === "high"
                          ? "bg-orange-400"
                          : "bg-yellow-400"
                      }`}
                    />
                    <div>
                      <p className="text-sm text-text-primary">{v.title}</p>
                      <p className="mt-1 text-[10px] text-white/25">
                        {v.id.slice(0, 8)} · {v.owasp_category}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`w-fit rounded-full border px-3 py-1 text-[9px] tracking-widest ${severityStyle(v.severity)}`}
                  >
                    {(v.severity || "").toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* LIVE ACTIVITY */}
        <section className="glass-dark mt-6 overflow-hidden rounded-2xl">
          <div className="flex items-center justify-between border-b border-white/10 p-5">
            <div>
              <h2 className="font-medium text-text-primary">Live Agent Activity</h2>
              <p className="mt-1 text-xs text-white/30">Real-time autonomous security events</p>
            </div>
            <div className="flex items-center gap-2 text-[9px] tracking-widest text-emerald-400">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              LIVE
            </div>
          </div>

          <div className="overflow-x-auto font-mono">
            {recentEvents.length === 0 ? (
              <p className="p-8 text-center text-xs text-white/25">
                Waiting for the swarm to begin. Start a scan to see agents work in real time.
              </p>
            ) : (
              recentEvents.map((e, i) => {
                const level = eventLevel(e);
                return (
                  <div
                    key={`${e.timestamp}-${i}`}
                    className="grid min-w-[650px] grid-cols-[80px_170px_1fr_90px] gap-4 border-b border-white/[0.04] px-5 py-3 text-[10px] transition hover:bg-white/[0.025] last:border-b-0"
                  >
                    <span className="text-white/20">
                      {new Date(e.timestamp).toLocaleTimeString("en-US", { hour12: false })}
                    </span>
                    <span className="truncate text-cyan-300/50">{e.agent_type || e.event_type}</span>
                    <span className="truncate text-white/45">{e.message}</span>
                    <span
                      className={
                        level === "CRITICAL"
                          ? "text-red-400"
                          : level === "WARNING"
                          ? "text-yellow-400"
                          : level === "SUCCESS"
                          ? "text-emerald-400"
                          : "text-white/25"
                      }
                    >
                      {level}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
