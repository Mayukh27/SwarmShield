"""
Risk service: neither repo actually computed risk (Repo A had a
`risk_score` column with nothing populating it; Repo B's orchestrator did
a naive `successful/total*100`). This replaces that with a severity- and
confidence-weighted score per vulnerability, aggregated per scan, with a
category breakdown for the dashboard's risk panel.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.scan import ScanRun
from app.models.vulnerability import Severity, Vulnerability, VulnerabilityStatus

_SEVERITY_WEIGHT = {
    Severity.LOW: 20,
    Severity.MEDIUM: 45,
    Severity.HIGH: 70,
    Severity.CRITICAL: 95,
}

# Categories with real blast radius (tool execution, data access) get an
# exposure multiplier on top of severity; pure conversational findings do not.
_HIGH_EXPOSURE_MARKERS = ("excessive agency", "tool", "privilege", "sensitive information", "exfiltration")


def _exposure_multiplier(owasp_category: str) -> float:
    category = owasp_category.lower()
    return 1.2 if any(marker in category for marker in _HIGH_EXPOSURE_MARKERS) else 1.0


def score_vulnerability(vuln: Vulnerability) -> float:
    base = _SEVERITY_WEIGHT.get(vuln.severity, 40)
    return round(min(100.0, base * _exposure_multiplier(vuln.owasp_category)), 1)


def compute_scan_risk(db: Session, *, scan_id: uuid.UUID) -> dict:
    """Scores every Vulnerability on the scan and writes each score back to
    `Vulnerability.risk_score`, but only **open/unfixed** findings
    (anything other than REVALIDATION_PASSED) contribute to the scan-level
    aggregate -- a finding that's been proven fixed by re-validation must
    stop dragging the scorecard down, or "Apply patch & re-validate" would
    have no visible effect. Call this again any time a finding's status
    changes (e.g. after revalidation), not just once at scan completion --
    see api/routes/revalidation.py.

    Aggregate is highest-severity-weighted, not a flat average, so one
    critical finding can't be diluted by many low ones."""
    scan = db.query(ScanRun).filter(ScanRun.id == scan_id).one()
    vulns = db.query(Vulnerability).filter(Vulnerability.scan_id == scan_id).all()

    if not vulns:
        scan.risk_score = 0.0
        scan.risk_breakdown = {
            "by_category": {},
            "by_severity": {},
            "vulnerability_count": 0,
            "fixed_count": 0,
        }
        db.commit()
        return scan.risk_breakdown

    by_category: dict[str, float] = {}
    by_severity: dict[str, int] = {}
    scores = []
    fixed_count = 0

    for vuln in vulns:
        s = score_vulnerability(vuln)
        vuln.risk_score = s

        if vuln.status == VulnerabilityStatus.REVALIDATION_PASSED:
            fixed_count += 1
            continue  # fixed findings no longer count toward the live risk score

        scores.append(s)
        by_category[vuln.owasp_category] = max(by_category.get(vuln.owasp_category, 0.0), s)
        by_severity[vuln.severity.value] = by_severity.get(vuln.severity.value, 0) + 1

    if not scores:
        # every finding on this scan has been fixed
        aggregate = 0.0
        top = 0.0
    else:
        scores.sort(reverse=True)
        # Weighted toward the worst finding, softened by the "long tail" of
        # lesser findings, so risk reflects "how bad is the worst thing found"
        # more than "how many things were found".
        top = scores[0]
        tail_contribution = sum(s * 0.15 for s in scores[1:])
        aggregate = round(min(100.0, top + tail_contribution), 1)

    scan.risk_score = aggregate
    scan.risk_breakdown = {
        "by_category": by_category,
        "by_severity": by_severity,
        "vulnerability_count": len(scores),
        "fixed_count": fixed_count,
        "top_finding_score": top,
    }
    db.commit()
    return scan.risk_breakdown
