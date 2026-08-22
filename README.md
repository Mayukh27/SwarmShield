# SwarmShield

**An autonomous multi-agent AI security testing framework.** SwarmShield deploys a swarm of specialist AI agents to red-team another AI system — planning attacks, executing them, judging the results with evidence, learning across attempts, evolving its strategy, mapping the full attack chain, scoring risk, generating remediation, and then **proving the fix actually works** by re-attacking the patched target.

Built for a hackathon by combining two independent prototypes ([`SaumyajitDas001/SwarmShield`](https://github.com/SaumyajitDas001/SwarmShield) and [`Sunanda02/swarmshield`](https://github.com/Sunanda02/swarmshield)) into one working system, plus a from-scratch controlled vulnerable target, risk engine, and remediation/re-validation loop that neither original repo implemented.

> ⚠️ **Authorized testing only.** SwarmShield is designed to attack a target you own or are explicitly authorized to test — by default the included **controlled local target**. Every target must be explicitly attested as authorized before it can be scanned; SwarmShield refuses (HTTP 403) to start a scan against one that isn't, enforced server-side, not just a disabled button in the UI.

The dashboard presents all of this through a "siege" framing — targets are **Realms**, a scan is a **Siege**, the risk score is **Fortress Integrity**, findings are **breaches** in the fortress wall, and a remediation patch is a **Ward**. It's cosmetic dressing over real data: every number, badge, and status on screen comes straight from the API responses below, nothing is scripted or hardcoded for the demo.

---

## What it actually does

```
Authorized Target
     ↓
Attack Surface Discovery         Planner Agent reads the target's declared
     ↓                           tools/capabilities and proposes attack vectors
Planner Agent
     ↓
Specialized Agent Swarm          5 specialists: Prompt Injection, Jailbreak,
     ↓                           Tool Abuse, Data Exfiltration, Privilege Escalation
Controlled Target
     ↓
Sentinel Agent                   Judges the target's actual response for
     ↓                           evidence of a real violation (not a keyword match),
     ↓                           and explains it against the target's own declared
     ↓                           security policy when one applies (see below)
Evidence / Finding
     ↓
Shared Memory                    Every outcome is written to memory and
     ↓                           consulted by later agents in the same scan
Attack DNA / Adaptive Mutation    Failed attempts mutate (Sentinel's own hint
     ↓                           picks the mutation type) and retry
Next Attack ⟲
     ↓
Attack Graph                     Evidence-linked graph of the whole campaign
     ↓
Risk                             Severity/exposure-weighted score, not a
     ↓                           flat success ratio
Remediation                      LLM-generated patch suggestion per finding
     ↓
Re-validation                    Applies the patch to the live target and
                                  replays the exact winning payload — proves
                                  fixed vs. still-vulnerable, doesn't assume it
```

Every one of these boxes is a real, wired-together implementation — see [`SWARMSHIELD_RECONCILIATION_PLAN.md`](./SWARMSHIELD_RECONCILIATION_PLAN.md) for exactly which parts came from which source repo, which were rebuilt from scratch, and what was actually executed and tested to confirm it works (real Postgres, a real end-to-end scan, a real pre-patch → post-patch verdict flip, `npm run build`, `pytest`).

---

## Why a controlled target?

Red-teaming a real, unauthorized AI system is out of scope for a hackathon demo and genuinely unsafe. SwarmShield ships with its own **authorized, local-only, intentionally vulnerable target** (`controlled_target/`) modeling a realistic architecture:

```
User → LLM → RAG → Mock Tools
```

It has real, documented, non-scripted vulnerabilities — search `VULN:` in [`controlled_target/app.py`](./controlled_target/app.py):

- **Indirect prompt injection via RAG poisoning** — a "support ticket" document planted in the knowledge base carries attacker instructions the model follows as if they were the system prompt, but only when retrieved (a benign query stays completely clean).
- **Unsafe tool permissions** — `execute_admin_action` and `read_file("internal_notes.txt")` have no role check at all.
- **Data exfiltration** — confidential file content leaks straight into the chat response and an outbound "email" once the injection lands.
- **Direct prompt injection** — a plain `"ignore previous instructions..."` user turn triggers the same override path independent of RAG.

The target also exposes `/admin/apply_patch` and `/admin/reset_patch`, which SwarmShield's revalidation flow calls for real — so "the finding is now fixed" is a genuinely different target response to a genuinely replayed payload, not a database flag.

It runs entirely offline (`SAFE_MODE = True`, never makes outbound network calls) and can optionally be backed by real Gemini for its own responses.

---

## Architecture

| Layer | Technology |
|---|---|
| Agents (Planner, Sentinel, 5 specialists, Remediation) | Google Gemini via `google-genai`, or a deterministic offline fallback engine (see below) |
| Backend API | FastAPI, SQLAlchemy, PostgreSQL |
| Live agent activity stream | Server-Sent Events |
| Frontend dashboard | React, Tailwind CSS, React Flow, Zustand |
| Controlled target | FastAPI, standalone service |

### Security policy awareness

A target can optionally declare a lightweight security policy on the existing `permission_map` field (no schema change — this column already existed and was already accepted by the API, just unused until now):

```json
{
  "tools": {
    "execute_admin_action": {"restriction": "admin_only"},
    "send_email": {"restriction": "external_recipients_restricted"},
    "read_file": {"restriction": "restricted_paths", "restricted_paths": ["internal_notes.txt"]}
  },
  "protected_resources": ["internal_notes", "customer data", "confidential pricing"],
  "policies": ["no_unauthorized_tool_execution", "no_privilege_escalation", "no_confidential_exfiltration", "detect_prompt_injection"]
}
```

When set, the Planner raises priority on vectors that target something explicitly restricted, and the Sentinel explains confirmed findings against the specific declared restriction that was breached, e.g.:

> *"Policy violation: non-admin context successfully invoked admin-only capability 'execute_admin_action'."*

Not an RBAC system — just enough structure for the Sentinel to explain *why* a finding matters in the target's own terms instead of generic severity language. See `backend/app/services/policy_service.py`.

### Authorization gate

Every `TargetProfile` has an `authorized` flag and an `authorization_note` (what the attestation is — "I own this," "written permission from X," etc). `POST /api/scans` checks it server-side and returns `403` for anything unauthorized — this is enforced in `api/routes/scans.py`, not just a required checkbox in the registration form (though the dashboard's Realm Registry screen does require it too, and surfaces a 403 as a visible error banner rather than failing silently).

### The offline fallback engine

`backend/app/services/fallback_engine.py` stands in for Gemini when `GEMINI_API_KEY` is unset. It is **not** a scripted "always succeeds" stub — it inspects the target's actual declared tools, the actual `target_response` text, and the actual Sentinel `mutation_hint`, and produces genuinely different outputs for different inputs (a benign response and a compromised one get different Sentinel verdicts; a retry's payload is genuinely shaped by the mutation hint). This is what the whole system was built and tested against in an environment with no outbound access to the real Gemini API. Set `GEMINI_API_KEY` and every agent switches to real Gemini calls with zero other code changes.

---

## Repository layout

```
merged/
├── backend/                  FastAPI backend
│   ├── app/
│   │   ├── agents/           Planner, Sentinel, 5 specialists, Remediation, orchestrator
│   │   ├── api/routes/       targets, scans, vulnerabilities, patches, graph, memory_dna, revalidation
│   │   ├── models/           SQLAlchemy models (9 tables)
│   │   ├── services/         gemini_client, fallback_engine, memory_service, dna_service, policy_service,
│   │   │                     risk, graph_service, revalidation_service, target_client, event_bus
│   │   ├── schemas/          Pydantic response models
│   │   ├── core/             config
│   │   └── db/                init_db, session/engine
│   ├── tests/                 pytest suite (13 tests, real Postgres)
│   ├── requirements.txt
│   └── Dockerfile
├── controlled_target/         the authorized vulnerable target
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                  React dashboard ("siege" themed — see below)
│   ├── src/
│   │   ├── AppShell.jsx        top-level shell: HUD + bottom nav + 7-screen router
│   │   ├── screens/             WarRoom, RealmRegistry, LiveSiege, SiegeReport,
│   │   │                        RemediationForge, Outcome, Settings
│   │   ├── components/hud/      TopHUD, BottomNav
│   │   ├── components/sprites/  FortressSprite, TroopSprite, SiegeBackdrop, VictoryConfetti, ClanCrest
│   │   ├── components/          RiskBreakdownPanel, VulnerabilityTable, PatchSuggestionPanel,
│   │   │                        MemoryPanel, AttackDnaPanel, AgentLogConsole, flow/AttackFlowCanvas
│   │   ├── theme/coc.js         game-term ↔ real-meaning mapping (severity colors, OWASP → wall structure)
│   │   ├── hooks/                useScanStream (SSE)
│   │   ├── store/                 scanStore (Zustand)
│   │   └── lib/                    api.js, refreshScan.js, policy.js
│   ├── nginx.conf              /api proxy for the production Docker build
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── DEMO_GUIDE.txt              step-by-step run + live-demo script
└── SWARMSHIELD_RECONCILIATION_PLAN.md   how the two source repos were merged, what was verified
```

---

## Quick start

**Docker (fastest):**
```bash
cp .env.example .env    # optionally set GEMINI_API_KEY
docker compose up --build
# frontend → http://localhost:5173
# api      → http://localhost:8000
# target   → http://localhost:9100
```

**Local (no Docker)** — full step-by-step in [`DEMO_GUIDE.txt`](./DEMO_GUIDE.txt):
```bash
# 1. Postgres
createdb swarmshield

# 2. Controlled target
cd controlled_target && pip install -r requirements.txt && python app.py &

# 3. Backend
cd ../backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg2://swarmshield:swarmshield@localhost:5432/swarmshield'
python -m app.db.init_db
uvicorn app.main:app --reload --port 8000 &

# 4. Frontend
cd ../frontend && npm install && npm run dev
```
Open http://localhost:5173, register the controlled target (check the authorization attestation — SwarmShield refuses to scan anything unauthorized), and click Declare War to start a scan.

See [`DEMO_GUIDE.txt`](./DEMO_GUIDE.txt) for the full walkthrough, including the curl commands for every step and a scripted "prove the fix works" demo moment.

---

## Running the tests

```bash
cd backend
source venv/bin/activate
export DATABASE_URL='postgresql+psycopg2://swarmshield:swarmshield@localhost:5432/swarmshield'
pytest tests/ -v
```
13 tests covering the merge-specific logic: offline-engine agent dispatch (including a regression test for a real bug found during the build — a specialist prompt's own text falsely matched the Sentinel's dispatch branch), Sentinel's evidence detection, Attack DNA mutation-hint mapping and generation lineage, risk-score weighting including that fixed findings are excluded from the aggregate, and shared-memory validation/retrieval. All 13 pass against a real Postgres instance.

---

## API reference (selected)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/targets` | Register a target (requires `"authorized": true` or the target can never be scanned) |
| `POST` | `/api/scans` | Start a scan — 403 if the target isn't authorized (runs the full Planner→Swarm→Sentinel→... loop) |
| `GET` | `/api/scans/{id}` | Scan status, risk score, risk breakdown |
| `GET` | `/api/scans/{id}/events` | SSE stream of live agent activity |
| `GET` | `/api/scans/{id}/attack-logs` | Every attempt, including mutation lineage |
| `GET` | `/api/scans/{id}/memory` | Shared memory items written/consulted during the scan |
| `GET` | `/api/scans/{id}/attack-dna` | Attack DNA genomes and mutation history per vector |
| `GET` | `/api/scans/{id}/graph` | Evidence-linked attack graph (nodes/edges) |
| `GET` | `/api/vulnerabilities?scan_id=` | Confirmed findings with evidence and risk scores |
| `POST` | `/api/patches/generate/{vulnerability_id}` | Generate a remediation patch |
| `POST` | `/api/vulnerabilities/{id}/apply-and-revalidate` | Apply a patch to the live target and re-test (`?apply=false` to check without applying) |
| `GET` | `/api/vulnerabilities/{id}/revalidation-history` | Full history of re-validation attempts |

---

## Security notes

- The controlled target makes **zero outbound network calls** by default (`SAFE_MODE`) and every "dangerous" tool call is mocked and logged, never executed for real.
- Authorization, allowed scopes, and audit logging are preserved from the source repos' safety controls.
- Do not point `endpoint_url` on a `TargetProfile` at any system you don't own or have explicit authorization to test.

---

## Credits

Built on top of two hackathon prototypes:
- [SaumyajitDas001/SwarmShield](https://github.com/SaumyajitDas001/SwarmShield) — data model, shared memory types, Attack DNA schema, evidence graph builder
- [Sunanda02/swarmshield](https://github.com/Sunanda02/swarmshield) — agent framework, Gemini integration, Planner/Sentinel/specialists, adaptive attack loop, dashboard

Combined, extended, and verified in this repository. Full decision-by-decision rationale in [`SWARMSHIELD_RECONCILIATION_PLAN.md`](./SWARMSHIELD_RECONCILIATION_PLAN.md).
