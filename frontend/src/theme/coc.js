/**
 * Single source of truth for the Clash-of-Clans re-skin.
 *
 * Rule for this whole redesign: every game term on screen is paired with
 * a plain-English label pulled from the real data. Someone who has never
 * played CoC should be able to read any screen and understand exactly what
 * security thing just happened, using the plain label alone. The game
 * flavor (icon, color, motion) is decoration on top of that, never a
 * replacement for it.
 */

// OWASP LLM Top-10 category -> which "structure" in the fortress gets hit,
// so vulnerability_found events land visually somewhere meaningful instead
// of a generic explosion.
export const CATEGORY_TO_STRUCTURE = {
  "Prompt Injection": { icon: "🧱", structure: "Firewall Wall" },
  "Insecure Output Handling": { icon: "🏹", structure: "Archer Tower" },
  "Sensitive Information Disclosure": { icon: "🏦", structure: "Data Vault" },
  "Excessive Agency": { icon: "⚙️", structure: "Tool Gate" },
  "Model Denial of Service": { icon: "🏰", structure: "Keep" },
  "System Prompt Leakage": { icon: "📜", structure: "Scroll Tower" },
  "Insecure Plugin Design": { icon: "🔧", structure: "Workshop" },
  "Training Data Poisoning": { icon: "🧪", structure: "Alchemy Lab" },
  "Overreliance": { icon: "👁️", structure: "Watchtower" },
  "Model Theft": { icon: "💎", structure: "Treasury" },
};
export const DEFAULT_STRUCTURE = { icon: "🛡️", structure: "Outer Wall" };

// Real stored owasp_category values are prefixed like "LLM06: Excessive
// Agency" (see backend/app/agents/planner.py), not the bare label used as
// keys above -- without stripping the prefix, every single finding fell
// through to DEFAULT_STRUCTURE regardless of its real category, which is
// why every finding badge showed "Outer Wall" no matter what it actually was.
export function structureFor(owaspCategory) {
  const bare = (owaspCategory || "").replace(/^LLM\d+:\s*/i, "").trim();
  return CATEGORY_TO_STRUCTURE[bare] || DEFAULT_STRUCTURE;
}

// Backend agent_type -> troop, with the real role spelled out plainly.
export const AGENT_TO_TROOP = {
  planner: { icon: "🗺️", troop: "Scout", role: "Plans the attack route" },
  sentinel: { icon: "🦅", troop: "Watcher", role: "Judges every response for a real breach" },
  prompt_injection_specialist: { icon: "⚔️", troop: "Barbarian", role: "Prompt injection attacks" },
  jailbreak_specialist: { icon: "🪓", troop: "Berserker", role: "Roleplay / jailbreak attacks" },
  tool_abuse_specialist: { icon: "🔨", troop: "Siege Engineer", role: "Tool / function abuse attacks" },
  data_exfiltration_specialist: { icon: "🗡️", troop: "Rogue", role: "Data exfiltration attacks" },
  privilege_escalation_specialist: { icon: "🔱", troop: "Warlord", role: "Privilege escalation attacks" },
};
export const DEFAULT_TROOP = { icon: "🛡️", troop: "Trooper", role: "Attack specialist" };

export function troopFor(agentType) {
  return AGENT_TO_TROOP[agentType] || DEFAULT_TROOP;
}

// Severity -> damage tone (kept aligned with the existing SOC palette
// meaning: red only for confirmed, amber for in-progress, cyan/hp for clear).
export const SEVERITY_TONE = {
  critical: { text: "text-critical", bg: "bg-critical", dim: "bg-critical-dim", label: "Critical" },
  high: { text: "text-critical", bg: "bg-critical/70", dim: "bg-critical-dim", label: "High" },
  medium: { text: "text-gold", bg: "bg-gold", dim: "bg-gold-dim", label: "Medium" },
  low: { text: "text-cyan", bg: "bg-cyan", dim: "bg-cyan-dim", label: "Low" },
};

// Scan status -> plain banner text used across screens (War Room HUD,
// Live Siege header, bottom nav badge).
export const STATUS_COPY = {
  pending: "Queued — waiting to begin",
  planning: "Scout is mapping attack routes",
  attacking: "Siege in progress — troops attacking live",
  completed: "Siege complete — review findings",
  failed: "Siege failed to complete",
  cancelled: "Siege cancelled",
};

// Fortress integrity is just the inverse of risk_score, clamped, with the
// real number always shown alongside it (never game-score-only).
export function integrityFromRisk(riskScore) {
  if (riskScore === null || riskScore === undefined) return null;
  return Math.max(0, Math.min(100, Math.round(100 - riskScore)));
}

export function integrityTone(integrity) {
  if (integrity === null) return "text-text-muted";
  if (integrity < 50) return "text-critical";
  if (integrity < 80) return "text-gold";
  return "text-hp";
}
