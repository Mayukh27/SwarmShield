"""
Deterministic ToolFrame extraction (spec sections 6, 28: "Capability
extraction should NOT require an LLM whenever possible").

Source support, in priority order, degrading gracefully when absent
(spec section 37):
  1. TargetProfile.declared_tools["tools"] — list of {name, description,
     permissions, input_schema, output_schema} (this is SwarmShield's
     actual declared_tools shape; see app/models/target.py docstring).
  2. OpenAI-style function schemas: {"type": "function", "function": {...}}
  3. MCP-style tool definitions: {"name", "inputSchema", ...}
  4. Bare {"name": ..., "description": ...} entries.

Unrecognized shapes are skipped with a warning appended to the result
rather than raising — a malformed target must never crash a scan
(spec section 37).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.capability.models import ToolFrame


@dataclass
class ExtractionResult:
    tool_frames: list[ToolFrame] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _coerce_one(raw: dict, source: str) -> ToolFrame | None:
    if not isinstance(raw, dict):
        return None

    # OpenAI function-calling shape
    if raw.get("type") == "function" and isinstance(raw.get("function"), dict):
        fn = raw["function"]
        return ToolFrame(
            tool_name=str(fn.get("name", "")).strip(),
            tool_description=str(fn.get("description", "")),
            input_schema=fn.get("parameters", {}) or {},
            declared_permissions=list(fn.get("permissions", []) or []),
            source=source,
            raw=raw,
        )

    # MCP-style
    if "inputSchema" in raw or "input_schema" in raw:
        return ToolFrame(
            tool_name=str(raw.get("name", "")).strip(),
            tool_description=str(raw.get("description", "")),
            input_schema=raw.get("inputSchema") or raw.get("input_schema") or {},
            output_schema=raw.get("outputSchema") or raw.get("output_schema") or {},
            declared_permissions=list(raw.get("permissions", []) or []),
            source=source,
            raw=raw,
        )

    # Bare declared_tools entry (SwarmShield's native shape)
    if "name" in raw:
        return ToolFrame(
            tool_name=str(raw.get("name", "")).strip(),
            tool_description=str(raw.get("description", "")),
            input_schema=raw.get("input_schema", {}) or {},
            output_schema=raw.get("output_schema", {}) or {},
            declared_permissions=list(raw.get("permissions", []) or []),
            source=source,
            raw=raw,
        )

    return None


def extract_permission_map_frames(permission_map: dict | None, existing_names: set[str] | None = None) -> ExtractionResult:
    """Tool names declared only in TargetProfile.permission_map (spec
    section 6, source priority #6) that weren't already present in
    declared_tools -- still a real declared capability, just from a
    different part of the target's own metadata."""
    result = ExtractionResult()
    if not permission_map or not isinstance(permission_map, dict):
        return result

    existing_names = existing_names or set()
    tools = permission_map.get("tools")
    if not isinstance(tools, dict):
        return result

    for name, policy in tools.items():
        name = str(name).strip()
        if not name or name in existing_names:
            continue
        restriction = (policy or {}).get("restriction") if isinstance(policy, dict) else None
        result.tool_frames.append(ToolFrame(
            tool_name=name,
            tool_description=f"restriction: {restriction}" if restriction else "",
            source="permission_map",
            declared_permissions=[restriction] if restriction else [],
            raw=policy if isinstance(policy, dict) else {},
        ))

    return result


def extract_tool_frames(declared_tools: dict | None) -> ExtractionResult:
    """declared_tools is TargetProfile.declared_tools (a JSONB dict).
    Expected shape: {"tools": [...], "system_prompt_summary": "...", ...}
    but this function tolerates a bare list, missing keys, or None
    entirely -- extraction must never raise on attacker-influenced or
    incomplete target metadata."""
    result = ExtractionResult()

    if not declared_tools:
        return result

    if isinstance(declared_tools, dict):
        tools_raw = declared_tools.get("tools", [])
    elif isinstance(declared_tools, list):
        tools_raw = declared_tools
    else:
        result.warnings.append(f"declared_tools has unexpected top-level type {type(declared_tools).__name__}; skipped")
        return result

    if not isinstance(tools_raw, list):
        result.warnings.append("declared_tools['tools'] is not a list; skipped")
        return result

    seen_names: set[str] = set()
    for idx, raw in enumerate(tools_raw):
        frame = _coerce_one(raw, source="declared_tools")
        if frame is None:
            result.warnings.append(f"declared_tools[{idx}] did not match any known tool schema shape; skipped")
            continue
        if not frame.tool_name:
            result.warnings.append(f"declared_tools[{idx}] has no usable 'name'; skipped")
            continue
        if frame.tool_name in seen_names:
            result.warnings.append(f"duplicate tool name '{frame.tool_name}' in declared_tools; kept first occurrence")
            continue
        seen_names.add(frame.tool_name)
        result.tool_frames.append(frame)

    return result
