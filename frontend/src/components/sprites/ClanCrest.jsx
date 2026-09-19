/**
 * Original vector crest — a shield-and-crossed-blades emblem, entirely
 * hand-drawn geometry. Used in the header (small) and as a larger watermark
 * on War Room. No external art, no third-party marks.
 */
export default function ClanCrest({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40">
      <defs>
        <linearGradient id="crestGold" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#F0B93D" />
          <stop offset="100%" stopColor="#E8A33D" />
        </linearGradient>
      </defs>
      {/* shield body */}
      <path
        d="M20 3 L34 8 V19 C34 28 28 34 20 37 C12 34 6 28 6 19 V8 Z"
        fill="#161D26"
        stroke="url(#crestGold)"
        strokeWidth="1.6"
      />
      {/* inner shield accent line */}
      <path
        d="M20 7 L30 10.5 V19 C30 25.5 26 30 20 32.5 C14 30 10 25.5 10 19 V10.5 Z"
        fill="none"
        stroke="#F0B93D"
        strokeWidth="0.8"
        opacity="0.45"
      />
      {/* crossed blades */}
      <path d="M13 13 L27 27 M27 13 L13 27" stroke="#E4EAEF" strokeWidth="2.2" strokeLinecap="round" />
      {/* pommels */}
      <circle cx="13" cy="13" r="1.6" fill="url(#crestGold)" />
      <circle cx="27" cy="13" r="1.6" fill="url(#crestGold)" />
      <circle cx="13" cy="27" r="1.6" fill="url(#crestGold)" />
      <circle cx="27" cy="27" r="1.6" fill="url(#crestGold)" />
    </svg>
  );
}
