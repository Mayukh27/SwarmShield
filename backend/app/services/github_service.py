"""
GitHub integration for the auto-PR remediation workflow:

  Finding -> patch generated -> (human reviews patch content) -> branch
  created -> patch committed -> PR opened -> human approval -> human merge
  -> revalidation.

This module never merges anything -- there is no merge function here and
none anywhere else in the codebase. Merge is a human action taken on
GitHub's own UI/API, outside SwarmShield's write surface.

SECURITY
--------
- The token is read once from `settings.GITHUB_TOKEN` (env var / secrets
  manager, never hardcoded -- see app/core/config.py) and used only as an
  in-memory Authorization header value on outbound requests to GitHub.
- The token is never logged, never included in any exception message we
  raise or return, and never present in any Pydantic response schema
  (see schemas/remediation_pr.py).
- If GITHUB_TOKEN or GITHUB_REPO is unset, `open_remediation_pr` returns a
  structured "not configured" result rather than raising an unhandled
  error or silently no-op'ing -- callers get a clear, safe signal either
  way and there is no code path that fabricates credentials.
- Least privilege: the README/`.env.example` call out that the PAT used
  here should be a fine-grained token scoped to Contents:write +
  Pull requests:write on the single target repo -- not a broad classic
  token. This module does not require or use any scope beyond that (it
  never calls any endpoint outside git refs / contents / pulls on the one
  configured repo).
"""
import base64
import uuid
from typing import Any, Optional

import httpx

from app.core.config import settings


class GitHubNotConfiguredError(Exception):
    """Raised when a GitHub operation is attempted without GITHUB_TOKEN /
    GITHUB_REPO configured. Never carries any secret in its message."""


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _redact_httpx_error(e: httpx.HTTPStatusError) -> str:
    """Turns an httpx error into a message safe to store/return -- strips
    request headers (which would include the Authorization token) and
    keeps only the status code and a short slice of the response body."""
    status = e.response.status_code if e.response is not None else "unknown"
    body = ""
    if e.response is not None:
        try:
            body = e.response.text[:300]
        except Exception:
            body = ""
    return f"GitHub API error (status={status}): {body}"


async def _get_base_branch_sha(client: httpx.AsyncClient, repo: str, base_branch: str) -> str:
    resp = await client.get(f"/repos/{repo}/git/ref/heads/{base_branch}", headers=_headers())
    resp.raise_for_status()
    return resp.json()["object"]["sha"]


async def _create_branch(client: httpx.AsyncClient, repo: str, branch_name: str, base_sha: str) -> None:
    resp = await client.post(
        f"/repos/{repo}/git/refs",
        headers=_headers(),
        json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
    )
    resp.raise_for_status()


async def _commit_patch_file(
    client: httpx.AsyncClient, repo: str, branch_name: str, file_path: str, content: str, commit_message: str
) -> None:
    resp = await client.put(
        f"/repos/{repo}/contents/{file_path}",
        headers=_headers(),
        json={
            "message": commit_message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch_name,
        },
    )
    resp.raise_for_status()


async def _open_pull_request(
    client: httpx.AsyncClient, repo: str, branch_name: str, base_branch: str, title: str, body: str
) -> dict[str, Any]:
    resp = await client.post(
        f"/repos/{repo}/pulls",
        headers=_headers(),
        json={"title": title, "head": branch_name, "base": base_branch, "body": body},
    )
    resp.raise_for_status()
    return resp.json()


async def open_remediation_pr(
    *,
    vulnerability_id: uuid.UUID,
    patch_id: uuid.UUID,
    patch_summary: str,
    patch_explanation: str,
    patch_type: str,
    patch_content: str,
) -> dict[str, Any]:
    """Creates a branch off GITHUB_BASE_BRANCH, commits the patch content as
    a single reviewable file, and opens a PR back to the base branch. Does
    NOT merge, approve, or auto-close anything -- returns as soon as the PR
    exists so a human can take it from there.

    Returns a dict with keys: configured (bool), status ("created" |
    "failed" | "not_configured"), repo, base_branch, branch_name, pr_number,
    pr_url, error. Never includes the token.
    """
    if not settings.github_configured():
        return {
            "configured": False,
            "status": "not_configured",
            "repo": settings.GITHUB_REPO or None,
            "base_branch": settings.GITHUB_BASE_BRANCH,
            "branch_name": None,
            "pr_number": None,
            "pr_url": None,
            "error": (
                "GitHub integration is not configured (GITHUB_TOKEN and/or "
                "GITHUB_REPO unset). Set them as environment variables to "
                "enable auto-PR creation."
            ),
        }

    repo = settings.GITHUB_REPO
    base_branch = settings.GITHUB_BASE_BRANCH
    branch_name = f"swarmshield/remediation-{str(patch_id)[:8]}"
    file_path = f"swarmshield-remediations/{vulnerability_id}.md"

    file_content = (
        f"# SwarmShield remediation\n\n"
        f"- Vulnerability: `{vulnerability_id}`\n"
        f"- Patch: `{patch_id}`\n"
        f"- Type: `{patch_type}`\n\n"
        f"## Summary\n{patch_summary}\n\n"
        f"## Why this fixes the root cause\n{patch_explanation}\n\n"
        f"## Suggested change\n```\n{patch_content}\n```\n\n"
        f"_Generated by SwarmShield. Review before merging -- this PR is "
        f"never auto-merged._\n"
    )
    commit_message = f"SwarmShield: remediation for vulnerability {str(vulnerability_id)[:8]}"
    pr_title = f"SwarmShield remediation: {patch_summary[:80]}"
    pr_body = (
        f"Automatically generated by SwarmShield from a confirmed finding.\n\n"
        f"**Vulnerability:** `{vulnerability_id}`\n**Patch:** `{patch_id}`\n\n"
        f"{patch_explanation}\n\n"
        f"This PR requires human review and manual merge -- SwarmShield does "
        f"not merge pull requests."
    )

    async with httpx.AsyncClient(base_url=settings.GITHUB_API_URL, timeout=20.0) as client:
        try:
            base_sha = await _get_base_branch_sha(client, repo, base_branch)
            await _create_branch(client, repo, branch_name, base_sha)
            await _commit_patch_file(client, repo, branch_name, file_path, file_content, commit_message)
            pr = await _open_pull_request(client, repo, branch_name, base_branch, pr_title, pr_body)
            return {
                "configured": True,
                "status": "created",
                "repo": repo,
                "base_branch": base_branch,
                "branch_name": branch_name,
                "pr_number": pr.get("number"),
                "pr_url": pr.get("html_url"),
                "error": None,
            }
        except httpx.HTTPStatusError as e:
            return {
                "configured": True,
                "status": "failed",
                "repo": repo,
                "base_branch": base_branch,
                "branch_name": branch_name,
                "pr_number": None,
                "pr_url": None,
                "error": _redact_httpx_error(e),
            }
        except httpx.HTTPError as e:
            return {
                "configured": True,
                "status": "failed",
                "repo": repo,
                "base_branch": base_branch,
                "branch_name": branch_name,
                "pr_number": None,
                "pr_url": None,
                "error": f"GitHub request failed: {type(e).__name__}",
            }
