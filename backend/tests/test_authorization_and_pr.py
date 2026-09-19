"""
Tests for:
  - server-side read-only enforcement (direct patch application blocked
    unless a target explicitly opts into read_write + allow_direct_patch_apply)
  - remediation generation still working regardless of access mode
  - the auto-PR workflow, using a mocked GitHub boundary (github_service is
    monkeypatched -- no real network calls, no real token required)
  - no secrets (GitHub token) ever appearing in an API response

Uses the real Postgres DB configured via DATABASE_URL, same convention as
tests/test_services.py. Each test creates and cleans up its own rows.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.base import SessionLocal, get_db
from app.main import app
from app.models.attack import AgentType, AttackLog
from app.models.patch import RemediationPatch
from app.models.remediation_pr import RemediationPR, RemediationPRStatus
from app.models.scan import ScanRun
from app.models.target import TargetAccessMode, TargetProfile
from app.models.vulnerability import Severity, Vulnerability
from app.services import github_service
from app.services.authorization import ensure_direct_apply_allowed, ensure_pr_allowed
from app.services.revalidation_service import apply_patch_to_target
from fastapi import HTTPException


@pytest.fixture
def db():
    session: Session = SessionLocal()
    yield session
    session.rollback()
    session.close()


def _override_get_db(session):
    def _get_db():
        try:
            yield session
        finally:
            pass
    return _get_db


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = _override_get_db(db)
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def full_finding(db):
    """Builds target -> scan -> attack_log -> vulnerability -> patch, the
    full chain needed to exercise apply-and-revalidate and create-pr.
    Target defaults to read_only / no write permissions (the safe default)
    unless the test mutates it before calling an endpoint."""
    target = TargetProfile(
        id=uuid.uuid4(), name="authz-test-target", endpoint_url="http://127.0.0.1:9999/nonexistent",
        declared_tools={}, permission_map={}, authorized=True,
    )
    db.add(target)
    db.commit()

    scan = ScanRun(id=uuid.uuid4(), target_id=target.id)
    db.add(scan)
    db.commit()

    log = AttackLog(id=uuid.uuid4(), scan_id=scan.id, agent_type=AgentType.PROMPT_INJECTION, payload="x", succeeded=True)
    db.add(log)
    db.commit()

    vuln = Vulnerability(
        id=uuid.uuid4(), scan_id=scan.id, source_attack_id=log.id,
        title="t", owasp_category="LLM01: Prompt Injection", severity=Severity.HIGH, description="d",
    )
    db.add(vuln)
    db.commit()

    patch = RemediationPatch(
        id=uuid.uuid4(), vulnerability_id=vuln.id,
        summary="Harden input validation", explanation="root cause fix",
        patch_type="input_validation", patch_content="reject payloads matching X",
    )
    db.add(patch)
    db.commit()
    db.refresh(target)
    db.refresh(vuln)
    db.refresh(patch)

    yield {"target": target, "scan": scan, "log": log, "vuln": vuln, "patch": patch}

    db.rollback()
    for cls, obj_id in [
        (RemediationPR, None), (RemediationPatch, patch.id), (Vulnerability, vuln.id),
        (AttackLog, log.id), (ScanRun, scan.id), (TargetProfile, target.id),
    ]:
        if cls is RemediationPR:
            for pr in db.query(RemediationPR).filter(RemediationPR.patch_id == patch.id).all():
                db.delete(pr)
            db.commit()
            continue
        obj = db.get(cls, obj_id)
        if obj:
            db.delete(obj)
            db.commit()


# --- Read-only enforcement (server-side, not just frontend) ------------------

def test_default_target_is_read_only(full_finding):
    """Safe-by-default: a target created without any access_mode override
    must default to read_only with both write permissions off."""
    target = full_finding["target"]
    assert target.access_mode == TargetAccessMode.READ_ONLY
    assert target.allow_direct_patch_apply is False
    assert target.allow_pr_creation is False


@pytest.mark.asyncio
async def test_direct_apply_rejected_for_read_only_target(full_finding):
    """The core requirement: direct patch application must be rejected in
    read-only mode, enforced in the service layer itself (not only the
    route), so no caller can bypass it."""
    target = full_finding["target"]
    patch = full_finding["patch"]
    with pytest.raises(HTTPException) as exc_info:
        await apply_patch_to_target(target, patch)
    assert exc_info.value.status_code == 403
    assert "read-only" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_direct_apply_rejected_when_read_write_but_no_explicit_apply_permission(db, full_finding):
    """read_write alone is not enough -- allow_direct_patch_apply must also
    be explicitly granted. Confirms the two gates are genuinely independent."""
    target = full_finding["target"]
    target.access_mode = TargetAccessMode.READ_WRITE
    db.commit()
    with pytest.raises(HTTPException) as exc_info:
        await apply_patch_to_target(target, full_finding["patch"])
    assert exc_info.value.status_code == 403
    assert "allow_direct_patch_apply" in exc_info.value.detail


@pytest.mark.asyncio
async def test_direct_apply_allowed_once_both_gates_granted(db, full_finding):
    """Once a target explicitly opts into read_write AND
    allow_direct_patch_apply, the authorization gate passes (the actual
    HTTP call to the target's admin hook then fails because the test target
    URL doesn't exist -- that's a network-layer failure, not a permission
    rejection, and it's returned as a dict, not raised)."""
    target = full_finding["target"]
    target.access_mode = TargetAccessMode.READ_WRITE
    target.allow_direct_patch_apply = True
    db.commit()
    result = await apply_patch_to_target(target, full_finding["patch"])
    assert result["applied"] is False
    assert "error" in result  # connection failure, not an authorization failure


def test_apply_and_revalidate_endpoint_returns_403_for_read_only_target(client, full_finding):
    """HTTP-level confirmation: POST .../apply-and-revalidate?apply=true
    against a read-only target is rejected server-side with 403, not a
    silently-degraded 200."""
    vuln_id = full_finding["vuln"].id
    patch_id = full_finding["patch"].id
    resp = client.post(f"/api/vulnerabilities/{vuln_id}/apply-and-revalidate?apply=true&patch_id={patch_id}")
    assert resp.status_code == 403
    assert "read-only" in resp.json()["detail"].lower()


def test_apply_and_revalidate_endpoint_allows_revalidate_only_on_read_only_target(client, full_finding):
    """apply=false (replay + Sentinel re-evaluation, no write) must work on
    every target regardless of access_mode -- this is the read-only-allowed
    'viewing reports' / revalidation-without-writing path."""
    vuln_id = full_finding["vuln"].id
    resp = client.post(f"/api/vulnerabilities/{vuln_id}/apply-and-revalidate?apply=false")
    assert resp.status_code == 200
    body = resp.json()
    assert body["patch_apply_result"]["applied"] is False
    assert "revalidation" in body


# --- Remediation generation unaffected by access mode ------------------------

def test_remediation_generation_works_on_read_only_target(client, full_finding):
    """Generating a NEW patch (not applying one) is a read-only-safe
    operation and must keep working regardless of access_mode."""
    vuln_id = full_finding["vuln"].id
    resp = client.post(f"/api/patches/generate/{vuln_id}")
    assert resp.status_code == 201
    body = resp.json()
    assert body["patch_content"]
    assert body["summary"]


# --- Auto-PR workflow, mocked GitHub boundary --------------------------------

def test_create_pr_rejected_without_explicit_pr_permission(client, full_finding):
    patch_id = full_finding["patch"].id
    resp = client.post(f"/api/patches/{patch_id}/create-pr")
    assert resp.status_code == 403
    assert "allow_pr_creation" in resp.json()["detail"]


def test_create_pr_safe_failure_when_github_not_configured(db, client, full_finding):
    """Permission granted, but no GITHUB_TOKEN/GITHUB_REPO configured --
    must fail safely with a clear 400, not crash and not invent creds."""
    target = full_finding["target"]
    target.allow_pr_creation = True
    db.commit()
    patch_id = full_finding["patch"].id

    from app.core.config import settings
    original_token, original_repo = settings.GITHUB_TOKEN, settings.GITHUB_REPO
    settings.GITHUB_TOKEN, settings.GITHUB_REPO = "", ""
    try:
        resp = client.post(f"/api/patches/{patch_id}/create-pr")
        assert resp.status_code == 400
        assert "not configured" in resp.json()["detail"].lower()
    finally:
        settings.GITHUB_TOKEN, settings.GITHUB_REPO = original_token, original_repo


def test_create_pr_succeeds_with_mocked_github_boundary(db, client, full_finding, monkeypatch):
    """PR creation exercised end-to-end through a mocked github_service --
    the safe boundary to test against when real GitHub credentials aren't
    available, per the task requirements. Confirms: branch/PR flow reaches
    the service, a RemediationPR row is recorded, and the response contains
    only non-secret fields."""
    target = full_finding["target"]
    target.allow_pr_creation = True
    db.commit()
    patch_id = full_finding["patch"].id
    vuln_id = full_finding["vuln"].id

    async def fake_open_remediation_pr(**kwargs):
        assert kwargs["patch_id"] == patch_id
        assert kwargs["vulnerability_id"] == vuln_id
        return {
            "configured": True,
            "status": "created",
            "repo": "acme/example-repo",
            "base_branch": "main",
            "branch_name": f"swarmshield/remediation-{str(patch_id)[:8]}",
            "pr_number": 42,
            "pr_url": "https://github.com/acme/example-repo/pull/42",
            "error": None,
        }

    monkeypatch.setattr(github_service, "open_remediation_pr", fake_open_remediation_pr)

    resp = client.post(f"/api/patches/{patch_id}/create-pr")
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "created"
    assert body["pr_number"] == 42
    assert body["pr_url"] == "https://github.com/acme/example-repo/pull/42"

    record = db.query(RemediationPR).filter(RemediationPR.patch_id == patch_id).first()
    assert record is not None
    assert record.status == RemediationPRStatus.CREATED


def test_create_pr_never_merges(full_finding):
    """There is no merge capability anywhere in the PR router or the
    GitHub service module -- confirms by introspection that the feature
    genuinely can't auto-merge, not just that it isn't called. Checks for
    actual merge-capable code (an HTTP call whose URL/path targets a merge
    endpoint, or a function that performs one) rather than the bare word,
    since the module's own comments legitimately say things like "never
    merges" as documentation of the safety property."""
    import ast
    import inspect

    import app.api.routes.remediation_pr as pr_route

    source = inspect.getsource(pr_route) + "\n" + inspect.getsource(github_service)
    tree = ast.parse(source)

    merge_call_found = False
    for node in ast.walk(tree):
        # Look for any client.<verb>(...) call (get/post/put/patch/delete --
        # the httpx call shapes used elsewhere in this codebase) whose
        # first string-literal argument contains "merge" as a path segment,
        # i.e. an actual outbound request to a merge endpoint.
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and "merge" in arg.value.lower():
                    merge_call_found = True
        # Also catch a function/method literally named merge / *_merge.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "merge" in node.name.lower():
            merge_call_found = True

    assert not merge_call_found, "found code that appears to call a merge endpoint or implement merging"


# --- No secrets leak through responses/logs ----------------------------------

def test_github_token_never_in_pr_response(db, client, full_finding, monkeypatch, capsys):
    target = full_finding["target"]
    target.allow_pr_creation = True
    db.commit()
    patch_id = full_finding["patch"].id

    from app.core.config import settings
    fake_token = "ghp_SUPERSECRETTOKENVALUE1234567890"
    original_token, original_repo = settings.GITHUB_TOKEN, settings.GITHUB_REPO
    settings.GITHUB_TOKEN, settings.GITHUB_REPO = fake_token, "acme/example-repo"

    async def fake_open_remediation_pr(**kwargs):
        return {
            "configured": True, "status": "created", "repo": "acme/example-repo",
            "base_branch": "main", "branch_name": "swarmshield/remediation-abcd1234",
            "pr_number": 7, "pr_url": "https://github.com/acme/example-repo/pull/7", "error": None,
        }

    monkeypatch.setattr(github_service, "open_remediation_pr", fake_open_remediation_pr)
    try:
        resp = client.post(f"/api/patches/{patch_id}/create-pr")
        assert resp.status_code == 201
        assert fake_token not in resp.text
        captured = capsys.readouterr()
        assert fake_token not in captured.out
        assert fake_token not in captured.err
    finally:
        settings.GITHUB_TOKEN, settings.GITHUB_REPO = original_token, original_repo


def test_target_response_never_includes_credentials(client, full_finding):
    """TargetProfileOut must not leak auth_header_value (the target's own
    stored credential) -- confirms the existing exclusion still holds after
    the schema changes made in this task."""
    target_id = full_finding["target"].id
    resp = client.get(f"/api/targets/{target_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert "auth_header_value" not in body
    assert "auth_header_name" not in body


# --- authorization.py unit-level sanity --------------------------------------

def test_ensure_pr_allowed_raises_for_default_target(full_finding):
    with pytest.raises(HTTPException) as exc_info:
        ensure_pr_allowed(full_finding["target"])
    assert exc_info.value.status_code == 403


def test_ensure_direct_apply_allowed_raises_for_default_target(full_finding):
    with pytest.raises(HTTPException) as exc_info:
        ensure_direct_apply_allowed(full_finding["target"])
    assert exc_info.value.status_code == 403
