# SwarmShield — Reconciliation & Build Plan
(Based on actual inspection of both repos, not the READMEs)

## What each repo actually is

**Repo A** (`SaumyajitDas001/SwarmShield`, ~1,230 backend LOC)
Strong data/reasoning layer, weak execution:
- `models.py` — clean SQLAlchemy schema: targets, campaigns, events, **findings**,
  **attack_dna** (genome + mutations + success_probability), **finding_consensus**.
  This is a better schema than Repo B's for DNA/consensus/risk.
- `memory/manager.py` — typed `MemoryItem` (DISCOVERY/SUCCESS/FAILURE/CAPABILITY/
  TOOL/VULNERABILITY/ATTACK_PATTERN) with validation + lexical retrieval. Real,
  usable shared-memory primitive.
- `mutation.py` — a *safe, enumerated* mutation vocabulary (context/role/format/
  multi-turn/indirect-delivery variation) rather than free-form LLM mutation.
  Good for auditability, but shallow — it only relabels genome fields, it
  doesn't generate new payload text.
- `graph/chain.py` — builds an evidence graph (nodes/edges) from attempts +
  memories + findings. Real and reusable.
- `orchestrator.py` — **does not execute anything locally**. It HMAC-signs a
  payload and POSTs it to an n8n webhook (`swarmshield-campaign-start`) and
  returns. All actual attack execution is delegated outside the repo.
- `adapters/demo.py` — the only target adapter present is `DemoTargetAdapter`,
  which **never makes a network call** and returns a hardcoded synthetic
  string. There is no real controlled target here.
- Net effect: Repo A's "attack execution" is faked/delegated; its data model,
  memory, mutation vocabulary, and evidence graph are real and good.

**Repo B** (`Sunanda02/swarmshield`, ~1,530 backend LOC)
Strong execution, thinner reasoning/evidence layer:
- `agents/orchestrator.py` — a real local loop: Planner → specialist →
  `TargetClient.send()` → Sentinel → persist `AttackLog` (+`Vulnerability` on
  success) → on failure, feed Sentinel's `mutation_hint` back to the same
  specialist and retry with `parent_attempt_id`/`generation` incremented.
  This is the actual adaptive attack loop the spec asks for.
- `services/gemini_client.py` — real `google-genai` wrapper (system
  instruction + JSON mode). Every agent (planner, sentinel, 5 specialists)
  calls through it.
- `services/target_client.py` — generic `POST {"input": payload}` HTTP
  client with pluggable output extraction. Works against any HTTP target.
- `agents/sentinel.py` — well-written judge prompt: takes payload +
  target_response, returns `{violation_detected, violation_type, confidence,
  reasoning, severity, mutation_hint}`. This *is* the evidence-backed
  verdict mechanism (evidence = the persisted target_response string).
- `mock_target.py` (repo root) — trivial: `POST /chat` echoes the prompt
  back. **No RAG, no tools, no injectable content, no vulnerability at
  all.** This is the "do not fake" gap the task calls out explicitly.
- No Attack DNA table, no shared-memory table, no attack-graph builder, no
  remediation/re-validation code exists in Repo B at all — `patches.py` /
  `remediation.py` exist as route/agent stubs oriented around static-patch
  suggestions, not re-validation.

## Component-by-component decision

| Component | Winner | Why |
|---|---|---|
| DB models — targets/campaigns/scans | **B**, renamed to A's nouns | B's `ScanRun`/`TargetProfile` are what's actually populated by real execution |
| DB models — attack_dna, memory, consensus | **A** | Only A has these tables at all |
| Attack log / attempt record | **B**'s `AttackLog` (parent_attempt_id, generation) merged with **A**'s evidence fields | B already models mutation lineage; A adds evidence/confidence/risk_score fields B lacks |
| Agent framework / base agent | **B** | Actually calls an LLM; A's `agents/base.py` is a thinner scaffold |
| Planner | **B** | Only real implementation |
| Sentinel | **B**'s prompt/verdict shape, **A**'s evidence-graph linkage | B's judge logic is solid; route its verdict into A's `FindingRecord`/`graph/chain.py` instead of B's thinner `Vulnerability` model |
| Specialist agents (5) | **B** | Only implementation; keep all 5, harden the 3 priority ones first (prompt injection, RAG/indirect injection, tool abuse) |
| Target client | **B** | Generic, works today |
| **Controlled target** | **Neither — build new** | A fakes it (synthetic, no network), B doesn't implement it (echo bot, no RAG/tools/vuln). Delivered below. |
| Shared memory | **A**, wired into B's orchestrator loop | A has the only real implementation; B's loop needs a `memory.write()`/`memory.retrieve_relevant()` call inserted after each Sentinel verdict, and specialists need to consult it before generating a payload |
| Attack DNA / mutation | **A**'s genome+mutation vocabulary, driven by **B**'s `mutation_hint` | Use B's Sentinel `mutation_hint` (real signal from a real failed attempt) to choose which of A's enumerated mutation types to apply, instead of A's current disconnected mutation.py |
| Attack graph | **A**'s `graph/chain.py` | Only implementation; feed it B's real `AttackLog`/`Vulnerability` rows instead of A's synthetic data |
| Risk scoring | **Build new (small)** | Neither repo has a real aggregate risk calculation; A has a `risk_score` *field* with nothing populating it, B computes a rough per-scan aggregate in the orchestrator only |
| Remediation | **Extend B's `remediation.py` agent** | It's a stub oriented the right way (LLM-generated patch suggestion per finding); needs prompting improvements, not a rewrite |
| Re-validation | **Build new** | Not implemented in either repo. Needed: re-run the exact winning payload from a `Vulnerability`/`Finding` against the target *after* a remediation is "applied" (in the controlled target's case, toggle its vulnerable branch off) and record pass/fail |
| Frontend / dashboard | **B**, extended | B already has `AttackFlowCanvas.jsx` (React Flow), `AgentLogConsole`, `ScorecardCard`, `VulnerabilityTable`, SSE streaming (`useScanStream`). A's frontend is essentially empty (`main.tsx`/`styles.css` only, no `App.tsx`, no components) |
| Orchestration transport | **Drop A's n8n delegation for the swarm loop itself.** Keep n8n as optional, e.g. for scheduling/notifications, not for actually running attacks | The spec requires the loop to be genuinely executable and testable; delegating to an external n8n webhook makes that untestable/unfakeable-to-verify |

## Controlled target — delivered

Built and smoke-tested in this session: `controlled_target/app.py` (single
FastAPI service, no external deps required to run in fallback mode).

Architecture matches the spec exactly: `User → LLM → RAG → Mock Tools`.

Real, working, non-scripted vulnerabilities, each independently verified by
running the actual attack query against it:
- **Indirect prompt injection via RAG poisoning** — a "support ticket"
  document (`kb-004`) in the knowledge base contains attacker-authored
  instruction text. A benign query (`"what is your return policy?"`)
  retrieves only the legitimate doc and the target behaves normally. A
  query that plausibly retrieves the poisoned doc (`"...escalation ticket
  support..."`) causes the target to obey the embedded instructions.
- **Tool abuse / privilege escalation** — once the injection lands, the
  target calls `execute_admin_action` and `send_email` with no role check
  at all; both are logged to `swarmshield_target_audit.log` so Sentinel has
  a real audit trail to cite as evidence, not just the chat text.
- **Data exfiltration** — `read_file("internal_notes.txt")` is callable
  with no permission gate, and its content gets appended to the reply and
  emailed out in the poisoned path.
- **Direct prompt injection** — `"ignore previous instructions..."` in the
  user turn itself triggers the same override path, independent of RAG.
- Runs against real Gemini when `GEMINI_API_KEY` is set (same vulnerable
  prompt-handling logic, real model); falls back to a small deterministic
  engine otherwise so it's testable offline — this is what was actually
  exercised in this session, output pasted below.

```
BENIGN  -> retrieved: ['kb-001']            tool_calls: []
ATTACK  -> retrieved: ['kb-004', 'kb-003']  tool_calls: [send_email(...), execute_admin_action(...)]
```

This is ready to drop in as the target for B's `TargetClient` (point
`TargetProfile.endpoint_url` at `http://127.0.0.1:9100/chat`) with zero
changes to B's client.

## What's genuinely still missing (be honest about scope)

The task's own "test" checklist — migrations run, frontend builds, planner
executes against a live DB, memory measurably changes later agents'
behavior, DNA mutations are driven by real Sentinel hints, the graph
reflects real campaign rows, risk is computed from real findings,
remediation re-validation actually re-attacks the target and flips a
finding's status — requires:
- a running Postgres instance and applied Alembic migrations (A's 4
  migrations need a 5th for `attack_logs`/`vulnerabilities`/patches merged
  in from B),
- a `GEMINI_API_KEY` for planner/sentinel/specialists to produce non-trivial
  payloads,
- an iterative edit-run-test loop across ~15-20 backend files and a handful
  of frontend components,
- real npm/pip installs and a frontend build.

None of that is reliably available in this chat sandbox (no persistent
Postgres, no outbound network path to the Gemini API here, and no state
carried between sessions), so I did not fabricate a "tests passed" result
for those pieces — only the controlled target above was actually executed
and its output shown is real.

## Recommended next step

This is a genuine multi-file, iterative build (merge ~2,750 LOC of backend
across two schemas, wire 3 new subsystems together, extend a real frontend,
run real migrations against a real DB, and re-test after each change). That
class of work is a much better fit for **Claude Code** working directly in
your cloned repos on your machine — it can run Postgres/Docker, use your
real `GEMINI_API_KEY`, and actually execute the "Test" checklist from your
prompt end-to-end across a long session, rather than a single chat reply.

Suggested sequence for that session, in order:
1. Fork B's backend as the base (`app/`, migrations rewritten to match B's
   models). Add A's `attack_dna`, `agent_memory`/memory items, and
   `finding_consensus` tables alongside B's `scan_runs`/`attack_logs`.
2. Drop in `controlled_target/app.py` from this session as
   `backend/controlled_target/`, add it to `docker-compose.yml`.
3. Wire A's `memory/manager.py` into B's `orchestrator.py`: after each
   Sentinel verdict, write a `MemoryItem`; before each specialist call,
   `retrieve_relevant()` and inject into its prompt.
4. Replace B's ad-hoc retry with A's `mutation.py` vocabulary, selected by
   Sentinel's `mutation_hint` (simple keyword→mutation_type mapping to
   start).
5. Feed real `AttackLog`/`Vulnerability`/memory rows into A's
   `graph/chain.py`; expose as a `/campaigns/{id}/graph` route for
   `AttackFlowCanvas.jsx`.
6. Add a small `risk.py` (severity × confidence × exposure, aggregated per
   campaign) — genuinely new code, not present in either repo.
7. Add `revalidation.py`: given a `Finding`, re-send its exact winning
   payload through `TargetClient` after remediation is "applied" and
   flip `status` based on the new Sentinel verdict.
8. Extend B's dashboard with panels for memory, DNA, risk, remediation,
   re-validation (component shells only need to exist for the 5 that are
   currently missing: everything except attack flow, log console,
   scorecard, vuln table).
9. Run the checklist from the prompt top to bottom, in that order, fixing
   as you go.
