/**
 * Sentinel folds a "Policy violation: ..." sentence (from the target's own
 * declared permission_map, see backend/app/services/policy_service.py)
 * onto the front of a finding's `description` when it maps to something
 * the target actually declared restricted. Split it out here so every
 * screen that renders a finding's description can show it as a distinct
 * callout instead of it disappearing into a paragraph of reasoning text --
 * used by both VulnerabilityTable.jsx (Siege Report) and
 * RemediationForge.jsx, so the two screens stay visually consistent.
 */
export function splitPolicyViolation(description) {
  if (!description || !description.startsWith("Policy violation:")) {
    return { policyLine: null, rest: description || "" };
  }
  const idx = description.indexOf(". ");
  if (idx === -1) return { policyLine: description, rest: "" };
  return { policyLine: description.slice(0, idx + 1), rest: description.slice(idx + 2) };
}
