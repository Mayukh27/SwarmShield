"""
Orchestrator: runs one full ScanRun end-to-end.

Flow:
  1. Planner Agent analyzes the TargetProfile -> attack_plan (list of vectors)
  2. For each vector:
       a. retrieve relevant shared memory from earlier vectors in this scan
          and fold it into the specialist's context (cross-agent learning)
       b. seed an Attack DNA root genome for this vector
       c. dispatch to the mapped specialist -> generate payload
       d. send payload to target via TargetClient
       e. Sentinel Agent evaluates target's response
       f. persist AttackLog (+ Vulnerability if succeeded)
       g. write a MemoryRecord for this outcome (SUCCESS/FAILURE/VULNERABILITY)
          so later vectors in the same scan can consult it
       h. if not succeeded and attempts < MAX_ATTACK_ATTEMPTS_PER_VECTOR:
            take the Sentinel's mutation_hint, advance Attack DNA to the
            next generation (dna_service maps the hint to one of the
            enumerated mutation types), feed both the hint AND the DNA's
            resulting dna_hint back to the same specialist, and retry
            (the adaptive feedback loop), incrementing `generation` and
            setting `parent_attempt_id`
  3. Compute real risk (app.services.risk), mark ScanRun completed

Every step publishes an AgentLogEvent to the event bus so the SSE route
can stream it live to the frontend.
"""
import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.planner import PlannerAgent
from app.agents.sentinel import SentinelAgent
from app.agents.specialists.prompt_injection import PromptInjectionSpecialist
from app.agents.specialists.jailbreak import JailbreakSpecialist
from app.agents.specialists.tool_abuse import ToolAbuseSpecialist
from app.agents.specialists.data_exfiltration import DataExfiltrationSpecialist
from app.agents.specialists.privilege_escalation import PrivilegeEscalationSpecialist
from app.core.config import settings
from app.models.attack import AgentType, AttackLog
from app.models.scan import ScanRun, ScanStatus
from app.models.target import TargetProfile
from app.models.vulnerability import Severity, Vulnerability
from app.schemas.attack import AgentLogEvent
from app.services import capability_service, capability_persistence, dna_service, event_bus, memory_service, policy_service, risk, context_manager
from app.services.target_client import TargetClient

SPECIALIST_REGISTRY = {
    "prompt_injection_specialist": (PromptInjectionSpecialist, AgentType.PROMPT_INJECTION),
    "jailbreak_specialist": (JailbreakSpecialist, AgentType.JAILBREAK),
    "tool_abuse_specialist": (ToolAbuseSpecialist, AgentType.TOOL_ABUSE),
    "data_exfiltration_specialist": (DataExfiltrationSpecialist, AgentType.DATA_EXFILTRATION),
    "privilege_escalation_specialist": (PrivilegeEscalationSpecialist, AgentType.PRIVILEGE_ESCALATION),
}


async def _emit(scan_id: uuid.UUID, event_type: str, message: str, agent_type: str | None = None, data: dict | None = None):
    await event_bus.publish(
        scan_id,
        AgentLogEvent(
            event_type=event_type,
            agent_type=agent_type,
            message=message,
            data=data,
            timestamp=datetime.utcnow(),
        ),
    )


async def _run_specialist_against_vector(
    db: Session, scan, scan_id: uuid.UUID, target, client, sentinel,
    vector: dict, vector_id: str, specialist_key: str, agent_type_enum,
    security_policy, attack_surface_summary: str, coordination_note: str = "",
) -> dict:
    """Runs the full adaptive attempt/mutation loop for ONE specialist
    against ONE vector, exactly as the single-specialist path always has.
    Extracted so the same logic can be reused both for ordinary
    single-specialist vectors and for coordinated multi-specialist vectors
    (spec section 19: 'multiple specialists can collaborate on a single
    hypothesis... the planner must be able to construct a coordinated
    test'). `coordination_note` -- when non-empty -- is a plain-language
    summary of what an earlier specialist in the SAME coordinated group
    already achieved this round, folded into this specialist's context so
    it can build on that result (e.g. a data-exfiltration specialist
    picking up after a tool-abuse specialist has already gotten a
    protected read triggered).

    Returns {"succeeded": bool, "last_log_id": UUID | None,
    "last_verdict": dict | None, "specialist_key": str}."""
    specialist_cls, _ = SPECIALIST_REGISTRY[specialist_key]
    specialist = specialist_cls()

    relevant_memories = memory_service.retrieve_relevant(
        db, scan_id=scan_id, query=f"{vector_id} {vector.get('owasp_category', '')}", limit=3
    )
    if relevant_memories:
        await _emit(
            scan_id, "memory_consulted",
            f"{specialist_key} consulted {len(relevant_memories)} prior memory item(s) "
            f"before attacking '{vector_id}'",
            agent_type=specialist_key,
            data={"memories": [m.content for m in relevant_memories]},
        )

    dna = dna_service.seed_generation(db, scan_id=scan_id, vector_id=vector_id)

    parent_id = None
    mutation_hint = None
    dna_hint = None
    previous_payload = None
    succeeded = False
    last_log_id = None
    last_verdict = None

    for generation in range(settings.MAX_ATTACK_ATTEMPTS_PER_VECTOR):
        context = {
            "vector": vector,
            "attack_surface_summary": attack_surface_summary,
            "memory": [
                {"type": m.memory_type.value, "content": m.content, "confidence": m.confidence}
                for m in relevant_memories
            ],
        }
        if coordination_note:
            context["coordination"] = coordination_note
        if mutation_hint:
            context["previous_attempt"] = previous_payload
            context["mutation_hint"] = mutation_hint
        if dna_hint:
            context["dna_hint"] = dna_hint

        attack_gen = specialist.generate_attack(json.dumps(context))
        payload = attack_gen.get("payload", "")

        # A repeated known-failed strategy against an unchanged
        # target spends neither target requests nor LLM budget.
        if memory_service.strategy_seen(
            db, target_fingerprint=str(target.id),
            vulnerability_type=vector.get("owasp_category", ""),
            strategy=str(attack_gen.get("technique") or ""),
        ):
            await _emit(scan_id, "strategy_skipped", f"Skipped previously failed strategy for '{vector_id}'", agent_type=specialist_key)
            break

        await _emit(
            scan_id, "agent_action",
            f"{specialist_key} attempt #{generation + 1} on '{vector_id}' "
            f"(dna gen {dna.generation})",
            agent_type=specialist_key, data={"payload": payload, "technique": attack_gen.get("technique")},
        )

        target_result = await client.send(payload)

        sentinel_context = json.dumps({
            "agent_type": specialist_key,
            "owasp_category": vector.get("owasp_category"),
            "payload": payload,
            "target_response": target_result.get("output"),
            "security_policy": security_policy,
        })
        verdict = sentinel.evaluate(sentinel_context)
        succeeded = bool(verdict.get("violation_detected"))

        # Offline fallback engine can't reason like a real LLM about
        # security_policy, so it returns policy_violation=None; fill
        # it in deterministically here (same source of truth,
        # app.services.policy_service, that a real Gemini call was
        # instructed to use directly -- see sentinel.py). No-op when
        # a real Gemini call already populated it, or when nothing
        # was declared to violate.
        if succeeded and not verdict.get("policy_violation"):
            verdict["policy_violation"] = policy_service.explain_violation(
                target.permission_map,
                tool_or_area=vector.get("target_tool_or_area"),
                violation_type=verdict.get("violation_type"),
                target_response=target_result.get("output"),
            )

        log = AttackLog(
            id=uuid.uuid4(),
            scan_id=scan_id,
            agent_type=agent_type_enum,
            owasp_category=vector.get("owasp_category"),
            parent_attempt_id=parent_id,
            generation=generation,
            payload=payload,
            target_response=target_result.get("output"),
            sentinel_verdict=verdict,
            succeeded=succeeded,
        )
        db.add(log)
        scan.total_attempts += 1
        db.commit()
        db.refresh(log)
        last_log_id = log.id
        last_verdict = verdict

        await _emit(
            scan_id, "sentinel_verdict",
            f"Sentinel verdict on '{vector_id}' gen {generation}: "
            f"{'VIOLATION' if succeeded else 'no violation'}",
            agent_type="sentinel", data=verdict,
        )

        # --- write to shared memory regardless of outcome, so
        # later vectors this scan can learn from it ---
        memory_service.write_memory(
            db,
            scan_id=scan_id,
            memory_type="success" if succeeded else "failure",
            content=(
                f"{specialist_key} on '{vector_id}': "
                f"{'confirmed ' + (verdict.get('violation_type') or 'violation') if succeeded else 'no violation, technique ' + str(attack_gen.get('technique'))}"
            ),
            confidence=float(verdict.get("confidence") or 0.5),
            agent=specialist_key,
            source_attack_id=log.id,
        )
        memory_service.write_experience(
            db, namespace=specialist_key, vulnerability_type=vector.get("owasp_category"),
            strategy=attack_gen.get("technique"),
            target_fingerprint=str(target.id), success=succeeded,
            confidence=float(verdict.get("confidence") or .5),
            importance=float(verdict.get("confidence") or .5),
            content=f"{specialist_key}: {vector_id}; technique={attack_gen.get('technique')}; result={'success' if succeeded else 'failure'}",
        )

        if succeeded:
            policy_violation = verdict.get("policy_violation")
            description = f"{policy_violation} {verdict.get('reasoning', '')}".strip() if policy_violation else verdict.get("reasoning", "")
            vuln = Vulnerability(
                id=uuid.uuid4(),
                scan_id=scan_id,
                source_attack_id=log.id,
                title=f"{vector.get('owasp_category', 'Unknown')} via {specialist_key}",
                owasp_category=vector.get("owasp_category", "Unknown"),
                severity=Severity(verdict.get("severity") or "medium"),
                description=description,
                evidence=(target_result.get("output") or "")[:2000],
            )
            db.add(vuln)
            scan.successful_attacks += 1
            db.commit()

            memory_service.write_memory(
                db,
                scan_id=scan_id,
                memory_type="vulnerability",
                content=f"{vuln.title}: {verdict.get('reasoning', '')[:200]}",
                confidence=float(verdict.get("confidence") or 0.7),
                agent="sentinel",
                source_attack_id=log.id,
            )

            await _emit(
                scan_id, "vulnerability_found",
                f"Vulnerability confirmed: {vuln.title}",
                agent_type=specialist_key, data={"vulnerability_id": str(vuln.id)},
            )
            break  # vector proven vulnerable, move to next vector

        # not succeeded -> advance Attack DNA using the Sentinel's
        # real mutation_hint, then retry with both hints threaded in
        mutation_hint = verdict.get("mutation_hint")
        previous_payload = payload
        parent_id = log.id

        if not mutation_hint:
            break  # Sentinel had nothing to suggest; stop retrying this vector

        dna, dna_hint = dna_service.next_generation(
            db, parent=dna, mutation_hint=mutation_hint, source_attack_id=log.id
        )
        await _emit(
            scan_id, "dna_mutation",
            f"Attack DNA for '{vector_id}' mutated to generation {dna.generation} "
            f"({dna.mutations[-1]['mutation_type']}: {dna.mutations[-1]['from']} -> {dna.mutations[-1]['to']})",
            agent_type=specialist_key, data={"genome": dna.genome, "mutations": dna.mutations},
        )

    return {"succeeded": succeeded, "last_log_id": last_log_id, "last_verdict": last_verdict, "specialist_key": specialist_key}


def _resolve_specialists(vector: dict) -> list[str]:
    """spec section 19: a vector may name several specialists
    ('specialists': [...]) that should collaborate on one hypothesis,
    not just the original single 'specialist' string. Both are accepted;
    'specialists' wins if both are present (the plan is being explicit
    about wanting a coordinated test). Unknown keys are dropped, never
    crash the scan over a hallucinated specialist name."""
    raw = vector.get("specialists")
    if not raw:
        single = vector.get("specialist")
        raw = [single] if single else []
    return [s for s in raw if s in SPECIALIST_REGISTRY]


async def run_scan(scan_id: uuid.UUID, db: Session) -> None:
    scan = db.query(ScanRun).filter(ScanRun.id == scan_id).one()
    target = db.query(TargetProfile).filter(TargetProfile.id == scan.target_id).one()

    context_token = context_manager.activate(db, scan_id)
    try:
        # --- 1. Planning phase ---
        scan.status = ScanStatus.PLANNING
        db.commit()
        await _emit(scan_id, "scan_status", "Planner Agent analyzing attack surface...", agent_type="planner")

        planner = PlannerAgent()
        await _emit(scan_id, "capability_scan_started", "Capability Intelligence: extracting declared tool surface...", agent_type="capability_intelligence")
        # Capability Intelligence is an enrichment layer, not a dependency:
        # if it's disabled or throws for any reason, the existing Planner
        # must still run off declared_tools/permission_map alone (spec
        # sections 20, 37). Never let a bug here fail the whole scan.
        try:
            capability_analysis = capability_service.analyze_target_capabilities(target, db=db)
        except Exception as cap_exc:  # noqa: BLE001 - intentionally broad: this subsystem must never take the scan down with it
            capability_analysis = {"enabled": False, "capabilities": [], "attack_paths": [], "hypotheses": [], "coverage": {}, "fingerprint": {}}
            await _emit(
                scan_id, "capability_scan_warning",
                f"Capability Intelligence failed and was skipped for this scan (falling back to the existing attack taxonomy): {cap_exc}",
                agent_type="capability_intelligence",
            )
        if not capability_analysis.get("enabled", True):
            await _emit(
                scan_id, "capability_scan_completed",
                capability_analysis.get("reason") or "Capability Intelligence is disabled — continuing with the existing attack taxonomy.",
                agent_type="capability_intelligence",
            )
        else:
            undeclared = capability_analysis.get("undeclared_observed_count", 0)
            if undeclared:
                await _emit(
                    scan_id, "capability_unknown_discovered",
                    f"Capability Intelligence: {undeclared} undeclared capability(ies) observed from prior runtime data.",
                    agent_type="capability_intelligence", data={"undeclared_observed_count": undeclared},
                )
            await _emit(
                scan_id, "capability_scan_completed",
                f"Capability Intelligence: {len(capability_analysis.get('capabilities', []))} capabilities, "
                f"{len(capability_analysis.get('attack_paths', []))} candidate attack paths, "
                f"{len(capability_analysis.get('hypotheses', []))} hypotheses generated"
                f"{' (' + str(capability_analysis.get('memory_informed_count', 0)) + ' informed by prior scan history)' if capability_analysis.get('memory_informed_count') else ''}.",
                agent_type="capability_intelligence",
                data={
                    "fingerprint": capability_analysis.get("fingerprint", {}).get("fingerprint"),
                    "coverage_summary": capability_analysis.get("coverage", {}).get("summary"),
                },
            )
        target_desc = json.dumps({
            "name": target.name,
            "declared_tools": target.declared_tools,
            "permission_map": target.permission_map,
            "capability_hypotheses": capability_service.summarize_hypotheses_for_planner(capability_analysis),
        })
        plan = planner.plan(target_desc)
        scan.attack_plan = plan
        db.commit()

        await _emit(
            scan_id, "agent_action",
            f"Plan ready: {len(plan.get('vectors', []))} vectors identified.",
            agent_type="planner", data=plan,
        )

        # --- 2. Attack + adaptive feedback loop ---
        scan.status = ScanStatus.ATTACKING
        db.commit()

        sentinel = SentinelAgent()
        attack_surface_summary = plan.get("attack_surface_summary", "")

        for vector in plan.get("vectors", []):
            specialists_list = _resolve_specialists(vector)
            if not specialists_list:
                continue  # Planner hallucinated an unknown specialist key; skip safely

            client = TargetClient(target)
            vector_id = vector.get("vector_id", specialists_list[0])
            security_policy = policy_service.resolve_policy_for_vector(target.permission_map, vector)

            if len(specialists_list) == 1:
                # Ordinary single-specialist vector -- unchanged behavior.
                specialist_key = specialists_list[0]
                _, agent_type_enum = SPECIALIST_REGISTRY[specialist_key]
                await _run_specialist_against_vector(
                    db, scan, scan_id, target, client, sentinel, vector, vector_id,
                    specialist_key, agent_type_enum, security_policy, attack_surface_summary,
                )
                continue

            # --- Coordinated multi-specialist test (spec section 19) ---
            # Each specialist runs its own adaptive attempt/mutation loop
            # (unchanged mechanics per specialist), but specialists after
            # the first are told what the earlier ones in this group
            # achieved, and the vector is only considered a fully-proven
            # chain if EVERY specialist in the group succeeds -- a broken
            # link anywhere means the chain doesn't hold end-to-end.
            await _emit(
                scan_id, "coordinated_test_started",
                f"Coordinated test on '{vector_id}': {', '.join(specialists_list)} will collaborate on one hypothesis.",
                agent_type="planner", data={"vector_id": vector_id, "specialists": specialists_list},
            )
            group_results = []
            coordination_note = ""
            for specialist_key in specialists_list:
                _, agent_type_enum = SPECIALIST_REGISTRY[specialist_key]
                sub_vector_id = f"{vector_id}::{specialist_key}"
                result = await _run_specialist_against_vector(
                    db, scan, scan_id, target, client, sentinel, vector, sub_vector_id,
                    specialist_key, agent_type_enum, security_policy, attack_surface_summary,
                    coordination_note=coordination_note,
                )
                group_results.append(result)
                verdict = result["last_verdict"] or {}
                coordination_note = (
                    f"Earlier in this coordinated test, {specialist_key} "
                    f"{'succeeded: ' + str(verdict.get('reasoning', ''))[:200] if result['succeeded'] else 'did not succeed on this link'}."
                )

            chain_succeeded = all(r["succeeded"] for r in group_results)
            await _emit(
                scan_id, "coordinated_test_completed",
                f"Coordinated test on '{vector_id}': "
                f"{'FULL CHAIN CONFIRMED' if chain_succeeded else 'chain not fully confirmed'} "
                f"({sum(1 for r in group_results if r['succeeded'])}/{len(group_results)} links succeeded).",
                agent_type="sentinel",
                data={"vector_id": vector_id, "chain_succeeded": chain_succeeded,
                      "links": [{"specialist": r["specialist_key"], "succeeded": r["succeeded"]} for r in group_results]},
            )

            if chain_succeeded:
                # Individual per-specialist Vulnerability rows already
                # exist (created inside the helper for each succeeding
                # link); this composite record captures the chain itself,
                # which is the actually-dangerous finding -- each link
                # alone might be low severity, but the composed chain
                # crossing a trust boundary end-to-end is not.
                last_log_id = group_results[-1]["last_log_id"]
                if last_log_id is not None:
                    chain_vuln = Vulnerability(
                        id=uuid.uuid4(),
                        scan_id=scan_id,
                        source_attack_id=last_log_id,
                        title=f"Chained capability abuse confirmed: {' -> '.join(specialists_list)} on '{vector_id}'",
                        owasp_category=vector.get("owasp_category", "LLM06: Excessive Agency"),
                        severity=Severity.CRITICAL,
                        description=(
                            f"Every link in this coordinated hypothesis succeeded end-to-end: "
                            f"{' -> '.join(specialists_list)}. {vector.get('rationale', '')}"
                        ),
                        evidence=coordination_note[:2000],
                    )
                    db.add(chain_vuln)
                    db.commit()
                    await _emit(
                        scan_id, "vulnerability_found",
                        f"Chain-level vulnerability confirmed: {chain_vuln.title}",
                        agent_type="sentinel", data={"vulnerability_id": str(chain_vuln.id)},
                    )

        # --- 3. Finalize: real risk scoring ---
        breakdown = risk.compute_scan_risk(db, scan_id=scan_id)
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.utcnow()
        db.commit()

        await _emit(
            scan_id, "scan_status",
            f"Scan completed. Risk score: {scan.risk_score}/100 "
            f"({scan.successful_attacks}/{scan.total_attempts} attempts succeeded). "
            f"Breakdown: {breakdown}",
        )

        # --- 4. Re-run capability analysis with this scan's real AttackLogs,
        # so declared-vs-observed and coverage reflect what actually
        # happened (not just what was planned before any attempt ran) ---
        final_logs = db.query(AttackLog).filter(AttackLog.scan_id == scan_id).all()
        try:
            final_analysis = capability_service.analyze_target_capabilities(target, attack_logs=final_logs, db=db)
            if final_analysis.get("enabled", True):
                capability_persistence.persist_analysis(db, scan_id=scan_id, target_id=target.id, analysis=final_analysis)
                cov = final_analysis.get("coverage", {}).get("summary", {})
                await _emit(
                    scan_id, "capability_coverage_updated",
                    f"Capability coverage after scan: {cov.get('operation_coverage_pct', 0)}% operations, "
                    f"{cov.get('path_coverage_pct', 0)}% attack paths tested.",
                    agent_type="capability_intelligence", data=cov,
                )
        except Exception as cap_exc:  # noqa: BLE001 - final capability snapshot is enrichment, must not fail an otherwise-completed scan
            await _emit(
                scan_id, "capability_scan_warning",
                f"Post-scan capability re-analysis/persistence failed and was skipped: {cap_exc}",
                agent_type="capability_intelligence",
            )

    except Exception as e:  # noqa: BLE001 - hackathon: surface any failure to the stream
        db.rollback()
        scan.status = ScanStatus.FAILED
        db.commit()
        await _emit(scan_id, "scan_status", f"Scan failed: {e}")
        raise
    finally:
        context_manager.clear(context_token)
