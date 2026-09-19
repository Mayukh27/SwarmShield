"""
Server-side write-authorization gates for SwarmShield operations.

These are intentionally the ONLY place that decides whether a write
operation (direct patch application to a live target, or PR creation
against GitHub) is allowed. Routes and services call these functions
instead of re-implementing the checks inline, so the rule can't drift
between call sites and can't be bypassed by a client that simply omits a
frontend confirmation step -- the frontend never gets a vote here.

Two independent permissions, by design (see models/target.py):
  - direct patch application requires access_mode == READ_WRITE AND
    allow_direct_patch_apply == True on the TargetProfile.
  - PR creation requires allow_pr_creation == True on the TargetProfile.
    It does not require READ_WRITE access_mode, because opening a PR never
    touches the live target -- it proposes a change to a code repo that a
    human must review and merge out of band.

Neither permission is ever inferred from `TargetProfile.authorized` (the
"I own/may test this target" attestation) -- authorization to scan a
target says nothing about authorization to write to it or to a connected
GitHub repo. Both must be granted explicitly, separately.
"""
from fastapi import HTTPException

from app.models.target import TargetAccessMode, TargetProfile


def ensure_direct_apply_allowed(target: TargetProfile) -> None:
    """Raises 403 unless this target has been explicitly opted into both
    read-write mode AND direct patch application. Call this from every
    code path that can result in a live write to a target -- not just the
    HTTP route -- so there is no way to reach the target's admin hook
    without both checks passing."""
    if target.access_mode != TargetAccessMode.READ_WRITE:
        raise HTTPException(
            status_code=403,
            detail=(
                "This target is in read-only mode. Direct remediation "
                "application is disabled. Scanning, attack execution, "
                "finding/remediation generation, and revalidation (without "
                "applying) remain available. Switch the target to "
                "read_write access_mode to enable direct patch application."
            ),
        )
    if not target.allow_direct_patch_apply:
        raise HTTPException(
            status_code=403,
            detail=(
                "This target has not been granted the "
                "allow_direct_patch_apply permission. read_write access_mode "
                "alone is not sufficient -- direct patch application "
                "requires its own explicit opt-in, separate from PR creation."
            ),
        )


def ensure_pr_allowed(target: TargetProfile) -> None:
    """Raises 403 unless this target has been explicitly opted into PR
    creation. Independent of access_mode / allow_direct_patch_apply."""
    if not target.allow_pr_creation:
        raise HTTPException(
            status_code=403,
            detail=(
                "This target has not been granted the allow_pr_creation "
                "permission. PR creation requires its own explicit opt-in, "
                "separate from direct patch application."
            ),
        )


def ensure_branch_write_allowed(target: TargetProfile) -> None:
    """Raises 403 unless SwarmShield may write a remediation branch for a
    private target. This is separate from direct live patch application:
    branch writes are code-repo writes, not target runtime writes."""
    if target.access_mode != TargetAccessMode.READ_WRITE:
        raise HTTPException(
            status_code=403,
            detail="Branch remediation requires read_write access_mode on the target.",
        )
    if not target.allow_branch_write:
        raise HTTPException(
            status_code=403,
            detail="This target has not granted allow_branch_write permission.",
        )
