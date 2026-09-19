import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useScanStore } from "../store/scanStore";

export default function TargetPanel({ onStartScan, scanInFlight }) {
  const targets = useScanStore((s) => s.targets);
  const setTargets = useScanStore((s) => s.setTargets);
  const selectedTargetId = useScanStore((s) => s.selectedTargetId);
  const selectTarget = useScanStore((s) => s.selectTarget);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", endpoint_url: "", tools: "" });
  const [submitting, setSubmitting] = useState(false);

  const loadTargets = async () => {
    const list = await api.listTargets();
    setTargets(list);
    if (!selectedTargetId && list.length > 0) selectTarget(list[0].id);
  };

  useEffect(() => {
    loadTargets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const toolNames = form.tools
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const target = await api.createTarget({
        name: form.name,
        endpoint_url: form.endpoint_url,
        declared_tools: {
          tools: toolNames.map((name) => ({ name, description: "", permissions: [] })),
        },
        permission_map: {},
      });
      await loadTargets();
      selectTarget(target.id);
      setForm({ name: "", endpoint_url: "", tools: "" });
      setShowForm(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-lg border border-grid bg-panel p-4">
      <div className="flex items-center justify-between">
        <span className="font-display text-xs font-semibold tracking-widest text-text-muted">
          TARGET
        </span>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="font-mono text-[11px] text-amber hover:underline"
        >
          {showForm ? "Cancel" : "+ New target"}
        </button>
      </div>

      {showForm ? (
        <form onSubmit={handleCreate} className="mt-3 flex flex-col gap-2">
          <input
            required
            placeholder="Name (e.g. Support Agent v2)"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="rounded border border-grid bg-void px-2.5 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:border-amber"
          />
          <input
            required
            placeholder="Endpoint URL"
            value={form.endpoint_url}
            onChange={(e) => setForm({ ...form, endpoint_url: e.target.value })}
            className="rounded border border-grid bg-void px-2.5 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:border-amber"
          />
          <input
            placeholder="Declared tools, comma-separated"
            value={form.tools}
            onChange={(e) => setForm({ ...form, tools: e.target.value })}
            className="rounded border border-grid bg-void px-2.5 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:border-amber"
          />
          <button
            type="submit"
            disabled={submitting}
            className="mt-1 rounded bg-amber px-3 py-1.5 font-mono text-xs font-semibold text-void hover:bg-amber/90 disabled:opacity-50"
          >
            {submitting ? "Creating…" : "Create target"}
          </button>
        </form>
      ) : (
        <>
          <select
            value={selectedTargetId || ""}
            onChange={(e) => selectTarget(e.target.value)}
            className="mt-3 w-full rounded border border-grid bg-void px-2.5 py-1.5 text-sm text-text-primary focus:border-amber"
          >
            {targets.length === 0 && <option value="">No targets yet</option>}
            {targets.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>

          <button
            onClick={() => onStartScan(selectedTargetId)}
            disabled={!selectedTargetId || scanInFlight}
            className="mt-3 w-full rounded bg-amber px-3 py-2 font-mono text-xs font-semibold text-void transition-colors hover:bg-amber/90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {scanInFlight ? "Swarm active…" : "Launch swarm scan"}
          </button>
        </>
      )}
    </div>
  );
}
