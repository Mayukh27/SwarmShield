import { motion } from "framer-motion";

/**
 * Original layered scene — distant hills, a torch-lit parapet silhouette,
 * banners, and floating embers. Pure vector + CSS, no external art. This
 * is a background layer (absolute, behind content, pointer-events-none) —
 * screens place their real content on top of it.
 */
function Ember({ x, delay, duration }) {
  return (
    <motion.div
      className="absolute bottom-0 h-1 w-1 rounded-full bg-ember"
      style={{ left: `${x}%`, boxShadow: "0 0 6px 1px rgba(255,122,51,0.8)" }}
      animate={{ y: [0, -180 - Math.random() * 80], opacity: [0, 0.9, 0], x: [0, (Math.random() - 0.5) * 40] }}
      transition={{ duration, delay, repeat: Infinity, ease: "easeOut" }}
    />
  );
}

function Torch({ x }) {
  return (
    <div className="absolute bottom-[38%]" style={{ left: `${x}%` }}>
      <div className="mx-auto h-6 w-1 rounded bg-stone" />
      <motion.div
        className="mx-auto -mt-1 h-3 w-3 rounded-full bg-ember"
        style={{ boxShadow: "0 0 12px 4px rgba(255,122,51,0.55)" }}
        animate={{ scale: [1, 1.25, 0.95, 1.1, 1], opacity: [0.85, 1, 0.8, 1, 0.85] }}
        transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}

export default function SiegeBackdrop({ variant = "warroom" }) {
  const embers = Array.from({ length: 10 }, (_, i) => ({
    x: 8 + i * 9 + Math.random() * 4,
    delay: Math.random() * 3,
    duration: 3 + Math.random() * 2.5,
  }));

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* deep radial glow, gives the whole scene a lit-from-below feel */}
      <div
        className="absolute inset-x-0 bottom-0 h-2/3"
        style={{
          background:
            "radial-gradient(ellipse 60% 100% at 50% 100%, rgba(232,163,61,0.10), transparent 70%)",
        }}
      />

      {/* distant hill silhouettes */}
      <svg className="absolute inset-x-0 bottom-[30%] w-full" height="120" viewBox="0 0 400 120" preserveAspectRatio="none">
        <path d="M0 120 L0 70 Q60 40 120 65 T240 55 T400 70 L400 120 Z" fill="#10161D" />
        <path d="M0 120 L0 90 Q80 65 160 85 T400 88 L400 120 Z" fill="#161D26" opacity="0.8" />
      </svg>

      {/* parapet / rampart silhouette along the base */}
      <svg className="absolute inset-x-0 bottom-0 w-full" height="90" viewBox="0 0 400 90" preserveAspectRatio="none">
        <rect x="0" y="40" width="400" height="50" fill="#0D1218" />
        {Array.from({ length: 21 }, (_, i) => (
          <rect key={i} x={i * 20} y="30" width="12" height="14" fill="#0D1218" />
        ))}
        <rect x="0" y="88" width="400" height="2" fill="#1E2731" />
      </svg>

      {variant === "warroom" && (
        <>
          <Torch x={14} />
          <Torch x={86} />
        </>
      )}

      {embers.map((e, i) => (
        <Ember key={i} {...e} />
      ))}

      {/* subtle vignette so foreground content stays legible over the scene */}
      <div
        className="absolute inset-0"
        style={{ background: "radial-gradient(ellipse 80% 60% at 50% 40%, transparent 40%, rgba(10,14,19,0.55) 100%)" }}
      />
    </div>
  );
}
