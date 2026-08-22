/**
 * SwarmShield design tokens — an oscilloscope / SOC-console palette.
 * Deliberately not the templated cream+terracotta or flat near-black+acid-green
 * defaults: deep graphite-blue base, amber for "in progress", cyan for "clear",
 * red reserved solely for confirmed violations so it stays meaningful.
 */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        void: "#0A0E13",
        panel: "#10161D",
        "panel-raised": "#161D26",
        grid: "#1E2731",
        "text-primary": "#E4EAEF",
        "text-muted": "#6B7A8A",
        amber: {
          DEFAULT: "#E8A33D",
          dim: "#3A2E1A",
        },
        cyan: {
          DEFAULT: "#3DDBD9",
          dim: "#123333",
        },
        critical: {
          DEFAULT: "#FF5C5C",
          dim: "#3A1414",
        },
        /* --- CoC layer: siege-fantasy palette, additive only --- */
        ember: { DEFAULT: "#FF7A33", dim: "#3A2011" },     // attacks / damage
        gold: { DEFAULT: "#F0B93D", dim: "#3A2E10" },      // CTAs / rewards (kin to amber)
        mana: { DEFAULT: "#9B6BFF", dim: "#241A3A" },      // DNA mutation / special events
        hp: { DEFAULT: "#3DDC7A", dim: "#0F2E1C" },        // fortress integrity / fixed
        stone: { DEFAULT: "#4A5568", dim: "#1A1F27" },     // structures / defense
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
        body: ["'Inter'", "sans-serif"],
        rune: ["'Cinzel'", "serif"],  // used sparingly for CoC-flavored titles only
        saga: ["'Cinzel Decorative'", "serif"], // heavier, for hero moments only: Outcome headline + big score
        scroll: ["'MedievalSharp'", "serif"], // rugged accent for small section labels only
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(232,163,61,0.25), 0 0 20px rgba(232,163,61,0.15)",
        "glow-critical": "0 0 0 1px rgba(255,92,92,0.35), 0 0 24px rgba(255,92,92,0.25)",
        "glow-cyan": "0 0 0 1px rgba(61,219,217,0.25), 0 0 20px rgba(61,219,217,0.12)",
        "glow-ember": "0 0 0 1px rgba(255,122,51,0.35), 0 0 24px rgba(255,122,51,0.25)",
        "glow-mana": "0 0 0 1px rgba(155,107,255,0.35), 0 0 24px rgba(155,107,255,0.25)",
        "glow-hp": "0 0 0 1px rgba(61,220,122,0.3), 0 0 20px rgba(61,220,122,0.18)",
      },
      keyframes: {
        scanline: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.35 },
        },
        shieldCrack: {
          "0%, 100%": { transform: "translateX(0)" },
          "20%": { transform: "translateX(-3px) rotate(-0.5deg)" },
          "40%": { transform: "translateX(3px) rotate(0.5deg)" },
          "60%": { transform: "translateX(-2px)" },
          "80%": { transform: "translateX(2px)" },
        },
        emberFloat: {
          "0%": { transform: "translateY(0) scale(1)", opacity: 1 },
          "100%": { transform: "translateY(-40px) scale(1.3)", opacity: 0 },
        },
      },
      animation: {
        scanline: "scanline 1.6s linear infinite",
        pulseDot: "pulseDot 1.4s ease-in-out infinite",
        shieldCrack: "shieldCrack 0.4s ease-in-out",
        emberFloat: "emberFloat 1.1s ease-out forwards",
      },
    },
  },
  plugins: [],
};
