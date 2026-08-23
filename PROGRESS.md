# Capability Intelligence Engine — Build Progress

## Status: Phase 6 update (this session)

Phase 5 (previous session) added persistence, diff, and approve/skip.
This phase closes the two gaps Phase 5 explicitly flagged as open, plus
one gap found by re-reading spec sections 15 and 21/47 against the actual
code rather than the summary: no weighted priority formula existed (just
a flat risk bucket), no multi-hop (3+) attack-path search existed (only
pairwise), and none of the spec's `CAPABILITY_*` settings existed at all.

### Added/changed this session (real, tested)
- `capability/prioritizer.py` (new) — the actual weighted formula from
  spec section 21 (`capability_risk + boundary_risk + authorization_risk
  + data_sensitivity + historical_signal + novelty + coverage_gap -
  previous_failure_penalty`, all inputs normalized to 0-100, weights
  configurable via `Settings`), replacing the flat `_priority_from_risk`
  bucket that `hypotheses.py` used previously.
- `capability/hypotheses.py` — rewritten to call the prioritizer, and to
  actually populate `authorization_requirements`, `mutation_context`,
  `fingerprint`, and the new `priority_breakdown` fields on
  `AttackHypothesis`, all of which existed on the dataclass already but
  were never set.
- `capability/models.py` — `AttackHypothesis` gained `priority_breakdown`
  (the per-factor score dict, for the decision trace UI, spec section
  34); `to_dict()` also now includes `mutation_context`, which it was
  silently dropping before.
- `capability/attack_paths.py` — added bounded multi-hop chain discovery
  (`_walk_multi_hop`, DFS over the same CAN_CHAIN adjacency, capped by
  `CAPABILITY_MAX_DEPTH`) so chains like the spec's own example
  ("search -> read -> send forms an exfiltration path") are actually
  discoverable, not just pairwise 2-hop chains.
- `services/capability_service.py` — now accepts an optional `db`
  session. When present: `_memory_signals_for_target()` queries
  `AgentMemory` by `target_fingerprint` (joined on `str(target.id)`, the
  same key the adaptive attack loop already writes in
  `orchestrator.py` — not the capability-hash fingerprint, which shifts
  whenever the tool surface changes slightly and would rarely match) and
  turns prior successes/failures into `MemorySignal`s consumed by the
  prioritizer (spec section 25: memory now actually influences
  prioritization, not just gets computed and ignored).
  `_enrich_top_hypotheses_with_rag()` attaches RAG-sourced document
  titles to the top `CAPABILITY_RAG_ENRICH_TOP_K` hypotheses only (spec
  section 26, bounded per section 38). Both are best-effort: any
  exception degrades to "no signal" rather than failing analysis.
  Also respects the new `CAPABILITY_INTELLIGENCE_ENABLED` /
  `CAPABILITY_RUNTIME_OBSERVATION` / `CAPABILITY_MAX_PATHS` /
  `CAPABILITY_MAX_HYPOTHESES` settings instead of hardcoded defaults.
- `core/config.py` — added the `CAPABILITY_*` settings block from spec
  section 47 (none of it existed before), plus the 8 configurable
  priority weights.
- `agents/orchestrator.py` — **bug fix**: both capability-intelligence
  call sites now wrap the call in `try/except` and emit a
  `capability_scan_warning` event on failure instead of letting an
  exception in this enrichment layer take the whole scan down (this was
  a real gap against spec section 20/37 — "Capability Intelligence
  failure -> existing attack taxonomy", "must never crash the scan").
  Both call sites now also pass `db=db` so memory/RAG enrichment
  actually runs during real scans, not just on-demand API reads.
- `api/routes/capabilities.py` — the two `analyze_target_capabilities()`
  call sites here were also missing `db=db` (meaning live `GET
  /targets/{id}/capabilities` reads never got memory/RAG enrichment even
  though the orchestrator did) — fixed.
- Frontend (`Intelligence.jsx`): hypothesis detail view now shows the
  priority breakdown as a small bar chart per factor, authorization
  requirements, RAG-sourced "related security guidance" references
  (parsed out of `context_sources`), and a compact "history: N✓/M✗" badge
  on the collapsed row when a hypothesis has prior attempts on this
  target. Attack paths show an explicit "N-HOP" badge so multi-hop
  chains are visually distinct from direct/pairwise ones. A
  "Memory-Informed" stat chip appears when `memory_informed_count > 0`.
  A disabled/unavailable banner renders if `analysis.enabled === false`
  instead of silently showing an empty board.

### Verified in this environment
- `pytest backend/tests/` -> 37 passed (up from the prior baseline of
  22 pure-logic tests; 15 new tests added in
  `tests/test_capability_prioritizer.py` covering the prioritizer
  formula's bounds/monotonicity, multi-hop path discovery, the
  memory-bridge aggregation logic with a fake DB, and the previously-dead
  hypothesis fields). Same 1 pre-existing failure + 23 pre-existing
  errors as before, all `psycopg2.OperationalError: connection refused`
  against `localhost:5433` -- no live Postgres in this sandbox, unrelated
  to this session's changes and unchanged from the prior baseline.
- End-to-end smoke test of `analyze_target_capabilities()` against a
  4-tool target mirroring the spec's own demo scenario (section 43):
  produced 4 capabilities, 4 correctly-prioritized hypotheses with full
  breakdown dicts, and a stable fingerprint, all without touching a DB.
- `app.main` imports cleanly and `app.openapi()` still lists all 10
  `/targets/{id}/capabilities...` routes after the `db=db` fix.
- `esbuild` transform-checked `Intelligence.jsx` (24.5kb output, no
  errors) after the UI changes -- syntax check only, not a real Vite
  build or a rendered-in-browser check (same caveat as Phase 5, this
  sandbox's `node_modules` is Windows-built).

### Explicitly still missing (be honest about scope)
- **Never run against a live database or a live Gemini/local LLM.** Same
  limitation as every prior phase in this sandbox. The memory-bridge
  logic is unit-tested against a fake DB object at the query-shape
  boundary, not against real Postgres/JSONB round-trip behavior.
- The historical-signal join is deliberately coarse (per-target,
  per-specialist-namespace), not per-exact-capability-and-strategy the
  way `strategy_seen()` is for the live adaptive loop. That's a
  reasonable scope call (spec doesn't require exact-match retrieval for
  *prioritization*, only for the *skip-if-already-failed* dedup, which
  `strategy_seen()` already handles separately) but worth knowing.
- `CAPABILITY_LLM_ENABLED` / `CAPABILITY_MAX_LOCAL_LLM_CALLS` settings
  are defined (spec section 47 asks for them) but nothing in the
  capability pipeline calls an LLM yet -- extraction/classification/
  hypothesis generation are still fully deterministic, which is
  spec-compliant (section 28: "deterministic first... use the LLM only
  for ambiguous descriptions/semantic classification/attack-hypothesis
  reasoning") but means these two settings are inert until an LLM path
  is added for genuinely ambiguous tool descriptions the keyword
  classifier can't confidently categorize.
- `docs/CAPABILITY_INTELLIGENCE.md` still not written, per explicit
  instruction this session to skip document/text generation and focus
  on implementation + necessary tests only.

## Next phase
The two items above worth doing next, in order: (1) an LLM fallback path
in `classifier.py` for tool descriptions that land as `UNKNOWN_CAPABILITY`
with low confidence, gated by `CAPABILITY_LLM_ENABLED` and routed through
the existing `LLMRouter` (never a second client, per spec section 27);
(2) a real Postgres run of a full scan end-to-end to confirm the
memory-bridge query shape holds up against actual JSONB rows, which
nothing in this sandbox has been able to verify yet.

## Status: Phase 5 update (previous session)

Phase 4 (previous session) added the coverage engine, target fingerprint,
capability-specific events, and granular read endpoints. This phase adds
the persistence layer that Phase 4 flagged as the blocking piece for
diff/approve/skip.

### Added this session (real, tested)
- `backend/app/models/capability.py` — two new tables:
  `capability_records` (one row per CapabilityFrame, snapshotted at the
  end of a scan) and `attack_hypothesis_records` (one row per
  AttackHypothesis, with a `status` column an operator can move from
  `pending` to `approved`/`skipped`). Registered in `app/models/__init__.py`
  so `init_db()`'s `Base.metadata.create_all()` creates them automatically
  on next backend startup -- no manual migration step needed, consistent
  with how every other table in this repo is created (no Alembic here).
- `backend/app/services/capability_persistence.py` — `persist_analysis()`
  (writes the snapshot), `diff_capabilities()` (compares a scan's
  snapshot against either an explicit prior scan or the most recent other
  snapshot for the same target), `set_hypothesis_status()` and
  `list_hypotheses()` for the approve/skip flow.
- `agents/orchestrator.py` — after the post-scan capability re-analysis
  (added in Phase 4) now calls `capability_persistence.persist_analysis()`
  so every completed scan leaves a durable capability snapshot behind.
- `api/routes/capabilities.py` — four new endpoints:
  `GET /targets/{id}/capabilities/diff?scan_id=...` (404 with a clear
  message if there's no prior scan to diff against yet -- not a silent
  empty diff), `GET /targets/{id}/capabilities/hypotheses/records`
  (persisted hypotheses + their decision status, distinct from the
  live-recomputed `/hypotheses`), and
  `POST .../hypotheses/{id}/approve` / `.../skip`.
- Frontend (`Intelligence.jsx`): a "Changed Since Last Siege" section
  (added/removed/changed capabilities vs the target's last completed
  scan, only rendered once a baseline exists) and Approve/Skip buttons
  on each hypothesis, with the decided status shown both on the
  collapsed row and inside the expanded detail. `lib/api.js` gained the
  four corresponding client calls.

### Verified in this environment
- `pytest backend/tests/...` -> still 17/17 (this phase didn't touch the
  pure analysis pipeline, only added a persistence layer around it).
- Imported the full FastAPI app (`app.main`) in this sandbox after
  installing its direct dependencies (sqlalchemy, psycopg2-binary,
  fastapi, sse_starlette, pydantic-settings) -- it built its OpenAPI
  schema successfully and all 10 `/targets/{id}/capabilities...` routes
  are registered correctly, including the 4 new ones. This confirms the
  new models/service/routes import cleanly and don't collide with any
  existing table or route name; it does NOT confirm runtime behavior
  against a live Postgres, since none is available here.
- `app.models` imports cleanly and `Base.metadata.tables` shows both new
  tables (`capability_records`, `attack_hypothesis_records`) alongside
  every pre-existing table, with no name collisions.
- Syntax-checked the three edited/new frontend files
  (`Intelligence.jsx`, `lib/api.js`, `AgentLogConsole.jsx`) with a
  freshly-installed Linux `esbuild` (the repo's bundled `node_modules`
  is Windows-built and won't run here, same issue as the Python venv) --
  all three transform cleanly as JSX/JS. This is a syntax check, not a
  real Vite build or a rendered-in-browser check.

### Explicitly still missing (be honest about scope)
- **Never actually run against a live database.** No Postgres is
  reachable from this sandbox, so `persist_analysis`/`diff_capabilities`/
  `set_hypothesis_status` have been read carefully and unit-tested at the
  pure-Python boundary they call into, but the actual SQL round-trip
  (insert, commit, query back, JSONB round-trip) has not been executed.
  Run a real scan against your Postgres instance and check
  `/api/targets/{id}/capabilities/diff?scan_id=...` after a second scan
  completes to confirm.
- `persist_analysis` currently writes a fresh snapshot every time it's
  called (once per scan, from the orchestrator) -- it does not attempt to
  deduplicate or update in place, which is deliberate (spec section 30:
  don't silently discard evidence) but means the tables will grow one row
  per capability/hypothesis per scan with no pruning. Fine for a
  hackathon/demo volume; worth a retention policy before heavy production
  use.
- Prioritization is still the simple risk-bucket function in
  `hypotheses.py`, not the full configurable weighted formula in spec
  section 21.
- RAG/persistent-memory still don't feed *into* hypothesis generation
  itself (spec sections 25-26) -- the fingerprint added in Phase 4 is
  there to support this but nothing consumes it yet for that purpose.
- `docs/CAPABILITY_INTELLIGENCE.md` still not written, per your
  instruction to skip unnecessary document generation -- this file
  remains the running record.

## Next phase
With persistence in place, the natural next step is actually wiring the
fingerprint into `memory_service` so a new scan's hypothesis generation
can retrieve prior experience for the *same* target fingerprint (spec
section 25) before falling back to generic retrieval -- that's the one
piece from the original spec that meaningfully changes hypothesis output,
as opposed to exposing more of what's already computed.
