"""
Unit tests for app.capability.extractor / classifier against the exact
fixtures from the Capability Intelligence spec (section 42, Fixtures A-E;
Fixture F needs runtime observations and is covered separately once
observations.py exists).
"""
from app.capability.classifier import classify_all
from app.capability.enums import (
    CapabilityCategory,
    CapabilityOperation,
    DestructiveRisk,
)
from app.capability.extractor import extract_tool_frames


def _declared(*tools: dict) -> dict:
    return {"tools": list(tools)}


def _tool(name: str, description: str = "", permissions: list[str] | None = None) -> dict:
    return {"name": name, "description": description, "permissions": permissions or []}


# ---------- extractor ----------

def test_extract_empty_declared_tools_returns_no_frames_no_crash():
    result = extract_tool_frames(None)
    assert result.tool_frames == []
    assert result.warnings == []

    result2 = extract_tool_frames({})
    assert result2.tool_frames == []


def test_extract_malformed_entries_produce_warnings_not_crashes():
    declared = {"tools": [{"no_name_field": True}, "not_a_dict", 42, _tool("read_file")]}
    result = extract_tool_frames(declared)
    assert len(result.tool_frames) == 1
    assert result.tool_frames[0].tool_name == "read_file"
    assert len(result.warnings) >= 2


def test_extract_openai_style_function_schema():
    declared = {"tools": [{
        "type": "function",
        "function": {"name": "send_email", "description": "Send an email", "parameters": {"type": "object"}},
    }]}
    result = extract_tool_frames(declared)
    assert len(result.tool_frames) == 1
    assert result.tool_frames[0].tool_name == "send_email"


def test_extract_mcp_style_tool_definition():
    declared = {"tools": [{
        "name": "execute_sql", "description": "Run SQL", "inputSchema": {"type": "object", "properties": {}},
    }]}
    result = extract_tool_frames(declared)
    assert result.tool_frames[0].tool_name == "execute_sql"
    assert result.tool_frames[0].input_schema == {"type": "object", "properties": {}}


def test_extract_duplicate_tool_names_keeps_first():
    declared = _declared(_tool("read_file", "first"), _tool("read_file", "second"))
    result = extract_tool_frames(declared)
    assert len(result.tool_frames) == 1
    assert result.tool_frames[0].tool_description == "first"
    assert any("duplicate" in w for w in result.warnings)


# ---------- classifier: Fixture A (read_file) ----------

def test_fixture_a_read_file():
    result = extract_tool_frames(_declared(_tool("read_file", "Read a file from disk")))
    frames = classify_all(result.tool_frames)
    assert len(frames) == 1
    f = frames[0]
    assert f.operation == CapabilityOperation.READ_FILE
    assert f.category == CapabilityCategory.FILESYSTEM
    assert f.filesystem_access is True
    assert f.declared is True
    assert f.observed is False


# ---------- Fixture B (read_file, send_email) ----------

def test_fixture_b_read_file_send_email():
    result = extract_tool_frames(_declared(
        _tool("read_file", "Read a file"),
        _tool("send_email", "Send an email to a recipient"),
    ))
    frames = classify_all(result.tool_frames)
    by_name = {f.name: f for f in frames}
    assert by_name["read_file"].operation == CapabilityOperation.READ_FILE
    email = by_name["send_email"]
    assert email.operation == CapabilityOperation.SEND_EMAIL
    assert email.external_effect is True
    assert email.side_effect is True
    assert email.reversible is False


# ---------- Fixture C (read_file, execute_code) ----------

def test_fixture_c_read_file_execute_code():
    result = extract_tool_frames(_declared(
        _tool("read_file"), _tool("execute_code", "Execute arbitrary python code"),
    ))
    frames = classify_all(result.tool_frames)
    by_name = {f.name: f for f in frames}
    exec_frame = by_name["execute_code"]
    assert exec_frame.operation == CapabilityOperation.RUN_CODE
    assert exec_frame.code_execution is True
    assert exec_frame.destructive in (DestructiveRisk.POSSIBLE, DestructiveRisk.LIKELY)


# ---------- Fixture D (search, fetch_url) ----------

def test_fixture_d_search_fetch_url():
    result = extract_tool_frames(_declared(
        _tool("search", "Search internal documents"),
        _tool("fetch_url", "Fetch an arbitrary URL"),
    ))
    frames = classify_all(result.tool_frames)
    by_name = {f.name: f for f in frames}
    assert by_name["search"].operation == CapabilityOperation.SEARCH
    fetch = by_name["fetch_url"]
    assert fetch.operation == CapabilityOperation.FETCH_URL
    assert fetch.network_access is True
    assert fetch.trust_boundary is True


# ---------- Fixture E (execute_sql, delete_user, admin_only) ----------

def test_fixture_e_execute_sql_delete_user_admin():
    result = extract_tool_frames(_declared(
        _tool("execute_sql", "Run a SQL query against the database"),
        _tool("delete_user", "Delete a user account", permissions=["admin"]),
        _tool("admin_only", "Administrative operation", permissions=["admin"]),
    ))
    frames = classify_all(result.tool_frames)
    by_name = {f.name: f for f in frames}

    sql = by_name["execute_sql"]
    assert sql.operation == CapabilityOperation.EXECUTE_QUERY
    assert sql.database_access is True
    assert sql.code_execution is True

    delete_user = by_name["delete_user"]
    assert delete_user.destructive == DestructiveRisk.LIKELY
    assert delete_user.authorization == "admin"
    assert delete_user.risk_score >= 50

    admin_only = by_name["admin_only"]
    assert admin_only.authorization == "admin"


# ---------- unknown capability handling (spec section 5) ----------

def test_unrecognized_operation_becomes_unknown_capability_not_discarded():
    result = extract_tool_frames(_declared(_tool("frobnicate_widget", "Frobnicates the widget subsystem")))
    frames = classify_all(result.tool_frames)
    assert len(frames) == 1
    assert frames[0].operation == CapabilityOperation.UNKNOWN_CAPABILITY
    assert frames[0].category == CapabilityCategory.UNKNOWN
    assert frames[0].confidence <= 0.3  # low confidence, but present


def test_every_capability_frame_has_confidence_and_provenance():
    result = extract_tool_frames(_declared(_tool("read_file"), _tool("send_email")))
    for f in classify_all(result.tool_frames):
        assert 0.0 <= f.confidence <= 1.0
        assert f.declared is True
        assert f.observed is False
        assert f.inferred is False
