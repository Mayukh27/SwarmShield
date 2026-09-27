"""SwarmShield security gate for LangGraph ``StateGraph`` workflows (``langgraph>=1.0``).

Topology added by :func:`add_swarmshield_gate`::

    START -> swarmshield_gatekeeper --allow--------------------------> <protected node>
                    |  \\--flag / overridable block--> swarmshield_review --approve--> <protected node>
                    |                                        \\--reject--> swarmshield_quarantine -> END
                    \\--RBAC / taint / circuit breaker--------------------> swarmshield_quarantine -> END

Why two nodes (gatekeeper + review)? ``interrupt()`` re-runs the *whole* node from the top when
the graph resumes. Keeping the gateway call in its own node means resuming after a human decision
never re-sends the payload (which would double-count it in the circuit breaker). The review node
contains no side effects before ``interrupt()``.

Human review is offered for FLAG verdicts (the gateway sets ``requires_human_review``) and when the
gateway is unreachable. A gateway 403 is final unless the developer opts in with
``overridable_violations={"prompt_injection"}``; a 429 circuit-breaker trip is never overridable.

A checkpointer is mandatory for ``interrupt()``::

    graph = builder.compile(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}}
    out = graph.invoke(state, cfg)                    # pauses; out["__interrupt__"] holds the request
    graph.invoke(Command(resume={"decision": "reject", "reviewer": "alice"}), cfg)
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Optional

try:  # optional dependency: importing swarmshield or the gateway never needs LangGraph
    from langchain_core.messages import AIMessage, AnyMessage, RemoveMessage
    from langgraph.graph import END, START, MessagesState, StateGraph
    from langgraph.types import Command, interrupt
except ImportError as exc:  # pragma: no cover - exercised in tests via a blocked import
    raise ImportError(
        "swarmshield.integrations.langgraph requires LangGraph >= 1.0. "
        'Install it with: pip install "swarmshield[langgraph]"'
    ) from exc

from swarmshield.exceptions import (
    SwarmShieldCircuitBreakerException,
    SwarmShieldError,
    SwarmShieldSecurityException,
    SwarmShieldUnavailableError,
)
from swarmshield.integrations._client import GatewayClient, GatewayVerdict

logger = logging.getLogger("swarmshield.langgraph")

GATEKEEPER_NODE = "swarmshield_gatekeeper"
REVIEW_NODE = "swarmshield_review"
QUARANTINE_NODE = "swarmshield_quarantine"

# Gateway 403s are final by default. Pass e.g. frozenset({"prompt_injection"}) to let a human override
# a blocked injection. HITL is otherwise reserved for FLAG verdicts (gateway sets requires_human_review)
# and for a gateway outage.
DEFAULT_OVERRIDABLE: frozenset[str] = frozenset()


class SwarmState(MessagesState, total=False):
    """Graph state expected by the gate. Everything except ``messages`` is optional."""

    sender_id: str
    sender_role: str
    receiver_id: str
    receiver_role: str
    target_tool: str
    tool_args: dict[str, Any]
    provenance: list[str]  # e.g. ["untrusted_web"]
    conversation_id: str
    hop_count: int
    shield: dict[str, Any]  # audit trail written by the gate


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b if isinstance(b, str) else str(b.get("text", "")) for b in content if isinstance(b, (str, dict)))
    return str(content)


def _thread_id() -> Optional[str]:
    """``configurable.thread_id`` of the current run, if we are inside one."""
    try:
        from langgraph.config import get_config

        thread = (get_config().get("configurable") or {}).get("thread_id")
        return str(thread) if thread else None
    except Exception:  # noqa: BLE001 - outside a runnable context
        return None


def _payload_from_state(state: SwarmState) -> dict[str, Any]:
    messages: list[AnyMessage] = state.get("messages", [])
    last = messages[-1] if messages else None
    return dict(
        message=_text(last.content) if last is not None else "",
        sender_id=state.get("sender_id", "unknown_sender"),
        sender_role=state.get("sender_role", "unknown"),
        receiver_id=state.get("receiver_id", "unknown_receiver"),
        receiver_role=state.get("receiver_role"),
        target_tool=state.get("target_tool"),
        tool_args=state.get("tool_args") or {},
        # Stable id across passes through the gate: without it a graph cycle (A -> gate -> B -> gate -> A)
        # would get a fresh conversation each time and the loop breaker could never see the loop.
        conversation_id=state.get("conversation_id") or _thread_id(),
        hop_count=int(state.get("hop_count", 0)),
        provenance=state.get("provenance") or [],
    )


def _route(
    *,
    protected_node: str,
    overridable: frozenset[str],
    verdict: Optional[GatewayVerdict],
    error: Optional[SwarmShieldError],
    hop: int = 0,
) -> Command:
    """Turn a gateway outcome into a ``Command`` (routing decision + audit state update).

    ``hop_count`` is incremented on every pass so the gateway can also enforce recursion depth in cyclic graphs.
    """
    if error is None and verdict is not None:
        shield = {
            "status": "flagged" if verdict.requires_human_review else "allowed",
            "verdict": verdict.verdict,
            "risk_score": verdict.risk_score,
            "reason": verdict.reason,
            "findings": list(verdict.findings),
            "violation_type": verdict.violation_type if verdict.requires_human_review else None,
            "message_id": verdict.message_id,
            "degraded": verdict.degraded,
        }
        goto = REVIEW_NODE if verdict.requires_human_review else protected_node
        return Command(goto=goto, update={"shield": shield, "hop_count": hop + 1})

    assert error is not None
    violation = error.violation_type
    shield = {
        "status": "blocked",
        "verdict": "trip" if isinstance(error, SwarmShieldCircuitBreakerException) else "block",
        "risk_score": error.risk_score,
        "reason": str(error),
        "findings": error.findings,
        "violation_type": violation,
    }
    if isinstance(error, SwarmShieldUnavailableError):
        # Gateway offline: fail closed by asking a human instead of silently dropping the work.
        shield.update(status="gateway_unavailable", violation_type="prompt_injection")
        return Command(goto=REVIEW_NODE, update={"shield": shield, "hop_count": hop + 1})
    if isinstance(error, SwarmShieldSecurityException) and violation in overridable:
        return Command(goto=REVIEW_NODE, update={"shield": shield, "hop_count": hop + 1})
    return Command(goto=QUARANTINE_NODE, update={"shield": shield, "hop_count": hop + 1})  # hard stop


def make_gatekeeper(
    *,
    protected_node: str = "agent",
    client: Optional[GatewayClient] = None,
    overridable_violations: frozenset[str] = DEFAULT_OVERRIDABLE,
    sync: bool = False,
) -> Any:
    """Build the gatekeeper node. ``protected_node`` is where clean traffic continues.

    By default the node works with both ``graph.invoke`` and ``graph.ainvoke``. ``sync=True`` builds a
    plain synchronous function instead (for callers that want a bare callable).
    """
    gateway = client or GatewayClient()

    def _decide(state: SwarmState, verdict: Optional[GatewayVerdict], error: Optional[SwarmShieldError]) -> Command:
        return _route(
            protected_node=protected_node, overridable=overridable_violations,
            verdict=verdict, error=error, hop=int(state.get("hop_count", 0)),
        )

    def gatekeeper(state: SwarmState) -> Command:
        try:
            return _decide(state, gateway.transfer(**_payload_from_state(state)), None)
        except SwarmShieldError as exc:
            return _decide(state, None, exc)

    if sync:
        return gatekeeper

    async def agatekeeper(state: SwarmState) -> Command:
        try:
            return _decide(state, await gateway.atransfer(**_payload_from_state(state)), None)
        except SwarmShieldError as exc:
            return _decide(state, None, exc)

    from langchain_core.runnables import RunnableLambda

    return RunnableLambda(gatekeeper, afunc=agatekeeper, name=GATEKEEPER_NODE)


def _parse_decision(resume: Any) -> tuple[bool, str, str]:
    """Accept ``{"decision": "approve", "reviewer": ..., "note": ...}``, a bool, or a string."""
    if isinstance(resume, dict):
        decision = str(resume.get("decision", "reject")).lower()
        return decision in {"approve", "approved", "allow", "yes"}, str(resume.get("reviewer", "unknown")), str(resume.get("note", ""))
    if isinstance(resume, bool):
        return resume, "unknown", ""
    return str(resume).strip().lower() in {"approve", "approved", "allow", "yes", "y"}, "unknown", ""


def make_review_node(protected_node: str = "agent") -> Callable[[SwarmState], Command]:
    """Human-in-the-loop step: pauses the graph and waits for an approve/reject decision."""

    def swarmshield_review(state: SwarmState) -> Command:
        shield: dict[str, Any] = dict(state.get("shield", {}))
        messages: list[AnyMessage] = state.get("messages", [])
        preview = _text(messages[-1].content)[:500] if messages else ""

        # Nothing with side effects may run before this line: the node restarts on resume.
        resume = interrupt(
            {
                "type": "swarmshield_approval_request",
                "reason": shield.get("reason"),
                "risk_score": shield.get("risk_score"),
                "violation_type": shield.get("violation_type"),
                "findings": shield.get("findings", []),
                "sender": {"id": state.get("sender_id"), "role": state.get("sender_role")},
                "receiver": {"id": state.get("receiver_id"), "role": state.get("receiver_role")},
                "target_tool": state.get("target_tool"),
                "provenance": state.get("provenance", []),
                "message_preview": preview,
                "options": ["approve", "reject"],
            }
        )

        approved, reviewer, note = _parse_decision(resume)
        shield.update(status="approved_by_human" if approved else "rejected_by_human", reviewer=reviewer, note=note)
        logger.info("SwarmShield review by %s: %s", reviewer, shield["status"])
        return Command(goto=protected_node if approved else QUARANTINE_NODE, update={"shield": shield})

    return swarmshield_review


def swarmshield_quarantine(state: SwarmState) -> dict[str, Any]:
    """Terminal node: scrub the tainted message from state and leave an audit message."""
    shield = dict(state.get("shield", {}))
    messages: list[AnyMessage] = state.get("messages", [])
    updates: list[Any] = []
    if messages and getattr(messages[-1], "id", None):
        updates.append(RemoveMessage(id=messages[-1].id))  # tainted payload must not stay in context
    updates.append(AIMessage(content=f"[SwarmShield] Quarantined: {shield.get('reason', 'policy violation')}"))
    shield["status"] = "quarantined"
    return {"messages": updates, "shield": shield}


def add_swarmshield_gate(
    builder: StateGraph,
    *,
    protected_node: str,
    client: Optional[GatewayClient] = None,
    overridable_violations: frozenset[str] = DEFAULT_OVERRIDABLE,
    sync: bool = False,
    connect_start: bool = True,
) -> None:
    """Register gatekeeper, review and quarantine nodes on ``builder``.

    With ``connect_start=True`` (default) the gate becomes the graph entry point, so every
    input is inspected before ``protected_node`` runs. Set it to ``False`` to wire the
    gate yourself (e.g. between two agents inside a swarm).
    """
    builder.add_node(
        GATEKEEPER_NODE,
        make_gatekeeper(
            protected_node=protected_node, client=client, overridable_violations=overridable_violations, sync=sync
        ),
        destinations=(protected_node, REVIEW_NODE, QUARANTINE_NODE),
    )
    builder.add_node(REVIEW_NODE, make_review_node(protected_node), destinations=(protected_node, QUARANTINE_NODE))
    builder.add_node(QUARANTINE_NODE, swarmshield_quarantine)
    builder.add_edge(QUARANTINE_NODE, END)
    if connect_start:
        builder.add_edge(START, GATEKEEPER_NODE)


# Ready-made node for the common case (protected node named "agent").
swarmshield_gatekeeper = make_gatekeeper(protected_node="agent")


def build_demo_graph(protected_node_fn: Optional[Callable[[SwarmState], dict[str, Any]]] = None) -> Any:
    """Compile a minimal gated graph with an in-memory checkpointer (needed for interrupt())."""
    from langgraph.checkpoint.memory import MemorySaver

    def default_agent(state: SwarmState) -> dict[str, Any]:
        return {"messages": [AIMessage(content=f"[{state.get('receiver_id', 'agent')}] executed task")]}

    builder = StateGraph(SwarmState)
    builder.add_node("agent", protected_node_fn or default_agent)
    builder.add_edge("agent", END)
    add_swarmshield_gate(builder, protected_node="agent")
    return builder.compile(checkpointer=MemorySaver())
