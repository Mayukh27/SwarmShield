// Primary six, mirroring the Sidebar's SOC section — kept compact for small
// screens. Siege Mode (War Room / Live Siege / Outcome / War Log) and
// Settings stay reachable from the Sidebar on larger screens; that's a
// mobile-layout call, not a functionality removal — every screen still
// renders and is routable via `screen` state regardless of viewport.
const NAV_ITEMS = [
<<<<<<< Updated upstream
  { id: "warroom", icon: "🏰", label: "War Room", sub: "Overview" },
  { id: "registry", icon: "🗺️", label: "Realm Registry", sub: "Targets" },
  { id: "intel", icon: "🧠", label: "Intelligence", sub: "Capabilities" },
  { id: "siege", icon: "⚔️", label: "Live Siege", sub: "Active scan" },
  { id: "report", icon: "📜", label: "Siege Report", sub: "Findings" },
  { id: "forge", icon: "🔨", label: "Remediation Forge", sub: "Fix & verify" },
  { id: "timeline", icon: "📜", label: "War Log", sub: "Timeline" },
  { id: "outcome", icon: "🏆", label: "Outcome", sub: "Results" },
  { id: "settings", icon: "⚙️", label: "Settings", sub: "" },
=======
  { id: "dashboard", label: "Dashboard", icon: "⌂" },
  { id: "agents", label: "Agents", icon: "◈" },
  { id: "targets", label: "Targets", icon: "◎" },
  { id: "vulnerabilities", label: "Vulns", icon: "△" },
  { id: "patches", label: "Patches", icon: "◇" },
  { id: "reports", label: "Reports", icon: "▤" },
>>>>>>> Stashed changes
];

export default function BottomNav({ screen, onNavigate }) {
  return (
    <nav className="glass-header flex shrink-0 items-stretch justify-around lg:hidden">
      {NAV_ITEMS.map((item) => {
        const active = screen === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            title={item.label}
            className={`flex flex-1 flex-col items-center gap-0.5 px-2 py-2.5 text-base transition-colors ${
              active ? "border-t-2 border-amber-400 bg-amber-400/[0.08] text-amber-300" : "border-t-2 border-transparent text-white/40 hover:text-white"
            }`}
          >
            <span className="leading-none">{item.icon}</span>
            <span className="text-[9px] font-medium leading-none">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
