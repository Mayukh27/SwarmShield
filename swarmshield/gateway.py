"""SwarmShield Security Proxy Gateway.

Central interception server for agent-to-agent (A2A) traffic.

Pipeline for every ``POST /a2a/transfer``::

    quarantine check -> tripped-breaker check -> injection scan -> RBAC / taint policy
        -> circuit breaker observation -> verdict (ALLOW | FLAG | BLOCK | TRIP)

HTTP contract
    200  ALLOW or FLAG (FLAG = suspicious, ``requires_human_review`` is true)
    403  BLOCK  (prompt injection, RBAC violation, taint violation, quarantined sender)
    429  TRIP   (circuit breaker: recursion depth, velocity, repetition, ping-pong, token budget)

Also exposes a ``/ws/telemetry`` WebSocket that streams every decision to the dashboard.

Run:
    uvicorn swarmshield.gateway:app --host 0.0.0.0 --port 8000

Environment:
    SWARMSHIELD_API_KEY   optional shared secret (header ``X-SwarmShield-Key``)
    SWARMSHIELD_POLICY    optional path to a YAML/JSON RBAC policy
    SWARMSHIELD_CORS      comma separated dashboard origins (default: Vite dev server)

State is in-memory and single-process: every check-then-update sequence below is synchronous
(no ``await`` in between), so it is atomic on the event loop. Swap the stores for Redis to
run several replicas.
"""

from __future__ import annotations

import base64
import binascii
import fnmatch
import hmac
import json
import logging
import os
import re
import time
import unicodedata
import uuid
import zlib
import asyncio
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Deque, Optional

import yaml
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("swarmshield.gateway")

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        logger.warning("Invalid float for %s, using %s", name, default)
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        logger.warning("Invalid int for %s, using %s", name, default)
        return default


@dataclass(frozen=True)
class Settings:
    """Runtime tunables (all overridable through ``SWARMSHIELD_*`` env vars)."""

    api_key: Optional[str] = None
    policy_path: Optional[str] = None
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://localhost:3000")

    # Injection scoring
    flag_threshold: float = 0.35  # >= -> FLAG (human review / "inspected")
    block_threshold: float = 0.70  # >= -> BLOCK (403)

    # Circuit breaker
    max_depth: int = 25  # recursion depth (hop_count, or transfers seen in the conversation)
    velocity_window_s: float = 10.0
    velocity_max: int = 20  # transfers per window per conversation
    repeat_similarity: float = 0.85  # Jaccard >= -> "near duplicate"
    repeat_count: int = 3  # earlier near-duplicates before the next one trips
    pingpong_cycles: int = 3  # A->B->A->B ... cycles with similar content
    pingpong_similarity: float = 0.50
    token_budget: int = 50_000  # estimated tokens (chars/4) per conversation
    breaker_cooldown_s: int = 60

    # Agent quarantine
    quarantine_after: int = 3  # violations before quarantine (severe = immediate)
    inspect_ttl_s: float = 30.0  # how long an agent stays "inspected" after a flag

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.getenv("SWARMSHIELD_CORS")
        return cls(
            api_key=os.getenv("SWARMSHIELD_API_KEY") or None,
            policy_path=os.getenv("SWARMSHIELD_POLICY") or None,
            cors_origins=tuple(o.strip() for o in origins.split(",")) if origins else cls.cors_origins,
            flag_threshold=_env_float("SWARMSHIELD_FLAG_THRESHOLD", cls.flag_threshold),
            block_threshold=_env_float("SWARMSHIELD_BLOCK_THRESHOLD", cls.block_threshold),
            max_depth=_env_int("SWARMSHIELD_MAX_DEPTH", cls.max_depth),
            velocity_window_s=_env_float("SWARMSHIELD_VELOCITY_WINDOW", cls.velocity_window_s),
            velocity_max=_env_int("SWARMSHIELD_VELOCITY_MAX", cls.velocity_max),
            repeat_similarity=_env_float("SWARMSHIELD_REPEAT_SIMILARITY", cls.repeat_similarity),
            repeat_count=_env_int("SWARMSHIELD_REPEAT_COUNT", cls.repeat_count),
            pingpong_cycles=_env_int("SWARMSHIELD_PINGPONG_CYCLES", cls.pingpong_cycles),
            pingpong_similarity=_env_float("SWARMSHIELD_PINGPONG_SIMILARITY", cls.pingpong_similarity),
            token_budget=_env_int("SWARMSHIELD_TOKEN_BUDGET", cls.token_budget),
            breaker_cooldown_s=_env_int("SWARMSHIELD_BREAKER_COOLDOWN", cls.breaker_cooldown_s),
            quarantine_after=_env_int("SWARMSHIELD_QUARANTINE_AFTER", cls.quarantine_after),
            inspect_ttl_s=_env_float("SWARMSHIELD_INSPECT_TTL", cls.inspect_ttl_s),
        )


# --------------------------------------------------------------------------------------
# API models
# --------------------------------------------------------------------------------------


class Verdict(str, Enum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"
    TRIP = "trip"


class AgentStatus(str, Enum):
    NORMAL = "normal"  # green
    INSPECTED = "inspected"  # yellow
    QUARANTINED = "quarantined"  # red


class TransferRequest(BaseModel):
    """One A2A hop (or one tool invocation / tool result) to be inspected."""

    message: str = Field(..., max_length=200_000, description="Payload being handed to the receiver")
    sender_id: str = Field(..., min_length=1, max_length=128)
    receiver_id: str = Field(..., min_length=1, max_length=128)
    sender_role: str = Field(..., min_length=1, max_length=64)
    receiver_role: Optional[str] = Field(default=None, max_length=64)
    target_tool: Optional[str] = Field(default=None, max_length=128, description="Tool the receiver will run")
    tool_args: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str = Field(default_factory=lambda: f"conv-{uuid.uuid4().hex[:12]}")
    hop_count: int = Field(default=0, ge=0, description="Client-side delegation depth, if known")
    provenance: list[str] = Field(
        default_factory=list,
        description="Where the content came from, e.g. ['user'], ['untrusted_web'], ['tool_output']",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class TransferResponse(BaseModel):
    message_id: str
    verdict: Verdict
    risk_score: float
    violation_type: Optional[str] = None  # prompt_injection | rbac | taint | quarantined_sender | circuit_breaker
    reason: str = ""
    findings: list[dict[str, Any]] = Field(default_factory=list)
    sender_status: AgentStatus = AgentStatus.NORMAL
    requires_human_review: bool = False
    retry_after: Optional[int] = None
    latency_ms: float = 0.0


# --------------------------------------------------------------------------------------
# Prompt-injection detector
# --------------------------------------------------------------------------------------

_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
_B64_BLOB = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")


def normalize_text(text: str) -> str:
    """NFKC-fold, strip zero-width chars, collapse whitespace, lowercase."""
    folded = unicodedata.normalize("NFKC", text)
    folded = _ZERO_WIDTH.sub("", folded)
    return re.sub(r"\s+", " ", folded).strip().lower()


@dataclass(frozen=True)
class Finding:
    rule: str
    category: str
    weight: float
    evidence: str

    def as_dict(self) -> dict[str, Any]:
        return {"rule": self.rule, "category": self.category, "weight": self.weight, "evidence": self.evidence}


# (rule name, category, weight, regex) - patterns run on normalized (lowercase) text.
_RULES: tuple[tuple[str, str, float, re.Pattern[str]], ...] = tuple(
    (name, cat, weight, re.compile(pattern))
    for name, cat, weight, pattern in (
        (
            "override_instructions", "instruction_override", 0.80,
            r"\b(?:ignore|disregard|forget|override|bypass)\b[^.\n]{0,40}\b(?:previous|prior|above|earlier|all|any|your|the)\b"
            r"[^.\n]{0,40}\b(?:instructions?|prompts?|rules?|guidelines?|directives?|constraints?|policies|policy)\b",
        ),
        (
            "role_hijack", "role_hijack", 0.45,
            r"\b(?:you are now|from now on,? you|act as if you|pretend (?:to be|you are)|new persona|your new (?:role|task|instructions?))\b",
        ),
        (
            "fake_system_markup", "delimiter_spoofing", 0.60,
            r"</?\s*(?:system|assistant|instructions?)\s*>|\[/?(?:system|inst)\]|<\|im_(?:start|end)\|>|#{2,}\s*(?:system|new instructions?)",
        ),
        (
            "secret_disclosure", "exfiltration", 0.60,
            r"\b(?:reveal|print|show|repeat|leak|dump|output)\b[^.\n]{0,30}\b(?:system prompt|hidden instructions?|initial prompt|"
            r"api[_ -]?keys?|credentials|passwords?|secrets?|env(?:ironment)? variables?)\b",
        ),
        (
            "outbound_exfil", "exfiltration", 0.50,
            r"\b(?:send|post|upload|forward|exfiltrate|email|curl|wget)\b[^\n]{0,80}(?:https?://|[\w.+-]+@[\w-]+\.[\w.]+)",
        ),
        (
            "destructive_sql", "destructive_action", 0.85,
            r"\b(?:drop|truncate)\s+(?:table|database|schema)\b|\bdrop\s+all\s+tables\b|\bdelete\s+from\s+[\w.`\"']+\s*(?:;|$)|;\s*--",
        ),
        (
            "destructive_shell", "destructive_action", 0.85,
            r"\brm\s+-rf\b|\bmkfs(?:\.\w+)?\b|:\(\)\s*\{\s*:\|:&\s*\};:|\bformat\s+c:",
        ),
        (
            "stealth_directive", "concealment", 0.50,
            r"\b(?:do not|don't|never)\s+(?:tell|inform|notify|alert|mention)\b[^.\n]{0,30}\b(?:user|human|operator|admin)"
            r"|\bwithout\s+(?:telling|informing|notifying|alerting)\b|\bsilently\b",
        ),
        (
            "authority_spoof", "authority_spoofing", 0.50,
            r"\b(?:admin(?:istrator)?|developer|system|root|security team)\s+(?:override|mode|message|says|command|notice)\b"
            r"|\bauthori[sz]ed by\s+(?:the\s+)?(?:admin|system|developer)",
        ),
        (
            "jailbreak_keywords", "jailbreak", 0.60,
            r"\b(?:dan mode|developer mode|jailbreak(?:ed)?|do anything now)\b",
        ),
        (
            # Weak on its own (normal delegation looks like this); matters in combination.
            "agent_redirect", "delegation_hijack", 0.25,
            r"\b(?:tell|instruct|ask|command|order)\s+(?:the\s+)?(?:\w+\s+){0,2}(?:agent|assistant|bot)\s+to\b",
        ),
        ("hidden_html_comment", "obfuscation", 0.30, r"<!--.{0,400}?-->"),
    )
)


class InjectionDetector:
    """Heuristic indirect-prompt-injection scanner.

    Scores are combined with noisy-OR so several weak signals add up without
    exceeding 1.0. Content from untrusted provenance is scored more aggressively.
    Swap ``scan`` for an ML classifier (e.g. Prompt Guard) without touching callers.
    """

    def __init__(self, untrusted_sources: frozenset[str]) -> None:
        self._untrusted = untrusted_sources

    @staticmethod
    def _scan_layer(text: str, prefix: str) -> list[Finding]:
        found: list[Finding] = []
        for name, category, weight, pattern in _RULES:
            match = pattern.search(text)
            if match:
                found.append(Finding(prefix + name, category, weight, match.group(0)[:80]))
        return found

    @staticmethod
    def _decode_blobs(text: str, limit: int = 5) -> list[str]:
        """Decode base64-looking blobs so encoded payloads get scanned too."""
        decoded: list[str] = []
        for blob in _B64_BLOB.findall(text)[:limit]:
            padded = blob + "=" * (-len(blob) % 4)
            try:
                raw = base64.b64decode(padded, validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError, ValueError):
                continue
            if raw and sum(c.isprintable() or c.isspace() for c in raw) / len(raw) > 0.9:
                decoded.append(raw)
        return decoded

    def scan(self, text: str, provenance: list[str]) -> tuple[float, list[Finding]]:
        findings = self._scan_layer(normalize_text(text), "")

        if _ZERO_WIDTH.search(text):
            findings.append(Finding("hidden_unicode", "obfuscation", 0.30, "zero-width / bidi control characters"))

        for decoded in self._decode_blobs(text):
            layer = self._scan_layer(normalize_text(decoded), "base64:")
            if layer:
                findings.extend(layer)
                findings.append(Finding("encoded_payload", "obfuscation", 0.20, "instructions hidden in base64"))

        survive = 1.0
        for f in findings:
            survive *= 1.0 - f.weight
        score = 1.0 - survive

        if findings and any(p in self._untrusted for p in provenance):
            score = min(1.0, score * 1.25 + 0.05)
        return round(score, 4), findings


def _flatten(obj: Any, depth: int = 0) -> str:
    """Flatten nested tool arguments to text so payloads hidden in args are scanned."""
    if depth > 6:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return " ".join(f"{k} {_flatten(v, depth + 1)}" for k, v in obj.items())
    if isinstance(obj, (list, tuple)):
        return " ".join(_flatten(v, depth + 1) for v in obj)
    return str(obj)


# --------------------------------------------------------------------------------------
# RBAC / taint policy engine
# --------------------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "version": 1,
    # Content from these provenance labels is treated as attacker-controllable.
    "untrusted_sources": ["untrusted_web", "email", "retrieved_document", "tool_output", "user_upload"],
    "roles": {
        "planner": {
            "allowed_tools": ["delegate_task", "plan", "summarize"],
            "can_message": ["planner", "researcher", "db_agent"],
        },
        "researcher": {
            "allowed_tools": ["web_search", "fetch_url", "summarize", "delegate_task"],
            "can_message": ["planner", "researcher", "db_agent"],
        },
        "db_agent": {
            "allowed_tools": ["sql_select", "sql_insert", "summarize"],
            "denied_tools": ["sql_drop", "sql_delete", "sql_truncate", "sql_execute", "shell_exec"],
        },
        "admin": {"allowed_tools": ["*"]},
    },
    "tools": {
        # block_untrusted_provenance: refuse when the triggering content is tainted (confused-deputy defence)
        "sql_drop": {"risk": "critical", "block_untrusted_provenance": True},
        "sql_truncate": {"risk": "critical", "block_untrusted_provenance": True},
        "sql_delete": {"risk": "high", "block_untrusted_provenance": True},
        "sql_execute": {"risk": "high", "block_untrusted_provenance": True},
        "shell_exec": {"risk": "critical", "block_untrusted_provenance": True},
        "send_email": {"risk": "high", "block_untrusted_provenance": True},
    },
}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str = ""
    violation_type: str = ""  # "rbac" | "taint"


class PolicyEngine:
    """Default-deny RBAC over tools plus taint-aware rules for high-risk tools."""

    def __init__(self, policy: dict[str, Any]) -> None:
        self._roles: dict[str, dict[str, Any]] = policy.get("roles", {})
        self._tools: dict[str, dict[str, Any]] = policy.get("tools", {})
        self.untrusted_sources: frozenset[str] = frozenset(policy.get("untrusted_sources", []))
        self.version = policy.get("version", 0)

    @classmethod
    def load(cls, path: Optional[str]) -> "PolicyEngine":
        """Load a YAML/JSON policy; fall back to the built-in default on any problem."""
        if not path:
            return cls(DEFAULT_POLICY)
        try:
            raw = Path(path).read_text(encoding="utf-8")
            data = json.loads(raw) if path.lower().endswith(".json") else yaml.safe_load(raw)
            if not isinstance(data, dict) or "roles" not in data:
                raise ValueError("policy must be a mapping with a 'roles' key")
            logger.info("Loaded policy from %s", path)
            return cls(data)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            logger.error("Could not load policy %s (%s); using built-in default", path, exc)
            return cls(DEFAULT_POLICY)

    def is_untrusted(self, provenance: list[str]) -> bool:
        return any(p in self.untrusted_sources for p in provenance)

    @staticmethod
    def _matches(patterns: list[str], value: str) -> bool:
        return any(fnmatch.fnmatchcase(value, p) for p in patterns)

    def check_tool(self, *, role: str, tool: str, provenance: list[str]) -> PolicyDecision:
        cfg = self._roles.get(role)
        if cfg is None:
            return PolicyDecision(False, f"unknown role '{role}' (default deny)", "rbac")
        if self._matches(cfg.get("denied_tools", []), tool):
            return PolicyDecision(False, f"role '{role}' is explicitly denied tool '{tool}'", "rbac")
        if not self._matches(cfg.get("allowed_tools", []), tool):
            return PolicyDecision(False, f"role '{role}' is not permitted to run tool '{tool}'", "rbac")
        tool_cfg = self._tools.get(tool, {})
        if tool_cfg.get("block_untrusted_provenance") and self.is_untrusted(provenance):
            return PolicyDecision(
                False,
                f"tool '{tool}' ({tool_cfg.get('risk', 'high')} risk) cannot be triggered by untrusted content "
                f"[{', '.join(provenance)}]",
                "taint",
            )
        return PolicyDecision(True)

    def check_messaging(self, sender_role: str, receiver_role: Optional[str]) -> PolicyDecision:
        """Only enforced when the sender's role declares a ``can_message`` list."""
        cfg = self._roles.get(sender_role, {})
        allowed = cfg.get("can_message")
        if allowed is None or receiver_role is None:
            return PolicyDecision(True)
        if self._matches(allowed, receiver_role):
            return PolicyDecision(True)
        return PolicyDecision(False, f"role '{sender_role}' may not message role '{receiver_role}'", "rbac")


# --------------------------------------------------------------------------------------
# Circuit breaker
# --------------------------------------------------------------------------------------


def _shingles(text: str) -> frozenset[int]:
    """Hashed word 3-grams: a cheap, dependency-free stand-in for semantic fingerprints."""
    words = normalize_text(text[:20_000]).split()
    if not words:
        return frozenset()
    grams = [" ".join(words[i : i + 3]) for i in range(len(words) - 2)] if len(words) >= 3 else [" ".join(words)]
    return frozenset(zlib.crc32(g.encode("utf-8")) for g in grams)


def _jaccard(a: frozenset[int], b: frozenset[int]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class _Entry:
    ts: float
    sender: str
    receiver: str
    sig: frozenset[int]


@dataclass
class ConversationState:
    entries: Deque[_Entry] = field(default_factory=lambda: deque(maxlen=64))
    transfers: int = 0
    est_tokens: int = 0
    tripped_at: Optional[float] = None
    trip_reason: str = ""
    last_seen: float = field(default_factory=time.monotonic)


class CircuitBreaker:
    """Stateful per-conversation infinite-loop / runaway-cost detector.

    Trips on any of: recursion depth, message velocity, semantic repetition
    (near-duplicate payloads), A->B->A->B ping-pong, or estimated token budget.
    """

    _IDLE_EVICT_S = 900.0

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._convs: dict[str, ConversationState] = {}

    def is_tripped(self, conversation_id: str) -> Optional[tuple[str, int]]:
        """Return (reason, retry_after_seconds) while the cooldown is active."""
        st = self._convs.get(conversation_id)
        if st is None or st.tripped_at is None:
            return None
        remaining = self._s.breaker_cooldown_s - (time.monotonic() - st.tripped_at)
        if remaining > 0:
            return st.trip_reason, max(1, int(remaining))
        del self._convs[conversation_id]  # cooldown over: fresh slate
        return None

    def reset(self, conversation_id: str) -> bool:
        return self._convs.pop(conversation_id, None) is not None

    def _evict_idle(self, now: float) -> None:
        stale = [k for k, v in self._convs.items() if now - v.last_seen > self._IDLE_EVICT_S]
        for key in stale:
            del self._convs[key]

    def observe(self, conversation_id: str, sender: str, receiver: str, message: str, hop_count: int) -> Optional[str]:
        """Record a transfer. Returns a trip reason, or None if the conversation is healthy."""
        s = self._s
        now = time.monotonic()
        if len(self._convs) > 1024:
            self._evict_idle(now)

        st = self._convs.setdefault(conversation_id, ConversationState())
        st.last_seen = now
        st.transfers += 1
        st.est_tokens += max(1, len(message) // 4)
        current = _Entry(now, sender, receiver, _shingles(message))
        history = list(st.entries)  # excludes the current entry
        st.entries.append(current)

        reason: Optional[str] = None

        # 1) recursion depth
        depth = hop_count if hop_count > 0 else st.transfers
        if depth > s.max_depth:
            reason = f"recursion depth {depth} exceeds limit {s.max_depth}"

        # 2) velocity
        if reason is None:
            in_window = sum(1 for e in st.entries if now - e.ts <= s.velocity_window_s)
            if in_window > s.velocity_max:
                reason = f"message velocity {in_window}/{s.velocity_window_s:.0f}s exceeds {s.velocity_max}"

        # 3) semantic repetition (near-duplicate payloads on the same edge)
        if reason is None:
            dupes = sum(
                1
                for e in history[-16:]
                if e.sender == sender and e.receiver == receiver and _jaccard(e.sig, current.sig) >= s.repeat_similarity
            )
            if dupes >= s.repeat_count:
                reason = f"semantic repetition: {dupes + 1} near-identical messages {sender} -> {receiver}"

        # 4) ping-pong delegation loop: A->B, B->A, A->B ... with similar content
        if reason is None and s.pingpong_cycles > 0:
            window = list(st.entries)[-2 * s.pingpong_cycles :]
            if len(window) == 2 * s.pingpong_cycles:
                a, b = window[0].sender, window[0].receiver
                alternating = a != b and all(
                    (e.sender, e.receiver) == ((a, b) if i % 2 == 0 else (b, a)) for i, e in enumerate(window)
                )
                if alternating and min(
                    _jaccard(window[i].sig, window[i + 2].sig) for i in range(len(window) - 2)
                ) >= s.pingpong_similarity:
                    reason = f"recursive delegation loop between {a} and {b} ({s.pingpong_cycles} cycles)"

        # 5) token budget
        if reason is None and st.est_tokens > s.token_budget:
            reason = f"estimated token usage {st.est_tokens} exceeds budget {s.token_budget}"

        if reason:
            st.tripped_at = now
            st.trip_reason = reason
        return reason

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "conversation_id": cid,
                "transfers": st.transfers,
                "est_tokens": st.est_tokens,
                "tripped": st.tripped_at is not None,
                "trip_reason": st.trip_reason or None,
            }
            for cid, st in self._convs.items()
        ]


# --------------------------------------------------------------------------------------
# Agent registry + telemetry hub
# --------------------------------------------------------------------------------------


@dataclass
class AgentRecord:
    agent_id: str
    role: str
    status: AgentStatus = AgentStatus.NORMAL
    violations: int = 0
    inspected_at: float = 0.0
    quarantine_reason: str = ""


class AgentRegistry:
    """Tracks the live status shown as green / yellow / red badges on the dashboard."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._agents: dict[str, AgentRecord] = {}

    def touch(self, agent_id: str, role: str) -> AgentRecord:
        rec = self._agents.get(agent_id)
        if rec is None:
            rec = self._agents[agent_id] = AgentRecord(agent_id, role)
        elif role != "unknown":
            rec.role = role
        return rec

    def effective(self, agent_id: str) -> AgentStatus:
        rec = self._agents.get(agent_id)
        if rec is None:
            return AgentStatus.NORMAL
        if rec.status is AgentStatus.INSPECTED and time.monotonic() - rec.inspected_at > self._s.inspect_ttl_s:
            rec.status = AgentStatus.NORMAL  # inspection badge decays back to green
        return rec.status

    def mark_inspected(self, agent_id: str) -> None:
        rec = self._agents.get(agent_id)
        if rec and rec.status is AgentStatus.NORMAL:
            rec.status = AgentStatus.INSPECTED
        if rec:
            rec.inspected_at = time.monotonic()

    def record_violation(self, agent_id: str, *, severe: bool, reason: str) -> AgentStatus:
        rec = self._agents.get(agent_id)
        if rec is None:
            return AgentStatus.NORMAL
        rec.violations += 1
        if severe or rec.violations >= self._s.quarantine_after:
            rec.status = AgentStatus.QUARANTINED
            rec.quarantine_reason = reason
        return rec.status

    def release(self, agent_id: str) -> bool:
        rec = self._agents.get(agent_id)
        if rec is None:
            return False
        rec.status, rec.violations, rec.quarantine_reason = AgentStatus.NORMAL, 0, ""
        return True

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "agent_id": r.agent_id,
                "role": r.role,
                "status": self.effective(r.agent_id).value,
                "violations": r.violations,
                "quarantine_reason": r.quarantine_reason or None,
            }
            for r in self._agents.values()
        ]


class TelemetryHub:
    """Fan-out of gateway decisions to WebSocket subscribers (the React dashboard)."""

    def __init__(self, history: int = 200) -> None:
        self._clients: set[WebSocket] = set()
        self.history: Deque[dict[str, Any]] = deque(maxlen=history)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def publish(self, event: dict[str, Any]) -> None:
        self.history.append(event)
        if not self._clients:
            return
        clients = list(self._clients)
        results = await asyncio.gather(
            *(asyncio.wait_for(c.send_json(event), timeout=2.0) for c in clients), return_exceptions=True
        )
        for client, result in zip(clients, results):
            if isinstance(result, Exception):  # dead or too slow: drop it
                self._clients.discard(client)


# --------------------------------------------------------------------------------------
# Gateway core
# --------------------------------------------------------------------------------------


@dataclass
class Evaluation:
    verdict: Verdict
    risk_score: float
    reason: str
    violation_type: Optional[str]
    findings: list[Finding]
    retry_after: Optional[int] = None


class GatewayState:
    """Wires every component together and owns the decision pipeline."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.policy = PolicyEngine.load(settings.policy_path)
        self.detector = InjectionDetector(self.policy.untrusted_sources)
        self.breaker = CircuitBreaker(settings)
        self.registry = AgentRegistry(settings)
        self.hub = TelemetryHub()
        self.counters: dict[str, int] = {v.value: 0 for v in Verdict}

    def reload_policy(self) -> None:
        self.policy = PolicyEngine.load(self.settings.policy_path)
        self.detector = InjectionDetector(self.policy.untrusted_sources)

    def evaluate(self, req: TransferRequest) -> Evaluation:
        s = self.settings
        self.registry.touch(req.sender_id, req.sender_role)
        self.registry.touch(req.receiver_id, req.receiver_role or "unknown")

        # 1) quarantined senders are cut off immediately
        if self.registry.effective(req.sender_id) is AgentStatus.QUARANTINED:
            return Evaluation(Verdict.BLOCK, 1.0, f"sender '{req.sender_id}' is quarantined", "quarantined_sender", [])

        # 2) conversation already tripped and still cooling down
        tripped = self.breaker.is_tripped(req.conversation_id)
        if tripped:
            reason, retry = tripped
            return Evaluation(Verdict.TRIP, 0.0, reason, "circuit_breaker", [], retry)

        # 3) indirect prompt injection scan (message body + tool arguments)
        text = req.message if not req.tool_args else f"{req.message} {_flatten(req.tool_args)}"
        score, findings = self.detector.scan(text, req.provenance)

        # 4) RBAC + taint policy
        policy_denial: Optional[PolicyDecision] = self.policy.check_messaging(req.sender_role, req.receiver_role)
        if policy_denial.allowed and req.target_tool:
            executor_role = req.receiver_role or req.sender_role  # the role that will run the tool
            policy_denial = self.policy.check_tool(role=executor_role, tool=req.target_tool, provenance=req.provenance)
        if not policy_denial.allowed:
            findings.append(Finding(policy_denial.violation_type, "policy", 1.0, policy_denial.reason))
            risk = max(score, 0.8)
            self.registry.record_violation(req.sender_id, severe=risk >= 0.9, reason=policy_denial.reason)
            return Evaluation(Verdict.BLOCK, risk, policy_denial.reason, policy_denial.violation_type, findings)

        # 5) injection threshold
        if score >= s.block_threshold:
            rules = ", ".join(f.rule for f in findings)
            reason = f"indirect prompt injection detected ({rules})"
            self.registry.record_violation(req.sender_id, severe=score >= 0.9, reason=reason)
            return Evaluation(Verdict.BLOCK, score, reason, "prompt_injection", findings)

        # 6) circuit breaker (only for messages that passed security checks)
        trip_reason = self.breaker.observe(
            req.conversation_id, req.sender_id, req.receiver_id, req.message, req.hop_count
        )
        if trip_reason:
            self.registry.mark_inspected(req.sender_id)
            return Evaluation(Verdict.TRIP, score, trip_reason, "circuit_breaker", findings, s.breaker_cooldown_s)

        # 7) suspicious but not conclusive -> human review
        if score >= s.flag_threshold:
            self.registry.mark_inspected(req.sender_id)
            return Evaluation(Verdict.FLAG, score, "suspicious content flagged for review", "prompt_injection", findings)

        return Evaluation(Verdict.ALLOW, score, "clean", None, findings)


# --------------------------------------------------------------------------------------
# FastAPI app
# --------------------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = Settings.from_env()
    if not settings.api_key:
        logger.warning("SWARMSHIELD_API_KEY is not set: gateway is running WITHOUT authentication")
    app.state.gw = GatewayState(settings)
    yield


app = FastAPI(
    title="SwarmShield Gateway",
    version="0.1.0",
    description="Security proxy for agent-to-agent communication",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(Settings.from_env().cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


async def require_api_key(request: Request, x_swarmshield_key: Optional[str] = Header(default=None)) -> None:
    expected = request.app.state.gw.settings.api_key
    if expected and not (x_swarmshield_key and hmac.compare_digest(x_swarmshield_key, expected)):
        raise HTTPException(status_code=401, detail="invalid or missing X-SwarmShield-Key")


_STATUS_FOR_VERDICT = {Verdict.ALLOW: 200, Verdict.FLAG: 200, Verdict.BLOCK: 403, Verdict.TRIP: 429}


@app.post(
    "/a2a/transfer",
    response_model=TransferResponse,
    responses={403: {"model": TransferResponse}, 429: {"model": TransferResponse}},
    summary="Inspect one agent-to-agent transfer",
)
async def a2a_transfer(req: TransferRequest, request: Request, _auth: None = Depends(require_api_key)) -> JSONResponse:
    gw: GatewayState = request.app.state.gw
    started = time.perf_counter()

    result = gw.evaluate(req)  # synchronous -> atomic on the event loop
    gw.counters[result.verdict.value] += 1

    message_id = f"msg-{uuid.uuid4().hex[:12]}"
    sender_status = gw.registry.effective(req.sender_id)
    body = TransferResponse(
        message_id=message_id,
        verdict=result.verdict,
        risk_score=result.risk_score,
        violation_type=result.violation_type if result.verdict is not Verdict.ALLOW else None,
        reason=result.reason,
        findings=[f.as_dict() for f in result.findings],
        sender_status=sender_status,
        requires_human_review=result.verdict is Verdict.FLAG,
        retry_after=result.retry_after,
        latency_ms=round((time.perf_counter() - started) * 1000, 3),
    )

    await gw.hub.publish(
        {
            "type": "a2a_transfer",
            "event_id": message_id,
            "ts": time.time(),
            "conversation_id": req.conversation_id,
            "sender_id": req.sender_id,
            "sender_role": req.sender_role,
            "receiver_id": req.receiver_id,
            "receiver_role": req.receiver_role,
            "target_tool": req.target_tool,
            "verdict": result.verdict.value,
            "risk_score": result.risk_score,
            "violation_type": body.violation_type,
            "reason": result.reason,
            "rules": [f.rule for f in result.findings],
            "sender_status": sender_status.value,
            "receiver_status": gw.registry.effective(req.receiver_id).value,
            "preview": re.sub(r"\s+", " ", req.message)[:140],
        }
    )

    headers = {"Retry-After": str(result.retry_after)} if result.verdict is Verdict.TRIP and result.retry_after else None
    return JSONResponse(status_code=_STATUS_FOR_VERDICT[result.verdict], content=body.model_dump(mode="json"), headers=headers)


@app.get("/health")
async def health(request: Request) -> dict[str, Any]:
    gw: GatewayState = request.app.state.gw
    return {"status": "ok", "policy_version": gw.policy.version, "counters": gw.counters}


@app.get("/v1/agents", dependencies=[Depends(require_api_key)])
async def list_agents(request: Request) -> dict[str, Any]:
    gw: GatewayState = request.app.state.gw
    return {"agents": gw.registry.snapshot(), "conversations": gw.breaker.snapshot()}


@app.post("/v1/agents/{agent_id}/release", dependencies=[Depends(require_api_key)])
async def release_agent(agent_id: str, request: Request) -> dict[str, Any]:
    """Human operator lifts a quarantine."""
    gw: GatewayState = request.app.state.gw
    if not gw.registry.release(agent_id):
        raise HTTPException(status_code=404, detail=f"unknown agent '{agent_id}'")
    await gw.hub.publish({"type": "agent_released", "ts": time.time(), "agent_id": agent_id, "status": "normal"})
    return {"agent_id": agent_id, "status": "normal"}


@app.post("/v1/circuit/{conversation_id}/reset", dependencies=[Depends(require_api_key)])
async def reset_circuit(conversation_id: str, request: Request) -> dict[str, Any]:
    gw: GatewayState = request.app.state.gw
    return {"conversation_id": conversation_id, "reset": gw.breaker.reset(conversation_id)}


@app.post("/v1/policy/reload", dependencies=[Depends(require_api_key)])
async def reload_policy(request: Request) -> dict[str, Any]:
    gw: GatewayState = request.app.state.gw
    gw.reload_policy()
    return {"policy_version": gw.policy.version, "roles": sorted(gw.policy._roles)}  # noqa: SLF001


@app.websocket("/ws/telemetry")
async def ws_telemetry(ws: WebSocket, token: Optional[str] = Query(default=None)) -> None:
    """Live decision stream. If an API key is configured pass it as ``?token=...``."""
    gw: GatewayState = ws.app.state.gw
    expected = gw.settings.api_key
    if expected and not (token and hmac.compare_digest(token, expected)):
        await ws.close(code=4401)
        return

    await gw.hub.connect(ws)
    try:
        await ws.send_json({"type": "snapshot", "agents": gw.registry.snapshot(), "recent": list(gw.hub.history)[-50:]})
        while True:
            await ws.receive_text()  # keep-alive; client pings are ignored
    except WebSocketDisconnect:
        pass
    finally:
        gw.hub.disconnect(ws)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("swarmshield.gateway:app", host="0.0.0.0", port=8000, reload=False)
