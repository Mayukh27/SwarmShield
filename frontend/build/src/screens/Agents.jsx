import { useMemo, useState } from "react";
import { useScanStore } from "../store/scanStore";
import { deriveAgentStates } from "../theme/roster";
import AgentLogConsole from "../components/AgentLogConsole";
import BattlePlanPanel from "../components/BattlePlanPanel";
import MemoryPanel from "../components/MemoryPanel";
import AttackDnaPanel from "../components/AttackDnaPanel";
import AgentDetailPanel from "../components/AgentDetailPanel";

export default function Agents({ scanInFlight }) {
  const events = useScanStore((s) => s.events);
  const activeScan = useScanStore((s) => s.activeScan);
  const [selectedAgent, setSelectedAgent] = useState(null);

  const agents = useMemo(
    () => deriveAgentStates(events, scanInFlight, activeScan?.status),
    [events, scanInFlight, activeScan?.status]
  );

  return (
    <div className="relative min-h-full p-6 lg:p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">SECURITY OPERATIONS</p>
          <h1 className="mt-1 text-xl font-semibold text-text-primary">AI Agents</h1>
          <p className="mt-1 text-xs text-white/30">
            The real specialist agents the backend deploys, and what they're doing right now.
          </p>
        </div>
      </div>

      {/* ROSTER */}
      <section className="glass overflow-hidden rounded-2xl">
        <div className="flex items-center justify-between border-b border-white/10 p-5">
          <h2 className="font-medium text-text-primary">Agent Swarm</h2>
          <span className="flex items-center gap-2 text-[9px] tracking-widest text-emerald-400">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            LIVE
          </span>
        </div>
        <div className="grid gap-px bg-white/5 md:grid-cols-2 xl:grid-cols-4">
          {agents.map((agent) => (
            <button
              key={agent.type}
              onClick={() => setSelectedAgent(agent.type)}
              className="bg-[#07090d] p-5 text-left transition hover:bg-white/[0.025]"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-text-primary">{agent.name}</p>
                  <p className="mt-1 text-[9px] tracking-widest text-white/25">{agent.group}</p>
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
              <p className="mt-4 truncate text-xs text-white/45">{agent.currentAction}</p>
            </button>
          ))}
        </div>
      </section>

      {/* PLAN + LIVE LOG */}
      <section className="mt-6 grid gap-6 xl:grid-cols-3">
        <div className="glass overflow-hidden rounded-2xl xl:col-span-1">
          <BattlePlanPanel />
        </div>
        <div className="glass h-[420px] overflow-hidden rounded-2xl xl:col-span-2">
          <AgentLogConsole />
        </div>
      </section>

      <section className="mt-6 grid gap-6 md:grid-cols-2">
        <div className="glass overflow-hidden rounded-2xl">
          <MemoryPanel />
        </div>
        <div className="glass overflow-hidden rounded-2xl">
          <AttackDnaPanel />
        </div>
      </section>

      {selectedAgent && (
        <AgentDetailPanel agentType={selectedAgent} onClose={() => setSelectedAgent(null)} />
      )}
    </div>
  );
}
