import { motion } from "framer-motion";

const COLORS = ["#F0B93D", "#3DDC7A", "#3DDBD9", "#FF7A33", "#9B6BFF"];
const PIECES = Array.from({ length: 28 }, (_, i) => ({
  id: i,
  x: (Math.random() - 0.5) * 320,
  delay: Math.random() * 0.25,
  rotate: Math.random() * 360,
  color: COLORS[i % COLORS.length],
  shape: i % 3 === 0 ? "circle" : "rect",
}));

/** One-shot burst, not a loop — mounts only when the parent's real
 * victory condition (activeScan.status === "completed" && openCount === 0)
 * is true. Pure vector shapes, nothing external. */
export default function VictoryConfetti() {
  return (
    <div className="pointer-events-none absolute inset-0 flex items-start justify-center overflow-hidden">
      {PIECES.map((p) => (
        <motion.span
          key={p.id}
          initial={{ y: -20, x: 0, opacity: 1, rotate: 0 }}
          animate={{ y: 260, x: p.x, opacity: 0, rotate: p.rotate }}
          transition={{ duration: 1.6 + Math.random() * 0.6, delay: p.delay, ease: "easeIn" }}
          style={{
            position: "absolute",
            top: 0,
            width: p.shape === "circle" ? 7 : 5,
            height: p.shape === "circle" ? 7 : 10,
            borderRadius: p.shape === "circle" ? "50%" : "1px",
            background: p.color,
          }}
        />
      ))}
    </div>
  );
}
