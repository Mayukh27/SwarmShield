import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

const scanSteps = [
  "Initializing security agents",
  "Discovering attack surface",
  "Enumerating endpoints",
  "Analyzing technologies",
  "Testing security controls",
  "Correlating vulnerabilities",
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

export default function Targets() {
  const [target, setTarget] = useState("");
  const [scanType, setScanType] = useState("Deep Scan");
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!scanning) return;

    const timer = setInterval(() => {
      setProgress((current) => {
        if (current >= 100) {
          clearInterval(timer);
          return 100;
        }

        return current + 2;
      });
    }, 120);

    return () => clearInterval(timer);
  }, [scanning]);

  useEffect(() => {
    if (!scanning) return;

    const currentStep = Math.min(
      Math.floor(progress / 17),
      scanSteps.length - 1
    );

    setStep(currentStep);

    if (progress >= 100) {
      setScanning(false);
    }
  }, [progress, scanning]);

  const startScan = () => {
    if (!target.trim()) return;

    setProgress(0);
    setStep(0);
    setScanning(true);
  };

  const resetScan = () => {
    setScanning(false);
    setProgress(0);
    setStep(0);
  };

  return (
    <div>
      {/* HEADER */}
      <header className="flex min-h-20 items-center justify-between border-b border-white/10 bg-black/30 px-6 backdrop-blur-xl lg:px-8">

        <div>
          <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">
            SECURITY OPERATIONS
          </p>

          <h1 className="mt-1 text-xl font-semibold">
            Targets
          </h1>
        </div>

        <div className="flex items-center gap-2 text-[9px] tracking-widest">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              scanning
                ? "animate-pulse bg-cyan-400"
                : "bg-emerald-400"
            }`}
          />

          <span
            className={
              scanning
                ? "text-cyan-300"
                : "text-emerald-400"
            }
          >
            {scanning ? "SCAN IN PROGRESS" : "SCAN ENGINE READY"}
          </span>
        </div>

      </header>

      <div className="p-6 lg:p-8">

        {/* INTRO */}
        <section className="mb-6 rounded-2xl border border-cyan-400/10 bg-cyan-400/[0.03] p-6">

          <p className="text-[10px] tracking-[0.25em] text-cyan-300">
            AUTONOMOUS TARGET MANAGEMENT
          </p>

          <h2 className="mt-3 text-2xl font-semibold">
            Scan your infrastructure
          </h2>

          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-white/35">
            Deploy autonomous security agents against an authorized
            target and continuously analyze its security posture.
          </p>

        </section>

        {/* MAIN SCANNER */}
        <section className="grid gap-6 xl:grid-cols-3">

          {/* CONFIGURATION */}
          <div className="xl:col-span-2 rounded-2xl border border-white/10 bg-white/[0.025] p-6 backdrop-blur-xl">

            <div className="mb-6">
              <h2 className="font-medium">
                Security Scan
              </h2>

              <p className="mt-1 text-xs text-white/30">
                Configure your authorized target.
              </p>
            </div>

            <div className="space-y-6">

              {/* TARGET */}
              <div>
                <label className="mb-2 block text-xs text-white/50">
                  Target URL / IP
                </label>

                <input
                  value={target}
                  onChange={(event) =>
                    setTarget(event.target.value)
                  }
                  disabled={scanning}
                  placeholder="https://api.example.com"
                  className="h-12 w-full rounded-xl border border-white/10 bg-black/30 px-4 text-sm text-white outline-none placeholder:text-white/20 transition focus:border-cyan-400/40 focus:ring-1 focus:ring-cyan-400/10 disabled:opacity-50"
                />

                <p className="mt-2 text-[9px] text-white/20">
                  Only scan systems you own or have explicit authorization to test.
                </p>
              </div>

              {/* SCAN TYPES */}
              <div>
                <label className="mb-3 block text-xs text-white/50">
                  Scan Profile
                </label>

                <div className="grid gap-3 md:grid-cols-3">

                  {[
                    ["Quick Scan", "Fast surface analysis"],
                    ["Deep Scan", "Full vulnerability analysis"],
                    ["Continuous", "Recurring monitoring"],
                  ].map(([name, description]) => (

                    <button
                      key={name}
                      disabled={scanning}
                      onClick={() => setScanType(name)}
                      className={`rounded-xl border p-4 text-left transition ${
                        scanType === name
                          ? "border-cyan-400/30 bg-cyan-400/[0.06] shadow-[0_0_25px_rgba(34,211,238,0.04)]"
                          : "border-white/10 bg-white/[0.02] hover:border-white/20"
                      }`}
                    >

                      <div className="flex items-center justify-between">

                        <p className="text-xs font-medium">
                          {name}
                        </p>

                        {scanType === name && (
                          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                        )}

                      </div>

                      <p className="mt-2 text-[10px] leading-relaxed text-white/25">
                        {description}
                      </p>

                    </button>

                  ))}

                </div>
              </div>

              {/* AGENTS */}
              <div>

                <label className="mb-3 block text-xs text-white/50">
                  Autonomous Agents
                </label>

                <div className="grid gap-3 sm:grid-cols-2">

                  {[
                    ["Recon Agent", "Attack surface discovery"],
                    ["Exploit Agent", "Controlled validation"],
                    ["Vulnerability Agent", "CVE analysis"],
                    ["Patch Agent", "Remediation suggestions"],
                  ].map(([name, description], index) => (

                    <label
                      key={name}
                      className={`flex items-center gap-4 rounded-xl border border-white/10 bg-white/[0.02] p-4 transition ${
                        scanning
                          ? "opacity-50"
                          : "hover:border-cyan-400/20"
                      }`}
                    >

                      <input
                        type="checkbox"
                        defaultChecked={index < 3}
                        disabled={scanning}
                        className="h-4 w-4 accent-cyan-400"
                      />

                      <div>
                        <p className="text-xs font-medium">
                          {name}
                        </p>

                        <p className="mt-1 text-[10px] text-white/25">
                          {description}
                        </p>
                      </div>

                    </label>

                  ))}

                </div>

              </div>

              {/* START BUTTON */}
              {!scanning ? (
                <Button
                  onClick={startScan}
                  disabled={!target.trim()}
                  className="h-12 w-full rounded-xl bg-cyan-400 font-semibold text-black hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-30"
                >
                  Initialize Autonomous Scan
                </Button>
              ) : (
                <Button
                  onClick={resetScan}
                  variant="outline"
                  className="h-12 w-full rounded-xl border-red-400/20 bg-red-400/5 text-red-400 hover:bg-red-400/10"
                >
                  Stop Scan
                </Button>
              )}

            </div>
          </div>

          {/* SCAN ENGINE */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-6 backdrop-blur-xl">

            <p className="text-[9px] tracking-[0.2em] text-white/25">
              SCAN ENGINE
            </p>

            {/* SCANNER */}
            <div className="mt-8 flex justify-center">

              <div
                className={`relative flex h-48 w-48 items-center justify-center rounded-full border transition ${
                  scanning
                    ? "border-cyan-400/30"
                    : "border-white/10"
                }`}
              >

                {scanning && (
                  <>
                    <div className="absolute inset-2 animate-ping rounded-full border border-cyan-400/10" />

                    <div className="absolute inset-5 rounded-full border border-cyan-400/10" />

                    <div className="absolute inset-8 rounded-full border border-cyan-400/10" />
                  </>
                )}

                <div className="text-center">

                  <div
                    className={`mx-auto h-3 w-3 rounded-full transition ${
                      scanning
                        ? "animate-pulse bg-cyan-400 shadow-[0_0_25px_rgba(34,211,238,0.9)]"
                        : "bg-emerald-400"
                    }`}
                  />

                  <p className="mt-4 text-[10px] tracking-[0.2em] text-cyan-300">
                    {scanning
                      ? `${progress}%`
                      : "READY"}
                  </p>

                  <p className="mt-1 max-w-[130px] text-[9px] text-white/25">
                    {scanning
                      ? scanSteps[step]
                      : "AWAITING TARGET"}
                  </p>

                </div>

              </div>

            </div>

            {/* PROGRESS */}
            {scanning && (
              <div className="mt-8">

                <div className="mb-2 flex justify-between text-[9px]">

                  <span className="text-white/25">
                    SCAN PROGRESS
                  </span>

                  <span className="text-cyan-300">
                    {progress}%
                  </span>

                </div>

                <div className="h-1.5 overflow-hidden rounded-full bg-white/5">

                  <div
                    className="h-full rounded-full bg-cyan-400 transition-all duration-200"
                    style={{
                      width: `${progress}%`,
                    }}
                  />

                </div>

              </div>
            )}

            {/* ENGINE INFO */}
            <div className="mt-8 space-y-4">

              {[
                ["Agents Available", "08"],
                ["Scan Profile", scanType],
                ["Current Target", target || "Not configured"],
                ["Last Scan", "2m ago"],
              ].map(([name, value]) => (

                <div
                  key={name}
                  className="border-b border-white/5 pb-3"
                >

                  <div className="flex justify-between gap-4">

                    <span className="text-[10px] text-white/25">
                      {name}
                    </span>

                    <span className="max-w-[150px] truncate text-right text-[10px] text-white/60">
                      {value}
                    </span>

                  </div>

                </div>

              ))}

            </div>

          </div>

        </section>

        {/* SCAN COMPLETE */}
        {!scanning && progress === 100 && (
          <section className="mt-6 rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.04] p-6">

            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">

              <div className="flex items-center gap-4">

                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-400/10 text-emerald-400">
                  ✓
                </div>

                <div>

                  <p className="text-sm font-medium text-emerald-400">
                    Scan completed successfully
                  </p>

                  <p className="mt-1 text-xs text-white/30">
                    Security analysis is ready for review.
                  </p>

                </div>

              </div>

              <Button
                variant="outline"
                className="border-emerald-400/20 bg-emerald-400/5 text-emerald-400 hover:bg-emerald-400/10"
              >
                View Findings →
              </Button>

            </div>

          </section>
        )}

        {/* CONNECTED TARGETS */}
        <section className="mt-8">

          <div className="mb-4">

            <h2 className="font-medium">
              Connected Targets
            </h2>

            <p className="mt-1 text-xs text-white/30">
              Infrastructure currently monitored by SwarmShield.
            </p>

          </div>

          <div className="grid gap-4 lg:grid-cols-3">

            {targets.map((item) => (

              <div
                key={item.name}
                className="group rounded-2xl border border-white/10 bg-white/[0.025] p-5 backdrop-blur-xl transition duration-300 hover:-translate-y-1 hover:border-cyan-400/20"
              >

                <div className="flex items-start justify-between">

                  <div>

                    <p className="text-sm font-medium">
                      {item.name}
                    </p>

                    <p className="mt-1 text-[10px] text-white/25">
                      {item.type}
                    </p>

                  </div>

                  <span
                    className={`text-[8px] tracking-widest ${
                      item.status === "HEALTHY"
                        ? "text-emerald-400"
                        : item.status === "WARNING"
                        ? "text-yellow-400"
                        : "text-red-400"
                    }`}
                  >
                    {item.status}
                  </span>

                </div>

                <div className="mt-6">

                  <div className="mb-2 flex justify-between text-[9px]">

                    <span className="text-white/20">
                      SECURITY SCORE
                    </span>

                    <span>
                      {item.score}%
                    </span>

                  </div>

                  <div className="h-1 rounded-full bg-white/5">

                    <div
                      className={`h-full rounded-full ${
                        item.status === "HEALTHY"
                          ? "bg-emerald-400"
                          : item.status === "WARNING"
                          ? "bg-yellow-400"
                          : "bg-red-400"
                      }`}
                      style={{
                        width: `${item.score}%`,
                      }}
                    />

                  </div>

                </div>

              </div>

            ))}

          </div>

        </section>

      </div>
    </div>
  );
}