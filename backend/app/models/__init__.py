"""
Import all models here so `Base.metadata.create_all()` and Alembic
autogenerate can discover them via a single import of `app.models`.
"""
from app.models.target import TargetProfile          # noqa: F401
from app.models.scan import ScanRun, ScanStatus       # noqa: F401
from app.models.attack import AttackLog, AgentType    # noqa: F401
from app.models.vulnerability import Vulnerability, Severity, VulnerabilityStatus  # noqa: F401
from app.models.patch import RemediationPatch         # noqa: F401
from app.models.memory import MemoryRecord, MemoryType             # noqa: F401
from app.models.attack_dna import AttackDNARecord, ConsensusRecord  # noqa: F401
from app.models.revalidation import RevalidationRecord, RevalidationResult  # noqa: F401
from app.models.remediation_pr import RemediationPR, RemediationPRStatus  # noqa: F401
