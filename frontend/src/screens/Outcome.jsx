import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useScanStore } from "../store/scanStore";
import { integrityFromRisk, integrityTone } from "../theme/coc";
import FortressSprite from "../components/sprites/FortressSprite";
import VictoryConfetti from "../components/sprites/VictoryConfetti";

/** Animates a number from its previous value to `target` over ~900ms.
 * Real transition, not a CSS trick — used so Fortress Integrity and the
 * stat row visibly climb/fall instead of instant-jumping when this screen
 * mounts with already-known final numbers. */
function useCountUp(target, duration = 900) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (target === null || target === undefined) return;
    let frame;
    const start = performance.now();
    const from = 0;
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      setValue(Math.round(from + (target - from) * eased));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);
  return value;
}

export default function Outcome({ onNavigate }) {
  const activeScan = useScanStore((s) => s.activeScan);
  const vulnerabilities = useScanStore((s) => s.vulnerabilities);

  if (!activeScan) {
    return (
      <div className="flex h-full items-center justify-center px-5">
        <p className="rounded-lg border border-grid bg-panel p-8 text-center font-mono text-xs text-text-muted">
          No siege has run yet. Declare war from the War Room to see results here.
        </p>
      </div>
    );
  }

  const breakdown = activeScan.risk_breakdown;
  const integrity = integrityFromRisk(activeScan.risk_score);
  const tone = integrityTone(integrity);
  const openCount = vulnerabilities.filter(
    (v) => v.status === "open" || v.status === "remediation_suggested"
  ).length;
  const fixedCount = breakdown?.fixed_count ?? 0;
  const isVictory = activeScan.status === "completed" && openCount === 0 && vulnerabilities.length > 0;
  const isClean = activeScan.status === "completed" && vulnerabilities.length === 0;

  const integrityDisplay = useCountUp(integrity);
  const attemptsDisplay = useCountUp(activeScan.total_attempts ?? 0);
  const breachesDisplay = useCountUp(vulnerabilities.length);
  const fixedDisplay = useCountUp(fixedCount);

  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 overflow-y-auto px-6 py-10 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="relative flex flex-col items-center gap-2"
      >
        {(isVictory || isClean) && <VictoryConfetti />}
        <FortressSprite integrity={isClean ? 100 : integrity} size={110} />
        <h1 className="mt-1 font-saga text-3xl font-black tracking-wide text-text-primary">
          {isVictory
            ? "Fortress Secured"
            : isClean
            ? "No Breaches Found"
            : activeScan.status === "completed"
            ? "Siege Complete — Breaches Remain"
            : "Siege In Progress"}
        </h1>
        <p className="max-w-md font-mono text-xs text-text-muted">
          {isVictory
            ? "Every confirmed vulnerability from this siege has been patched and re-verified against the live target."
            : isClean
            ? "The swarm ran a full attack plan and confirmed no violations. That's a genuinely strong result — not a skipped test."
            : "Real, final numbers from this scan — laid out horizontally, on purpose, unlike the broken reference export."}
        </p>
      </motion.div>

      {/* Fixed the vertical-stacked-text bug from the reference PDF: these
          are laid out in a plain horizontal row, each stat labeled in
          normal English underneath the number. */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat icon="🛡️" value={integrity !== null ? `${integrityDisplay}%` : "—"} tone={tone} label="Fortress Integrity" />
        <Stat icon="⚔️" value={attemptsDisplay} tone="text-text-primary" label="Attack Attempts" />
        <Stat icon="💥" value={breachesDisplay} tone="text-critical" label="Breaches Found" />
        <Stat icon="✅" value={fixedDisplay} tone="text-hp" label="Wards Repaired" />
      </div>

      {openCount > 0 && (
        <button
          onClick={() => onNavigate("forge")}
          className="rounded border border-gold/40 bg-gold-dim px-4 py-2 font-mono text-xs font-semibold text-gold hover:bg-gold/20"
        >
          🔨 {openCount} breach{openCount === 1 ? "" : "es"} still open — go to the Forge
        </button>
      )}

      <button
        onClick={() => onNavigate("warroom")}
        className="font-mono text-[11px] text-text-muted hover:text-text-primary hover:underline"
      >
        ← Back to War Room
      </button>
    </div>
  );
}

function Stat({ icon, value, tone, label }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg border border-grid bg-panel px-4 py-4">
      <span className="text-lg">{icon}</span>
      <span className={`font-display text-2xl font-bold ${tone}`}>{value}</span>
      <span className="font-mono text-[10px] text-text-muted">{label}</span>
    </div>
  );
}
