"""
Remediation-apply + re-validation service. Neither source repo implemented
this at all. Flow:

  1. `apply_patch_to_target` — POSTs to the target's `/admin/apply_patch`
     endpoint (implemented on our controlled target, see
     controlled_target/app.py) so the fix is actually live before we
     re-test, not just a status flag we set ourselves.
  2. `revalidate_vulnerability` — replays the EXACT winning payload from
     the vulnerability's source AttackLog through the same TargetClient,
     runs it through the same SentinelAgent used during the original scan,
     and records a RevalidationRecord with a genuine pass/fail based on
     the new verdict -- not a hardcoded "now it's fixed".

This only works against targets that expose an apply-patch admin hook (our
controlled target does); for arbitrary third-party targets in a real
deployment, apply_patch_to_target would be a no-op and re-validation would
simply confirm whether the finding is still exploitable after a human
applies the fix out-of-band.
"""
import json
import uuid
from urllib.parse import urljoin

import httpx
from sqlalchemy.orm import Session

from app.agents.sentinel import SentinelAgent
from app.models.attack import AttackLog
from app.models.patch import RemediationPatch
from app.models.revalidation import RevalidationRecord, RevalidationResult
from app.models.vulnerability import Vulnerability, VulnerabilityStatus
from app.services.authorization import ensure_direct_apply_allowed
from app.services.target_client import TargetClient


async def apply_patch_to_target(target, patch: RemediationPatch) -> dict:
    """Best-effort: only the controlled target implements this admin hook.
    Real third-party targets won't, and that's fine -- revalidation still
    works, it'll just show the finding as still open until a human applies
    the fix out of band.

    SECURITY: this is the one function that can actually write to a live
    target, so the read-only/permission gate is enforced right here (not
    just in the route) -- ensure_direct_apply_allowed raises HTTPException
    (403) if the target hasn't been explicitly opted into read_write access
    AND allow_direct_patch_apply. This makes the check apply no matter what
    calls this function in the future, not only today's single route."""
    ensure_direct_apply_allowed(target)

    admin_url = urljoin(target.endpoint_url, "/admin/apply_patch")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(admin_url)
            resp.raise_for_status()
            return {"applied": True, "target_ack": resp.json()}
    except httpx.HTTPError as e:
        return {"applied": False, "error": str(e)}


async def revalidate_vulnerability(db: Session, *, vulnerability_id: uuid.UUID, patch_id: uuid.UUID | None = None) -> RevalidationRecord:
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vulnerability_id).one()
    source_attack = db.query(AttackLog).filter(AttackLog.id == vuln.source_attack_id).one()
    target = vuln.scan.target

    client = TargetClient(target)
    replay_result = await client.send(source_attack.payload)
    replay_output = replay_result.get("output") or ""

    sentinel = SentinelAgent()
    sentinel_context = json.dumps({
        "agent_type": source_attack.agent_type.value,
        "owasp_category": vuln.owasp_category,
        "payload": source_attack.payload,
        "target_response": replay_output,
    })
    verdict = sentinel.evaluate(sentinel_context)
    still_vulnerable = bool(verdict.get("violation_detected"))

    result = RevalidationResult.STILL_VULNERABLE if still_vulnerable else RevalidationResult.FIXED
    record = RevalidationRecord(
        id=uuid.uuid4(),
        vulnerability_id=vuln.id,
        patch_id=patch_id,
        replayed_payload=source_attack.payload,
        replayed_response=replay_output,
        sentinel_verdict=json.dumps(verdict),
        result=result,
        passed=not still_vulnerable,
    )
    db.add(record)

    vuln.status = (
        VulnerabilityStatus.REVALIDATION_FAILED if still_vulnerable else VulnerabilityStatus.REVALIDATION_PASSED
    )
    db.commit()
    db.refresh(record)
    return record
