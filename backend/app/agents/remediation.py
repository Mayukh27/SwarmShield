"""
Remediation Agent: given a confirmed Vulnerability (+ the AttackLog that
proved it), generates a concrete fix suggestion. Not part of the
attack/sentinel loop — invoked on-demand when the dashboard requests a
patch for a finding.
"""
from app.agents.base import BaseAgent

REMEDIATION_SYSTEM_PROMPT = """\
You are the Remediation Agent inside SwarmShield, an AI security testing
framework. Given a confirmed vulnerability finding (the attack payload
that worked, the target's vulnerable response, and the OWASP category),
propose a concrete, actionable fix.

INPUT: a JSON object with owasp_category, title, description, payload,
target_response.

OUTPUT FORMAT — return ONLY valid JSON, no markdown fences, matching:
{
  "summary": "<one-line fix summary>",
  "explanation": "<2-4 sentences on why this fixes the root cause, not just this one payload>",
  "patch_type": "system_prompt" | "input_validation" | "permission_scope" | "code",
  "patch_content": "<the actual suggested snippet - e.g. a hardened system-prompt clause, a validation regex/rule, a permission-scoping change, or a short code fix>"
}

Prefer defense-in-depth: where possible, suggest BOTH a system-prompt-level
mitigation AND a structural one (input validation, permission scoping, or
output filtering), but keep patch_content focused on the single most
impactful change. Be specific to the evidence given, not generic advice.
"""


class RemediationAgent(BaseAgent):
    SYSTEM_PROMPT = REMEDIATION_SYSTEM_PROMPT

    def generate_patch(self, vulnerability_context_json: str) -> dict:
        return self.run(vulnerability_context_json, as_json=True)
