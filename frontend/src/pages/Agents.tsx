import { useState } from "react";
import { Button } from "@/components/ui/button";

const agents = [
  {
    name: "Recon Agent",
    code: "AG-001",
    role: "DISCOVERY",
    status: "ACTIVE",
    target: "api.swarmshield.local",
    action: "Mapping attack surface",
    progress: 78,
    findings: 12,
    description:
      "Discovers endpoints, services, ports, technologies and exposed attack surfaces.",
  },
  {
    name: "Exploit Agent",
    code: "AG-002",
    role: "VALIDATION",
    status: "ACTIVE",
    target: "auth-service",
    action: "Testing authentication vectors",
    progress: 52,
    findings: 7,
    description:
      "Validates suspected vulnerabilities using controlled security testing.",
  },
  {
    name: "Vulnerability Agent",
    code: "AG-003",
    role: "ANALYSIS",
    status: "ACTIVE",
    target: "payment-api",
    action: "Correlating CVE signatures",
    progress: 64,
    findings: 5,
    description:
      "Analyzes discovered weaknesses and correlates them with known vulnerability intelligence.",
  },
  {
    name: "Patch Agent",
    code: "AG-004",
    role: "REMEDIATION",
    status: "STANDBY",
    target: "payment-api",
    action: "Waiting for remediation approval",
    progress: 0,
    findings: 0,
    description:
      "Generates and validates remediation suggestions for confirmed vulnerabilities.",
  },
];

const activity = [
  ["21:40:18", "Recon Agent", "New endpoint discovered: /admin", "INFO"],
  ["21:40:04", "Exploit Agent", "Authentication vector validated", "SUCCESS"],
  ["21:39:52", "Vulnerability Agent", "CVE correlation completed", "WARNING"],
  ["21:39:31", "Recon Agent", "Attack surface mapping updated", "INFO"],
  ["21:39:10", "Exploit Agent", "Authentication bypass candidate found", "CRITICAL"],
  ["21:38:54", "Patch Agent", "Waiting for remediation approval", "INFO"],
];

export default function Agents() {
  const [selectedAgent, setSelectedAgent] = useState(agents[0]);

  return (
    <div>
      {/* HEADER */}
      <header className="glass-header flex min-h-20 items-center justify-between px-6 lg:px-8">
        <div>
          <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">
            AUTONOMOUS NETWORK
          </p>

          <h1 className="mt-1 text-xl font-semibold">
            AI Agents
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden items-center gap-2 rounded-lg border border-emerald-400/10 bg-emerald-400/5 px-3 py-2 text-[10px] text-emerald-400 md:flex">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            4 AGENTS ACTIVE
          </div>

          <Button className="bg-cyan-400 text-black hover:bg-cyan-300">
            + Deploy Agent
          </Button>
        </div>
      </header>

      <div className="p-6 lg:p-8">

        {/* INTRO */}
        <section className="glass-cyan mb-6 rounded-2xl p-6">

          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">

            <div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.8)]" />

                <span className="text-[10px] tracking-[0.25em] text-cyan-300">
                  SWARM INTELLIGENCE ACTIVE
                </span>
              </div>

              <h2 className="mt-3 text-2xl font-semibold">
                Autonomous Security Agents
              </h2>

              <p className="mt-2 max-w-2xl text-sm text-white/35">
                Coordinate specialized AI agents to discover, validate,
                analyze and remediate security threats.
              </p>
            </div>

            <div className="text-right">
              <p className="text-3xl font-semibold">
                08
              </p>

              <p className="text-[9px] tracking-widest text-white/25">
                TOTAL AGENTS
              </p>
            </div>

          </div>
        </section>

        {/* STATS */}
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

          {[
            ["Total Agents", "08", "REGISTERED"],
            ["Active", "04", "RUNNING"],
            ["Standby", "03", "AVAILABLE"],
            ["Findings", "24", "DETECTED"],
          ].map(([title, value, label]) => (
            <div
              key={title}
              className="glass glass-hover rounded-2xl p-5"
            >
              <div className="flex justify-between">
                <p className="text-xs text-white/35">
                  {title}
                </p>

                <span className="text-[8px] tracking-widest text-white/20">
                  {label}
                </span>
              </div>

              <p className="mt-5 text-3xl font-semibold">
                {value}
              </p>
            </div>
          ))}

        </section>

        {/* AGENT CARDS */}
        <section className="mt-6">

          <div className="mb-4">
            <h2 className="font-medium">
              Agent Network
            </h2>

            <p className="mt-1 text-xs text-white/30">
              Select an agent to inspect its current operation.
            </p>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">

            {agents.map((agent) => {
              const selected = selectedAgent.code === agent.code;

              return (
                <button
                  key={agent.code}
                  onClick={() => setSelectedAgent(agent)}
                  className={`group relative overflow-hidden rounded-2xl border p-6 text-left transition duration-300 ${
                    selected
                      ? "border-cyan-400/30 bg-cyan-400/[0.04] shadow-[0_0_35px_rgba(34,211,238,0.05)]"
                      : "border-white/10 bg-white/[0.025] hover:border-cyan-400/20"
                  }`}
                >

                  <div className="pointer-events-none absolute -right-16 -top-16 h-36 w-36 rounded-full bg-cyan-400/5 blur-3xl" />

                  <div className="relative flex items-start justify-between">

                    <div className="flex items-center gap-4">

                      <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-cyan-400/15 bg-cyan-400/5 text-lg text-cyan-300 transition group-hover:shadow-[0_0_25px_rgba(34,211,238,0.12)]">
                        ◈
                      </div>

                      <div>
                        <h3 className="text-sm font-medium">
                          {agent.name}
                        </h3>

                        <p className="mt-1 text-[9px] tracking-[0.2em] text-white/25">
                          {agent.code} · {agent.role}
                        </p>
                      </div>

                    </div>

                    <span
                      className={
                        agent.status === "ACTIVE"
                          ? "rounded-full border border-emerald-400/20 bg-emerald-400/5 px-3 py-1 text-[8px] tracking-widest text-emerald-400"
                          : "rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[8px] tracking-widest text-white/30"
                      }
                    >
                      {agent.status}
                    </span>

                  </div>

                  <div className="relative mt-6 grid grid-cols-2 gap-4">

                    <div>
                      <p className="text-[8px] tracking-widest text-white/20">
                        TARGET
                      </p>

                      <p className="mt-2 truncate text-xs text-white/55">
                        {agent.target}
                      </p>
                    </div>

                    <div>
                      <p className="text-[8px] tracking-widest text-white/20">
                        FINDINGS
                      </p>

                      <p className="mt-2 text-xs text-white/55">
                        {agent.findings}
                      </p>
                    </div>

                  </div>

                  <div className="relative mt-5 rounded-xl border border-white/5 bg-black/20 p-4">

                    <p className="text-[8px] tracking-widest text-white/20">
                      CURRENT ACTION
                    </p>

                    <p className="mt-2 text-xs text-white/55">
                      {agent.action}
                    </p>

                  </div>

                  <div className="relative mt-5">

                    <div className="mb-2 flex justify-between text-[8px] tracking-widest">

                      <span className="text-white/20">
                        OPERATION
                      </span>

                      <span className="text-cyan-300">
                        {agent.progress}%
                      </span>

                    </div>

                    <div className="h-1.5 overflow-hidden rounded-full bg-white/5">

                      <div
                        className="h-full rounded-full bg-cyan-400 transition-all duration-700"
                        style={{
                          width: `${agent.progress}%`,
                        }}
                      />

                    </div>

                  </div>

                </button>
              );
            })}

          </div>
        </section>

        {/* SELECTED AGENT */}
        <section className="mt-6 grid gap-6 xl:grid-cols-3">

          <div className="glass xl:col-span-2 rounded-2xl p-6">

            <div className="flex items-start justify-between">

              <div>
                <p className="text-[9px] tracking-[0.2em] text-cyan-300/50">
                  SELECTED AGENT
                </p>

                <h2 className="mt-2 text-xl font-semibold">
                  {selectedAgent.name}
                </h2>

                <p className="mt-1 text-xs text-white/30">
                  {selectedAgent.code} · {selectedAgent.role}
                </p>
              </div>

              <span className="rounded-full border border-emerald-400/20 bg-emerald-400/5 px-3 py-1 text-[9px] text-emerald-400">
                {selectedAgent.status}
              </span>

            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-3">

              <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                <p className="text-[8px] tracking-widest text-white/20">
                  TARGET
                </p>

                <p className="mt-2 text-xs text-white/60">
                  {selectedAgent.target}
                </p>
              </div>

              <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                <p className="text-[8px] tracking-widest text-white/20">
                  FINDINGS
                </p>

                <p className="mt-2 text-xs text-white/60">
                  {selectedAgent.findings}
                </p>
              </div>

              <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                <p className="text-[8px] tracking-widest text-white/20">
                  PROGRESS
                </p>

                <p className="mt-2 text-xs text-cyan-300">
                  {selectedAgent.progress}%
                </p>
              </div>

            </div>

            <div className="mt-5 rounded-xl border border-cyan-400/10 bg-cyan-400/[0.02] p-5">

              <p className="text-[9px] tracking-widest text-cyan-300/50">
                AGENT CAPABILITY
              </p>

              <p className="mt-3 text-sm leading-relaxed text-white/40">
                {selectedAgent.description}
              </p>

            </div>

            <div className="mt-5 flex gap-3">

              <Button className="bg-cyan-400 text-black hover:bg-cyan-300">
                Open Console
              </Button>

              <Button
                variant="outline"
                className="border-white/10 bg-white/5 text-white hover:bg-white/10"
              >
                Configure Agent
              </Button>

              <Button
                variant="outline"
                className="border-white/10 bg-white/5 text-white hover:bg-white/10"
              >
                Pause
              </Button>

            </div>

          </div>

          {/* NETWORK HEALTH */}
          <div className="glass rounded-2xl p-6">

            <p className="text-[9px] tracking-[0.2em] text-white/25">
              SWARM HEALTH
            </p>

            <div className="mt-8 flex justify-center">

              <div className="relative flex h-40 w-40 items-center justify-center rounded-full border-[10px] border-cyan-400/10">

                <div className="absolute inset-[-10px] rounded-full border-[10px] border-transparent border-t-cyan-400 border-r-cyan-400 rotate-[30deg]" />

                <div className="text-center">
                  <p className="text-4xl font-semibold">
                    94
                  </p>

                  <p className="mt-1 text-[8px] tracking-widest text-emerald-400">
                    OPTIMAL
                  </p>
                </div>

              </div>

            </div>

            <div className="mt-8 space-y-4">

              {[
                ["Connectivity", "98%"],
                ["Coordination", "94%"],
                ["Availability", "91%"],
              ].map(([label, value]) => (

                <div key={label}>

                  <div className="mb-2 flex justify-between text-[10px]">
                    <span className="text-white/30">
                      {label}
                    </span>

                    <span>
                      {value}
                    </span>
                  </div>

                  <div className="h-1 rounded-full bg-white/5">
                    <div
                      className="h-full rounded-full bg-cyan-400/70"
                      style={{ width: value }}
                    />
                  </div>

                </div>

              ))}

            </div>

          </div>

        </section>

        {/* ACTIVITY CONSOLE */}
        <section className="glass-dark mt-6 overflow-hidden rounded-2xl">

          <div className="flex items-center justify-between border-b border-white/10 p-5">

            <div>
              <h2 className="font-medium">
                Agent Activity Console
              </h2>

              <p className="mt-1 text-xs text-white/30">
                Real-time autonomous agent events
              </p>
            </div>

            <div className="flex items-center gap-2 text-[9px] tracking-widest text-emerald-400">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              LIVE
            </div>

          </div>

          <div className="overflow-x-auto font-mono">

            {activity.map(([time, agent, message, level]) => (

              <div
                key={`${time}-${message}`}
                className="grid min-w-[700px] grid-cols-[80px_150px_1fr_90px] gap-4 border-b border-white/[0.04] px-5 py-3 text-[10px] transition hover:bg-white/[0.025]"
              >

                <span className="text-white/20">
                  {time}
                </span>

                <span className="text-cyan-300/50">
                  {agent}
                </span>

                <span className="text-white/45">
                  {message}
                </span>

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

            ))}

          </div>

        </section>

      </div>
    </div>
  );
}