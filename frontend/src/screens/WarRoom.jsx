import { motion } from "framer-motion";
import { useScanStore } from "../store/scanStore";
import { integrityFromRisk, integrityTone } from "../theme/coc";
import SiegeBackdrop from "../components/sprites/SiegeBackdrop";
import FortressSprite from "../components/sprites/FortressSprite";
import ClanCrest from "../components/sprites/ClanCrest";

export default function WarRoom({ onNavigate, onDeclareWar, scanInFlight }) {
  const targets = useScanStore((s) => s.targets);
  const selectedTargetId = useScanStore((s) => s.selectedTargetId);
  const activeScan = useScanStore((s) => s.activeScan);
  const vulnerabilities = useScanStore((s) => s.vulnerabilities);

  const target = targets.find((t) => t.id === selectedTargetId);
  const integrity = integrityFromRisk(activeScan?.risk_score);
  const tone = integrityTone(integrity);
  const fixedCount = activeScan?.risk_breakdown?.fixed_count ?? 0;

  return (
    <div className="relative flex h-full flex-col items-center justify-center gap-8 overflow-y-auto px-6 py-10">
      <SiegeBackdrop variant="warroom" />

      {/* faint oversized crest watermark, purely atmospheric, behind everything */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 -z-0 -translate-x-1/2 -translate-y-1/2 opacity-[0.05]">
        <ClanCrest size={420} />
      </div>

      {/* Hero: the real fortress, its integrity, plain-English throughout */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 flex flex-col items-center gap-3 text-center"
      >
        <div className="relative flex h-36 w-36 items-center justify-center">
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-gold/30"
            animate={{ scale: [1, 1.08, 1], opacity: [0.5, 0.9, 0.5] }}
            transition={{ duration: 2.4, repeat: Infinity }}
          />
          <FortressSprite integrity={target ? integrity ?? 100 : 100} size={128} />
        </div>
        <h1 className="font-display text-2xl font-bold text-text-primary drop-shadow-[0_0_12px_rgba(232,163,61,0.25)]">
          {target ? target.name : "No Realm Selected"}
        </h1>
        <p className="max-w-sm font-mono text-xs text-text-muted">
          {target
            ? "Your registered AI system, ready to be tested for real security vulnerabilities."
            : "Register a target AI system in the Realm Registry before you can start a siege."}
        </p>
      </motion.div>

      {/* Real stats, gamified labels but every number is the real backend value.
          Stronger contrast: raised panel surface + visible border glow, not
          the flat bg-panel cards used elsewhere, since this is the hero screen. */}
      <div className="relative z-10 grid w-full max-w-lg grid-cols-3 gap-3">
        <StatTile
          icon="🛡️"
          value={integrity !== null ? `${integrity}%` : "—"}
          tone={tone}
          label="Fortress Integrity"
          sub="Security score (100 = fully hardened)"
          glow="shadow-glow-hp"
        />
        <StatTile
          icon="⚔️"
          value={vulnerabilities.length}
          tone="text-critical"
          label="Breaches Found"
          sub="Confirmed vulnerabilities"
          glow="shadow-glow-critical"
        />
        <StatTile
          icon="✅"
          value={fixedCount}
          tone="text-hp"
          label="Wards Repaired"
          sub="Findings verified fixed"
          glow="shadow-glow-hp"
        />
      </div>

      {/* Primary CTA */}
      <motion.button
        whileHover={{ scale: target && !scanInFlight ? 1.04 : 1 }}
        whileTap={{ scale: target && !scanInFlight ? 0.97 : 1 }}
        onClick={() => (target ? onDeclareWar(target.id) : onNavigate("registry"))}
        disabled={scanInFlight}
        className="relative z-10 flex items-center gap-2.5 rounded-lg border border-gold/60 bg-gold-dim px-7 py-4 font-display text-base font-bold tracking-wide text-gold shadow-glow-ember disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span className="text-lg">⚔️</span>
        {scanInFlight
          ? "Siege underway…"
          : target
          ? "Declare War (Start Security Scan)"
          : "Register a Target to Begin"}
      </motion.button>

      {activeScan && (
        <button
          onClick={() => onNavigate("siege")}
          className="relative z-10 font-mono text-[11px] text-cyan hover:underline"
        >
          → View the live siege in progress
        </button>
      )}
    </div>
  );
}

function StatTile({ icon, value, tone, label, sub, glow }) {
  return (
    <div className={`flex flex-col items-center gap-1 rounded-lg border border-grid bg-panel-raised px-3 py-4 text-center ${glow}`}>
      <span className="text-xl">{icon}</span>
      <span className={`font-display text-2xl font-bold ${tone}`}>{value}</span>
      <span className="font-mono text-[10px] font-medium text-text-primary">{label}</span>
      <span className="font-mono text-[9px] text-text-muted">{sub}</span>
    </div>
  );
}
