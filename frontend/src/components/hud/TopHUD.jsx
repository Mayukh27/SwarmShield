import { motion } from "framer-motion";
import { useScanStore } from "../../store/scanStore";
import { integrityFromRisk, integrityTone, STATUS_COPY } from "../../theme/coc";
import ClanCrest from "../sprites/ClanCrest";

export default function TopHUD() {
  const activeScan = useScanStore((s) => s.activeScan);
  const targets = useScanStore((s) => s.targets);
  const selectedTargetId = useScanStore((s) => s.selectedTargetId);

  const target = targets.find((t) => t.id === selectedTargetId);
  const integrity = integrityFromRisk(activeScan?.risk_score);
  const tone = integrityTone(integrity);
  const live = activeScan?.status === "planning" || activeScan?.status === "attacking";

  return (
    <header className="flex shrink-0 items-center justify-between border-b border-grid bg-panel/80 px-5 py-3 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded border border-gold/40 bg-gold-dim">
          <ClanCrest size={20} />
        </div>
        <div className="flex flex-col leading-none">
          <span className="font-display text-sm font-bold tracking-wide text-text-primary">
            SWARM<span className="text-gold">SHIELD</span>
          </span>
          <span className="mt-0.5 font-mono text-[10px] text-text-muted">
            autonomous AI red-team &middot; {target ? target.name : "no realm selected"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-5">
        {/* Fortress Integrity = plain-English restated inline, not just an icon */}
        <div className="flex items-center gap-2">
          <span className="text-lg" title="Fortress Integrity">🛡️</span>
          <div className="flex flex-col leading-none">
            <span className={`font-display text-lg font-bold ${tone}`}>
              {integrity !== null ? `${integrity}%` : "—"}
            </span>
            <span className="font-mono text-[9px] text-text-muted">
              Fortress Integrity (Security Score)
            </span>
          </div>
        </div>

        <div className="h-8 w-px bg-grid" />

        <div className="flex items-center gap-1.5">
          {live && (
            <motion.span
              className="h-2 w-2 rounded-full bg-ember"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.1, repeat: Infinity }}
            />
          )}
          <span className="font-mono text-[11px] text-text-muted">
            {activeScan ? STATUS_COPY[activeScan.status] || activeScan.status : "No siege underway"}
          </span>
        </div>
      </div>
    </header>
  );
}
