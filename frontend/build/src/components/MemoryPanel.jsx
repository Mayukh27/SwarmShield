import { useScanStore } from "../store/scanStore";

const TYPE_STYLE = {
  success: "text-cyan bg-cyan-dim border-cyan/30",
  failure: "text-text-muted bg-panel-raised border-grid",
  vulnerability: "text-critical bg-critical-dim border-critical/40",
  discovery: "text-amber bg-amber-dim border-amber/30",
};

export default function MemoryPanel() {
  const memory = useScanStore((s) => s.memory);

  return (
    <div className="rounded-lg border border-grid bg-panel">
      <div className="border-b border-grid px-4 py-2.5 font-display text-xs font-semibold tracking-widest text-text-muted">
        SHARED MEMORY
      </div>
      <div className="max-h-64 overflow-y-auto divide-y divide-grid">
        {memory.length === 0 ? (
          <p className="px-4 py-3 text-sm text-text-muted">
            No memory items yet — specialists write here after every attempt,
            and later vectors consult it before attacking.
          </p>
        ) : (
          memory.map((m) => (
            <div key={m.id} className="px-4 py-2.5">
              <div className="flex items-center gap-2">
                <span
                  className={`shrink-0 rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase ${
                    TYPE_STYLE[m.memory_type] || TYPE_STYLE.discovery
                  }`}
                >
                  {m.memory_type}
                </span>
                <span className="font-mono text-[11px] text-text-muted">{m.agent}</span>
                <span className="ml-auto font-mono text-[10px] text-text-muted">
                  conf {Math.round(m.confidence * 100)}%
                </span>
              </div>
              <p className="mt-1 text-sm text-text-primary">{m.content}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
