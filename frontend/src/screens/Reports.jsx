import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { useScanStore } from "../store/scanStore";
import { integrityFromRisk } from "../theme/coc";

const FILTERS = [
  { id: "all", label: "ALL" },
  { id: "agent_action", label: "ATTACK" },
  { id: "sentinel_verdict", label: "SENTINEL" },
  { id: "vulnerability_found", label: "FINDINGS" },
  { id: "memory_consulted", label: "MEMORY" },
  { id: "dna_mutation", label: "DNA" },
  { id: "scan_status", label: "SYSTEM" },
];

function matchesFilter(event, filterId) {
  if (filterId === "all") return true;
  return event.event_type === filterId;
}

const ACTIVE_STATUSES = new Set(["pending", "planning", "attacking"]);
const USAGE_POLL_MS = 4000;

const fmt = (n) => Number(n ?? 0).toLocaleString("en-US");

// "qwen2.5:3b" -> "Qwen2.5 3B"; "ollama" -> "Ollama". Display-only formatting of what the backend recorded.
function prettyModel(model) {
  if (!model) return null;
  const [name, tag] = model.split(":");
  const base = name.charAt(0).toUpperCase() + name.slice(1);
  if (!tag || tag === "latest") return base;
  return `${base} ${/^\d+(\.\d+)?[bm]$/i.test(tag) ? tag.toUpperCase() : tag}`;
}
const prettyProvider = (p) => (p ? p.charAt(0).toUpperCase() + p.slice(1) : null);

// Real provider-reported LLM usage for the scan (GET /api/scans/{id}/usage). Never estimated.
function useScanUsage(scanId, status) {
  const [usage, setUsage] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const running = ACTIVE_STATUSES.has(status);

  useEffect(() => {
    setUsage(null);
    setLoaded(false);
    setFailed(false);
  }, [scanId]);

  useEffect(() => {
    if (!scanId) return undefined;
    let cancelled = false;
    const load = async () => {
      try {
        const data = await api.getScanUsage(scanId);
        if (cancelled) return;
        setUsage(data);
        setFailed(false);
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled) setLoaded(true);
      }
    };
    load();
    // Live-refresh while the swarm is still running; one final fetch happens when status flips to completed/failed.
    const timer = running ? setInterval(load, USAGE_POLL_MS) : null;
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [scanId, status, running]);

  return { usage, loaded, failed };
}

// "Download Logs": fetches the server-built export (already redacted) and saves it as a file.
function DownloadLogs({ scanId }) {
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);

  const download = async (format) => {
    setBusy(format);
    setError(null);
    try {
      const res = await fetch(api.scanExportUrl(scanId, format));
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `swarmshield-battle-log-${scanId}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(`Could not download logs (${e.message}).`);
    } finally {
      setBusy(null);
    }
  };

  const btn =
    "rounded-lg border px-2.5 py-1 text-[10px] font-medium transition-colors disabled:opacity-40 border-cyan-400/30 bg-cyan-400/10 text-cyan-200 hover:bg-cyan-400/20";
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-1.5">
        <button className={btn} disabled={busy !== null} onClick={() => download("json")} title="Structured JSON export of this battle">
          {busy === "json" ? "Preparing…" : "⬇ Download Logs"}
        </button>
        <button className={btn} disabled={busy !== null} onClick={() => download("txt")} title="Plain-text summary">
          {busy === "txt" ? "Preparing…" : "TXT"}
        </button>
      </div>
      {error && <span className="text-[10px] text-red-300/80">{error}</span>}
    </div>
  );
}

function TokenUsagePanel({ usage, loaded, failed }) {
  const hasUsage = usage && usage.llm_calls > 0;
  const modelLabel = usage ? [prettyModel(usage.model), prettyProvider(usage.provider)].filter(Boolean).join(" · ") : "";
  const tiles = hasUsage
    ? [
        ["Input Tokens", usage.input_tokens],
        ["Output Tokens", usage.output_tokens],
        ["Total Tokens", usage.total_tokens],
        ["LLM Calls", usage.llm_calls],
      ]
    : [];

  return (
    <section className="glass rounded-2xl px-4 py-4" aria-label="Token usage">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">TOKEN USAGE</p>
        {hasUsage && modelLabel && <p className="text-[11px] text-white/40">{modelLabel}</p>}
      </div>

      {!loaded ? (
        <p className="mt-3 text-xs text-white/25">Loading token usage…</p>
      ) : failed && !usage ? (
        <p className="mt-3 text-xs text-white/25">Token usage could not be loaded.</p>
      ) : !hasUsage ? (
        <p className="mt-3 text-[11px] tracking-wide text-white/30">
          NO LLM USAGE RECORDED YET FOR THIS SCAN — figures appear here as real provider calls report token counts (never
          estimated).
        </p>
      ) : (
        <>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {tiles.map(([label, value]) => (
              <div key={label} className="flex flex-col items-center gap-1 rounded-xl border border-white/5 bg-white/[0.03] px-3 py-3">
                <span className="text-xl font-bold tabular-nums text-text-primary">{fmt(value)}</span>
                <span className="text-[10px] tracking-widest text-white/30">{label.toUpperCase()}</span>
              </div>
            ))}
          </div>
          {usage.by_agent?.length > 1 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {usage.by_agent.map((a) => (
                <span
                  key={a.agent_type}
                  title={`${fmt(a.input_tokens)} in · ${fmt(a.output_tokens)} out · ${fmt(a.llm_calls)} calls`}
                  className="rounded-lg border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-white/40"
                >
                  <span className="text-cyan-300/60">{a.agent_type}</span> {fmt(a.total_tokens)}
                </span>
              ))}
            </div>
          )}
          {usage.partial_calls > 0 && (
            <p className="mt-2 text-[10px] text-white/25">
              {usage.partial_calls} call{usage.partial_calls === 1 ? "" : "s"} reported only part of the counters; totals are a lower bound.
            </p>
          )}
        </>
      )}
    </section>
  );
}

export default function Reports() {
  const events = useScanStore((s) => s.events);
  const activeScan = useScanStore((s) => s.activeScan);
  const vulnerabilities = useScanStore((s) => s.vulnerabilities);
  const [filter, setFilter] = useState("all");
  const { usage, loaded: usageLoaded, failed: usageFailed } = useScanUsage(activeScan?.id, activeScan?.status);

  const filtered = useMemo(() => events.filter((e) => matchesFilter(e, filter)), [events, filter]);
  const VISIBLE_LIMIT = 300;
  const hiddenCount = Math.max(0, filtered.length - VISIBLE_LIMIT);
  const visible = filtered.slice(hiddenCount);

  const integrity = integrityFromRisk(activeScan?.risk_score);
  const fixedCount = activeScan?.risk_breakdown?.fixed_count ?? 0;

  return (
    <div className="mx-auto flex h-full max-w-4xl flex-col gap-4 overflow-y-auto px-6 py-8 lg:px-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] tracking-[0.25em] text-cyan-300/50">SECURITY OPERATIONS</p>
          <h1 className="mt-1 text-xl font-semibold text-text-primary">Reports</h1>
          <p className="mt-1 text-xs text-white/30">
            {activeScan
              ? "Real scan summary and full event timeline for the current scan."
              : "No scan yet — start one from Targets to build a report."}
          </p>
        </div>
        {activeScan?.id && <DownloadLogs scanId={activeScan.id} />}
      </div>

      {activeScan && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            ["Security Score", integrity !== null ? `${integrity}%` : "—"],
            ["Attack Attempts", activeScan.total_attempts ?? 0],
            ["Vulnerabilities", vulnerabilities.length],
            ["Fixed", fixedCount],
          ].map(([label, value]) => (
            <div key={label} className="glass flex flex-col items-center gap-1 rounded-2xl px-4 py-4">
              <span className="text-2xl font-bold text-text-primary">{value}</span>
              <span className="text-[10px] tracking-widest text-white/30">{label}</span>
            </div>
          ))}
        </div>
      )}

      {activeScan && <TokenUsagePanel usage={usage} loaded={usageLoaded} failed={usageFailed} />}

      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`rounded-lg border px-2.5 py-1 text-[10px] font-medium transition-colors ${
              filter === f.id
                ? "border-amber-400/40 bg-amber-400/10 text-amber-300"
                : "border-white/10 bg-white/5 text-white/40 hover:text-white"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="glass scroll-thin flex-1 overflow-y-auto rounded-2xl">
        {filtered.length === 0 ? (
          <p className="p-6 text-xs text-white/25">No events yet for this filter.</p>
        ) : (
          <ol className="divide-y divide-white/5">
            {hiddenCount > 0 && (
              <li className="px-4 py-2 text-[10px] text-white/25">
                {hiddenCount} earlier {hiddenCount === 1 ? "entry" : "entries"} not shown.
              </li>
            )}
            {visible.map((e, i) => (
              <li key={hiddenCount + i} className="flex flex-wrap gap-2 px-4 py-2.5 text-xs sm:flex-nowrap sm:gap-3">
                <span className="shrink-0 text-[10px] text-white/25">
                  {new Date(e.timestamp).toLocaleTimeString("en-US", { hour12: false })}
                </span>
                <div className="min-w-0">
                  {e.agent_type && <span className="mr-2 text-[10px] text-cyan-300/60">{e.agent_type}</span>}
                  <span className="text-white/60">{e.message}</span>
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
