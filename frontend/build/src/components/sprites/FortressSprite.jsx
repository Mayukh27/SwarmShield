import { motion, AnimatePresence } from "framer-motion";

/**
 * Original vector fortress, 4 integrity-driven stages (not decoration —
 * `stage` is derived directly from the real integrity % passed in by the
 * caller, which itself comes straight from activeScan.risk_score):
 *   stage 3 (81-100): pristine, banner flying
 *   stage 2 (51-80):  visible cracks
 *   stage 1 (21-50):  a tower down, smoke
 *   stage 0 (0-20):   breached, wall broken open
 *
 * Rebuilding (integrity climbing after a patch is verified — see
 * PatchSuggestionPanel -> refreshScanData) plays the same stage transition
 * in reverse with a brief golden "repair" flash, so the fix is something
 * you watch happen, not just a number that jumps.
 */
function stageFor(integrity) {
  if (integrity === null || integrity === undefined) return 3;
  if (integrity > 80) return 3;
  if (integrity > 50) return 2;
  if (integrity > 20) return 1;
  return 0;
}

const STAGE_TONE = ["#FF5C5C", "#FF7A33", "#F0B93D", "#3DDC7A"];

export default function FortressSprite({ integrity, size = 120 }) {
  const stage = stageFor(integrity);
  const tone = STAGE_TONE[stage];

  return (
    <div className="relative flex flex-col items-center">
      <AnimatePresence mode="wait">
        <motion.svg
          key={stage}
          width={size}
          height={size}
          viewBox="0 0 100 100"
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 1.05 }}
          transition={{ duration: 0.45 }}
        >
          {/* ground */}
          <rect x="10" y="82" width="80" height="4" rx="1" fill="#1E2731" />

          {/* outer wall — cracked path only rendered at stage <= 2 */}
          <rect x="18" y="52" width="64" height="30" rx="2" fill="#2A3441" stroke={tone} strokeWidth="1.5" />
          {stage <= 2 && (
            <path d="M30 52 L34 62 L28 68 L33 82" stroke={tone} strokeWidth="1.2" fill="none" opacity="0.8" />
          )}
          {stage <= 1 && (
            <path d="M66 52 L60 60 L68 66 L62 82" stroke={tone} strokeWidth="1.2" fill="none" opacity="0.8" />
          )}

          {/* breach gap at stage 0 — wall physically broken open */}
          {stage === 0 ? (
            <path d="M42 82 L46 60 L54 60 L58 82 Z" fill="#0A0E13" />
          ) : (
            <rect x="44" y="66" width="12" height="16" rx="1.5" fill="#161D26" />
          )}

          {/* left tower — down (smoking rubble) at stage <= 1 */}
          {stage <= 1 ? (
            <>
              <rect x="14" y="66" width="16" height="10" rx="1" fill="#161D26" opacity="0.7" />
              <motion.circle
                cx="20" cy="64" r="2" fill="#4A5568"
                animate={{ y: [-2, -14], opacity: [0.6, 0] }}
                transition={{ duration: 1.6, repeat: Infinity, ease: "easeOut" }}
              />
            </>
          ) : (
            <rect x="14" y="40" width="16" height="42" rx="2" fill="#2A3441" stroke={tone} strokeWidth="1.5" />
          )}

          {/* right tower — always standing, tone reflects damage */}
          <rect x="70" y="40" width="16" height="42" rx="2" fill="#2A3441" stroke={tone} strokeWidth="1.5" />
          <path d="M70 40 L78 32 L86 40 Z" fill={tone} opacity="0.85" />
          {stage === 3 && (
            <path d="M14 40 L22 32 L30 40 Z" fill={tone} opacity="0.85" />
          )}

          {/* keep / banner — only flies proudly at full integrity */}
          <rect x="40" y="26" width="20" height="26" rx="2" fill="#2A3441" stroke={tone} strokeWidth="1.5" />
          <path d="M40 26 L50 16 L60 26 Z" fill={tone} />
          {stage === 3 && (
            <motion.path
              d="M50 16 L50 4 L58 8 L50 12 Z"
              fill="#F0B93D"
              animate={{ scaleX: [1, 0.85, 1] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
              style={{ originX: "50px" }}
            />
          )}
        </motion.svg>
      </AnimatePresence>
    </div>
  );
}
