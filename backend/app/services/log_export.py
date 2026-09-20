"""
Battle-log export (Phase 2): one scan ("battle") -> structured JSON / plain text.

Safety model
  1. EXPLICIT ALLOW-LIST: every exported DB record is built field by field
     below. Columns that are not listed are never exported -- in particular
     TargetProfile.auth_header_name / auth_header_value.
  2. REDACTION of free text: payloads, target responses, evidence etc. can
     legitimately contain leaked secrets (that is what the swarm hunts for),
     so all strings are scrubbed for key/value secrets, bearer/JWT/well-known
     token shapes, and the exact values of secrets configured for this
     backend (Gemini/Grok/GitHub/gateway keys).
  3. Gateway (A2A) data has no fixed schema, so it is sanitised recursively:
     values under secret-looking keys are dropped and strings are scrubbed.
  4. Large text is truncated (marked) so an export cannot balloon unbounded.
Nothing is invented: sections that have no data are empty / marked unavailable.
"""
from __future__ import annotations

import enum
import json
import re
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.attack import AttackLog
from app.models.attack_dna import AttackDNARecord, ConsensusRecord
from app.models.llm_usage import LLMUsageRecord
from app.models.memory import MemoryRecord
from app.models.revalidation import RevalidationRecord
from app.models.scan import ScanRun
from app.models.vulnerability import Vulnerability
from app.services import usage_service

SCHEMA_VERSION = "1.0"
MAX_TEXT_CHARS = 20_000       # per string field
MAX_GATEWAY_EVENTS = 200
REDACTED = "[REDACTED]"

_SECRET_KEY = re.compile(
    r"(?i)(api[_-]?key|apikey|secret|passw(?:or)?d|passwd|token|authorization|credential|"
    r"cookie|private[_-]?key|access[_-]?key|auth[_-]?header)"
)
# key = value / key: value  (value up to whitespace, quote or comma)
_KV = re.compile(
    r"(?i)\b([\w.-]*(?:api[_-]?key|apikey|secret|passw(?:or)?d|passwd|token|authorization|"
    r"credential|session[_-]?cookie|private[_-]?key|access[_-]?key)[\w.-]*)(\s*[:=]\s*)"
    r"(?:Bearer\s+|Basic\s+)?(\"[^\"]*\"|'[^']*'|[^\s\"',;}]+)"
)
_BEARER = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_TOKEN_SHAPES = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),                       # OpenAI/Anthropic-style
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}"),                     # Google API key
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),                 # GitHub tokens
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),               # Slack
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                         # AWS access key id
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),  # JWT
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"),
]


def _configured_secrets() -> list[str]:
    values = [settings.GEMINI_API_KEY, settings.GROK_API_KEY, settings.GITHUB_TOKEN, settings.SWARMSHIELD_API_KEY]
    return sorted({v for v in values if v and len(v) >= 6}, key=len, reverse=True)


def redact_text(text: str) -> str:
    """Scrub secrets from one string and truncate it if huge."""
    if not text:
        return text
    truncated = 0
    if len(text) > MAX_TEXT_CHARS:
        truncated = len(text) - MAX_TEXT_CHARS
        text = text[:MAX_TEXT_CHARS]
    for secret in _configured_secrets():
        text = text.replace(secret, REDACTED)
    text = _KV.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
    text = _BEARER.sub(lambda m: f"{m.group(1)} {REDACTED}", text)
    for rx in _TOKEN_SHAPES:
        text = rx.sub(REDACTED, text)
    if truncated:
        text += f"\n[truncated {truncated} more characters]"
    return text


def sanitize(value: Any, _depth: int = 0) -> Any:
    """Recursively make arbitrary data JSON-safe and secret-free."""
    if _depth > 12:
        return "[max depth]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            key = str(k)
            # only STRING values under secret-looking keys are dropped (so counters such as "total_tokens" stay)
            out[key] = REDACTED if (_SECRET_KEY.search(key) and isinstance(v, str) and v) else sanitize(v, _depth + 1)
        return out
    if isinstance(value, (list, tuple, set)):
        return [sanitize(v, _depth + 1) for v in value]
    return redact_text(str(value))


def _safe_url(url: str | None) -> str | None:
    """Drop userinfo and query string (both can carry credentials)."""
    if not url:
        return url
    try:
        p = urlsplit(url)
        host = p.hostname or ""
        if p.port:
            host = f"{host}:{p.port}"
        return urlunsplit((p.scheme, host, p.path, "", ""))
    except ValueError:
        return REDACTED


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _val(x: Any) -> Any:
    return x.value if isinstance(x, enum.Enum) else x


def fetch_gateway_snapshot(timeout: float = 2.0) -> dict[str, Any]:
    """Best-effort A2A gateway snapshot. The gateway keeps its recent events
    and quarantine registry in memory and does not tag them per scan, so this
    is GATEWAY-WIDE context, labelled as such."""
    if not settings.SWARMSHIELD_GATEWAY_URL:
        return {"available": False, "reason": "SWARMSHIELD_GATEWAY_URL is not configured"}
    base = settings.SWARMSHIELD_GATEWAY_URL.rstrip("/")
    headers = {"X-SwarmShield-Key": settings.SWARMSHIELD_API_KEY} if settings.SWARMSHIELD_API_KEY else {}
    try:
        with httpx.Client(timeout=timeout) as client:
            ev = client.get(f"{base}/v1/events?limit={MAX_GATEWAY_EVENTS}", headers=headers)
            ev.raise_for_status()
            ag = client.get(f"{base}/v1/agents", headers=headers)
            ag.raise_for_status()
        return {"available": True, "events": ev.json(), "agents": ag.json()}
    except (httpx.HTTPError, ValueError) as exc:
        return {"available": False, "reason": f"gateway unreachable: {type(exc).__name__}"}


def _a2a_section(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    note = "Gateway-wide recent decisions; the gateway does not tag events per scan."
    if not snapshot or not snapshot.get("available"):
        return {"available": False, "scope": "gateway-wide", "reason": (snapshot or {}).get("reason", "not collected"),
                "events": [], "quarantine_events": [], "quarantined_agents": [], "counters": {}, "note": note}
    ev = snapshot.get("events") or {}
    events = sanitize(list(ev.get("events") or [])[-MAX_GATEWAY_EVENTS:])
    agents = sanitize((snapshot.get("agents") or {}).get("agents") or [])
    quarantined = [a for a in agents if isinstance(a, dict) and "quarantin" in str(a.get("status", "")).lower()]
    q_events = [e for e in events if isinstance(e, dict) and (
        e.get("quarantined_agents")  # gateway lists the agents this decision quarantined
        or any("quarantin" in str(v).lower() for v in e.values() if isinstance(v, str)))]
    return {
        "available": True, "scope": "gateway-wide", "note": note,
        "events": events, "quarantine_events": q_events, "quarantined_agents": quarantined,
        "conversations": sanitize((snapshot.get("agents") or {}).get("conversations") or []),
        "counters": sanitize(ev.get("counters") or {}),
    }


def build_scan_export(db: Session, scan_id: uuid.UUID, *, gateway_snapshot: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return the allow-listed, redacted export dict, or None if the scan doesn't exist."""
    scan = db.query(ScanRun).filter(ScanRun.id == scan_id).first()
    if scan is None:
        return None
    target = scan.target

    attacks = db.query(AttackLog).filter(AttackLog.scan_id == scan_id).order_by(AttackLog.created_at).all()
    vulns = db.query(Vulnerability).filter(Vulnerability.scan_id == scan_id).order_by(Vulnerability.created_at).all()
    memories = db.query(MemoryRecord).filter(MemoryRecord.scan_id == scan_id).order_by(MemoryRecord.created_at).all()
    dna = db.query(AttackDNARecord).filter(AttackDNARecord.scan_id == scan_id).order_by(AttackDNARecord.created_at).all()
    usage_rows = db.query(LLMUsageRecord).filter(LLMUsageRecord.scan_id == scan_id).order_by(LLMUsageRecord.created_at).all()

    findings = []
    for v in vulns:
        consensus = db.query(ConsensusRecord).filter(ConsensusRecord.vulnerability_id == v.id).order_by(ConsensusRecord.created_at).all()
        findings.append({
            "id": str(v.id), "source_attack_id": str(v.source_attack_id),
            "title": v.title, "owasp_category": v.owasp_category,
            "severity": _val(v.severity), "status": _val(v.status),
            "risk_score": v.risk_score, "description": v.description,
            "evidence": v.evidence, "created_at": _iso(v.created_at),
            "consensus": [{"agent": c.agent, "verdict": c.verdict, "confidence": c.confidence,
                           "evidence_summary": c.evidence_summary, "created_at": _iso(c.created_at)} for c in consensus],
            "remediation": [{"id": str(p.id), "summary": p.summary, "explanation": p.explanation,
                             "patch_type": p.patch_type, "patch_content": p.patch_content,
                             "created_at": _iso(p.created_at)} for p in sorted(v.patches, key=lambda p: p.created_at or datetime.min)],
            "revalidation": [{"id": str(r.id), "patch_id": str(r.patch_id) if r.patch_id else None,
                              "replayed_payload": r.replayed_payload, "replayed_response": r.replayed_response,
                              "sentinel_verdict": r.sentinel_verdict, "result": _val(r.result), "passed": r.passed,
                              "created_at": _iso(r.created_at)}
                             for r in sorted(v.revalidation_records, key=lambda r: r.created_at or datetime.min)],
        })

    per_agent: dict[str, dict[str, int]] = {}
    for a in attacks:
        d = per_agent.setdefault(_val(a.agent_type), {"attempts": 0, "successful": 0})
        d["attempts"] += 1
        d["successful"] += 1 if a.succeeded else 0

    usage = usage_service.get_scan_usage(db, scan_id)
    usage["calls"] = [{"agent_type": u.agent_type, "provider": u.provider, "model": u.model,
                       "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                       "total_tokens": u.total_tokens, "timestamp": _iso(u.created_at)} for u in usage_rows]
    usage["available"] = usage["llm_calls"] > 0

    export = {
        "export": {"schema_version": SCHEMA_VERSION, "exported_at": datetime.utcnow().isoformat() + "Z",
                   "generator": "SwarmShield", "redaction": "Secrets (keys, passwords, tokens, credentials) are redacted; large text is truncated."},
        "battle": {
            "id": str(scan.id), "status": _val(scan.status),
            "start_time": _iso(scan.started_at), "end_time": _iso(scan.completed_at),
            "risk_score": scan.risk_score, "risk_breakdown": scan.risk_breakdown,
            "total_attempts": scan.total_attempts, "successful_attacks": scan.successful_attacks,
            "attack_plan": scan.attack_plan,
        },
        "target": {
            "id": str(target.id), "name": target.name, "description": target.description,
            "endpoint_url": _safe_url(target.endpoint_url),
            "access_mode": _val(target.access_mode), "code_visibility": _val(target.code_visibility),
            "authorized": target.authorized,
            "declared_tools": target.declared_tools, "permission_map": target.permission_map,
        } if target else None,
        "agents": [{"agent_type": k, **v} for k, v in sorted(per_agent.items())],
        "attack_steps": [{
            "id": str(a.id), "step": i + 1, "agent_type": _val(a.agent_type), "attack_type": a.owasp_category,
            "generation": a.generation, "parent_attempt_id": str(a.parent_attempt_id) if a.parent_attempt_id else None,
            "payload": a.payload, "target_response": a.target_response,
            "verdict": a.sentinel_verdict, "succeeded": a.succeeded, "timestamp": _iso(a.created_at),
        } for i, a in enumerate(attacks)],
        "findings": findings,
        "attack_dna": [{"id": str(d.id), "vector_id": d.vector_id, "generation": d.generation,
                        "parent_id": str(d.parent_id) if d.parent_id else None,
                        "genome": d.genome, "mutations": d.mutations,
                        "success_probability": d.success_probability, "confidence": d.confidence,
                        "source_attack_id": str(d.source_attack_id) if d.source_attack_id else None,
                        "timestamp": _iso(d.created_at)} for d in dna],
        "shared_memory": [{"id": str(m.id), "type": _val(m.memory_type), "agent": m.agent, "content": m.content,
                           "confidence": m.confidence, "source_attack_id": str(m.source_attack_id) if m.source_attack_id else None,
                           "timestamp": _iso(m.created_at)} for m in memories],
        "token_usage": usage,
        "a2a_security": _a2a_section(gateway_snapshot),
    }
    return sanitize(export)


def to_json(export: dict[str, Any]) -> str:
    return json.dumps(export, indent=2, ensure_ascii=False, default=str)


def to_text(export: dict[str, Any]) -> str:
    """Human-readable rendering of the same (already redacted) export dict."""
    b, t = export["battle"], export.get("target") or {}
    L: list[str] = []
    add = L.append
    add("SWARMSHIELD BATTLE LOG")
    add("=" * 60)
    add(f"Battle ID : {b['id']}")
    add(f"Status    : {b['status']}")
    add(f"Target    : {t.get('name')} ({t.get('endpoint_url')})")
    add(f"Started   : {b['start_time']}")
    add(f"Ended     : {b['end_time']}")
    add(f"Risk score: {b['risk_score']}   Attempts: {b['total_attempts']}   Successful: {b['successful_attacks']}")
    add(f"Exported  : {export['export']['exported_at']}  (secrets redacted)")
    u = export["token_usage"]
    add("")
    add("TOKEN USAGE")
    add("-" * 60)
    if u["available"]:
        add(f"{u['provider']} / {u['model']}: input {u['input_tokens']}  output {u['output_tokens']}  total {u['total_tokens']}  calls {u['llm_calls']}")
    else:
        add("No LLM usage recorded for this battle.")
    add("")
    add(f"ATTACK STEPS ({len(export['attack_steps'])})")
    add("-" * 60)
    for s in export["attack_steps"]:
        add(f"[{s['step']}] {s['timestamp']}  {s['agent_type']}  {s['attack_type'] or ''}  gen={s['generation']}  succeeded={s['succeeded']}")
        add(f"    payload : {s['payload']}")
        add(f"    response: {s['target_response']}")
        add(f"    verdict : {json.dumps(s['verdict'], default=str) if s['verdict'] is not None else None}")
    add("")
    add(f"FINDINGS ({len(export['findings'])})")
    add("-" * 60)
    for f in export["findings"]:
        add(f"* [{str(f['severity']).upper()}] {f['title']}  ({f['owasp_category']})  status={f['status']}  risk={f['risk_score']}")
        add(f"    evidence: {f['evidence']}")
        for p in f["remediation"]:
            add(f"    remediation ({p['patch_type']}): {p['summary']}")
        for r in f["revalidation"]:
            add(f"    revalidation: {r['result']} passed={r['passed']} at {r['created_at']}")
    a2a = export["a2a_security"]
    add("")
    add("A2A SECURITY (gateway-wide)")
    add("-" * 60)
    if a2a["available"]:
        add(f"events: {len(a2a['events'])}  quarantine events: {len(a2a['quarantine_events'])}  quarantined agents: {len(a2a['quarantined_agents'])}")
    else:
        add(f"not available: {a2a.get('reason')}")
    add("")
    add("Full detail (agents, DNA, memory, per-call tokens) is in the JSON export.")
    return "\n".join(L) + "\n"
