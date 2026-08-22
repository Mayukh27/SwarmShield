"""
Attack DNA service: enumerated, auditable mutation vocabulary ported from
Repo A's `mutation.py`, now driving Repo B's real adaptive loop instead of
sitting disconnected from it. `next_generation()` is called by the
orchestrator on every retry: it reads the Sentinel's real `mutation_hint`
text for THIS scan's attempt, maps it to one of the enumerated mutation
types (auditable -- no free-form LLM-generated mutation), persists the new
generation's genome as an `AttackDNARecord`, and returns the mutation's
`dna_hint` field so the specialist's next payload is causally shaped by it
(see fallback_engine._specialist and the real specialist prompts, which
both read `context["dna_hint"]`).
"""
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.attack_dna import AttackDNARecord

ALLOWED_MUTATIONS: dict[str, tuple[str, str]] = {
    "context_variation": ("context_strategy", "retrieval_relevance_camouflage"),
    "role_variation": ("role_strategy", "reviewer_context"),
    "format_variation": ("format_strategy", "structured_validation"),
    "multi_turn_continuation": ("conversation_strategy", "bounded_follow_up"),
    "indirect_content_variation": ("delivery_strategy", "document_metadata"),
}

# Keyword -> mutation_type mapping used to pick a mutation from the
# Sentinel's free-text mutation_hint (real signal from a real failed
# attempt), so DNA evolution is grounded in what actually failed rather
# than cycling through mutations arbitrarily.
_HINT_KEYWORDS: dict[str, str] = {
    "role": "role_variation",
    "reviewer": "role_variation",
    "format": "format_variation",
    "structure": "format_variation",
    "ticket": "context_variation",
    "context": "context_variation",
    "explicit": "context_variation",
    "follow": "multi_turn_continuation",
    "continu": "multi_turn_continuation",
    "document": "indirect_content_variation",
    "retriev": "indirect_content_variation",
}


def _mutation_type_from_hint(mutation_hint: str | None) -> str:
    hint = (mutation_hint or "").lower()
    for keyword, mutation_type in _HINT_KEYWORDS.items():
        if keyword in hint:
            return mutation_type
    return "context_variation"  # sensible default: broaden retrieval framing


def mutate_genome(genome: dict[str, Any], mutation_type: str) -> tuple[dict[str, Any], dict[str, str]]:
    if mutation_type not in ALLOWED_MUTATIONS:
        raise ValueError("Unsupported mutation type")
    field, value = ALLOWED_MUTATIONS[mutation_type]
    child = dict(genome)
    previous = str(child.get(field, "unset"))
    child[field] = value
    return child, {"feature": field, "from": previous, "to": value, "mutation_type": mutation_type}


def seed_generation(
    db: Session, *, scan_id: uuid.UUID, vector_id: str, source_attack_id: uuid.UUID | None = None
) -> AttackDNARecord:
    """Root genome (generation 0) for a vector, created on its first attempt."""
    record = AttackDNARecord(
        id=uuid.uuid4(),
        scan_id=scan_id,
        vector_id=vector_id,
        parent_id=None,
        generation=0,
        genome={"context_strategy": "unset", "role_strategy": "unset", "format_strategy": "unset"},
        mutations=[],
        success_probability=0.3,
        confidence=0.5,
        source_attack_id=source_attack_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def next_generation(
    db: Session,
    *,
    parent: AttackDNARecord,
    mutation_hint: str | None,
    source_attack_id: uuid.UUID | None = None,
) -> tuple[AttackDNARecord, str]:
    """Applies one real mutation, driven by the Sentinel's own hint from
    the failed attempt on `parent`. Returns the new record plus the
    `dna_hint` (the mutated field's new value) the orchestrator threads
    into the specialist's next context."""
    mutation_type = _mutation_type_from_hint(mutation_hint)
    child_genome, mutation_record = mutate_genome(parent.genome, mutation_type)

    record = AttackDNARecord(
        id=uuid.uuid4(),
        scan_id=parent.scan_id,
        vector_id=parent.vector_id,
        parent_id=parent.id,
        generation=parent.generation + 1,
        genome=child_genome,
        mutations=[*parent.mutations, mutation_record],
        success_probability=min(0.95, parent.success_probability + 0.15),
        confidence=min(0.95, parent.confidence + 0.1),
        source_attack_id=source_attack_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    dna_hint = mutation_record["feature"]  # e.g. "role_strategy" -> read by specialist fallback
    return record, dna_hint
