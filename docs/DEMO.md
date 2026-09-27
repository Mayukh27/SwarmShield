# SwarmShield: Red Team + Runtime Security demo

One product, two halves:

| Half | Question it answers | Where you see it |
|---|---|---|
| **Autonomous AI Red Team** (existing) | "Where is my AI system vulnerable?" | Dashboard, AI Agents, Vulnerabilities, Reports |
| **SwarmShield Runtime Gateway** (new) | "Can I stop those attacks while the agents are running?" | A2A Security page + panel on the AI Agents page |

## Run it (Windows CMD)

```
cd SwarmShield-main
copy .env.example .env
docker compose up --build
```

Open http://localhost:5173. Services: frontend 5173, API 8000, gateway 8100, controlled target 9100.
Reset between rehearsals with `docker compose down -v`, then `docker compose up --build`
(scan memory skips strategies that failed before, and the target keeps its patched state until restarted).

## What each part does

- **Controlled target** (`controlled_target/`): a deliberately vulnerable app (user -> LLM -> RAG -> mock tools).
- **Red-team platform** (`backend/app/agents`): Planner, specialists and Sentinel attack the target and report findings.
- **SwarmShield gateway** (`swarmshield/gateway.py`): every message and tool call goes through
  `POST /a2a/transfer`. It applies, in order: quarantine check, injection scan, RBAC and taint policy,
  circuit breaker. It answers 200 (allow or flag), 403 (blocked) or 429 (loop tripped).
- **Scan monitor** (`backend/app/services/shield_runtime.py`): during a scan, delegations and the target's
  output go to the gateway in monitor mode. Real verdicts are shown; the scan is never blocked
  (the red team is authorized to attack).
- **Security Demo** (same file, button in the UI): sends a scripted indirect-injection attack and a
  recursive A<->B delegation loop to the real gateway and streams the real 403 and 429 responses.
- **Apply patch & re-validate** (existing button): with `APPLY_PATCH_MODE=both` it also routes the
  target through the gateway, so replayed attacks are blocked at the user input, the RAG document and the tool call.

## Browser walkthrough

1. Open http://localhost:5173 and click **New scan** (the demo target is pre-registered).
2. Open **A2A Security**: agents are 🟢, the target is 🟡 (its output leaked confidential text). All from real gateway calls.
3. Click **Run Security Demo**: 🟢 clean, 🟡 inspected, 🔴 403 injection in a web page, 🔴 403 `sql_drop`
   (Agent A quarantined), then 🔴 429 recursive loop with evidence (both agents quarantined).
4. Vulnerabilities / Patch Center: **Apply & re-validate**. The gateway now blocks the same attacks on the target.
5. Reports: findings from the red team plus the runtime protection that stops them.

## How to explain it to mentors

*Problem.* Multi-agent AI systems trust each other's messages. One poisoned web page or document can make
Agent A order Agent B to drop a database, or send two agents into a loop that burns the token budget.

*Approach.* We built both sides. The red team finds the weaknesses; the gateway sits between agents and
enforces three controls on every hop: prompt-injection detection, least-privilege tool access
(a low-privilege agent cannot trigger a dangerous tool, and content from untrusted sources cannot trigger
one at all), and a circuit breaker for loops.

*Proof.* Nothing in the demo is scripted on the UI side. The backend fires real traffic at the real gateway and
the screen shows the actual HTTP 200/403/429 responses and their reasons. Then the same attacks that
succeeded against the unprotected target are replayed and blocked.

*Be upfront about limits.* Detection is heuristic (rules), not a trained model, so novel phrasings can slip
past the text scan; the RBAC and taint layers still stop dangerous tool calls. The circuit breaker uses
word-overlap similarity, not embeddings. State is in memory on a single gateway process. The bundled
target is a lab app, and the demo target is auto-registered as authorized only for that reason.
