import { NavLink, Outlet } from "react-router-dom";
import FloatingLines from "@/components/FloatingLines";

export default function DashboardLayout() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#05030a] text-white">

      {/* ========================================================= */}
      {/* REACT BITS — PROMINENT FLOATING LINES */}
      {/* ========================================================= */}

      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">

        {/* Main animated lines */}
        <div
          className="absolute inset-[-10%] opacity-[0.78]"
          style={{
            filter:
              "hue-rotate(105deg) saturate(1.7) brightness(1.35)",
          }}
        >
          <FloatingLines
            enabledWaves={["top", "middle", "bottom"]}
            lineCount={10}
            lineDistance={4}
            animationSpeed={0.45}
          />
        </div>

        {/* Purple atmospheric glow */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(168,85,247,0.12),transparent_55%)]" />

        {/* Pink/violet light source */}
        <div className="absolute left-[55%] top-[25%] h-[500px] w-[700px] -translate-x-1/2 rounded-full bg-fuchsia-500/[0.035] blur-[140px]" />

        {/* Keep background dark but NOT hidden */}
        <div className="absolute inset-0 bg-[#05030a]/25" />

        {/* Very subtle grid */}
        <div
          className="absolute inset-0 opacity-[0.025]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.5) 1px, transparent 1px)",
            backgroundSize: "64px 64px",
          }}
        />

        {/* Bottom fade */}
        <div className="absolute inset-x-0 bottom-0 h-64 bg-gradient-to-t from-[#05030a] to-transparent" />

      </div>


      {/* ========================================================= */}
      {/* SIDEBAR */}
      {/* ========================================================= */}

      <aside className="fixed left-0 top-0 z-40 hidden h-screen w-64 border-r border-white/[0.07] bg-[#05030a]/75 backdrop-blur-2xl lg:block">

        {/* LOGO */}
        <div className="flex h-20 items-center border-b border-white/[0.07] px-6">

          <div className="mr-3 flex h-9 w-9 items-center justify-center rounded-xl border border-violet-400/20 bg-violet-400/[0.07] shadow-[0_0_25px_rgba(139,92,246,0.12)]">

            <span className="text-sm font-bold text-violet-300">
              S
            </span>

          </div>

          <div>

            <p className="text-sm font-semibold tracking-wide">
              SwarmShield
            </p>

            <p className="mt-0.5 text-[8px] tracking-[0.2em] text-white/25">
              SECURITY PLATFORM
            </p>

          </div>

        </div>


        {/* ======================================================= */}
        {/* NAVIGATION */}
        {/* ======================================================= */}

        <nav className="space-y-1 p-4">

          <NavItem
            href="/dashboard"
            label="Dashboard"
            icon="⌂"
          />

          <NavItem
            href="/agents"
            label="AI Agents"
            icon="◈"
          />

          <NavItem
            href="/targets"
            label="Targets"
            icon="◎"
          />

          <NavItem
            href="/vulnerabilities"
            label="Vulnerabilities"
            icon="△"
          />

          <NavItem
            href="/patch-center"
            label="Patch Center"
            icon="◇"
          />

          <NavItem
            href="/reports"
            label="Reports"
            icon="▤"
          />

        </nav>


        {/* ======================================================= */}
        {/* SYSTEM STATUS */}
        {/* ======================================================= */}

        <div className="absolute bottom-5 left-4 right-4 rounded-xl border border-white/[0.07] bg-white/[0.025] p-4 backdrop-blur-xl">

          <div className="flex items-center gap-2">

            <span className="relative flex h-2 w-2">

              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-40" />

              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />

            </span>

            <span className="text-[9px] tracking-widest text-emerald-400">
              SYSTEM OPERATIONAL
            </span>

          </div>

          <p className="mt-2 text-[9px] leading-relaxed text-white/20">
            Autonomous security agents are monitoring your infrastructure.
          </p>

        </div>

      </aside>


      {/* ========================================================= */}
      {/* MAIN APPLICATION */}
      {/* ========================================================= */}

      <main className="relative z-10 min-h-screen lg:ml-64">
        <Outlet />
      </main>

    </div>
  );
}


/* =============================================================== */
/* NAV ITEM */
/* =============================================================== */

function NavItem({
  href,
  label,
  icon,
}: {
  href: string;
  label: string;
  icon: string;
}) {
  return (
    <NavLink
      to={href}
      className={({ isActive }) =>
        `group relative flex h-11 items-center gap-3 rounded-xl px-4 text-xs transition-all duration-300 ${
          isActive
            ? "border border-violet-400/15 bg-violet-400/[0.08] text-violet-300 shadow-[inset_2px_0_0_rgba(139,92,246,0.9)]"
            : "text-white/40 hover:bg-white/[0.035] hover:text-white"
        }`
      }
    >
      {({ isActive }) => (
        <>
          <span
            className={`text-base transition-all duration-300 group-hover:scale-110 ${
              isActive
                ? "text-violet-300"
                : "text-white/30 group-hover:text-white/60"
            }`}
          >
            {icon}
          </span>

          <span>
            {label}
          </span>

          {isActive && (
            <span className="absolute right-3 h-1 w-1 rounded-full bg-violet-300 shadow-[0_0_10px_rgba(139,92,246,0.9)]" />
          )}
        </>
      )}
    </NavLink>
  );
}