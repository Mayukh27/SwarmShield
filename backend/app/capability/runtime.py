"""
Runtime tool-call observation + declared/observed reconciliation
(spec sections 3, 4). No LLM call -- regex over AttackLog.target_response,
matching the "TOOL_CALL: name(args)" shape already produced by the real
target client's tool-call surface and the offline fallback engine.
"""
from __future__ import annotations

import re
from datetime import datetime

from app.capability.classifier import classify_tool_frame
from app.capability.enums import CapabilityStatus
from app.capability.extractor import ExtractionResult
from app.capability.models import CapabilityFrame, ToolFrame

_TOOL_CALL_RE = re.compile(r"TOOL_CALL:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")


def extract_observed_tool_frames(attack_logs: list) -> ExtractionResult:
    """attack_logs: list of AttackLog rows (or anything with a
    `target_response` text attribute). Never raises on malformed/missing
    response text -- observation extraction must not crash a scan."""
    result = ExtractionResult()
    seen: set[str] = set()

    for log in attack_logs or []:
        text = getattr(log, "target_response", None)
        if not text:
            continue
        for match in _TOOL_CALL_RE.finditer(text):
            name = match.group(1).strip()
            if not name:
                continue
            seen.add(name)
            result.tool_frames.append(
                ToolFrame(tool_name=name, tool_description="", source="runtime_observation", raw={})
            )

    return result


def classify_observed(tool_frames: list[ToolFrame]) -> list[CapabilityFrame]:
    frames = []
    for tool in tool_frames:
        frame = classify_tool_frame(tool)
        frame.declared = False
        frame.observed = True
        frame.status = CapabilityStatus.UNDECLARED_OBSERVED  # corrected in reconcile() if a declared match exists
        frame.first_observed = frame.last_observed = datetime.utcnow()
        frame.observation_count = 1
        frames.append(frame)
    return frames


def reconcile(declared: list[CapabilityFrame], observed: list[CapabilityFrame]) -> list[CapabilityFrame]:
    """Merge declared + observed capability frames (spec section 4:
    undeclared-but-observed capabilities must be surfaced, never
    discarded or silently merged away)."""
    by_name: dict[str, CapabilityFrame] = {f.tool_name: f for f in declared}
    merged: list[CapabilityFrame] = list(declared)

    for obs in observed:
        existing = by_name.get(obs.tool_name)
        if existing is None:
            merged.append(obs)
            by_name[obs.tool_name] = obs
            continue
        existing.observed = True
        existing.status = CapabilityStatus.DECLARED_OBSERVED
        existing.observation_count += 1
        existing.last_observed = datetime.utcnow()
        if existing.first_observed is None:
            existing.first_observed = existing.last_observed

    return merged
