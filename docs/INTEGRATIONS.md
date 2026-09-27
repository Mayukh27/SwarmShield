# Framework integrations (LangChain / LangGraph)

Thin adapters. They contain **no detection or policy logic**: every message, tool call and tool result is
sent to the SwarmShield gateway (`POST /a2a/transfer`) and the adapter only translates the answer into the
framework's own control flow. Same gateway, same policy file, same circuit breaker as the rest of the project.

```
pip install "swarmshield[langchain]"   # LangChain >= 1.0
pip install "swarmshield[langgraph]"   # LangGraph >= 1.0
```

LangChain/LangGraph are optional: `import swarmshield` and the gateway never import them, and using an adapter
without its framework raises an `ImportError` that names the extra to install.

Configuration (both adapters): `SWARMSHIELD_URL` (default `http://localhost:8100`), `SWARMSHIELD_API_KEY`
(only if the gateway sets one), or pass `gateway_url=` / `api_key=` / a `GatewayClient(...)`.
`fail_mode="closed"` (default) blocks when the gateway is unreachable; `"open"` lets traffic through uninspected.

## How gateway answers become framework behaviour

| Gateway | Meaning | LangChain middleware | LangGraph gate |
|---|---|---|---|
| 200 `allow` | clean | continue | route to your node |
| 200 `flag` (`requires_human_review`) | suspicious | continue (logged) | `interrupt()` for human approve/reject |
| 403 | injection / RBAC / taint / quarantined sender | agent halted, or tool call returns an error `ToolMessage` (tool never runs) | quarantine node (final by default) |
| 429 | circuit breaker (loop, depth, velocity, tokens) | same as 403 | quarantine node, never overridable |
| unreachable | outage | fail closed: block. Fail open: allow | fail closed: ask a human. Fail open: allow |

## LangChain

```python
from langchain.agents import create_agent
from swarmshield.integrations.langchain import SwarmShieldMiddleware

shield = SwarmShieldMiddleware(agent_id="researcher-1", role="researcher")   # role must exist in the gateway policy
agent = create_agent("openai:gpt-4o", tools=[web_search, sql_select], middleware=[shield])
```

`before_agent` inspects the inbound message before the LLM sees it. `wrap_tool_call` (LangChain's around-tool hook)
inspects every proposed tool call (RBAC + taint, with the agent's `role`) and, for tools listed in
`untrusted_output_tools` (web/search/retrieval by default), scans the **output** before the model reads it.

To carry provenance from another agent, attach an envelope to the message:

```python
HumanMessage(text, additional_kwargs={"swarmshield": {
    "sender_id": "planner-1", "sender_role": "planner",
    "provenance": ["untrusted_web"], "conversation_id": "task-42"}})
```

## LangGraph

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command
from swarmshield.integrations.langgraph import SwarmState, add_swarmshield_gate

builder = StateGraph(SwarmState)
builder.add_node("agent", my_agent_node)
builder.add_edge("agent", END)
add_swarmshield_gate(builder, protected_node="agent")        # adds START -> gatekeeper -> (review) -> agent
graph = builder.compile(checkpointer=MemorySaver())          # a checkpointer is required for interrupt()

cfg = {"configurable": {"thread_id": "t1"}}
out = graph.invoke({"messages": [msg], "sender_id": "planner-1", "sender_role": "planner",
                    "receiver_id": "researcher-1", "receiver_role": "researcher",
                    "provenance": ["untrusted_web"]}, cfg)
if "__interrupt__" in out:                                    # gateway said: needs a human
    print(out["__interrupt__"][0].value)                      # reason, risk score, findings, message preview
    graph.invoke(Command(resume={"decision": "approve", "reviewer": "alice"}), cfg)
```

State fields the gate reads (all optional): `sender_id`, `sender_role`, `receiver_id`, `receiver_role`,
`target_tool`, `tool_args`, `provenance`, `conversation_id` (falls back to the `thread_id`), `hop_count`
(incremented on every pass, so cyclic graphs get recursion-depth protection). The gate writes its audit trail to
`state["shield"]`. Works with `invoke` and `ainvoke`. A 403 is final unless you opt in:
`add_swarmshield_gate(..., overridable_violations=frozenset({"prompt_injection"}))`.

## Tests (no LLM, no API keys)

```
pip install -e ".[langchain,langgraph,test]"
pytest swarmshield/tests
```

The tests start the real gateway in-process and run real `create_agent` / `StateGraph` workflows against it
with a scripted offline chat model.
