# SwarmShield

### Autonomous AI Red-Team & Runtime Security Platform

SwarmShield is a security platform for **authorized AI and multi-agent systems**. It combines autonomous red-team testing with a runtime security gateway that inspects agent-to-agent communication, enforces tool/role policies, detects prompt injection, and stops runaway agent delegation.

> **Authorized testing only.** Use SwarmShield only against systems you own or are explicitly authorized to security-test.

## Overview

```text
                    SWARMSHIELD
                         |
          +--------------+--------------+
          |                             |
   AUTONOMOUS RED TEAM            RUNTIME SHIELD
          |                             |
      Planner                       A2A Gateway
          |                             |
   +------+-------+             +-------+-------+
   |      |       |             |       |       |
Prompt  Jailbreak Tool       Injection  RBAC  Circuit
Inject  Specialist Abuse     Detection Policy Breaker
   |      |       |             |       |       |
   +------+-------+             +-------+-------+
          |                             |
       Sentinel                    ALLOW / FLAG /
          |                       BLOCK / TRIP
          +-------------+---------------+
                        |
                 Patch & Revalidate
```

### Security lifecycle

**Discover -> Attack -> Detect -> Protect -> Patch -> Revalidate**

## Core Capabilities

### Autonomous Red-Team Scanning

The security swarm includes:

- Planner
- Sentinel
- Prompt Injection Specialist
- Jailbreak Specialist
- Tool Abuse Specialist
- Data Exfiltration Specialist
- Privilege Escalation Specialist
- Orchestrator
- Remediation workflow

The Planner identifies attack paths and delegates tests to specialists. The Sentinel evaluates target responses and evidence before a vulnerability is confirmed.

### Runtime A2A Security Gateway

Agent-to-agent transfers can pass through the SwarmShield gateway before reaching the receiving agent.

```text
Agent A
   |
   | A2A transfer
   v
SwarmShield Gateway
   |
   +-- Prompt-injection detection
   +-- Role/tool authorization
   +-- Security state
   +-- Circuit breaker
   |
   +--> ALLOW
   +--> FLAG / HUMAN REVIEW
   +--> BLOCK / HTTP 403
   +--> CIRCUIT BREAK / HTTP 429
```

### Prompt Injection Detection

SwarmShield detects malicious instructions embedded in untrusted content, including indirect prompt injection arriving through retrieved or external content.

### RBAC / Tool Authorization

The gateway evaluates sender/receiver roles and tool permissions so unauthorized tool activity can be blocked before execution.

### Recursive-Agent Circuit Breaker

Repeated A2A delegation is tracked across a conversation. A runaway loop can be terminated with HTTP 429.

```text
A -> B  ALLOW
B -> A  ALLOW
A -> B  ALLOW
B -> A  ALLOW
A -> B  ALLOW
B -> A  HTTP 429
          |
     Circuit Breaker
          |
       Loop stopped
```

### Patch & Revalidation

```text
Finding
   |
Remediation
   |
Patch
   |
Replay / Revalidate
   |
Verify whether vulnerability remains exploitable
```

## Runtime Attack Simulation

The repository includes an executable demonstration against the actual SwarmShield gateway.

```cmd
python -m swarmshield.tests.simulate_attacks
```

### Scenario A — Indirect Prompt Injection

Untrusted web content contains an injected instruction attempting an unauthorized database operation.

Expected:

```text
SwarmShield INTERCEPTED the transfer (HTTP 403)
```

The receiving agent does not receive the blocked payload.

### Scenario B — Recursive A2A Loop

Two agents repeatedly delegate the same task to each other.

Expected:

```text
hop 1  ALLOW
hop 2  ALLOW
hop 3  ALLOW
hop 4  ALLOW
hop 5  ALLOW
hop 6  HTTP 429
```

The stateful circuit breaker identifies the recursive delegation pattern and terminates the loop.

## LangChain Integration

Native integration:

```text
swarmshield/integrations/langchain.py
```

```text
LangChain Agent
      |
SwarmShield Middleware
      |
Gateway /a2a/transfer
      |
Security Decision
```

The adapter can inspect inbound messages, proposed tool calls, and tool/retrieval outputs before the model consumes them.

**Verified with LangChain 1.4.2.**

## LangGraph Integration

Native integration:

```text
swarmshield/integrations/langgraph.py
```

The adapter adds a SwarmShield gate to a LangGraph `StateGraph`.

```text
LangGraph StateGraph
        |
 SwarmShield Gate
        |
   +----+---------+
   |              |
 ALLOW          FLAG/BLOCK
                  |
             interrupt()
                  |
             Human Review
```

It supports synchronous and asynchronous invocation, human-in-the-loop interruption, quarantine, RBAC hard stops, and recursive graph/delegation protection.

**Verified with LangGraph 1.2.11.**

> LangChain and LangGraph are integrations used by agent applications. They are intentionally not installed inside the framework-agnostic gateway container.

## Integration Testing

Run the complete integration suite against a running gateway:

```cmd
set SWARMSHIELD_TEST_GATEWAY_URL=http://localhost:8100
pytest swarmshield\tests -v
```

Verified result:

```text
27 passed
```

Coverage includes gateway behavior, prompt injection, circuit breaker, failure modes, LangChain, LangGraph, RBAC, human review, and recursive graph protection.

## Docker Deployment

Start the stack:

```cmd
copy .env.example .env
docker compose up --build
```

Open:

```text
http://localhost:5173
```

### Services

| Service | Port | Purpose |
|---|---:|---|
| frontend | 5173 | React/Nginx security dashboard |
| api | 8000 | FastAPI platform API |
| swarmshield-gateway | 8100 | Runtime A2A security gateway |
| controlled-target | 9100 | Local authorized demo target |
| db | 5432 | PostgreSQL |

Health endpoints:

```text
http://localhost:8100/health
http://localhost:9100/health
```

Stop:

```cmd
docker compose down
```

## Controlled Target

The repository includes a local authorized target for demonstrations and development.

```text
Chat
 |
 +-- RAG
 |
 +-- Tools
```

It provides a safe environment for demonstrating prompt injection, tool authorization, information disclosure, and runtime shielding.

## Security Dashboard

The frontend provides:

- Autonomous scan activity
- Agent activity
- Vulnerability findings
- Runtime security events
- Agent/security topology
- Patch/remediation state
- Revalidation results

The Security view uses React Flow to visualize agent communication and security state.

Add project screenshots/GIFs under `docs/screenshots/` and reference them here.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Styling | Tailwind CSS |
| Visualization | React Flow |
| Backend | FastAPI |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy |
| Runtime HTTP | HTTPX |
| Live events | Server-Sent Events |
| Containerization | Docker Compose |
| Agent integration | LangChain 1.4.2 |
| Agent integration | LangGraph 1.2.11 |
| Local LLM boundary | Ollama |
| Cloud LLM boundary | Gemini / optional provider |
| Testing | Pytest |

## Repository Structure

```text
SwarmShield/
├── backend/
├── controlled_target/
├── frontend/
├── swarmshield/
│   ├── gateway.py
│   ├── integrations/
│   │   ├── langchain.py
│   │   ├── langgraph.py
│   │   └── _client.py
│   ├── policies/
│   └── tests/
│       ├── test_client_and_imports.py
│       ├── test_langchain.py
│       ├── test_langgraph.py
│       └── simulate_attacks.py
├── docs/
│   ├── DEMO.md
│   └── INTEGRATIONS.md
├── scripts/
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Demo Flow

For a short hackathon demonstration:

1. Start the Docker stack.
2. Run the autonomous red-team scan.
3. Show Planner -> Specialists -> Sentinel -> findings.
4. Open Runtime Security and show the agent topology.
5. Demonstrate indirect prompt injection -> HTTP 403.
6. Demonstrate recursive A2A loop -> HTTP 429.
7. Apply remediation and revalidate.
8. Mention native LangChain and LangGraph integrations.

The central story is:

```text
Autonomous Attack
       |
       v
Vulnerability Found
       |
       v
Runtime Protection
       |
       v
Attack Blocked
       |
       v
Patch
       |
       v
Revalidate
```

## Configuration

Copy the example environment:

```cmd
copy .env.example .env
```

Keep secrets out of source control. Optional integrations include Gemini, Ollama/local LLM routing, and GitHub remediation workflows.

## Limitations

SwarmShield is a security research/hackathon platform, not a guarantee of complete AI-system security.

Detection quality depends on configured policies, detectors, target behavior, and available evidence. Production deployments require appropriate authentication, secret management, network isolation, logging, monitoring, and operational controls.

## Project Status

Verified capabilities:

- Autonomous red-team scanning
- Runtime A2A security gateway
- Prompt-injection blocking
- RBAC/tool authorization
- Stateful recursive-agent circuit breaker
- Patch and revalidation workflow
- React Flow security visualization
- LangChain 1.4.2 integration
- LangGraph 1.2.11 integration
- Executable 403/429 attack simulations
- Docker Compose deployment
- 27/27 integration/security tests passing

## License

Add the project's applicable license here.

---

**SwarmShield — discover the weakness, shield the runtime, and verify the fix.**
