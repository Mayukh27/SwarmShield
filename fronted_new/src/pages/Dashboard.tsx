import { Button } from "@/components/ui/button";

const agents = [
  {
    name: "Recon Agent",
    role: "DISCOVERY",
    status: "ACTIVE",
    target: "api.swarmshield.local",
    action: "Mapping attack surface",
    progress: 78,
  },
  {
    name: "Exploit Agent",
    role: "VALIDATION",
    status: "ACTIVE",
    target: "auth-service",
    action: "Testing authentication vectors",
    progress: 52,
  },
  {
    name: "Vulnerability Agent",
    role: "ANALYSIS",
    status: "ACTIVE",
    target: "payment-api",
    action: "Correlating CVE signatures",
    progress: 64,
  },
  {
    name: "Patch Agent",
    role: "REMEDIATION",
    status: "STANDBY",
    target: "payment-api",
    action: "Waiting for remediation approval",
    progress: 0,
  },
];

const targets = [
  {
    name: "api.swarmshield.local",
    type: "API Gateway",
    score: 87,
    status: "HEALTHY",
  },
  {
    name: "auth-service",
    type: "Authentication",
    score: 72,
    status: "WARNING",
  },
  {
    name: "payment-api",
    type: "Payment Service",
    score: 41,
    status: "CRITICAL",
  },
];

const vulnerabilities = [
  {
    id: "VUL-042",
    name: "Authentication Bypass",
    target: "auth-service",
    severity: "CRITICAL",
  },
  {
    id: "VUL-039",
    name: "SQL Injection",
    target: "api-gateway",
    severity: "HIGH",
  },
  {
    id: "VUL-031",
    name: "Missing Security Headers",
    target: "web-client",
    severity: "MEDIUM",
  },
  {
    id: "VUL-027",
    name: "Weak Session Configuration",
    target: "auth-service",
    severity: "MEDIUM",
  },
];

const logs = [
  ["21:40:18", "Recon Agent", "New endpoint discovered: /admin", "INFO"],
  ["21:40:04", "Exploit Agent", "Authentication vector validated", "SUCCESS"],
  ["21:39:52", "Vulnerability Agent", "CVE correlation completed", "WARNING"],
  ["21:39:31", "Recon Agent", "Attack surface mapping updated", "INFO"],
  ["21:39:10", "Exploit Agent", "Authentication bypass candidate found", "CRITICAL"],
  ["21:38:54", "Patch Agent", "Waiting for remediation approval", "INFO"],
];

function severityStyle(severity: string) {
  if (severity === "CRITICAL") {
    return "border-red-400/20 bg-red-400/5 text-red-400";
  }

  if (severity === "HIGH") {
    return "border-orange-400/20 bg-orange-400/5 text-orange-400";
  }

  return "border-yellow-400/20 bg-yellow-400/5 text-yellow-400";
}

function targetStyle(status: string) {
  if (status === "HEALTHY") {
    return "text-emerald-400";
  }

  if (status === "WARNING") {
    return "text-yellow-400";
  }

  return "text-red-400";
}

export default function Dashboard() {
  return (
    <div className="min-h-screen">

      {/* TOP BAR */}
      <header className="sticky top-0 z-20 flex min-h-20 items-center justify-between border-b border-white/10 bg-[#030508]/80 px-6 backdrop-blur-xl lg:px-8">

        <div>
          <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">
            SECURITY OPERATIONS
          </p>

          <h1 className="mt-1 text-xl font-semibold">
            Command Center
          </h1>
        </div>

        <div className="flex items-center gap-3">

          <div className="hidden items-center gap-2 rounded-lg border border-emerald-400/10 bg-emerald-400/5 px-3 py-2 text-[10px] text-emerald-400 md:flex">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            SYSTEM ONLINE
          </div>

          <Button className="bg-cyan-400 text-black hover:bg-cyan-300">
            + New Scan
          </Button>

          <div className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-xs">
            SP
          </div>

        </div>
      </header>

      <div className="p-6 lg:p-8">

        {/* WELCOME */}
        <section className="relative mb-6 overflow-hidden rounded-2xl border border-cyan-400/10 bg-cyan-400/[0.03] p-6">

          <div className="pointer-events-none absolute -right-20 -top-20 h-48 w-48 rounded-full bg-cyan-400/10 blur-3xl" />

          <div className="relative flex flex-col justify-between gap-5 md:flex-row md:items-center">

            <div>

              <div className="flex items-center gap-2">
                <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.8)]" />

                <span className="text-[10px] tracking-[0.25em] text-cyan-300">
                  AUTONOMOUS SECURITY ACTIVE
                </span>
              </div>

              <h2 className="mt-3 text-2xl font-semibold">
                Your infrastructure is being protected.
              </h2>

              <p className="mt-2 max-w-2xl text-sm text-white/35">
                Autonomous AI agents are continuously discovering,
                validating, and analyzing security threats across
                your connected infrastructure.
              </p>

            </div>

            <Button
              variant="outline"
              className="border-white/10 bg-white/5 text-white hover:bg-white/10"
            >
              View Live Activity
            </Button>

          </div>
        </section>

        {/* KPI CARDS */}
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">

          {[
            ["Security Score", "87", "+4.2%", "GOOD"],
            ["Active Agents", "08", "+2", "RUNNING"],
            ["Targets", "03", "+1", "MONITORED"],
            ["Vulnerabilities", "24", "-6", "DETECTED"],
            ["Critical", "03", "-2", "ACTION"],
          ].map(([title, value, change, label]) => (

            <div
              key={title}
              className="group rounded-2xl border border-white/10 bg-white/[0.025] p-5 backdrop-blur-xl transition duration-300 hover:-translate-y-1 hover:border-cyan-400/20 hover:bg-white/[0.04]"
            >

              <div className="flex items-center justify-between">

                <p className="text-xs text-white/40">
                  {title}
                </p>

                <span className="text-[8px] tracking-[0.2em] text-white/20">
                  {label}
                </span>

              </div>

              <div className="mt-5 flex items-end justify-between">

                <p className="text-3xl font-semibold">
                  {value}
                </p>

                <span
                  className={
                    change.startsWith("-")
                      ? "text-xs text-emerald-400"
                      : "text-xs text-cyan-300"
                  }
                >
                  {change}
                </span>

              </div>

            </div>
          ))}

        </section>

        {/* AGENTS + SCORE */}
        <section className="mt-6 grid gap-6 xl:grid-cols-3">

          {/* AGENT SWARM */}
          <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.025] backdrop-blur-xl xl:col-span-2">

            <div className="flex items-center justify-between border-b border-white/10 p-5">

              <div>
                <h2 className="font-medium">
                  Autonomous Agent Swarm
                </h2>

                <p className="mt-1 text-xs text-white/30">
                  Live intelligence across your security network
                </p>
              </div>

              <span className="flex items-center gap-2 text-[9px] tracking-widest text-emerald-400">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                LIVE
              </span>

            </div>

            <div className="grid gap-px bg-white/5 md:grid-cols-2">

              {agents.map((agent) => (

                <div
                  key={agent.name}
                  className="group bg-[#07090d] p-5 transition hover:bg-white/[0.025]"
                >

                  <div className="flex items-start justify-between">

                    <div className="flex items-center gap-3">

                      <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-400/15 bg-cyan-400/5 text-cyan-300 transition group-hover:border-cyan-400/30 group-hover:shadow-[0_0_25px_rgba(34,211,238,0.08)]">
                        ◈
                      </div>

                      <div>
                        <p className="text-sm font-medium">
                          {agent.name}
                        </p>

                        <p className="mt-1 text-[9px] tracking-widest text-white/25">
                          {agent.role}
                        </p>
                      </div>

                    </div>

                    <span
                      className={
                        agent.status === "ACTIVE"
                          ? "rounded-full border border-emerald-400/20 bg-emerald-400/5 px-2 py-1 text-[8px] tracking-widest text-emerald-400"
                          : "rounded-full border border-white/10 px-2 py-1 text-[8px] tracking-widest text-white/25"
                      }
                    >
                      {agent.status}
                    </span>

                  </div>

                  <div className="mt-5">

                    <div className="flex justify-between text-[9px]">

                      <span className="text-white/20">
                        TARGET
                      </span>

                      <span className="text-white/50">
                        {agent.target}
                      </span>

                    </div>

                    <div className="mt-3 rounded-lg border border-white/5 bg-black/20 p-3">

                      <p className="text-[9px] tracking-widest text-white/20">
                        CURRENT ACTION
                      </p>

                      <p className="mt-1 text-xs text-white/50">
                        {agent.action}
                      </p>

                    </div>

                    <div className="mt-4">

                      <div className="mb-2 flex justify-between text-[9px]">

                        <span className="text-white/20">
                          OPERATION
                        </span>

                        <span className="text-cyan-300">
                          {agent.progress}%
                        </span>

                      </div>

                      <div className="h-1 overflow-hidden rounded-full bg-white/5">

                        <div
                          className="h-full rounded-full bg-cyan-400 transition-all duration-700"
                          style={{
                            width: `${agent.progress}%`,
                          }}
                        />

                      </div>

                    </div>

                  </div>

                </div>

              ))}

            </div>
          </div>

          {/* SECURITY SCORE */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-6 backdrop-blur-xl">

            <div className="flex items-center justify-between">

              <div>
                <p className="text-xs tracking-widest text-white/30">
                  SECURITY SCORE
                </p>

                <p className="mt-1 text-[10px] text-white/20">
                  GLOBAL INFRASTRUCTURE HEALTH
                </p>
              </div>

              <span className="text-emerald-400">
                ↑ 4.2%
              </span>

            </div>

            <div className="mt-7 flex justify-center">

              <div className="relative flex h-48 w-48 items-center justify-center rounded-full border-[13px] border-cyan-400/10">

                <div className="absolute inset-[-13px] rounded-full border-[13px] border-transparent border-t-cyan-400 border-r-cyan-400 rotate-[25deg] shadow-[0_0_30px_rgba(34,211,238,0.08)]" />

                <div className="text-center">

                  <p className="text-5xl font-semibold">
                    87
                  </p>

                  <p className="mt-1 text-[10px] tracking-[0.2em] text-emerald-400">
                    GOOD
                  </p>

                </div>

              </div>

            </div>

            <div className="mt-7 space-y-4">

              {[
                ["Infrastructure", "92%"],
                ["Applications", "84%"],
                ["Identity", "86%"],
              ].map(([name, score]) => (

                <div key={name}>

                  <div className="mb-2 flex justify-between text-xs">

                    <span className="text-white/35">
                      {name}
                    </span>

                    <span className="text-white/70">
                      {score}
                    </span>

                  </div>

                  <div className="h-1 rounded-full bg-white/5">

                    <div
                      className="h-full rounded-full bg-cyan-400/70"
                      style={{ width: score }}
                    />

                  </div>

                </div>

              ))}

            </div>

          </div>

        </section>

        {/* TARGETS */}
        <section className="mt-6 rounded-2xl border border-white/10 bg-white/[0.025] backdrop-blur-xl">

          <div className="flex items-center justify-between border-b border-white/10 p-5">

            <div>
              <h2 className="font-medium">
                Monitored Targets
              </h2>

              <p className="mt-1 text-xs text-white/30">
                Infrastructure currently protected by the swarm
              </p>
            </div>

            <Button
              variant="outline"
              className="border-white/10 bg-white/5 text-xs text-white hover:bg-white/10"
            >
              Manage Targets
            </Button>

          </div>

          <div className="grid gap-px bg-white/5 md:grid-cols-3">

            {targets.map((target) => (

              <div
                key={target.name}
                className="bg-[#07090d] p-5 transition hover:bg-white/[0.025]"
              >

                <div className="flex items-start justify-between">

                  <div>
                    <p className="text-sm font-medium">
                      {target.name}
                    </p>

                    <p className="mt-1 text-[10px] text-white/25">
                      {target.type}
                    </p>
                  </div>

                  <span
                    className={`text-[9px] tracking-widest ${targetStyle(
                      target.status
                    )}`}
                  >
                    {target.status}
                  </span>

                </div>

                <div className="mt-6">

                  <div className="mb-2 flex justify-between text-[9px]">

                    <span className="text-white/20">
                      SECURITY SCORE
                    </span>

                    <span>
                      {target.score}%
                    </span>

                  </div>

                  <div className="h-1.5 rounded-full bg-white/5">

                    <div
                      className={`h-full rounded-full ${
                        target.status === "HEALTHY"
                          ? "bg-emerald-400"
                          : target.status === "WARNING"
                          ? "bg-yellow-400"
                          : "bg-red-400"
                      }`}
                      style={{
                        width: `${target.score}%`,
                      }}
                    />

                  </div>

                </div>

              </div>

            ))}

          </div>

        </section>

        {/* VULNERABILITIES */}
        <section className="mt-6 overflow-hidden rounded-2xl border border-white/10 bg-white/[0.025] backdrop-blur-xl">

          <div className="flex items-center justify-between border-b border-white/10 p-5">

            <div>
              <h2 className="font-medium">
                Recent Vulnerabilities
              </h2>

              <p className="mt-1 text-xs text-white/30">
                Latest findings discovered by autonomous agents
              </p>
            </div>

            <Button
              variant="outline"
              className="border-white/10 bg-white/5 text-xs text-white hover:bg-white/10"
            >
              View All
            </Button>

          </div>

          <div>

            {vulnerabilities.map((vulnerability) => (

              <div
                key={vulnerability.id}
                className="flex flex-col justify-between gap-4 border-b border-white/5 p-5 transition hover:bg-white/[0.025] md:flex-row md:items-center"
              >

                <div className="flex items-center gap-4">

                  <span
                    className={`h-2 w-2 rounded-full ${
                      vulnerability.severity === "CRITICAL"
                        ? "bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.6)]"
                        : vulnerability.severity === "HIGH"
                        ? "bg-orange-400"
                        : "bg-yellow-400"
                    }`}
                  />

                  <div>

                    <p className="text-sm">
                      {vulnerability.name}
                    </p>

                    <p className="mt-1 text-[10px] text-white/25">
                      {vulnerability.id} · {vulnerability.target}
                    </p>

                  </div>

                </div>

                <span
                  className={`w-fit rounded-full border px-3 py-1 text-[9px] tracking-widest ${severityStyle(
                    vulnerability.severity
                  )}`}
                >
                  {vulnerability.severity}
                </span>

              </div>

            ))}

          </div>

        </section>

        {/* LIVE ACTIVITY */}
        <section className="mt-6 overflow-hidden rounded-2xl border border-white/10 bg-black/40 backdrop-blur-xl">

          <div className="flex items-center justify-between border-b border-white/10 p-5">

            <div>
              <h2 className="font-medium">
                Live Agent Activity
              </h2>

              <p className="mt-1 text-xs text-white/30">
                Real-time autonomous security events
              </p>
            </div>

            <div className="flex items-center gap-2 text-[9px] tracking-widest text-emerald-400">

              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />

              LIVE

            </div>

          </div>

          <div className="overflow-x-auto font-mono">

            {logs.map(([time, agent, message, level]) => (

              <div
                key={`${time}-${message}`}
                className="grid min-w-[650px] grid-cols-[80px_150px_1fr_90px] gap-4 border-b border-white/[0.04] px-5 py-3 text-[10px] transition hover:bg-white/[0.025]"
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