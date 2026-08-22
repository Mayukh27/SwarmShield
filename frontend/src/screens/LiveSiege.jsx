import { useEffect, useState, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useScanStore } from "../store/scanStore";
import { structureFor, SEVERITY_TONE, STATUS_COPY, integrityFromRisk } from "../theme/coc";
import MemoryPanel from "../components/MemoryPanel";
import AttackDnaPanel from "../components/AttackDnaPanel";
import AgentLogConsole from "../components/AgentLogConsole";
import TroopSprite from "../components/sprites/TroopSprite";
import FortressSprite from "../components/sprites/FortressSprite";
import SiegeBackdrop from "../components/sprites/SiegeBackdrop";

/**
 * Every visual beat here maps to real state already in the store — see
 * useScanStream.js / scanStore.js. Note the SSE `AgentLogEvent.data` dict
 * only carries `{vulnerability_id}` on vulnerability_found (not category
 * or score — see backend/app/agents/orchestrator.py), so the accurate
 * source for breach details is the `vulnerabilities` array itself, which
 * useScanStream already refetches on every relevant event. Diffing that
 * array (real DB rows: owasp_category, severity, title) is therefore more
 * correct than trusting the raw event payload, and it's still 100%
 * real-data-driven — nothing here is scripted or invented.
 *
 *   agent_action         -> a troop marches in (battlefield ping)
 *   vulnerabilities grows -> a real breach flash, real category + severity
 *   sentinel_verdict      -> a generic "judgment landed" pulse (verdict dict
 *                            has no category field to target a structure with)
 *   dna_mutation          -> shown in the real Attack DNA panel alongside
 *   memory_consulted      -> shown in the real Memory panel alongside
 */
export default function LiveSiege({ onNavigate }) {
  const events = useScanStore((s) => s.events);
  const activeScan = useScanStore((s) => s.activeScan);
  const vulnerabilities = useScanStore((s) => s.vulnerabilities);
  const [flashes, setFlashes] = useState([]); // transient breach flashes {id, structure, icon, severity}
  const [judgmentPulse, setJudgmentPulse] = useState(false);
  const [attackingAgent, setAttackingAgent] = useState(null);
  const lastEventCount = useRef(0);
  const lastVulnCount = useRef(0);

  // Breach flashes: driven by real growth of the vulnerabilities array
  // (the actual DB-backed findings), not by guessing at event payload shape.
  useEffect(() => {
    if (vulnerabilities.length > lastVulnCount.current) {
      const newOnes = vulnerabilities.slice(lastVulnCount.current);
      newOnes.forEach((v) => {
        const s = structureFor(v.owasp_category);
        const id = `${Date.now()}-${Math.random()}`;
        setFlashes((f) => [...f, { id, ...s, severity: v.severity, title: v.title }]);
        setTimeout(() => setFlashes((f) => f.filter((x) => x.id !== id)), 1800);
      });
    }
    lastVulnCount.current = vulnerabilities.length;
  }, [vulnerabilities]);

  // Generic judgment pulse on every real sentinel_verdict event.
  useEffect(() => {
    if (events.length <= lastEventCount.current) {
      lastEventCount.current = events.length;
      return;
    }
    const newEvents = events.slice(lastEventCount.current);
    lastEventCount.current = events.length;

    if (newEvents.some((e) => e.event_type === "sentinel_verdict")) {
      setJudgmentPulse(true);
      setTimeout(() => setJudgmentPulse(false), 450);
    }

    const attackEvent = [...newEvents].reverse().find(
      (e) => e.event_type === "attack_started" || e.event_type === "agent_action"
    );
    if (attackEvent?.agent_type) {
      setAttackingAgent(attackEvent.agent_type);
      setTimeout(() => setAttackingAgent(null), 420);
    }
  }, [events]);

  const status = activeScan?.status;
  const isDone = status === "completed" || status === "failed" || status === "cancelled";

  // Real troops = real agent_action events, deduped by agent, most recent first
  const activeTroops = [];
  const seen = new Set();
  for (let i = events.length - 1; i >= 0 && activeTroops.length < 6; i--) {
    const e = events[i];
    if (e.event_type === "agent_action" && e.agent_type && !seen.has(e.agent_type)) {
      seen.add(e.agent_type);
      activeTroops.push(e);
    }
  }

  // Real structures = derived from real confirmed vulnerabilities' categories
  const structureCategories = [...new Set(vulnerabilities.map((v) => v.owasp_category))];

  return (
    <div className="grid h-full grid-cols-[1fr_320px] gap-3 overflow-hidden p-3">
      <div className="flex min-h-0 flex-col gap-3">
        {/* Battlefield */}
        <div className="relative flex-1 overflow-hidden rounded-lg border border-grid bg-panel">
          <SiegeBackdrop variant="battlefield" />
          <div className="absolute left-3 top-3 z-10 font-mono text-[11px] text-text-muted">
            Live Siege — {activeScan ? STATUS_COPY[status] : "no active scan"}
          </div>

          <div className="flex h-full flex-col items-center justify-center pt-6">
            <FortressSprite integrity={integrityFromRisk(activeScan?.risk_score)} size={140} />
          </div>

          {/* Breach flashes: fires when a real vulnerability lands in the store */}
          <div className="pointer-events-none absolute inset-0 flex flex-wrap content-center items-center justify-center gap-6 p-10">
            <AnimatePresence>
              {flashes.map((f) => {
                const tone = SEVERITY_TONE[f.severity] || SEVERITY_TONE.medium;
                return (
                  <motion.div
                    key={f.id}
                    initial={{ scale: 0.4, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 1.4, opacity: 0 }}
                    transition={{ duration: 0.35 }}
                    className={`flex flex-col items-center gap-1 rounded-lg border px-4 py-3 shadow-glow-critical border-critical/50 bg-critical-dim`}
                  >
                    <span className="text-2xl">💥</span>
                    <span className="font-display text-xs font-bold text-critical">
                      {f.structure} breached
                    </span>
                    <span className={`font-mono text-[10px] ${tone.text}`}>
                      severity: {tone.label} — {f.title}
                    </span>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>

          {/* Structures = real confirmed findings' categories, grouped */}
          <div className="absolute inset-x-0 bottom-0 flex flex-wrap justify-center gap-3 border-t border-grid bg-void/60 p-3">
            {structureCategories.length === 0 ? (
              <span className="font-mono text-[11px] text-text-muted">
                No structures breached yet — they'll appear here as real findings are confirmed.
              </span>
            ) : (
              structureCategories.map((cat) => {
                const s = structureFor(cat);
                const count = vulnerabilities.filter((v) => v.owasp_category === cat).length;
                return (
                  <div
                    key={cat}
                    className={`flex flex-col items-center gap-0.5 rounded border border-stone/50 bg-stone-dim px-3 py-2 ${
                      judgmentPulse ? "animate-shieldCrack" : ""
                    }`}
                    title={cat}
                  >
                    <span className="text-xl">{s.icon}</span>
                    <span className="font-mono text-[9px] text-text-primary">{s.structure}</span>
                    <span className="font-mono text-[9px] text-critical">{count} hit{count === 1 ? "" : "s"}</span>
                    <span className="font-mono text-[8px] text-text-muted">{cat}</span>
                  </div>
                );
              })
            )}
          </div>

          {/* Troops = real active agents right now */}
          <div className="absolute inset-x-0 top-10 flex flex-wrap justify-center gap-3 px-3">
            {activeTroops.map((e, i) => (
              <motion.div
                key={`${e.agent_type}-${i}`}
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                className="rounded-lg border border-gold/30 bg-gold-dim/40 px-2 py-1.5 backdrop-blur-sm"
              >
                <TroopSprite agentType={e.agent_type} size={34} attacking={attackingAgent === e.agent_type} />
              </motion.div>
            ))}
          </div>
        </div>

        {/* Real live text log, unchanged logic, just reframed */}
        <div className="h-40 shrink-0">
          <AgentLogConsole />
        </div>

        {isDone && (
          <button
            onClick={() => onNavigate("outcome")}
            className="shrink-0 rounded border border-gold/40 bg-gold-dim px-3 py-2 font-mono text-xs font-semibold text-gold hover:bg-gold/20"
          >
            🏆 View Outcome
          </button>
        )}
      </div>

      {/* Side panels: real Memory + real Attack DNA, just restyled */}
      <div className="flex min-h-0 flex-col gap-3 overflow-y-auto">
        <MemoryPanel />
        <AttackDnaPanel />
      </div>
    </div>
  );
}
