import { motion } from "framer-motion";

/**
 * App-wide atmospheric background — the diagonal aurora/nebula sweep from
 * the approved concept UI: a deep-navy → mana-violet → magenta → cyan band
 * running across the whole viewport, with soft drifting glow blooms and a
 * faint structural grid for depth. This is the SOC/liquid-glass equivalent
 * of `SiegeBackdrop` (used by WarRoom/LiveSiege for the siege-fantasy
 * screens) — same "lit scene behind translucent panels" idea, concept
 * colors instead of torches/embers.
 *
 * Mounted once in AppShell, positioned at z-0 with the sidebar/header/
 * content stack above it at z-10+ (see AppShell.jsx / Sidebar.jsx), so it
 * always renders behind the UI. Fixed + pointer-events-none + no layout
 * participation: it can never intercept clicks, block scrolling, or shift
 * anything on the page.
 */
export default function Atmosphere() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-void">
      {/* primary diagonal sweep — the concept's signature aurora band */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(128deg, " +
            "#060911 0%, " +
            "#0c1830 16%, " +
            "#1b2a52 30%, " +
            "rgba(107,76,190,0.55) 44%, " +
            "rgba(168,90,190,0.4) 55%, " +
            "rgba(60,110,170,0.4) 68%, " +
            "rgba(20,60,80,0.35) 80%, " +
            "#060911 100%)",
        }}
      />

      {/* soft cyan light-beam highlight crossing the sweep, screen-blended
          so it brightens rather than flattens the colors beneath it */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(112deg, transparent 38%, rgba(34,211,238,0.16) 50%, transparent 62%)",
          mixBlendMode: "screen",
        }}
      />

      {/* faint structural grid — reads as console/HUD depth, not decoration */}
      <div
        className="absolute inset-0 opacity-50"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), " +
            "linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />

      {/* slow-drifting glow blooms — the "alive" layer, large and heavily
          blurred so it reads as ambient light, not shapes */}
      <motion.div
        className="absolute left-[66%] top-[6%] h-[620px] w-[820px] -translate-x-1/2 rounded-full blur-[170px]"
        style={{ background: "rgba(34,211,238,0.16)" }}
        animate={{ x: [0, 34, -14, 0], y: [0, -24, 12, 0] }}
        transition={{ duration: 28, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute left-[30%] top-[46%] h-[520px] w-[560px] rounded-full blur-[160px]"
        style={{ background: "rgba(155,107,255,0.18)" }}
        animate={{ x: [0, -28, 16, 0], y: [0, 18, -16, 0] }}
        transition={{ duration: 32, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute left-[8%] top-[58%] h-[420px] w-[480px] rounded-full blur-[150px]"
        style={{ background: "rgba(198,110,207,0.13)" }}
        animate={{ x: [0, 22, -12, 0], y: [0, -14, 10, 0] }}
        transition={{ duration: 30, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute left-[78%] bottom-[-6%] h-[480px] w-[620px] -translate-x-1/2 rounded-full blur-[160px]"
        style={{ background: "rgba(34,211,238,0.12)" }}
        animate={{ x: [0, 20, -20, 0] }}
        transition={{ duration: 36, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* edge vignette — keeps foreground content legible over the glow */}
      <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-void/70 to-transparent" />
      <div className="absolute inset-x-0 bottom-0 h-56 bg-gradient-to-t from-void/80 to-transparent" />
      <div className="absolute inset-y-0 left-0 w-24 bg-gradient-to-r from-void/60 to-transparent" />
    </div>
  );
}
