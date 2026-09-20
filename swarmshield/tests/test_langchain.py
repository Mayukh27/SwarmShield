"""LangChain adapter: real ``create_agent`` + real gateway + a scripted (offline) chat model."""
from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("langchain", minversion="1.0")

from langchain.agents import create_agent  # noqa: E402
from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402
from langchain_core.tools import tool  # noqa: E402

from swarmshield.integrations._client import GatewayClient  # noqa: E402
from swarmshield.integrations.langchain import SwarmShieldMiddleware  # noqa: E402

from .conftest import INJECTION  # noqa: E402


class ScriptedModel(BaseChatModel):
    """Replays a fixed list of AIMessages: no LLM, no API key."""

    script: list[Any]
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        msg = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools, **kwargs):
        return self


def call(name: str, args: dict, cid: str = "c1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": cid}])


def make_tools(executed: list, web_result: str = "Q3 market grew 4%."):
    @tool
    def web_search(query: str) -> str:
        """Search the web."""
        executed.append(("web_search", query))
        return web_result

    @tool
    def sql_drop(statement: str) -> str:
        """Drop tables."""
        executed.append(("sql_drop", statement))
        return "dropped"

    @tool
    def execute_admin_action(action: str) -> str:
        """Run an admin action."""
        executed.append(("execute_admin_action", action))
        return "done"

    return [web_search, sql_drop, execute_admin_action]


def build(gateway_url, uid, role, script, executed, *, web_result="Q3 market grew 4%.", client=None):
    model = ScriptedModel(script=script)
    shield = SwarmShieldMiddleware(
        agent_id=f"{role}-{uid}", role=role, client=client or GatewayClient(gateway_url)
    )
    return create_agent(model, tools=make_tools(executed, web_result), middleware=[shield]), model


def last_tool_message(result) -> ToolMessage:
    return [m for m in result["messages"] if isinstance(m, ToolMessage)][-1]


def test_clean_flow_runs_tool_and_model(gateway_url, uid):
    executed: list = []
    agent, model = build(gateway_url, uid, "researcher", [call("web_search", {"query": "q3 market"}), AIMessage("done")], executed)
    result = agent.invoke({"messages": [HumanMessage("Summarize the Q3 market")]})
    assert executed == [("web_search", "q3 market")]
    assert result["messages"][-1].content == "done" and model.calls == 2


def test_injected_inbound_message_halts_before_the_model(gateway_url, uid):
    executed: list = []
    agent, model = build(gateway_url, uid, "researcher", [AIMessage("should never run")], executed)
    msg = HumanMessage(INJECTION, additional_kwargs={"swarmshield": {
        "sender_id": f"web-{uid}", "sender_role": "web_content", "provenance": ["untrusted_web"]}})
    result = agent.invoke({"messages": [msg]})
    assert result["messages"][-1].content.startswith("[SwarmShield]")
    assert model.calls == 0 and executed == []


def test_rbac_blocks_tool_call_before_it_executes(gateway_url, uid):
    executed: list = []
    agent, _ = build(gateway_url, uid, "db_agent",
                     [call("sql_drop", {"statement": "DROP TABLE users;"}), AIMessage("ok")], executed)
    result = agent.invoke({"messages": [HumanMessage("clean the database")]})
    tm = last_tool_message(result)
    assert executed == []  # the tool function never ran
    assert tm.status == "error" and "[SwarmShield]" in tm.content and "sql_drop" in tm.content


def test_poisoned_tool_output_is_replaced_before_the_llm_sees_it(gateway_url, uid):
    executed: list = []
    agent, model = build(gateway_url, uid, "researcher",
                         [call("web_search", {"query": "market report"}), AIMessage("done")], executed, web_result=INJECTION)
    result = agent.invoke({"messages": [HumanMessage("research the market")]})
    tm = last_tool_message(result)
    assert executed == [("web_search", "market report")]  # the tool ran (that is where the poison arrives)...
    assert tm.status == "error" and "output blocked" in tm.content
    assert "SYSTEM UPDATE" not in tm.content and "DROP TABLE" not in tm.content  # ...but the LLM never reads it


def test_taint_blocks_high_risk_tool_only_after_untrusted_output(gateway_url, uid):
    # clean context: an admin session may run the admin tool
    ok: list = []
    agent, _ = build(gateway_url, f"{uid}a", "admin_assistant", [call("execute_admin_action", {"action": "rotate_logs"}), AIMessage("k")], ok)
    agent.invoke({"messages": [HumanMessage("rotate the logs")]})
    assert ok == [("execute_admin_action", "rotate_logs")]

    # same tool, but untrusted web output is already in the context -> blocked as taint
    tainted: list = []
    script = [call("web_search", {"query": "x"}, "c1"), call("execute_admin_action", {"action": "rotate_logs"}, "c2"), AIMessage("k")]
    agent, _ = build(gateway_url, f"{uid}b", "admin_assistant", script, tainted)
    result = agent.invoke({"messages": [HumanMessage("research then rotate the logs")]})
    assert tainted == [("web_search", "x")]
    assert "untrusted content" in last_tool_message(result).content


def test_repeating_the_same_prompt_across_runs_is_not_a_loop(gateway_url, uid):
    executed: list = []
    agent, _ = build(gateway_url, uid, "researcher", [AIMessage("answer")], executed)
    for _ in range(8):  # would trip the repetition breaker if runs shared one conversation id
        result = agent.invoke({"messages": [HumanMessage("What is your return policy?")]})
        assert result["messages"][-1].content == "answer"


def test_gateway_outage_fail_closed_and_fail_open(dead_url, uid):
    executed: list = []
    agent, model = build(None, uid, "researcher", [AIMessage("answer")], executed,
                         client=GatewayClient(dead_url, timeout=0.5, fail_mode="closed"))
    assert agent.invoke({"messages": [HumanMessage("hi")]})["messages"][-1].content.startswith("[SwarmShield]")
    assert model.calls == 0

    agent, model = build(None, uid, "researcher", [AIMessage("answer")], executed,
                         client=GatewayClient(dead_url, timeout=0.5, fail_mode="open"))
    assert agent.invoke({"messages": [HumanMessage("hi")]})["messages"][-1].content == "answer"


@pytest.mark.asyncio
async def test_async_path(gateway_url, uid):
    executed: list = []
    agent, _ = build(gateway_url, uid, "db_agent", [call("sql_drop", {"statement": "DROP TABLE users;"}), AIMessage("ok")], executed)
    result = await agent.ainvoke({"messages": [HumanMessage("clean the database")]})
    assert executed == [] and last_tool_message(result).status == "error"

    agent, model = build(gateway_url, f"{uid}x", "researcher", [AIMessage("fine")], executed)
    bad = HumanMessage(INJECTION, additional_kwargs={"swarmshield": {"provenance": ["untrusted_web"], "sender_id": f"web-{uid}"}})
    result = await agent.ainvoke({"messages": [bad]})
    assert result["messages"][-1].content.startswith("[SwarmShield]") and model.calls == 0
