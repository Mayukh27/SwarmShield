import { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { useScanStore } from "../store/scanStore";
import CapabilityGraphCanvas from "../components/flow/CapabilityGraphCanvas";

const STATUS_BADGE = {
  declared: { label: "DECLARED", tone: "text-cyan bg-cyan-dim border-cyan/40" },
  declared_observed: { label: "DECLARED + OBSERVED", tone: "text-hp bg-hp-dim border-hp/40" },
  undeclared_observed: { label: "UNDECLARED — OBSERVED", tone: "text-critical bg-critical-dim border-critical/50" },
};

const PRIORITY_TONE = {
  critical: "text-critical bg-critical-dim border-critical/50",
  high: "text-critical bg-critical-dim border-critical/40",
  medium: "text-gold bg-gold-dim border-gold/40",
  low: "text-cyan bg-cyan-dim border-cyan/40",
};

const BREAKDOWN_LABELS = {
  capability_risk: "Capability risk",
  boundary_risk: "Trust boundary",
  authorization_risk: "Authorization gap",
  data_sensitivity: "Data sensitivity",
  historical_signal: "Prior success signal",
  novelty: "Novelty",
  coverage_gap: "Coverage gap",
  previous_failure_penalty: "Prior-failure penalty (−)",
};

function PriorityBreakdown({ breakdown }) {
  if (!breakdown || Object.keys(breakdown).length === 0) return null;
  return (
    <div className="mt-2">
      <div className="mb-1 font-mono text-[9px] uppercase tracking-wide text-text-muted">
        Priority breakdown (spec §21 weighted formula)
      </div>
      <div className="flex flex-col gap-1">
        {Object.entries(breakdown).map(([key, value]) => {
          const isPenalty = key === "previous_failure_penalty";
          return (
            <div key={key} className="flex items-center gap-2">
              <span className="w-32 shrink-0 font-mono text-[9px] text-text-muted">
                {BREAKDOWN_LABELS[key] || key}
              </span>
              <div className="h-1.5 flex-1 overflow-hidden rounded bg-panel-raised">
                <div
                  className={`h-full rounded ${isPenalty ? "bg-critical/60" : "bg-cyan/60"}`}
                  style={{ width: `${Math.min(100, value)}%` }}
                />
              </div>
              <span className="w-9 shrink-0 text-right font-mono text-[9px] text-text-primary">{value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatChip({ label, value, tone }) {
  return (
    <div className="flex flex-col items-center gap-0.5 rounded-xl border border-grid/80 bg-panel-raised/80 px-3 py-2 backdrop-blur-xl">
      <span className={`font-display text-lg font-bold ${tone || "text-text-primary"}`}>{value}</span>
      <span className="font-mono text-[9px] uppercase tracking-wide text-text-muted">{label}</span>
    </div>
  );
}

export default function Intelligence() {
  const targets = useScanStore((s) => s.targets);
  const selectedTargetId = useScanStore((s) => s.selectedTargetId);
  const activeScan = useScanStore((s) => s.activeScan);
  const target = targets.find((t) => t.id === selectedTargetId) || targets.find((t) => t.id === activeScan?.target_id);

  const [analysis, setAnalysis] = useState(null);
  const [llmHealth, setLlmHealth] = useState(null);
  const [memoryStats, setMemoryStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedTool, setExpandedTool] = useState(null);
  const [expandedHyp, setExpandedHyp] = useState(null);
  const [hypStatuses, setHypStatuses] = useState({});
  const [decidingHyp, setDecidingHyp] = useState(null);
  const [diff, setDiff] = useState(null);
  const [diffError, setDiffError] = useState(null);

  const load = useCallback(async () => {
    if (!target?.id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTargetCapabilities(target.id, activeScan?.id);
      setAnalysis(data);
    } catch (e) {
      setError(e.message || "Could not load capability intelligence.");
    } finally {
      setLoading(false);
    }
  }, [target?.id, activeScan?.id]);

  useEffect(() => {
    load();
  }, [load]);

  // Re-pull once a running scan finishes — observed capabilities only
  // change once real attack_logs exist for this scan.
  useEffect(() => {
    if (activeScan?.status === "completed" || activeScan?.status === "failed") load();
  }, [activeScan?.status, load]);

  useEffect(() => {
    api.getLlmHealth().then(setLlmHealth).catch(() => setLlmHealth(null));
    api.getMemoryStats().then(setMemoryStats).catch(() => setMemoryStats(null));
  }, []);

  // Persisted hypothesis decisions + capability diff only exist once a
  // scan has actually completed (that's when the snapshot is written).
  useEffect(() => {
    if (!target?.id || !activeScan?.id || activeScan.status !== "completed") {
      setHypStatuses({});
      setDiff(null);
      return;
    }
    api
      .getHypothesisRecords(target.id, activeScan.id)
      .then((records) => {
        const map = {};
        for (const r of records) map[r.hypothesis_id] = r.status;
        setHypStatuses(map);
      })
      .catch(() => setHypStatuses({}));
    api
      .getCapabilityDiff(target.id, activeScan.id)
      .then(setDiff)
      .catch((e) => {
        setDiff(null);
        const msg = e?.message || "";
        setDiffError(msg.startsWith("404") ? null : msg || "Could not load capability diff.");
      });
  }, [target?.id, activeScan?.id, activeScan?.status]);

  const decideHypothesis = async (hypothesisId, decision) => {
    if (!target?.id || !activeScan?.id) return;
    setDecidingHyp(hypothesisId);
    try {
      const fn = decision === "approve" ? api.approveHypothesis : api.skipHypothesis;
      const result = await fn(target.id, hypothesisId, activeScan.id);
      setHypStatuses((prev) => ({ ...prev, [hypothesisId]: result.status }));
    } catch (e) {
      setError(e.message || "Could not record decision.");
    } finally {
      setDecidingHyp(null);
    }
  };

  if (!target) {
    return (
      <div className="mx-auto flex h-full max-w-3xl items-center justify-center px-5">
        <p className="rounded-2xl border border-grid/80 bg-panel/70 p-8 text-center font-mono text-xs text-text-muted backdrop-blur-xl">
          🗺️ No realm selected — pick a target in Realm Registry to see its Capability Intelligence.
        </p>
      </div>
    );
  }

  const caps = analysis?.capabilities || [];
  const unknown = caps.filter((c) => c.category === "unknown" || c.status === "undeclared_observed");
  const hypotheses = analysis?.hypotheses || [];
  const attackPaths = analysis?.attack_paths || [];

  return (
    <div className="mx-auto flex h-full max-w-5xl flex-col gap-5 overflow-y-auto px-5 py-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-lg font-bold text-text-primary">🧠 Capability Intelligence</h1>
          <p className="font-mono text-[11px] text-text-muted">
            {target.name} — what this target can actually do, from declared tools + real runtime
            observations{activeScan?.id ? " for this siege" : " (no active siege — declared-only)"}.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="shrink-0 rounded-xl border border-gold/40 bg-gold-dim px-3 py-1.5 font-mono text-xs font-medium text-gold transition-colors hover:bg-gold/20 hover:shadow-glow disabled:opacity-50"
        >
          {loading ? "Scanning…" : "↻ Refresh"}
        </button>
      </div>

      {error && (
        <p className="rounded border border-critical/40 bg-critical-dim px-3 py-2 font-mono text-[11px] text-critical">
          ⚠ {error}
        </p>
      )}

      {analysis && analysis.enabled === false && (
        <p className="rounded border border-gold/30 bg-gold-dim px-3 py-2 font-mono text-[11px] text-gold">
          ⚠ Capability Intelligence is currently disabled or unavailable for this target — falling back to the
          existing attack taxonomy. {analysis.reason || ""}
        </p>
      )}

      {!analysis && !loading && !error && (
        <p className="font-mono text-[11px] text-text-muted">NOT YET AVAILABLE</p>
      )}

      {analysis && analysis.enabled !== false && (
        <>
          {/* Section 6: counts */}
          <div className="flex flex-wrap gap-2">
            <StatChip label="Capabilities" value={caps.length} />
            <StatChip label="Declared" value={analysis.declared_count ?? 0} tone="text-cyan" />
            <StatChip label="Observed" value={analysis.observed_count ?? 0} tone="text-hp" />
            <StatChip label="Undeclared, Observed" value={analysis.undeclared_observed_count ?? 0} tone="text-critical" />
            <StatChip label="Attack Paths" value={attackPaths.length} />
            <StatChip label="Hypotheses" value={hypotheses.length} />
            {analysis.memory_informed_count > 0 && (
              <StatChip label="Memory-Informed" value={analysis.memory_informed_count} tone="text-gold" />
            )}
          </div>

          {/* Section 8: unknown capability alert */}
          {unknown.length > 0 && (
            <div className="flex flex-col gap-2">
              {unknown.map((c) => (
                <div
                  key={c.capability_id}
                  className="rounded-2xl border border-critical/50 bg-critical-dim px-4 py-3 backdrop-blur-xl"
                >
                  <div className="font-display text-sm font-bold text-critical">
                    ⚠️ UNKNOWN CAPABILITY DISCOVERED — {c.tool_name || c.name}
                  </div>
                  <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 font-mono text-[11px] text-text-primary sm:grid-cols-4">
                    <span>Declared: {c.declared ? "YES" : "NO"}</span>
                    <span>Observed: {c.observed ? "YES" : "NO"}</span>
                    <span>Operation: {c.operation}</span>
                    <span>Risk: {c.risk_score ?? "UNKNOWN"}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {analysis.warnings?.length > 0 && (
            <div className="rounded border border-gold/30 bg-gold-dim px-3 py-2 font-mono text-[10px] text-gold">
              {analysis.warnings.map((w, i) => (
                <div key={i}>⚠ {w}</div>
              ))}
            </div>
          )}

          {/* Section 7: ToolFrame view */}
          <section>
            <h2 className="mb-2 font-display text-xs font-bold uppercase tracking-wide text-text-muted">
              Tool Inventory ({caps.length})
            </h2>
            {caps.length === 0 ? (
              <p className="font-mono text-[11px] text-text-muted">NOT YET OBSERVED</p>
            ) : (
              <div className="flex flex-col gap-1.5">
                {caps.map((c) => {
                  const badge = STATUS_BADGE[c.status] || STATUS_BADGE.declared;
                  const isOpen = expandedTool === c.capability_id;
                  return (
                    <div key={c.capability_id} className="rounded-xl border border-grid/80 bg-panel/70 backdrop-blur-xl">
                      <button
                        onClick={() => setExpandedTool(isOpen ? null : c.capability_id)}
                        className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-left hover:bg-panel-raised"
                      >
                        <span className="min-w-0 flex-1 truncate font-mono text-xs text-text-primary">
                          {c.tool_name || c.name}
                        </span>
                        <span className="shrink-0 font-mono text-[10px] text-text-muted">{c.category}</span>
                        <span className="shrink-0 font-mono text-[10px] text-text-muted">{c.operation}</span>
                        <span className="shrink-0 font-mono text-[10px] text-text-primary">
                          risk {c.risk_score ?? "—"}
                        </span>
                        <span className={`shrink-0 rounded border px-1.5 py-0.5 font-mono text-[9px] ${badge.tone}`}>
                          {badge.label}
                        </span>
                      </button>
                      {isOpen && (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 border-t border-grid bg-void/40 px-3 py-2 font-mono text-[11px] text-text-muted sm:grid-cols-3">
                          <span>Resource: {(c.resources || []).join(", ") || "—"}</span>
                          <span>Sensitivity: {c.data_sensitivity}</span>
                          <span>Required role: {c.required_role || "—"}</span>
                          <span>Side effect: {c.side_effect ? "YES" : "NO"}</span>
                          <span>Destructive: {c.destructive}</span>
                          <span>Trust boundary: {c.trust_boundary ? "CROSSES" : "no"}</span>
                          {c.risk_reasons?.length > 0 && (
                            <span className="col-span-full">Why: {c.risk_reasons.join("; ")}</span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Section 9: capability graph */}
          <section>
            <h2 className="mb-2 font-display text-xs font-bold uppercase tracking-wide text-text-muted">
              Capability Graph
            </h2>
            <CapabilityGraphCanvas graph={analysis.graph} />
          </section>

          {/* Section 10: attack paths */}
          <section>
            <h2 className="mb-2 font-display text-xs font-bold uppercase tracking-wide text-text-muted">
              Attack Paths ({attackPaths.length})
            </h2>
            {attackPaths.length === 0 ? (
              <p className="font-mono text-[11px] text-text-muted">NOT YET AVAILABLE</p>
            ) : (
              <div className="flex flex-col gap-2">
                {attackPaths.map((p) => (
                  <div key={p.path_id} className="rounded-xl border border-grid/80 bg-panel/70 px-3 py-2 backdrop-blur-xl">
                    <div className="flex items-center gap-2">
                      <span
                        className={`shrink-0 rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase ${
                          p.capability_ids.length >= 3
                            ? "border-critical/50 bg-critical-dim text-critical"
                            : "border-grid bg-panel-raised text-text-muted"
                        }`}
                      >
                        {p.capability_ids.length}-HOP
                      </span>
                      <div className="min-w-0 flex-1 font-mono text-[11px] text-text-primary">
                        {p.operations.join(" → ")}
                      </div>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-3 font-mono text-[10px] text-text-muted">
                      <span>{p.description}</span>
                      <span>risk {p.risk_score}</span>
                      <span>{p.crosses_trust_boundary ? "CROSSES TRUST BOUNDARY" : "within trust boundary"}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Coverage engine: what's actually been tested vs still open */}
          <section>
            <h2 className="mb-2 font-display text-xs font-bold uppercase tracking-wide text-text-muted">
              Coverage
            </h2>
            {!analysis.coverage ? (
              <p className="font-mono text-[11px] text-text-muted">NOT YET AVAILABLE</p>
            ) : (
              <div className="flex flex-col gap-2">
                <div className="flex flex-wrap gap-2">
                  <StatChip
                    label="Operations Tested"
                    value={`${analysis.coverage.summary?.operation_coverage_pct ?? 0}%`}
                    tone="text-cyan"
                  />
                  <StatChip
                    label="Attack Paths Tested"
                    value={`${analysis.coverage.summary?.path_coverage_pct ?? 0}%`}
                    tone="text-gold"
                  />
                  <StatChip
                    label="Specialists Exercised"
                    value={`${analysis.coverage.summary?.specialist_coverage_pct ?? 0}%`}
                    tone="text-hp"
                  />
                </div>
                {analysis.coverage.summary?.untested_high_priority_paths?.length > 0 && (
                  <p className="rounded border border-gold/30 bg-gold-dim px-3 py-2 font-mono text-[10px] text-gold">
                    {analysis.coverage.summary.untested_high_priority_paths.length} attack path(s) still untested —
                    run a siege to close the gap.
                  </p>
                )}
              </div>
            )}
          </section>

          {/* Capability diff vs the previous completed scan of this target */}
          {activeScan?.status === "completed" && (diff || diffError) && (
            <section>
              <h2 className="mb-2 font-display text-xs font-bold uppercase tracking-wide text-text-muted">
                Changed Since Last Siege
              </h2>
              {diffError && (
                <p className="rounded border border-critical/40 bg-critical-dim px-3 py-2 font-mono text-[11px] text-critical">
                  ⚠ {diffError}
                </p>
              )}
              {diff && !diff.has_baseline && (
                <p className="font-mono text-[11px] text-text-muted">
                  No prior completed siege on this target yet — nothing to compare against.
                </p>
              )}
              {diff && diff.has_baseline && (
                <div className="flex flex-col gap-1.5 font-mono text-[11px]">
                  {diff.added.length === 0 && diff.removed.length === 0 && diff.changed.length === 0 ? (
                    <p className="text-text-muted">No capability changes since the last siege.</p>
                  ) : (
                    <>
                      {diff.added.length > 0 && (
                        <p className="text-hp">+ New: {diff.added.join(", ")}</p>
                      )}
                      {diff.removed.length > 0 && (
                        <p className="text-text-muted">- No longer seen: {diff.removed.join(", ")}</p>
                      )}
                      {diff.changed.map((c) => (
                        <p key={c.name} className="text-gold">
                          ~ {c.name}: {c.from.status} → {c.to.status} (risk {c.from.risk_score} → {c.to.risk_score})
                        </p>
                      ))}
                    </>
                  )}
                </div>
              )}
            </section>
          )}

          {/* Section 11/12: hypotheses (planner's leads) */}
          <section>
            <h2 className="mb-2 font-display text-xs font-bold uppercase tracking-wide text-text-muted">
              Attack Hypotheses ({hypotheses.length})
            </h2>
            {hypotheses.length === 0 ? (
              <p className="font-mono text-[11px] text-text-muted">NOT YET AVAILABLE</p>
            ) : (
              <div className="flex flex-col gap-2">
                {hypotheses.map((h) => {
                  const isOpen = expandedHyp === h.hypothesis_id;
                  return (
                    <div key={h.hypothesis_id} className="rounded-xl border border-grid/80 bg-panel/70 backdrop-blur-xl">
                      <button
                        onClick={() => setExpandedHyp(isOpen ? null : h.hypothesis_id)}
                        className="flex w-full items-start justify-between gap-3 px-3 py-2 text-left hover:bg-panel-raised"
                      >
                        <div className="min-w-0">
                          <div className="font-display text-xs font-semibold text-text-primary">{h.title}</div>
                          <div className="mt-0.5 font-mono text-[10px] text-text-muted">{h.objective}</div>
                        </div>
                        <div className="flex shrink-0 flex-col items-end gap-1">
                          <span
                            className={`rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase ${
                              PRIORITY_TONE[h.priority] || PRIORITY_TONE.medium
                            }`}
                          >
                            {h.priority}
                          </span>
                          <span className="font-mono text-[9px] text-text-muted">
                            risk {h.risk_score} · conf {h.confidence}
                          </span>
                          {h.previous_attempts > 0 && (
                            <span className="rounded border border-gold/30 bg-gold-dim px-1 py-0.5 font-mono text-[8px] uppercase text-gold">
                              history: {h.mutation_context?.prior_successes ?? 0}✓/{h.mutation_context?.prior_failures ?? 0}✗
                            </span>
                          )}
                          {hypStatuses[h.hypothesis_id] && hypStatuses[h.hypothesis_id] !== "pending" && (
                            <span
                              className={`font-mono text-[9px] uppercase ${
                                hypStatuses[h.hypothesis_id] === "approved" ? "text-hp" : "text-text-muted"
                              }`}
                            >
                              {hypStatuses[h.hypothesis_id]}
                            </span>
                          )}
                        </div>
                      </button>
                      {isOpen && (
                        <div className="border-t border-grid bg-void/40 px-3 py-2 font-mono text-[11px] text-text-muted">
                          <div>Security property: {h.security_property || "—"}</div>
                          <div>Specialists: {(h.required_specialists || []).join(", ") || "—"}</div>
                          <div>Authorization requirements: {(h.authorization_requirements || []).join(", ") || "—"}</div>
                          <div>
                            Coverage: {h.coverage_gap ? "NOT TESTED" : "TESTED"} · previous attempts:{" "}
                            {h.previous_attempts ?? 0}
                            {h.previous_attempts > 0 && h.mutation_context && (
                              <span>
                                {" "}
                                ({h.mutation_context.prior_successes ?? 0} succeeded, {h.mutation_context.prior_failures ?? 0}{" "}
                                failed on this target before)
                              </span>
                            )}
                          </div>
                          {h.evidence?.length > 0 && (
                            <div className="mt-1">
                              WHY:
                              <ul className="ml-3 list-disc">
                                {h.evidence.map((e, i) => (
                                  <li key={i}>{e}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {(h.context_sources || []).some((s) => s.startsWith("rag:")) && (
                            <div className="mt-1">
                              <span className="text-text-muted">Related security guidance (RAG): </span>
                              {h.context_sources
                                .filter((s) => s.startsWith("rag:"))
                                .map((s) => s.slice(4))
                                .join("; ")}
                            </div>
                          )}
                          <PriorityBreakdown breakdown={h.priority_breakdown} />
                          {activeScan?.status === "completed" && (
                            <div className="mt-2 flex items-center gap-2">
                              {hypStatuses[h.hypothesis_id] && hypStatuses[h.hypothesis_id] !== "pending" ? (
                                <span
                                  className={`rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase ${
                                    hypStatuses[h.hypothesis_id] === "approved"
                                      ? "border-hp/40 bg-hp-dim text-hp"
                                      : "border-grid bg-panel-raised text-text-muted"
                                  }`}
                                >
                                  {hypStatuses[h.hypothesis_id]}
                                </span>
                              ) : (
                                <>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      decideHypothesis(h.hypothesis_id, "approve");
                                    }}
                                    disabled={decidingHyp === h.hypothesis_id}
                                    className="rounded border border-hp/40 bg-hp-dim px-2 py-1 font-mono text-[9px] uppercase text-hp hover:bg-hp/20 disabled:opacity-50"
                                  >
                                    Approve
                                  </button>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      decideHypothesis(h.hypothesis_id, "skip");
                                    }}
                                    disabled={decidingHyp === h.hypothesis_id}
                                    className="rounded border border-grid bg-panel-raised px-2 py-1 font-mono text-[9px] uppercase text-text-muted hover:bg-panel disabled:opacity-50"
                                  >
                                    Skip
                                  </button>
                                </>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Section 19: LLM routing / RAG / memory */}
          <section>
            <h2 className="mb-2 font-display text-xs font-bold uppercase tracking-wide text-text-muted">
              LLM Routing &amp; Knowledge Engine
            </h2>
            {!llmHealth && !memoryStats ? (
              <p className="font-mono text-[11px] text-text-muted">NOT AVAILABLE</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                <StatChip
                  label="Local LLM"
                  value={llmHealth?.available ? "✓ " + (llmHealth.model || llmHealth.provider) : "OFFLINE"}
                  tone={llmHealth?.available ? "text-hp" : "text-critical"}
                />
                <StatChip label="Cache hits" value={memoryStats?.metrics?.llm_cache_hits ?? 0} />
                <StatChip label="RAG queries" value={memoryStats?.metrics?.rag_queries ?? 0} />
                <StatChip label="Local calls" value={memoryStats?.metrics?.local_llm_calls ?? 0} tone="text-cyan" />
                <StatChip
                  label="Cloud fallback"
                  value={memoryStats?.metrics?.cloud_fallback_count ?? 0}
                  tone={memoryStats?.metrics?.cloud_fallback_count ? "text-gold" : undefined}
                />
                <StatChip label="Memories" value={memoryStats?.total_memories ?? 0} />
                <StatChip label="Knowledge docs" value={memoryStats?.knowledge_documents ?? 0} />
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
