import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "../lib/api";
import { useScanStore } from "../store/scanStore";

export default function RealmRegistry({ onDeclareWar, scanInFlight }) {
  const targets = useScanStore((s) => s.targets);
  const setTargets = useScanStore((s) => s.setTargets);
  const selectedTargetId = useScanStore((s) => s.selectedTargetId);
  const selectTarget = useScanStore((s) => s.selectTarget);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    endpoint_url: "",
    tools: "",
    authorized: false,
    code_visibility: "unknown",
    access_mode: "read_only",
    allow_pr_creation: false,
    allow_branch_write: false,
    allow_direct_patch_apply: false,
  });
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
      const toolNames = form.tools.split(",").map((t) => t.trim()).filter(Boolean);
      const target = await api.createTarget({
        name: form.name,
        endpoint_url: form.endpoint_url,
        declared_tools: { tools: toolNames.map((name) => ({ name, description: "", permissions: [] })) },
        permission_map: {},
        authorized: form.authorized,
        authorization_note: form.authorized
          ? "Attested at registration: operator owns or has written permission to test this target."
          : null,
        code_visibility: form.code_visibility,
        access_mode: form.access_mode,
        allow_pr_creation: form.code_visibility === "public" || form.allow_pr_creation,
        allow_branch_write: form.access_mode === "read_write" && form.allow_branch_write,
        allow_direct_patch_apply: form.access_mode === "read_write" && form.allow_direct_patch_apply,
      });
      await loadTargets();
      selectTarget(target.id);
      setForm({
        name: "",
        endpoint_url: "",
        tools: "",
        authorized: false,
        code_visibility: "unknown",
        access_mode: "read_only",
        allow_pr_creation: false,
        allow_branch_write: false,
        allow_direct_patch_apply: false,
      });
      setShowForm(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-4 overflow-y-auto px-6 py-8 lg:px-8">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">SECURITY OPERATIONS</p>
          <h1 className="mt-1 text-xl font-semibold text-text-primary">Targets</h1>
          <p className="mt-1 text-xs text-white/30">
            Your registered AI systems. Each is a real endpoint the swarm will attack.
          </p>
        </div>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded-lg bg-cyan-400 px-4 py-2 text-xs font-semibold text-black transition hover:bg-cyan-300"
        >
          {showForm ? "Cancel" : "+ New Target"}
        </button>
      </div>

      {showForm && (
        <motion.form
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          onSubmit={handleCreate}
          className="glass-cyan flex flex-col gap-2.5 rounded-2xl p-5"
        >
          <p className="font-mono text-[10px] text-text-muted">
            Register a real AI system endpoint. Nothing fictional here — this creates an
            actual <code>TargetProfile</code> the swarm will send live requests to.
          </p>
          <input
            required
            placeholder="Name (e.g. Support Agent v2)"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="rounded border border-grid bg-void px-2.5 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:border-gold"
          />
          <input
            required
            placeholder="Endpoint URL"
            value={form.endpoint_url}
            onChange={(e) => setForm({ ...form, endpoint_url: e.target.value })}
            className="rounded border border-grid bg-void px-2.5 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:border-gold"
          />
          <input
            placeholder="Declared tools, comma-separated"
            value={form.tools}
            onChange={(e) => setForm({ ...form, tools: e.target.value })}
            className="rounded border border-grid bg-void px-2.5 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:border-gold"
          />
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-wider text-text-muted">
              Code visibility
              <select
                value={form.code_visibility}
                onChange={(e) =>
                  setForm({
                    ...form,
                    code_visibility: e.target.value,
                    allow_pr_creation: e.target.value === "public" ? true : form.allow_pr_creation,
                  })
                }
                className="rounded border border-grid bg-void px-2.5 py-1.5 text-sm normal-case tracking-normal text-text-primary focus:border-gold"
              >
                <option value="unknown">Read-only / unknown</option>
                <option value="public">Public codebase</option>
                <option value="private">Private codebase</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-wider text-text-muted">
              SwarmShield code access
              <select
                value={form.access_mode}
                onChange={(e) =>
                  setForm({
                    ...form,
                    access_mode: e.target.value,
                    allow_branch_write: e.target.value === "read_write" && form.allow_branch_write,
                    allow_direct_patch_apply: e.target.value === "read_write" && form.allow_direct_patch_apply,
                  })
                }
                className="rounded border border-grid bg-void px-2.5 py-1.5 text-sm normal-case tracking-normal text-text-primary focus:border-gold"
              >
                <option value="read_only">Read only</option>
                <option value="read_write">Read and write</option>
              </select>
            </label>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            <label className="flex items-start gap-2 font-mono text-[11px] leading-snug text-text-muted">
              <input
                type="checkbox"
                checked={form.code_visibility === "public" || form.allow_pr_creation}
                disabled={form.code_visibility === "public"}
                onChange={(e) => setForm({ ...form, allow_pr_creation: e.target.checked })}
                className="mt-0.5 accent-gold"
              />
              <span>Allow PR creation</span>
            </label>
            <label className="flex items-start gap-2 font-mono text-[11px] leading-snug text-text-muted">
              <input
                type="checkbox"
                checked={form.allow_branch_write}
                disabled={form.access_mode !== "read_write"}
                onChange={(e) => setForm({ ...form, allow_branch_write: e.target.checked })}
                className="mt-0.5 accent-gold"
              />
              <span>Allow branch write</span>
            </label>
            <label className="flex items-start gap-2 font-mono text-[11px] leading-snug text-text-muted">
              <input
                type="checkbox"
                checked={form.allow_direct_patch_apply}
                disabled={form.access_mode !== "read_write"}
                onChange={(e) => setForm({ ...form, allow_direct_patch_apply: e.target.checked })}
                className="mt-0.5 accent-gold"
              />
              <span>Allow live apply</span>
            </label>
          </div>
          <label className="mt-1 flex items-start gap-2 font-mono text-[11px] leading-snug text-text-muted">
            <input
              type="checkbox"
              required
              checked={form.authorized}
              onChange={(e) => setForm({ ...form, authorized: e.target.checked })}
              className="mt-0.5 accent-gold"
            />
            <span>
              I own this system or have explicit written authorization to security-test it.
              SwarmShield will refuse to scan a target without this confirmed.
            </span>
          </label>
          <button
            type="submit"
            disabled={submitting}
            className="mt-1 rounded-xl bg-gold px-3 py-1.5 font-mono text-xs font-semibold text-void transition-colors hover:bg-gold/90 disabled:opacity-50"
          >
            {submitting ? "Registering…" : "Register Realm"}
          </button>
        </motion.form>
      )}

      <div className="flex flex-col gap-2.5">
        {targets.length === 0 && (
          <p className="glass rounded-2xl p-6 text-center text-xs text-white/30">
            No targets registered yet. Add one to begin.
          </p>
        )}
        {targets.map((t) => {
          const selected = t.id === selectedTargetId;
          return (
            <button
              key={t.id}
              onClick={() => selectTarget(t.id)}
              className={`glass glass-hover flex items-center gap-3 rounded-2xl p-4 text-left transition-all ${
                selected ? "border border-amber-400/40 shadow-[0_0_20px_rgba(242,184,75,0.1)]" : ""
              }`}
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-cyan-400/20 bg-cyan-400/5 text-cyan-300">◎</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate font-display text-sm font-semibold text-text-primary">
                    {t.name}
                  </span>
                  {t.authorized ? (
                    <span className="shrink-0 rounded border border-hp/30 bg-hp-dim px-1.5 py-0.5 font-mono text-[9px] text-hp">
                      Authorized
                    </span>
                  ) : (
                    <span className="shrink-0 rounded border border-critical/30 bg-critical-dim px-1.5 py-0.5 font-mono text-[9px] text-critical">
                      Not authorized
                    </span>
                  )}
                </div>
                <div className="truncate font-mono text-[10px] text-text-muted">{t.endpoint_url}</div>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  <span className="rounded border border-grid bg-void px-1.5 py-0.5 font-mono text-[9px] uppercase text-text-muted">
                    {t.code_visibility || "unknown"} code
                  </span>
                  <span className="rounded border border-grid bg-void px-1.5 py-0.5 font-mono text-[9px] uppercase text-text-muted">
                    {t.access_mode}
                  </span>
                </div>
              </div>
              {selected && (
                <motion.button
                  whileTap={{ scale: 0.95 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeclareWar(t.id);
                  }}
                  disabled={scanInFlight}
                  className="shrink-0 rounded-lg bg-cyan-400 px-3 py-1.5 text-xs font-semibold text-black transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {scanInFlight ? "Busy…" : "+ Start Scan"}
                </motion.button>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
