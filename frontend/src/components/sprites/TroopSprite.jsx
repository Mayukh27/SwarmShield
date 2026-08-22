import { motion } from "framer-motion";
import { troopFor } from "../../theme/coc";

/**
 * 100% original vector art — geometric "chibi warrior" silhouette, shared
 * base shape recolored + re-weaponed per troop type via theme/coc.js's
 * existing AGENT_TO_TROOP mapping. No external images, no third-party IP.
 *
 * Two animation states, both real (driven by props, not decorative loops
 * for their own sake):
 *   - idle/walking: a continuous subtle bob + leg-swing, framer-motion loop
 *   - attacking: a one-shot lunge + weapon swing, fired by the parent when
 *     this troop's specialist agent actually produces a real attack_started
 *     event — see LiveSiege.jsx
 */

const TONE = {
  planner: { body: "#3DDBD9", weapon: "map" },
  sentinel: { body: "#F0B93D", weapon: "eye" },
  prompt_injection_specialist: { body: "#FF5C5C", weapon: "sword" },
  jailbreak_specialist: { body: "#FF7A33", weapon: "axe" },
  tool_abuse_specialist: { body: "#9B6BFF", weapon: "hammer" },
  data_exfiltration_specialist: { body: "#3DDC7A", weapon: "dagger" },
  privilege_escalation_specialist: { body: "#E8A33D", weapon: "trident" },
};
const DEFAULT_TONE = { body: "#6B7A8A", weapon: "sword" };

function Weapon({ kind, color }) {
  switch (kind) {
    case "sword":
      return <path d="M20 2 L22 2 L22 16 L26 20 L24 22 L21 19 L18 22 L16 20 L20 16 Z" fill={color} />;
    case "axe":
      return (
        <path
          d="M19 3 L21 3 L21 20 L23 22 L21 24 L19 22 Z M14 6 Q19 2 26 6 Q22 11 19 9 Q16 11 14 6 Z"
          fill={color}
        />
      );
    case "hammer":
      return (
        <>
          <rect x="19.2" y="6" width="1.6" height="17" fill={color} />
          <rect x="14" y="2" width="12" height="6" rx="1.5" fill={color} />
        </>
      );
    case "dagger":
      return <path d="M20 6 L21.4 6 L21.4 17 L23.5 19.5 L21.4 21 L20 21 L18.5 19.5 L20 17 Z" fill={color} />;
    case "trident":
      return (
        <>
          <rect x="19.2" y="6" width="1.6" height="17" fill={color} />
          <path d="M14 3 L16 9 L18 4 M26 3 L24 9 L22 4" stroke={color} strokeWidth="1.6" fill="none" strokeLinecap="round" />
        </>
      );
    case "eye":
      return (
        <ellipse cx="20" cy="10" rx="6" ry="3.4" fill="none" stroke={color} strokeWidth="1.6" />
      );
    case "map":
      return (
        <rect x="14" y="5" width="12" height="9" rx="1" fill="none" stroke={color} strokeWidth="1.6" />
      );
    default:
      return null;
  }
}

export default function TroopSprite({ agentType, size = 40, attacking = false, label = true }) {
  const t = troopFor(agentType);
  const tone = TONE[agentType] || DEFAULT_TONE;

  return (
    <div className="flex flex-col items-center gap-1" title={t.role}>
      <motion.svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        animate={
          attacking
            ? { x: [0, 6, -2, 0], rotate: [0, -6, 3, 0], scale: [1, 1.12, 1] }
            : { y: [0, -1.5, 0] }
        }
        transition={
          attacking
            ? { duration: 0.4, ease: "easeOut" }
            : { duration: 1.3, repeat: Infinity, ease: "easeInOut" }
        }
      >
        {/* legs — simple swing to read as "marching" even at idle */}
        <motion.rect
          x="16" y="27" width="3" height="9" rx="1.4"
          fill={tone.body} opacity="0.85"
          animate={attacking ? {} : { rotate: [-6, 6, -6] }}
          style={{ originX: "17.5px", originY: "27px" }}
          transition={{ duration: 1.3, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.rect
          x="21" y="27" width="3" height="9" rx="1.4"
          fill={tone.body} opacity="0.85"
          animate={attacking ? {} : { rotate: [6, -6, 6] }}
          style={{ originX: "22.5px", originY: "27px" }}
          transition={{ duration: 1.3, repeat: Infinity, ease: "easeInOut" }}
        />
        {/* torso */}
        <rect x="13" y="16" width="14" height="13" rx="4" fill={tone.body} />
        {/* head */}
        <circle cx="20" cy="10" r="7" fill={tone.body} />
        {/* face plate accent, keeps it from reading as a blank blob */}
        <rect x="15.5" y="9" width="9" height="2.4" rx="1.2" fill="#0A0E13" opacity="0.55" />
        {/* weapon / emblem, per troop type — original geometry only */}
        <Weapon kind={tone.weapon} color="#E4EAEF" />
      </motion.svg>
      {label && (
        <span className="font-mono text-[9px] leading-none text-text-primary">{t.troop}</span>
      )}
    </div>
  );
}
