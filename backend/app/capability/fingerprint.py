"""
Target fingerprint (spec section 24): a stable identity for "this target,
with this capability set, at this point in time" so persistent memory can
tell whether a previous experience actually applies. Deterministic hash,
no secrets included.
"""
from __future__ import annotations

import hashlib

from app.capability.models import CapabilityFrame


def compute_target_fingerprint(target, frames: list[CapabilityFrame]) -> dict:
    tool_names = sorted({f.name for f in frames})
    operations = sorted({f.operation.value for f in frames})
    categories = sorted({f.category.value for f in frames})
    roles = sorted({f.required_role for f in frames if f.required_role})

    basis = "|".join([
        str(getattr(target, "name", "")),
        str(getattr(target, "endpoint_url", "")),
        ",".join(tool_names),
        ",".join(operations),
        ",".join(categories),
        ",".join(roles),
    ])
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]

    return {
        "fingerprint": digest,
        "tool_count": len(tool_names),
        "operations": operations,
        "categories": categories,
        "roles": roles,
    }
