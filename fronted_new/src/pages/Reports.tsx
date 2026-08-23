import { Button } from "@/components/ui/button";

const reports = [
  {
    id: "RPT-026",
    title: "Weekly Security Assessment",
    type: "SECURITY ASSESSMENT",
    date: "22 Aug 2026",
    findings: 24,
    score: 87,
    status: "READY",
  },
  {
    id: "RPT-025",
    title: "API Infrastructure Scan",
    type: "TARGET SCAN",
    date: "21 Aug 2026",
    findings: 18,
    score: 82,
    status: "READY",
  },
  {
    id: "RPT-024",
    title: "Authentication Security Review",
    type: "DEEP ANALYSIS",
    date: "20 Aug 2026",
    findings: 11,
    score: 76,
    status: "READY",
  },
];

const metrics = [
  ["Security Score", "87", "+4.2%"],
  ["Findings Resolved", "18", "+6"],
  ["Critical Findings", "03", "-2"],
  ["Agents Executed", "126", "+18"],
];

export default function Reports() {
  return (
    <div>
      {/* HEADER */}
      <header className="flex min-h-20 items-center justify-between border-b border-white/10 bg-black/30 px-6 backdrop-blur-xl lg:px-8">
        <div>
          <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">
            SECURITY INTELLIGENCE
          </p>

          <h1 className="mt-1 text-xl font-semibold">
            Reports
          </h1>
        </div>

        <Button className="bg-cyan-400 text-black hover:bg-cyan-300">
          Generate Report
        </Button>
      </header>

      <div className="p-6 lg:p-8">

        {/* INTRO */}
        <section className="mb-6 rounded-2xl border border-cyan-400/10 bg-cyan-400/[0.03] p-6">

          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">

            <div>
              <p className="text-[10px] tracking-[0.25em] text-cyan-300">
                SECURITY REPORTING ENGINE
              </p>

              <h2 className="mt-3 text-2xl font-semibold">
                Security intelligence at a glance.
              </h2>

              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-white/35">
                Review security posture, autonomous agent activity,
                vulnerability trends and remediation progress.
              </p>
            </div>

            <div className="rounded-xl border border-cyan-400/10 bg-black/20 px-5 py-4">
              <p className="text-[9px] tracking-widest text-white/25">
                REPORTS GENERATED
              </p>

              <p className="mt-1 text-2xl font-semibold">
                26
              </p>
            </div>

          </div>
        </section>

        {/* METRICS */}
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

          {metrics.map(([title, value, change]) => (

            <div
              key={title}
              className="rounded-2xl border border-white/10 bg-white/[0.025] p-5 backdrop-blur-xl transition hover:-translate-y-1 hover:border-cyan-400/20"
            >

              <p className="text-xs text-white/35">
                {title}
              </p>

              <div className="mt-5 flex items-end justify-between">

                <p className="text-3xl font-semibold">
                  {value}
                </p>

                <span className="text-xs text-emerald-400">
                  {change}
                </span>

              </div>

            </div>

          ))}

        </section>

        {/* SECURITY POSTURE */}
        <section className="mt-6 grid gap-6 xl:grid-cols-3">

          <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-6 backdrop-blur-xl xl:col-span-2">

            <div className="flex items-center justify-between">

              <div>
                <h2 className="font-medium">
                  Security Posture
                </h2>

                <p className="mt-1 text-xs text-white/30">
                  Infrastructure security trend
                </p>
              </div>

              <span className="text-[9px] tracking-widest text-emerald-400">
                IMPROVING
              </span>

            </div>

            {/* Fake chart */}
            <div className="relative mt-8 h-48 overflow-hidden rounded-xl border border-white/5 bg-black/20">

              <div className="absolute inset-0 flex flex-col justify-between p-5">

                {[100, 75, 50, 25, 0].map((value) => (
                  <div
                    key={value}
                    className="border-t border-white/5"
                  />
                ))}

              </div>

              <svg
                viewBox="0 0 800 220"
                preserveAspectRatio="none"
                className="absolute inset-0 h-full w-full"
              >
                <polyline
                  points="0,175 100,160 200,165 300,130 400,142 500,105 600,95 700,65 800,45"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  className="text-cyan-400"
                />

                <polyline
                  points="0,175 100,160 200,165 300,130 400,142 500,105 600,95 700,65 800,45 800,220 0,220"
                  fill="currentColor"
                  className="text-cyan-400/5"
                />
              </svg>

              <div className="absolute bottom-3 left-5 right-5 flex justify-between text-[8px] tracking-widest text-white/20">
                <span>JUN</span>
                <span>JUL</span>
                <span>AUG</span>
              </div>

            </div>

            <div className="mt-5 grid grid-cols-3 gap-4">

              {[
                ["Jun", "74"],
                ["Jul", "81"],
                ["Aug", "87"],
              ].map(([month, score]) => (

                <div
                  key={month}
                  className="rounded-xl border border-white/5 bg-black/20 p-4 text-center"
                >
                  <p className="text-[9px] text-white/25">
                    {month}
                  </p>

                  <p className="mt-2 text-lg font-semibold">
                    {score}
                  </p>

                </div>

              ))}

            </div>

          </div>

          {/* RISK DISTRIBUTION */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-6 backdrop-blur-xl">

            <h2 className="font-medium">
              Risk Distribution
            </h2>

            <p className="mt-1 text-xs text-white/30">
              Current vulnerability severity
            </p>

            <div className="mt-8 flex justify-center">

              <div className="relative flex h-44 w-44 items-center justify-center rounded-full border-[18px] border-white/5">

                <div className="absolute inset-[-18px] rounded-full border-[18px] border-transparent border-t-red-400 border-r-orange-400 border-b-yellow-400 rotate-[20deg]" />

                <div className="text-center">

                  <p className="text-3xl font-semibold">
                    24
                  </p>

                  <p className="text-[8px] tracking-widest text-white/25">
                    FINDINGS
                  </p>

                </div>

              </div>

            </div>

            <div className="mt-8 space-y-4">

              {[
                ["Critical", "03", "12%"],
                ["High", "07", "29%"],
                ["Medium", "10", "42%"],
                ["Low", "04", "17%"],
              ].map(([name, count, percentage]) => (

                <div
                  key={name}
                  className="flex items-center justify-between"
                >

                  <div className="flex items-center gap-2">

                    <span
                      className={`h-2 w-2 rounded-full ${
                        name === "Critical"
                          ? "bg-red-400"
                          : name === "High"
                          ? "bg-orange-400"
                          : name === "Medium"
                          ? "bg-yellow-400"
                          : "bg-emerald-400"
                      }`}
                    />

                    <span className="text-xs text-white/40">
                      {name}
                    </span>

                  </div>

                  <div className="flex gap-4 text-xs">

                    <span className="text-white/60">
                      {count}
                    </span>

                    <span className="text-white/20">
                      {percentage}
                    </span>

                  </div>

                </div>

              ))}

            </div>

          </div>

        </section>

        {/* REPORT LIST */}
        <section className="mt-6 overflow-hidden rounded-2xl border border-white/10 bg-white/[0.025] backdrop-blur-xl">

          <div className="flex items-center justify-between border-b border-white/10 p-5">

            <div>
              <h2 className="font-medium">
                Generated Reports
              </h2>

              <p className="mt-1 text-xs text-white/30">
                Security reports generated by SwarmShield
              </p>
            </div>

            <Button
              variant="outline"
              className="border-white/10 bg-white/5 text-xs text-white hover:bg-white/10"
            >
              Export All
            </Button>

          </div>

          <div>

            {reports.map((report) => (

              <div
                key={report.id}
                className="flex flex-col justify-between gap-5 border-b border-white/5 p-5 transition hover:bg-white/[0.025] md:flex-row md:items-center"
              >

                <div className="flex items-center gap-4">

                  <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-400/10 bg-cyan-400/5 text-cyan-300">
                    ▣
                  </div>

                  <div>

                    <p className="text-sm font-medium">
                      {report.title}
                    </p>

                    <p className="mt-1 text-[9px] tracking-widest text-white/20">
                      {report.id} · {report.type}
                    </p>

                  </div>

                </div>

                <div className="grid grid-cols-3 gap-8 text-xs">

                  <div>
                    <p className="text-[8px] tracking-widest text-white/20">
                      DATE
                    </p>

                    <p className="mt-1 text-white/45">
                      {report.date}
                    </p>
                  </div>

                  <div>
                    <p className="text-[8px] tracking-widest text-white/20">
                      FINDINGS
                    </p>

                    <p className="mt-1 text-white/45">
                      {report.findings}
                    </p>
                  </div>

                  <div>
                    <p className="text-[8px] tracking-widest text-white/20">
                      SCORE
                    </p>

                    <p className="mt-1 text-cyan-300">
                      {report.score}
                    </p>
                  </div>

                </div>

                <div className="flex items-center gap-3">

                  <span className="text-[8px] tracking-widest text-emerald-400">
                    {report.status}
                  </span>

                  <Button
                    variant="outline"
                    className="border-white/10 bg-white/5 text-xs text-white hover:bg-white/10"
                  >
                    View
                  </Button>

                  <Button
                    variant="outline"
                    className="border-white/10 bg-white/5 text-xs text-white hover:bg-white/10"
                  >
                    Export
                  </Button>

                </div>

              </div>

            ))}

          </div>

        </section>

        {/* AI SUMMARY */}
        <section className="mt-6 rounded-2xl border border-cyan-400/10 bg-cyan-400/[0.03] p-6">

          <div className="flex items-start gap-4">

            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan-400/20 bg-cyan-400/10 text-xs text-cyan-300">
              AI
            </div>

            <div>

              <p className="text-[9px] tracking-[0.2em] text-cyan-300/60">
                AI EXECUTIVE SUMMARY
              </p>

              <h3 className="mt-2 text-sm font-medium">
                Security posture improved 4.2% this period.
              </h3>

              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-white/35">
                Autonomous agents identified 24 vulnerabilities,
                including 3 critical findings. 18 previously
                identified issues have been resolved and the overall
                infrastructure security score is currently 87.
              </p>

            </div>

          </div>

        </section>

      </div>
    </div>
  );
}