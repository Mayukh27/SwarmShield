# Capability Intelligence Engine — Build Progress

## Status: Phase 5 update (this session)

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
