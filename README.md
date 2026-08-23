# SwarmShield

### Autonomous AI Red-Team & Security Validation Platform

SwarmShield is an autonomous, multi-agent security testing platform for **authorized AI systems and agentic applications**. It discovers an AI target's attack surface, plans and executes adversarial tests, evaluates evidence, learns from previous attempts, builds attack intelligence, generates remediation, and can revalidate whether a vulnerability was actually fixed.

> **Authorized testing only.** SwarmShield requires an explicit authorization attestation before a target can be scanned. Read-only operation is the safe default, while live patch application, branch writes, and pull-request creation are independently permission-gated.

---

## Overview

SwarmShield treats an AI application as a security boundary rather than simply testing a conventional HTTP endpoint.

```text
                         ┌──────────────────────────┐
                         │      Target Registry      │
                         │ URL + Auth + Tools +     │
                         │ Policy + Access Controls │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │   Capability Discovery    │
                         │   Attack Surface Mapping  │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │      Planner Agent        │
                         │ Prioritizes attack paths  │
                         └────────────┬─────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              Prompt Injection   Jailbreak          Tool Abuse
              Specialist         Specialist         Specialist
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      ▼
                           ┌─────────────────────┐
                           │    Target System    │
                           └──────────┬──────────┘
                                      ▼
                           ┌─────────────────────┐
                           │   Sentinel Agent    │
                           │ Evidence + Verdict  │
                           └──────────┬──────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │ Memory + Attack DNA +    │
                         │ Attack Graph + Risk      │
                         └────────────┬─────────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │ Remediation + Auto PR    │
                         │ + Revalidation           │
                         └──────────────────────────┘
```

---

## Core Capabilities

### 🤖 Multi-Agent Security Testing

The backend contains a coordinated swarm consisting of:

- Planner Agent
- Sentinel Agent
- Remediation Agent
- Prompt Injection Specialist
- Jailbreak Specialist
- Tool Abuse Specialist
- Data Exfiltration Specialist
- Privilege Escalation Specialist
- Orchestrator for campaign execution and adaptive retries

Agents operate against the registered target and persist their findings and attack lineage in PostgreSQL.

### 🧠 Capability Intelligence

SwarmShield analyzes the target's declared and observed capabilities to identify:

- exposed tools
- authorization boundaries
- sensitive resources
- capability relationships
- potential multi-hop attack paths
- coverage gaps
- historical attack signals
- attack hypotheses

Capability graphs and attack paths are exposed through the API and surfaced through the intelligence UI.

### 🧬 Shared Memory & Attack DNA

The swarm persists campaign intelligence so later attempts can use previous outcomes.

Attack DNA records track:

- attack vector lineage
- parent attempts
- generations
- mutations
- success probability
- confidence
- mutation-driven retries

This enables adaptive testing instead of repeatedly sending identical payloads.

### 🔎 Evidence-Based Findings

Findings are generated from the target's actual responses and persisted attack evidence.

The Sentinel evaluates:

- target response
- attack vector
- security policy
- tool/capability context
- previous attack information

Findings are categorized using OWASP LLM-oriented categories and include severity, evidence, status, and remediation state.

### 📚 Local RAG & Persistent Intelligence

SwarmShield includes a local knowledge layer backed by PostgreSQL.

The RAG implementation provides:

- persistent knowledge documents
- embeddings
- metadata filtering
- lexical + cosine-similarity hybrid retrieval
- bounded retrieval per scan
- secret-material rejection during ingestion

If a local sentence-transformer model is unavailable, the embedding service falls back to a deterministic hashing-vector representation rather than downloading a model automatically.

The repository currently includes an explicit knowledge-ingestion CLI with curated OWASP/CWE content. External CVE or Exploit-DB corpora are **not automatically ingested by the current implementation**.

### ⚡ Local-First LLM Routing

LLM generation follows a local-first routing strategy:

```text
Cache
  ↓
Local LLM
  ↓
Confidence / retrieval evaluation
  ↓
Optional cloud fallback
  ↓
Deterministic fallback engine
```

Supported cloud/provider boundaries include Gemini and an optional Grok-compatible provider.

The local provider boundary currently supports **Ollama**.

The deterministic fallback engine allows the system to continue operating without a cloud API key.

### 🛡️ Read-Only by Default

Each target has an independent operational access mode:

| Permission | Default | Purpose |
|---|---:|---|
| `authorized` | `false` | Explicit authorization to security-test the target |
| `READ_ONLY` | ✅ | Safe default operational mode |
| `allow_direct_patch_apply` | ❌ | Explicit permission to modify the live target |
| `allow_pr_creation` | ❌ | Explicit permission to create a GitHub remediation PR |
| `allow_branch_write` | ❌ | Explicit permission to create a remediation branch |
| `code_visibility` | `unknown` | Public/private/unknown repository visibility |

Read-only mode still permits discovery, scanning, attack execution, finding generation, remediation generation, reporting, and revalidation **without applying a live patch**.

Direct patch application requires both:

```text
access_mode = READ_WRITE
AND
allow_direct_patch_apply = true
```

PR creation is independently gated and does not require live target write access.

### 🔧 Remediation & Auto PRs

For confirmed findings, SwarmShield can generate a remediation artifact containing:

- vulnerability
- patch
- patch type
- summary
- root-cause explanation
- suggested change

When GitHub integration is explicitly configured and PR creation is permitted, SwarmShield can:

1. create a remediation branch
2. commit the remediation artifact
3. open a pull request
4. return the PR URL and metadata

**SwarmShield never auto-merges the PR.** Human review and merge remain required.

### 🔁 Revalidation

Revalidation is designed to verify remediation rather than simply changing a database status.

The flow can:

1. select the vulnerability's original successful attack
2. optionally apply the generated patch
3. replay the original winning payload
4. evaluate the new target response
5. record whether the vulnerability remains exploitable
6. update the vulnerability's revalidation status

For read-only targets, revalidation can still be performed with `apply=false` without writing to the target.

---

## Target Model

A target is registered with:

- name
- endpoint URL
- optional authentication header
- declared tools
- permission/security policy
- authorization attestation
- operational access mode
- code visibility
- remediation permissions

The generic target adapter sends:

```json
{
  "input": "attack payload"
}
```

and accepts common response shapes such as:

```json
{
  "output": "target response"
}
```

The adapter also supports common fields such as `response`, `text`, `message`, `reply`, and `content`.

This keeps the target interface intentionally thin so the platform can test different AI/agent endpoints.

---

## Security Policy Awareness

A target can declare security expectations through its `permission_map`.

Example:

```json
{
  "tools": {
    "execute_admin_action": {
      "restriction": "admin_only"
    },
    "send_email": {
      "restriction": "external_recipients_restricted"
    },
    "read_file": {
      "restriction": "restricted_paths",
      "restricted_paths": [
        "internal_notes.txt"
      ]
    }
  },
  "protected_resources": [
    "internal_notes",
    "customer_data",
    "confidential_pricing"
  ],
  "policies": [
    "no_unauthorized_tool_execution",
    "no_privilege_escalation",
    "no_confidential_exfiltration",
    "detect_prompt_injection"
  ]
}
```

The policy layer is deliberately lightweight. It is **not an RBAC system**. Its purpose is to give the Planner and Sentinel target-specific security context so confirmed findings can be explained against the target's own declared restrictions.

---

## Controlled Target

The repository includes an authorized local controlled target for demonstrations and development.

Architecture:

```text
User → LLM → RAG → Mock Tools
```

The controlled target intentionally models vulnerabilities such as:

- indirect prompt injection through retrieved content
- unsafe tool permissions
- sensitive information disclosure
- data exfiltration
- direct prompt injection

It exposes patch/reset hooks used by the revalidation workflow.

The controlled target runs locally and is designed for safe testing rather than testing an unrelated production system.

---

## User Interface

The current frontend is a React/Tailwind dashboard with a dark, glass-style security operations interface.

### Command Center

The dashboard provides a high-level view of:

- security score
- active agents
- registered targets
- vulnerabilities
- critical findings
- autonomous agent activity

![SwarmShield Command Center](docs/screenshots/dashboard.png)

### War Room & Live Siege

The siege workflow gives the scan a real-time operational view with:

- target status
- attack agents
- attack attempts
- discovered breaches
- battle plan
- battle log
- live scan state
- outcome navigation

![SwarmShield War Room](docs/screenshots/war-room.png)

![SwarmShield Live Siege](docs/screenshots/live-siege.png)

### Vulnerability Management

Confirmed vulnerabilities are grouped by severity and OWASP category, with evidence-driven finding details and a direct path into remediation.

![SwarmShield Vulnerabilities](docs/screenshots/vulnerabilities.png)

### Remediation / Patch Center

The Patch Center presents generated remediation work and routes it according to the target's configured permissions.

![SwarmShield Patch Center](docs/screenshots/patch-center.png)

---

## Main UI Areas

The frontend currently exposes the following operational areas:

- Dashboard
- AI Agents
- Targets / Realm Registry
- Vulnerabilities / Siege Report
- Patch Center / Remediation Forge
- Intelligence
- Reports
- War Room
- Live Siege
- Outcome
- War Log
- Auto PR
- Revalidation
- Settings

The siege-oriented screens use the project's terminology:

| UI term | Meaning |
|---|---|
| Realm | Registered target |
| Siege | Security scan |
| Fortress Integrity | Security/risk score |
| Breach | Confirmed vulnerability |
| Ward | Remediation |
| War Room | Pre-/during-scan operational view |
| Live Siege | Live campaign activity |

---

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React 18 |
| Styling | Tailwind CSS |
| Motion | Framer Motion |
| State | Zustand |
| Graph visualization | React Flow |
| Backend | FastAPI |
| ORM | SQLAlchemy |
| Database | PostgreSQL 16 |
| Live updates | Server-Sent Events |
| HTTP client | HTTPX |
| Cloud LLM | Google Gemini |
| Local LLM | Ollama |
| Local RAG | PostgreSQL + persisted embeddings |
| Optional repository integration | GitHub API |
| Containerization | Docker Compose |

---

## Repository Structure

```text
SwarmShield_v2/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── specialists/
│   │   │   ├── orchestrator.py
│   │   │   ├── planner.py
│   │   │   ├── remediation.py
│   │   │   └── sentinel.py
│   │   ├── api/routes/
│   │   ├── capability/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── controlled_target/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── docker-compose.yml
└── .env.example
```

---

## Running with Docker

### 1. Configure the environment

Copy the example environment file:

**Windows CMD**

```bat
copy .env.example .env
```

**PowerShell**

```powershell
Copy-Item .env.example .env
```

At minimum, the stack can run without a Gemini API key by using the deterministic fallback path.

Optional integrations include:

- Gemini
- Ollama/local LLM
- GitHub remediation PRs
- Grok-compatible cloud routing

### 2. Start the complete stack

```bash
docker compose up --build
```

The default services are:

| Service | Address |
|---|---|
| Frontend | `http://localhost:5173` |
| API | `http://localhost:8000` |
| Controlled target | `http://localhost:9100` |
| PostgreSQL | `localhost:5432` |

### 3. Stop the stack

```bash
docker compose down
```

To remove the PostgreSQL volume as well:

```bash
docker compose down -v
```

> Removing the volume deletes the local SwarmShield database and scan history.

---

## Local Frontend Development

From `frontend/`:

```bash
npm install
npm run dev
```

The Vite development server normally runs at:

```text
http://localhost:5173
```

Build the production frontend with:

```bash
npm run build
```

---

## Local Backend Development

Create and activate a Python virtual environment, install dependencies, configure PostgreSQL, and start FastAPI:

```bash
cd backend

python -m venv venv
```

**Windows**

```bat
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Environment Variables

Important configuration is loaded through environment variables.

### Core

```env
DATABASE_URL=postgresql+psycopg2://swarmshield:swarmshield@localhost:5432/swarmshield
```

### Gemini

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
```

### Local LLM

```env
LLM_PROVIDER=auto
LOCAL_LLM_ENABLED=true
LOCAL_LLM_PROVIDER=ollama
LOCAL_LLM_MODEL=
LOCAL_LLM_BASE_URL=http://localhost:11434
```

### RAG / Intelligence

```env
RAG_ENABLED=true
RAG_TOP_K=6
EMBEDDING_MODEL=all-MiniLM-L6-v2
MEMORY_ENABLED=true
LLM_CACHE_ENABLED=true
```

### GitHub Auto PR

```env
GITHUB_TOKEN=
GITHUB_REPO=
GITHUB_BASE_BRANCH=main
```

Use a least-privilege GitHub token appropriate to the single repository being remediated. SwarmShield does not store credentials in source code.

---

## API Surface

The backend exposes routes for:

- `/api/targets`
- `/api/scans`
- `/api/vulnerabilities`
- `/api/patches`
- `/api/scans/{scan_id}/stream`
- `/api/scans/{scan_id}/graph`
- `/api/scans/{scan_id}/memory`
- `/api/scans/{scan_id}/attack-dna`
- `/api/targets/{target_id}/capabilities`
- `/api/rag/search`
- `/api/memory/search`
- `/api/llm/health`
- vulnerability revalidation
- remediation PR operations

The exact route definitions live under:

```text
backend/app/api/routes/
```

FastAPI's interactive documentation is available when the API is running:

```text
http://localhost:8000/docs
```

---

## Operational Flow

A typical campaign is:

```text
1. Register target
       ↓
2. Declare / discover capabilities
       ↓
3. Confirm authorization
       ↓
4. Launch Siege
       ↓
5. Planner creates attack vectors
       ↓
6. Specialist agents execute attacks
       ↓
7. Sentinel evaluates evidence
       ↓
8. Successful attempts enter memory
       ↓
9. Failed attempts can mutate and retry
       ↓
10. Attack graph + risk are persisted
       ↓
11. Remediation is generated
       ↓
12. Optional PR / branch / direct patch
       ↓
13. Revalidation replays the winning attack
       ↓
14. Vulnerability becomes verified fixed
    or remains vulnerable
```

---

## Safety Model

SwarmShield is intentionally designed around explicit authorization and least privilege.

### Target authorization

A scan is rejected unless:

```text
authorized = true
```

### Live target writes

A live patch requires:

```text
access_mode = READ_WRITE
allow_direct_patch_apply = true
```

### GitHub PR creation

PR creation requires:

```text
allow_pr_creation = true
```

### Branch writes

Branch remediation requires:

```text
access_mode = READ_WRITE
allow_branch_write = true
```

These controls are enforced server-side. Frontend checkboxes do not grant permissions on their own.

---

## Testing

Backend tests are located under:

```text
backend/tests/
```

Run them with:

```bash
cd backend
pytest
```

Frontend production build:

```bash
cd frontend
npm run build
```

---

## Design Principles

SwarmShield is built around a few core principles:

1. **Attack real behavior, not just static configuration.**
2. **Treat target responses as evidence.**
3. **Use adaptive retries instead of repeating identical attacks.**
4. **Persist attack lineage and memory across the campaign.**
5. **Separate authorization to test from authorization to modify.**
6. **Keep remediation reviewable by humans.**
7. **Verify remediation by replaying the original exploit.**
8. **Prefer local inference and bounded cloud fallback where configured.**
9. **Keep retrieved security knowledge as data, never executable instructions.**
10. **Make the security state visible through an operational interface.**

---

## Disclaimer

SwarmShield is a security testing and research platform intended for **systems you own or have explicit authorization to test**.

Do not register or attack third-party systems without permission. The included controlled target exists specifically to provide a safe environment for demonstrations and development.

---

## License

Add the project's applicable license here before public distribution.
