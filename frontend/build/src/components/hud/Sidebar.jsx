const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "⌂" },
  { id: "agents", label: "AI Agents", icon: "◈" },
  { id: "targets", label: "Targets", icon: "◎" },
  { id: "vulnerabilities", label: "Vulnerabilities", icon: "△" },
  { id: "patches", label: "Patch Center", icon: "◇" },
  { id: "intel", label: "Intelligence", icon: "◆" },
  { id: "reports", label: "Reports", icon: "▤" },
];

// Siege-mode screens — same real scan/store data as the sections above,
// ported from the original build's WarRoom/LiveSiege/Outcome/Timeline flow.
// Grouped separately since they're a different (gamified) lens on the same
// live scan rather than another SOC data screen.
const SIEGE_NAV_ITEMS = [
  { id: "warroom", label: "War Room", icon: "⚔️" },
  { id: "siege", label: "Live Siege", icon: "🏰" },
  { id: "outcome", label: "Outcome", icon: "🏆" },
  { id: "timeline", label: "War Log", icon: "📜" },
];

export default function Sidebar({ screen, onNavigate, systemOnline }) {
  return (
    <aside className="relative z-10 hidden h-screen w-64 shrink-0 flex-col border-r border-white/[0.07] bg-[#05070a]/75 backdrop-blur-2xl lg:flex">
      {/* LOGO */}
      <div className="flex h-20 items-center border-b border-white/[0.07] px-6">
        <div className="mr-3 flex h-9 w-9 items-center justify-center rounded-xl border border-amber-400/25 bg-amber-400/[0.08] shadow-[0_0_25px_rgba(242,184,75,0.14)]">
          <span className="text-sm font-bold text-amber-300">S</span>
        </div>
        <div>
          <p className="text-sm font-semibold tracking-wide text-text-primary">SwarmShield</p>
          <p className="mt-0.5 text-[8px] tracking-[0.2em] text-white/25">AUTONOMOUS SECURITY</p>
        </div>
      </div>

      {/* NAVIGATION */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-4">
        {NAV_ITEMS.map((item) => {
          const active = screen === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`group relative flex h-11 w-full items-center gap-3 rounded-xl px-4 text-left text-xs transition-all duration-300 ${
                active
                  ? "border border-amber-400/30 bg-amber-400/[0.08] text-amber-300 shadow-[0_0_20px_rgba(242,184,75,0.08)]"
                  : "border border-transparent text-white/40 hover:bg-white/[0.035] hover:text-white"
              }`}
            >
              <span
                className={`text-base transition-all duration-300 group-hover:scale-110 ${
                  active ? "text-amber-300" : "text-white/30 group-hover:text-white/60"
                }`}
              >
                {item.icon}
              </span>
              <span>{item.label}</span>
              {active && (
                <span className="absolute right-3 h-1 w-1 rounded-full bg-amber-300 shadow-[0_0_10px_rgba(242,184,75,0.9)]" />
              )}
            </button>
          );
        })}

        <p className="px-4 pb-1 pt-4 text-[9px] font-medium tracking-[0.2em] text-white/20">SIEGE MODE</p>
        {SIEGE_NAV_ITEMS.map((item) => {
          const active = screen === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`group relative flex h-11 w-full items-center gap-3 rounded-xl px-4 text-left text-xs transition-all duration-300 ${
                active
                  ? "border border-cyan-400/30 bg-cyan-400/[0.08] text-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.08)]"
                  : "border border-transparent text-white/40 hover:bg-white/[0.035] hover:text-white"
              }`}
            >
              <span
                className={`text-base transition-all duration-300 group-hover:scale-110 ${
                  active ? "text-cyan-300" : "text-white/30 group-hover:text-white/60"
                }`}
              >
                {item.icon}
              </span>
              <span>{item.label}</span>
              {active && (
                <span className="absolute right-3 h-1 w-1 rounded-full bg-cyan-300 shadow-[0_0_10px_rgba(34,211,238,0.9)]" />
              )}
            </button>
          );
        })}
      </nav>

      {/* SYSTEM STATUS — real health check, not a fixed label */}
      <div className="glass m-4 rounded-xl p-4">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            {systemOnline !== false && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-40" />
            )}
            <span
              className={`relative inline-flex h-2 w-2 rounded-full ${
                systemOnline === false ? "bg-critical" : "bg-emerald-400"
              }`}
            />
          </span>
          <span
            className={`text-[9px] tracking-widest ${
              systemOnline === false ? "text-critical" : "text-emerald-400"
            }`}
          >
            {systemOnline === false ? "SYSTEM OFFLINE" : "SYSTEM OPERATIONAL"}
          </span>
        </div>
        <p className="mt-2 text-[9px] leading-relaxed text-white/20">
          Autonomous security agents are monitoring your infrastructure.
        </p>
      </div>
    </aside>
  );
}
