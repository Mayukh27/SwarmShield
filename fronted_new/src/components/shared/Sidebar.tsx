import { NavLink } from "react-router-dom";

const navigation = [
  { icon: "⌂", label: "Overview", path: "/dashboard" },
  { icon: "◈", label: "AI Agents", path: "/agents" },
  { icon: "◎", label: "Targets", path: "/targets" },
  { icon: "⚠", label: "Vulnerabilities", path: "/vulnerabilities" },
  { icon: "◇", label: "Patch Center", path: "/patch-center" },
  { icon: "▣", label: "Reports", path: "/reports" },
];

export default function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-white/10 bg-black/40 backdrop-blur-xl lg:flex">

      {/* Logo */}
      <div className="flex h-20 items-center gap-3 border-b border-white/10 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-cyan-400/30 bg-cyan-400/10">
          <span className="font-bold text-cyan-300">S</span>
        </div>

        <div>
          <p className="text-sm font-semibold tracking-widest">
            SWARMSHIELD
          </p>

          <p className="text-[9px] tracking-widest text-white/30">
            COMMAND CENTER
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-4">
        {navigation.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm transition ${
                isActive
                  ? "border border-cyan-400/10 bg-cyan-400/10 text-cyan-300"
                  : "text-white/40 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <span className="w-5 text-center">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* System status */}
      <div className="m-4 rounded-xl border border-emerald-400/10 bg-emerald-400/5 p-4">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />

          <span className="text-xs text-emerald-300">
            SYSTEM OPERATIONAL
          </span>
        </div>

        <p className="mt-2 text-[10px] text-white/30">
          Autonomous network connected
        </p>
      </div>
    </aside>
  );
}