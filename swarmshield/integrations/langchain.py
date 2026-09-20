"""SwarmShield middleware for LangChain agents (``langchain>=1.0``).

Hooks used
    ``before_agent``      inspects the inbound message before the LLM ever sees it
    ``wrap_tool_call``    inspects the proposed tool call (RBAC + taint) *and* the tool's
                          output, which is where indirect prompt injection usually enters
    (LangChain names the "around tool" hook ``wrap_tool_call`` / ``awrap_tool_call``.)

Usage::

    from langchain.agents import create_agent
    from swarmshield.integrations.langchain import SwarmShieldMiddleware

    shield = SwarmShieldMiddleware(agent_id="researcher-1", role="researcher")
    agent = create_agent("openai:gpt-4o", tools=[web_search, sql_select], middleware=[shield])

To forward provenance from another agent, attach an envelope to the message::

    HumanMessage(content=text, additional_kwargs={"swarmshield": {
        "sender_id": "planner-1", "sender_role": "planner",
        "provenance": ["untrusted_web"], "conversation_id": "task-42", "hop_count": 3}})

Fail-closed by default: if the gateway is unreachable, the request/tool call is blocked.
Pass ``fail_mode="open"`` to let traffic through (uninspected) during an outage.

Note: this file is named ``langchain.py`` inside the ``swarmshield.integrations`` package;
that is safe because imports are absolute, but never run scripts from inside this folder.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Sequence

try:  # optional dependency: importing swarmshield or the gateway never needs LangChain
    from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
    from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
    from langgraph.types import Command
except ImportError as exc:  # pragma: no cover - exercised in tests via a blocked import
    raise ImportError(
        "swarmshield.integrations.langchain requires LangChain >= 1.0. "
        'Install it with: pip install "swarmshield[langchain]"'
    ) from exc

from swarmshield.exceptions import SwarmShieldError
from swarmshield.integrations._client import FailMode, GatewayClient

if TYPE_CHECKING:  # import location differs slightly between langchain 1.x releases
    from langchain.agents.middleware.types import ToolCallRequest
    from langgraph.runtime import Runtime

logger = logging.getLogger("swarmshield.langchain")

# Tools whose *output* is attacker-controllable and must be scanned before the LLM reads it.
DEFAULT_UNTRUSTED_OUTPUT_TOOLS: tuple[str, ...] = (
    "web_search", "fetch_url", "browse", "read_email", "read_document", "retriever", "scrape",
)


def _text(content: Any) -> str:
    """Flatten LangChain message content (str or list of content blocks) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b if isinstance(b, str) else str(b.get("text", "")) for b in content if isinstance(b, (str, dict))]
        return "\n".join(p for p in parts if p)
    return str(content)


def _thread_id() -> Optional[str]:
    """LangGraph ``configurable.thread_id`` of the current run, if we are inside one."""
    try:
        from langgraph.config import get_config

        thread = (get_config().get("configurable") or {}).get("thread_id")
        return str(thread) if thread else None
    except Exception:  # noqa: BLE001 - outside a runnable context / older langgraph
        return None


class SwarmShieldMiddleware(AgentMiddleware):
    """Routes every inbound message, tool call and tool result through the SwarmShield gateway."""

    def __init__(
        self,
        *,
        agent_id: str,
        role: str,
        client: Optional[GatewayClient] = None,
        gateway_url: Optional[str] = None,
        api_key: Optional[str] = None,
        fail_mode: FailMode = "closed",
        inspect_tool_outputs: bool = True,
        untrusted_output_tools: Sequence[str] = DEFAULT_UNTRUSTED_OUTPUT_TOOLS,
        default_provenance: Sequence[str] = ("user",),
    ) -> None:
        super().__init__()
        self.agent_id = agent_id
        self.role = role
        self._client = client or GatewayClient(gateway_url, api_key, fail_mode=fail_mode)
        self._inspect_outputs = inspect_tool_outputs
        self._untrusted_tools = frozenset(untrusted_output_tools)
        self._default_provenance = tuple(default_provenance)

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _envelope(msg: AnyMessage) -> dict[str, Any]:
        env = getattr(msg, "additional_kwargs", {}).get("swarmshield", {})
        return env if isinstance(env, dict) else {}

    @staticmethod
    def _latest_human(state: AgentState) -> Optional[AnyMessage]:
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage):
                return msg
        return None

    def _conversation_id(self, state: AgentState) -> str:
        """Conversation id the gateway's circuit breaker groups by.

        Priority: explicit envelope id > LangGraph ``thread_id`` (a real multi-turn conversation) >
        id of the latest human message (unique per agent run, so separate runs of the same prompt are
        never mistaken for a loop) > hash of the first message.
        """
        messages = state.get("messages", [])
        for msg in reversed(messages):
            cid = self._envelope(msg).get("conversation_id")
            if cid:
                return str(cid)
        thread_id = _thread_id()
        if thread_id:
            return f"lc-{thread_id}"
        human = self._latest_human(state)
        if human is not None and getattr(human, "id", None):
            return f"lc-run-{human.id}"
        seed = f"{self.agent_id}:{_text(messages[0].content) if messages else ''}"
        return "lc-" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]

    def _provenance(self, state: AgentState, envelope: Optional[dict[str, Any]] = None) -> list[str]:
        """Union of declared provenance and taint from any untrusted tool output already in context."""
        labels = list((envelope or {}).get("provenance") or self._default_provenance)
        for msg in state.get("messages", []):
            if isinstance(msg, ToolMessage) and (msg.name in self._untrusted_tools):
                labels.append("tool_output")
                break
        return sorted(set(labels))

    def _inbound_payload(self, state: AgentState, msg: AnyMessage) -> dict[str, Any]:
        env = self._envelope(msg)
        return dict(
            message=_text(msg.content),
            sender_id=str(env.get("sender_id", "user")),
            sender_role=str(env.get("sender_role", "user")),
            receiver_id=self.agent_id,
            receiver_role=self.role,
            conversation_id=self._conversation_id(state),
            hop_count=int(env.get("hop_count", 0)),
            provenance=self._provenance(state, env),
        )

    def _tool_payload(self, state: AgentState, name: str, args: dict[str, Any]) -> dict[str, Any]:
        return dict(
            message=json.dumps(args, default=str),
            sender_id=self.agent_id,
            sender_role=self.role,
            receiver_id=f"tool:{name}",
            receiver_role=self.role,  # tools run with this agent's privileges
            target_tool=name,
            tool_args=args,
            conversation_id=self._conversation_id(state),
            provenance=self._provenance(state),
        )

    def _output_payload(self, state: AgentState, name: str, result: ToolMessage) -> dict[str, Any]:
        return dict(
            message=_text(result.content),
            sender_id=f"tool:{name}",
            sender_role="tool",
            receiver_id=self.agent_id,
            receiver_role=self.role,
            conversation_id=self._conversation_id(state),
            provenance=["tool_output", "untrusted_web"],
        )

    @staticmethod
    def _halt(exc: SwarmShieldError) -> dict[str, Any]:
        """Stop the agent loop and return a safe message instead of calling the model."""
        logger.warning("SwarmShield halted agent: %s", exc)
        return {"jump_to": "end", "messages": [AIMessage(content=f"[SwarmShield] Request blocked: {exc}")]}

    @staticmethod
    def _blocked_tool_message(call: dict[str, Any], exc: SwarmShieldError, phase: str = "call") -> ToolMessage:
        logger.warning("SwarmShield blocked tool %s (%s): %s", call.get("name"), phase, exc)
        return ToolMessage(
            content=f"[SwarmShield] Tool {phase} blocked: {exc}",
            tool_call_id=call["id"],
            name=call.get("name"),
            status="error",
        )

    # ------------------------------------------------------------------ before_agent

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: "Runtime") -> Optional[dict[str, Any]]:
        msg = self._latest_human(state)
        if msg is None:
            return None
        try:
            self._client.transfer(**self._inbound_payload(state, msg))
        except SwarmShieldError as exc:  # security, circuit breaker, or unavailable (fail closed)
            return self._halt(exc)
        return None

    @hook_config(can_jump_to=["end"])
    async def abefore_agent(self, state: AgentState, runtime: "Runtime") -> Optional[dict[str, Any]]:
        msg = self._latest_human(state)
        if msg is None:
            return None
        try:
            await self._client.atransfer(**self._inbound_payload(state, msg))
        except SwarmShieldError as exc:
            return self._halt(exc)
        return None

    # ------------------------------------------------------------------ wrap_tool_call

    def wrap_tool_call(
        self,
        request: "ToolCallRequest",
        handler: Callable[["ToolCallRequest"], ToolMessage | Command],
    ) -> ToolMessage | Command:
        call = request.tool_call
        name: str = call["name"]
        state = request.state

        # 1) pre-execution: RBAC, taint and injection checks on the proposed call
        try:
            self._client.transfer(**self._tool_payload(state, name, dict(call.get("args") or {})))
        except SwarmShieldError as exc:
            return self._blocked_tool_message(call, exc)

        result = handler(request)

        # 2) post-execution: scan untrusted tool output before the LLM reads it
        if self._inspect_outputs and name in self._untrusted_tools and isinstance(result, ToolMessage):
            try:
                self._client.transfer(**self._output_payload(state, name, result))
            except SwarmShieldError as exc:
                return self._blocked_tool_message(call, exc, phase="output")
        return result

    async def awrap_tool_call(
        self,
        request: "ToolCallRequest",
        handler: Callable[["ToolCallRequest"], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        call = request.tool_call
        name: str = call["name"]
        state = request.state

        try:
            await self._client.atransfer(**self._tool_payload(state, name, dict(call.get("args") or {})))
        except SwarmShieldError as exc:
            return self._blocked_tool_message(call, exc)

        result = await handler(request)

        if self._inspect_outputs and name in self._untrusted_tools and isinstance(result, ToolMessage):
            try:
                await self._client.atransfer(**self._output_payload(state, name, result))
            except SwarmShieldError as exc:
                return self._blocked_tool_message(call, exc, phase="output")
        return result
