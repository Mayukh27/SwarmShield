const NAV_ITEMS = [
  { id: "warroom", icon: "🏰", label: "War Room", sub: "Overview" },
  { id: "registry", icon: "🗺️", label: "Realm Registry", sub: "Targets" },
  { id: "intel", icon: "🧠", label: "Intelligence", sub: "Capabilities" },
  { id: "siege", icon: "⚔️", label: "Live Siege", sub: "Active scan" },
  { id: "report", icon: "📜", label: "Siege Report", sub: "Findings" },
  { id: "forge", icon: "🔨", label: "Remediation Forge", sub: "Fix & verify" },
  { id: "timeline", icon: "📜", label: "War Log", sub: "Timeline" },
  { id: "outcome", icon: "🏆", label: "Outcome", sub: "Results" },
  { id: "settings", icon: "⚙️", label: "Settings", sub: "" },
];

export default function BottomNav({ screen, onNavigate, hasActiveScan }) {
  return (
    <nav className="flex shrink-0 items-stretch justify-around border-t border-grid bg-panel/90 backdrop-blur">
      {NAV_ITEMS.map((item) => {
        const active = screen === item.id;
        const disabled = (item.id === "siege" || item.id === "outcome") && !hasActiveScan;
        return (
          <button
            key={item.id}
            onClick={() => !disabled && onNavigate(item.id)}
            disabled={disabled}
            title={item.label}
            className={`flex flex-1 flex-col items-center gap-0.5 px-2 py-2.5 transition-colors ${
              active
                ? "border-t-2 border-gold bg-gold-dim/40 text-gold"
                : disabled
                ? "border-t-2 border-transparent text-text-muted/30"
                : "border-t-2 border-transparent text-text-muted hover:text-text-primary"
            }`}
          >
            <span className="text-base leading-none">{item.icon}</span>
            <span className="font-mono text-[9px] font-medium leading-none">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
