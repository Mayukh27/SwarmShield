import { useState } from "react";
import { Button } from "@/components/ui/button";

const patches = [
  {
    id: "PATCH-042",
    vulnerability: "Authentication Bypass",
    target: "auth-service",
    severity: "CRITICAL",
    confidence: "96%",
    status: "READY",
    description:
      "Restrict authentication flow and enforce server-side authorization checks.",
  },
  {
    id: "PATCH-039",
    vulnerability: "SQL Injection",
    target: "api-gateway",
    severity: "HIGH",
    confidence: "92%",
    status: "REVIEW",
    description:
      "Replace dynamic SQL construction with parameterized database queries.",
  },
  {
    id: "PATCH-031",
    vulnerability: "Missing Security Headers",
    target: "web-client",
    severity: "MEDIUM",
    confidence: "98%",
    status: "READY",
    description:
      "Add recommended security headers to the web application response policy.",
  },
];

const diff = [
  {
    number: 41,
    type: "remove",
    text: 'const query = "SELECT * FROM users WHERE id=" + userId;',
  },
  {
    number: 42,
    type: "add",
    text: "const query = db.prepare(",
  },
  {
    number: 43,
    type: "add",
    text: '  "SELECT * FROM users WHERE id = ?"',
  },
  {
    number: 44,
    type: "add",
    text: ");",
  },
];

export default function PatchCenter() {
  const [selected, setSelected] = useState(patches[0]);
  const [applied, setApplied] = useState(false);

  return (
    <div>
      {/* HEADER */}
      <header className="glass-header flex min-h-20 items-center justify-between px-6 lg:px-8">
        <div>
          <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">
            AUTONOMOUS REMEDIATION
          </p>

          <h1 className="mt-1 text-xl font-semibold">
            Patch Center
          </h1>
        </div>

        <div className="flex items-center gap-2 text-[9px] tracking-widest text-emerald-400">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
          PATCH ENGINE ONLINE
        </div>
      </header>

      <div className="p-6 lg:p-8">

        {/* INTRO */}
        <section className="glass-cyan mb-6 rounded-2xl p-6">

          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">

            <div>
              <p className="text-[10px] tracking-[0.25em] text-cyan-300">
                AI REMEDIATION ENGINE
              </p>

              <h2 className="mt-3 text-2xl font-semibold">
                Fix vulnerabilities with confidence.
              </h2>

              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-white/35">
                SwarmShield analyzes confirmed findings, generates
                remediation suggestions, and validates patches before
                deployment.
              </p>
            </div>

            <div className="rounded-xl border border-emerald-400/10 bg-emerald-400/5 px-5 py-4">
              <p className="text-2xl font-semibold">
                05
              </p>

              <p className="mt-1 text-[9px] tracking-widest text-emerald-400">
                PATCHES READY
              </p>
            </div>

          </div>
        </section>

        {/* SUMMARY */}
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

          {[
            ["Patch Candidates", "05", "GENERATED"],
            ["Ready", "03", "VALIDATED"],
            ["Under Review", "01", "REVIEW"],
            ["Applied", "12", "VERIFIED"],
          ].map(([title, value, label]) => (

            <div
              key={title}
              className="glass rounded-2xl p-5"
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

        {/* PATCH LIST */}
        <section className="mt-6 grid gap-6 xl:grid-cols-3">

          <div className="glass overflow-hidden rounded-2xl xl:col-span-1">

            <div className="border-b border-white/10 p-5">
              <h2 className="font-medium">
                Remediation Queue
              </h2>

              <p className="mt-1 text-xs text-white/30">
                AI-generated patch candidates
              </p>
            </div>

            <div>
              {patches.map((patch) => {
                const active = selected.id === patch.id;

                return (
                  <button
                    key={patch.id}
                    onClick={() => {
                      setSelected(patch);
                      setApplied(false);
                    }}
                    className={`w-full border-b border-white/5 p-5 text-left transition ${
                      active
                        ? "bg-cyan-400/[0.05]"
                        : "hover:bg-white/[0.025]"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">

                      <div>
                        <p className="text-xs font-medium">
                          {patch.vulnerability}
                        </p>

                        <p className="mt-1 text-[9px] text-white/25">
                          {patch.id} · {patch.target}
                        </p>
                      </div>

                      <span className="text-[8px] tracking-widest text-cyan-300">
                        {patch.status}
                      </span>

                    </div>

                    <div className="mt-4 flex items-center justify-between">

                      <span
                        className={`text-[9px] tracking-widest ${
                          patch.severity === "CRITICAL"
                            ? "text-red-400"
                            : patch.severity === "HIGH"
                            ? "text-orange-400"
                            : "text-yellow-400"
                        }`}
                      >
                        {patch.severity}
                      </span>

                      <span className="text-[9px] text-white/25">
                        {patch.confidence} CONFIDENCE
                      </span>

                    </div>
                  </button>
                );
              })}
            </div>

          </div>

          {/* PATCH DETAILS */}
          <div className="xl:col-span-2">

            <div className="glass rounded-2xl p-6">

              <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">

                <div>
                  <p className="text-[9px] tracking-[0.2em] text-cyan-300/50">
                    SELECTED PATCH
                  </p>

                  <h2 className="mt-2 text-xl font-semibold">
                    {selected.vulnerability}
                  </h2>

                  <p className="mt-1 text-xs text-white/30">
                    {selected.id} · {selected.target}
                  </p>
                </div>

                <span className="rounded-full border border-emerald-400/20 bg-emerald-400/5 px-3 py-1 text-[9px] tracking-widest text-emerald-400">
                  {selected.confidence} CONFIDENCE
                </span>

              </div>

              {/* AI recommendation */}
              <div className="mt-6 rounded-xl border border-cyan-400/10 bg-cyan-400/[0.025] p-5">

                <div className="flex gap-3">

                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-xs text-cyan-300">
                    AI
                  </div>

                  <div>
                    <p className="text-[9px] tracking-widest text-cyan-300/60">
                      AI RECOMMENDATION
                    </p>

                    <p className="mt-2 text-sm leading-relaxed text-white/50">
                      {selected.description}
                    </p>
                  </div>

                </div>

              </div>

              {/* Validation */}
              <div className="mt-6">

                <div className="mb-3 flex items-center justify-between">

                  <div>
                    <h3 className="text-sm font-medium">
                      Automated Validation
                    </h3>

                    <p className="mt-1 text-[10px] text-white/25">
                      Patch safety checks performed by SwarmShield.
                    </p>
                  </div>

                  <span className="text-[9px] tracking-widest text-emerald-400">
                    PASSED
                  </span>

                </div>

                <div className="grid gap-3 sm:grid-cols-3">

                  {[
                    ["Syntax Check", "PASSED"],
                    ["Security Test", "PASSED"],
                    ["Regression", "PASSED"],
                  ].map(([name, status]) => (

                    <div
                      key={name}
                      className="rounded-xl border border-white/5 bg-black/20 p-4"
                    >
                      <div className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />

                        <span className="text-[10px] text-white/50">
                          {name}
                        </span>
                      </div>

                      <p className="mt-2 text-[9px] tracking-widest text-emerald-400">
                        {status}
                      </p>
                    </div>

                  ))}

                </div>

              </div>

            </div>

            {/* CODE DIFF */}
            <div className="glass-dark mt-6 overflow-hidden rounded-2xl">

              <div className="flex items-center justify-between border-b border-white/10 p-5">

                <div>
                  <h2 className="font-medium">
                    Proposed Code Change
                  </h2>

                  <p className="mt-1 text-xs text-white/30">
                    Review the generated remediation before applying it.
                  </p>
                </div>

                <span className="rounded border border-cyan-400/10 bg-cyan-400/5 px-2 py-1 text-[8px] tracking-widest text-cyan-300">
                  AI GENERATED
                </span>

              </div>

              <div className="overflow-x-auto p-4 font-mono text-[11px]">

                {diff.map((line) => (

                  <div
                    key={line.number}
                    className={`flex min-w-[650px] gap-4 px-3 py-1.5 ${
                      line.type === "remove"
                        ? "bg-red-400/5 text-red-300/70"
                        : "bg-emerald-400/5 text-emerald-300/70"
                    }`}
                  >

                    <span className="w-8 text-right text-white/15">
                      {line.number}
                    </span>

                    <span className="w-3">
                      {line.type === "remove" ? "-" : "+"}
                    </span>

                    <span>
                      {line.text}
                    </span>

                  </div>

                ))}

              </div>

            </div>

            {/* ACTIONS */}
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">

              <Button
                onClick={() => setApplied(true)}
                disabled={applied}
                className="h-12 flex-1 bg-cyan-400 text-black hover:bg-cyan-300 disabled:bg-emerald-400"
              >
                {applied ? "Patch Applied ✓" : "Apply Patch"}
              </Button>

              <Button
                variant="outline"
                className="h-12 border-white/10 bg-white/5 text-white hover:bg-white/10"
              >
                Reject
              </Button>

              <Button
                variant="outline"
                className="h-12 border-white/10 bg-white/5 text-white hover:bg-white/10"
              >
                Request Review
              </Button>

            </div>

            {applied && (
              <div className="mt-4 rounded-xl border border-emerald-400/20 bg-emerald-400/5 p-4">

                <div className="flex items-center gap-3">

                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-400/10 text-emerald-400">
                    ✓
                  </span>

                  <div>
                    <p className="text-xs font-medium text-emerald-400">
                      Patch successfully applied
                    </p>

                    <p className="mt-1 text-[10px] text-white/30">
                      Verification scan initiated automatically.
                    </p>
                  </div>

                </div>

              </div>
            )}

          </div>

        </section>

      </div>
    </div>
  );
}