import { useEffect, useState } from "react";
import { api } from "../../lib/api";

/**
 * Shared page header for the liquid-glass shell. `eyebrow`/`title` describe
 * the current screen. `online` reflects a real backend health check (the
 * local-first LLM router health endpoint), not a hardcoded "online" label.
 */
export default function Header({ eyebrow, title, onNewScan, scanInFlight, onOpenSettings }) {
  const [online, setOnline] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        await api.getLlmHealth();
        if (!cancelled) setOnline(true);
      } catch {
        if (!cancelled) setOnline(false);
      }
    };
    check();
    const id = setInterval(check, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <header className="glass-header sticky top-0 z-20 flex min-h-20 items-center justify-between px-6 lg:px-8">
      <div>
        <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">{eyebrow}</p>
        <h1 className="mt-1 text-xl font-semibold text-text-primary">{title}</h1>
      </div>

      <div className="flex items-center gap-3">
        <div
          className={`hidden items-center gap-2 rounded-lg border px-3 py-2 text-[10px] md:flex ${
            online === false
              ? "border-critical/20 bg-critical/5 text-critical"
              : "border-emerald-400/10 bg-emerald-400/5 text-emerald-400"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              online === false ? "bg-critical" : "animate-pulse bg-emerald-400"
            }`}
          />
          {online === null ? "CHECKING…" : online ? "SYSTEM ONLINE" : "SYSTEM OFFLINE"}
        </div>

        {onNewScan && (
          <button
            onClick={onNewScan}
            disabled={scanInFlight}
            className="rounded-lg bg-cyan-400 px-4 py-2 text-xs font-semibold text-black transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {scanInFlight ? "Scan running…" : "+ New Scan"}
          </button>
        )}

        <button
          onClick={onOpenSettings}
          title="Settings"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-xs text-text-primary transition hover:bg-white/10"
        >
          SP
        </button>
      </div>
    </header>
  );
}
