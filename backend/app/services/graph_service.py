"""
Evidence-backed attack-chain graph, built from real persisted campaign
rows (AttackLog, MemoryRecord, Vulnerability, AttackDNARecord) for one
scan. Ported from Repo A's `graph/chain.py`; the original's CAUSED-edge
heuristic ("any memory whose source_attack_id matches any attempt implies
every finding is caused by it") was wrong for multi-vector scans, so this
version links each finding directly to its own `source_attack_id`
(the exact AttackLog row that produced it) and links DNA generations by
parent_id -> a genuine mutation lineage the frontend can render as a
sub-chain per vector.

Consumed by GET /scans/{scan_id}/graph (api/routes/graph.py) for
AttackFlowCanvas.jsx.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.attack import AttackLog
from app.models.attack_dna import AttackDNARecord
from app.models.memory import MemoryRecord
from app.models.target import TargetProfile
from app.models.vulnerability import Vulnerability


def build_scan_graph(db: Session, *, scan_id: uuid.UUID) -> dict:
    from app.models.scan import ScanRun

    scan = db.query(ScanRun).filter(ScanRun.id == scan_id).one()
    target = db.query(TargetProfile).filter(TargetProfile.id == scan.target_id).one()

    attempts = db.query(AttackLog).filter(AttackLog.scan_id == scan_id).order_by(AttackLog.created_at).all()
    memories = db.query(MemoryRecord).filter(MemoryRecord.scan_id == scan_id).all()
    findings = db.query(Vulnerability).filter(Vulnerability.scan_id == scan_id).all()
    dna_records = db.query(AttackDNARecord).filter(AttackDNARecord.scan_id == scan_id).all()

    nodes: list[dict] = [{"id": "target", "kind": "target", "label": target.name}]
    edges: list[dict] = []

    for attempt in attempts:
        node_id = f"attempt:{attempt.id}"
        nodes.append({
            "id": node_id,
            "kind": "attack",
            "label": f"{attempt.agent_type.value} gen{attempt.generation}",
            "agent": attempt.agent_type.value,
            "succeeded": attempt.succeeded,
            "owasp_category": attempt.owasp_category,
        })
        if attempt.parent_attempt_id:
            edges.append({
                "id": f"retry:{attempt.id}",
                "source": f"attempt:{attempt.parent_attempt_id}",
                "target": node_id,
                "kind": "MUTATED_RETRY",
            })
        else:
            edges.append({"id": f"targets:{attempt.id}", "source": "target", "target": node_id, "kind": "ATTACKS"})

    for dna in dna_records:
        node_id = f"dna:{dna.id}"
        nodes.append({
            "id": node_id,
            "kind": "dna",
            "label": f"{dna.vector_id} gen{dna.generation}",
            "success_probability": dna.success_probability,
        })
        if dna.parent_id:
            edges.append({"id": f"evolved:{dna.id}", "source": f"dna:{dna.parent_id}", "target": node_id, "kind": "EVOLVED"})
        if dna.source_attack_id:
            edges.append({
                "id": f"produced:{dna.id}", "source": f"attempt:{dna.source_attack_id}", "target": node_id, "kind": "PRODUCED",
            })

    for memory in memories:
        node_id = f"memory:{memory.id}"
        nodes.append({
            "id": node_id,
            "kind": "memory",
            "label": memory.memory_type.value,
            "content": memory.content,
            "confidence": memory.confidence,
        })
        if memory.source_attack_id:
            edges.append({
                "id": f"discovered:{memory.id}",
                "source": f"attempt:{memory.source_attack_id}",
                "target": node_id,
                "kind": "DISCOVERED",
            })

    for finding in findings:
        node_id = f"finding:{finding.id}"
        nodes.append({
            "id": node_id,
            "kind": "finding",
            "label": finding.title,
            "severity": finding.severity.value,
            "status": finding.status.value,
            "risk_score": finding.risk_score,
        })
        # exact causal edge -- this finding's own source attempt, not a heuristic guess
        edges.append({
            "id": f"caused:{finding.source_attack_id}:{finding.id}",
            "source": f"attempt:{finding.source_attack_id}",
            "target": node_id,
            "kind": "CAUSED",
        })

    return {
        "scan_id": str(scan_id),
        "nodes": nodes,
        "edges": edges,
        "supported_evaluations": sum(1 for a in attempts if a.succeeded),
    }
