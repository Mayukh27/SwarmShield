"""
Deterministic classification: ToolFrame -> CapabilityFrame (spec sections
6, 10-13). Keyword/regex-based against tool name + description + declared
permissions, matching the taxonomy in enums.py. No LLM call — this is the
"schema parsing / metadata / known operation mappings" path spec section
28 requires be preferred whenever possible.

Confidence model (spec section 29): exact name-token match against a
known operation keyword = 0.9; description-only keyword match = 0.7;
no match at all -> UNKNOWN_CAPABILITY with confidence 0.3 (still kept,
never discarded, but too low-confidence to drive destructive testing
on its own -- see prioritizer.py).
"""
from __future__ import annotations

import re

from app.capability.enums import (
    OPERATION_CATEGORY,
    CapabilityCategory,
    CapabilityOperation,
    DataSensitivity,
    DestructiveRisk,
    ResourceType,
    TrustLevel,
)
from app.capability.models import CapabilityFrame, ToolFrame

# operation -> keywords matched against tokenized tool name / description.
# Ordered roughly most-specific-first since the first match wins.
_OPERATION_KEYWORDS: list[tuple[CapabilityOperation, tuple[str, ...]]] = [
    (CapabilityOperation.EXECUTE_QUERY, ("execute_sql", "run_sql", "execute_query", "sql_query")),
    (CapabilityOperation.EXECUTE_PROCEDURE, ("execute_procedure", "stored_procedure")),
    (CapabilityOperation.RUN_CODE, ("run_code", "execute_code", "eval_code", "code_execution", "python_exec", "run_script")),
    (CapabilityOperation.RUN_COMMAND, ("run_command", "shell", "exec_command", "system_command", "bash")),
    (CapabilityOperation.SPAWN_PROCESS, ("spawn_process", "spawn_subprocess")),
    (CapabilityOperation.READ_FILE, ("read_file", "get_file", "open_file", "fetch_file", "load_file")),
    (CapabilityOperation.WRITE_FILE, ("write_file", "save_file", "create_file", "put_file")),
    (CapabilityOperation.DELETE_FILE, ("delete_file", "remove_file")),
    (CapabilityOperation.MOVE_FILE, ("move_file", "rename_file")),
    (CapabilityOperation.COPY_FILE, ("copy_file",)),
    (CapabilityOperation.LIST_DIRECTORY, ("list_directory", "list_files", "ls_dir")),
    (CapabilityOperation.SEND_EMAIL, ("send_email", "email_send", "mail_send")),
    (CapabilityOperation.SEND_MESSAGE, ("send_message", "send_sms", "send_slack", "post_message")),
    (CapabilityOperation.CREATE_NOTIFICATION, ("notify", "notification")),
    (CapabilityOperation.PUBLISH, ("publish",)),
    (CapabilityOperation.POST, ("post_",)),
    (CapabilityOperation.FETCH_URL, ("fetch_url", "fetch_page", "get_url", "http_get", "browse_url")),
    (CapabilityOperation.WEB_SEARCH, ("web_search", "search_web", "internet_search")),
    (CapabilityOperation.API_CALL, ("api_call", "call_api", "invoke_api")),
    (CapabilityOperation.HTTPS_REQUEST, ("https_request",)),
    (CapabilityOperation.HTTP_REQUEST, ("http_request", "make_request")),
    (CapabilityOperation.READ_SECRET, ("read_secret", "get_secret")),
    (CapabilityOperation.ACCESS_CREDENTIAL, ("credential", "access_credential")),
    (CapabilityOperation.ACCESS_TOKEN, ("access_token", "get_token", "api_key")),
    (CapabilityOperation.READ_ENVIRONMENT, ("read_env", "get_environment", "environment_variable")),
    (CapabilityOperation.ACCESS_PRIVATE_KEY, ("private_key",)),
    (CapabilityOperation.CREATE_USER, ("create_user", "add_user", "register_user")),
    (CapabilityOperation.MODIFY_USER, ("modify_user", "update_user", "edit_user")),
    (CapabilityOperation.DELETE, ("delete_user",)),  # checked before generic DELETE below via name match
    (CapabilityOperation.MODIFY_PERMISSION, ("modify_permission", "grant_permission", "set_role", "change_role")),
    (CapabilityOperation.ASSUME_ROLE, ("assume_role",)),
    (CapabilityOperation.IMPERSONATE, ("impersonate",)),
    (CapabilityOperation.AUTHENTICATE, ("authenticate", "login", "sign_in")),
    (CapabilityOperation.AUTHORIZE, ("authorize",)),
    (CapabilityOperation.DELEGATE_TO_AGENT, ("delegate_to_agent", "delegate_agent")),
    (CapabilityOperation.CALL_AGENT, ("call_agent", "invoke_agent")),
    (CapabilityOperation.SPAWN_AGENT, ("spawn_agent", "create_agent")),
    (CapabilityOperation.READ_DATABASE, ("read_database", "query_database", "db_read", "get_records")),
    (CapabilityOperation.WRITE_DATABASE, ("write_database", "db_write", "insert_record")),
    (CapabilityOperation.UPDATE_DATABASE, ("update_database", "db_update")),
    (CapabilityOperation.DELETE_DATABASE, ("delete_database", "db_delete")),
    (CapabilityOperation.EXPORT, ("export",)),
    (CapabilityOperation.IMPORT, ("import_",)),
    (CapabilityOperation.SEARCH, ("search", "find", "query", "lookup")),
    (CapabilityOperation.LIST, ("list_", "enumerate")),
    (CapabilityOperation.UPDATE, ("update", "edit", "modify", "patch_")),
    (CapabilityOperation.DELETE, ("delete", "remove", "purge")),
    (CapabilityOperation.WRITE, ("write", "create", "add", "insert", "save")),
    (CapabilityOperation.READ, ("read", "get", "fetch", "retrieve", "view")),
    (CapabilityOperation.TRANSFORM, ("transform", "convert")),
    (CapabilityOperation.SCHEDULE, ("schedule",)),
    (CapabilityOperation.EXECUTE, ("execute", "run_", "invoke")),
]

_DESTRUCTIVE_HINTS = ("delete", "remove", "purge", "drop", "destroy", "wipe")
_ADMIN_HINTS = ("admin", "root", "superuser", "privileged")
_SENSITIVE_RESOURCE_HINTS: dict[DataSensitivity, tuple[str, ...]] = {
    DataSensitivity.CREDENTIALS: ("credential", "password", "api_key", "apikey"),
    DataSensitivity.SECRETS: ("secret", "token", "private_key"),
    DataSensitivity.PII: ("pii", "customer", "user_data", "personal"),
    DataSensitivity.FINANCIAL: ("payment", "billing", "financial", "invoice", "card"),
    DataSensitivity.HEALTH: ("health", "medical", "patient"),
    DataSensitivity.SOURCE_CODE: ("source_code", "repository", "codebase"),
    DataSensitivity.SYSTEM_CONFIG: ("config", "environment", "settings"),
    DataSensitivity.USER_DATA: ("user", "account", "profile"),
}


def _tokenize(tool: ToolFrame) -> str:
    return f"{tool.tool_name} {tool.tool_description}".lower()


def _kw_matches(kw: str, haystack: str) -> bool:
    """Word-boundary match, not naive substring -- otherwise short
    keywords like 'get' false-positive inside unrelated words like
    'widget'. Keywords ending in '_' (e.g. 'run_', 'list_') are treated
    as prefix matches on a word."""
    if kw.endswith("_"):
        pattern = r"\b" + re.escape(kw)
    else:
        pattern = r"\b" + re.escape(kw) + r"\b"
    return re.search(pattern, haystack) is not None


def _match_operation(tool: ToolFrame) -> tuple[CapabilityOperation, float]:
    name_lower = tool.tool_name.lower().replace("_", " ")
    text = _tokenize(tool)
    for op, keywords in _OPERATION_KEYWORDS:
        for kw in keywords:
            if _kw_matches(kw.replace("_", " ") if not kw.endswith("_") else kw, name_lower):
                return op, 0.9
    for op, keywords in _OPERATION_KEYWORDS:
        for kw in keywords:
            if _kw_matches(kw.replace("_", " ") if not kw.endswith("_") else kw, text):
                return op, 0.7
    return CapabilityOperation.UNKNOWN_CAPABILITY, 0.3


def _infer_sensitivity(tool: ToolFrame) -> DataSensitivity:
    text = _tokenize(tool)
    for sensitivity, hints in _SENSITIVE_RESOURCE_HINTS.items():
        if any(h in text for h in hints):
            return sensitivity
    return DataSensitivity.INTERNAL


def _infer_destructive(operation: CapabilityOperation, text: str) -> DestructiveRisk:
    if operation in (
        CapabilityOperation.DELETE, CapabilityOperation.DELETE_FILE, CapabilityOperation.DELETE_DATABASE,
    ):
        return DestructiveRisk.LIKELY
    if any(h in text for h in _DESTRUCTIVE_HINTS):
        return DestructiveRisk.POSSIBLE
    if operation in (CapabilityOperation.WRITE, CapabilityOperation.UPDATE, CapabilityOperation.WRITE_FILE,
                      CapabilityOperation.WRITE_DATABASE, CapabilityOperation.UPDATE_DATABASE,
                      CapabilityOperation.RUN_CODE, CapabilityOperation.RUN_COMMAND, CapabilityOperation.EXECUTE_QUERY):
        return DestructiveRisk.POSSIBLE
    return DestructiveRisk.NONE


def _infer_authorization(tool: ToolFrame) -> tuple[str | None, str | None]:
    """Returns (authorization_label, required_role). Prefers declared
    permissions; falls back to keyword inference from name/description."""
    if tool.declared_permissions:
        return ", ".join(tool.declared_permissions), None
    text = _tokenize(tool)
    if any(h in text for h in _ADMIN_HINTS):
        return "admin", "admin"
    return None, None


def classify_tool_frame(tool: ToolFrame) -> CapabilityFrame:
    operation, op_confidence = _match_operation(tool)
    category = OPERATION_CATEGORY.get(operation, CapabilityCategory.UNKNOWN)
    text = _tokenize(tool)

    network_access = category.value == "network" or operation in (
        CapabilityOperation.HTTP_REQUEST, CapabilityOperation.HTTPS_REQUEST, CapabilityOperation.FETCH_URL,
        CapabilityOperation.API_CALL,
    )
    filesystem_access = category.value == "filesystem"
    database_access = category.value == "database"
    secret_access = category.value == "secrets"
    code_execution = operation in (CapabilityOperation.RUN_CODE, CapabilityOperation.RUN_COMMAND,
                                    CapabilityOperation.SPAWN_PROCESS, CapabilityOperation.EXECUTE_QUERY,
                                    CapabilityOperation.EXECUTE_PROCEDURE)
    identity_access = category.value == "identity"
    external_effect = operation in (CapabilityOperation.SEND_EMAIL, CapabilityOperation.SEND_MESSAGE,
                                     CapabilityOperation.POST, CapabilityOperation.PUBLISH,
                                     CapabilityOperation.EXTERNAL_NETWORK_ACCESS, CapabilityOperation.FETCH_URL)

    sensitivity = _infer_sensitivity(tool)
    destructive = _infer_destructive(operation, text)
    side_effect = destructive != DestructiveRisk.NONE or external_effect or database_access or filesystem_access or code_execution
    authorization, required_role = _infer_authorization(tool)

    resources: list[ResourceType] = []
    if database_access:
        resources.append(ResourceType.DATABASE)
    if filesystem_access:
        resources.append(ResourceType.FILESYSTEM)
    if network_access:
        resources.append(ResourceType.EXTERNAL_NETWORK if external_effect else ResourceType.INTERNAL_NETWORK)
    if operation in (CapabilityOperation.SEND_EMAIL, CapabilityOperation.SEND_MESSAGE):
        resources.append(ResourceType.EXTERNAL_RECIPIENT)

    destination_trust = TrustLevel.UNKNOWN
    if database_access:
        destination_trust = TrustLevel.DATABASE
    elif filesystem_access:
        destination_trust = TrustLevel.FILESYSTEM
    elif network_access and external_effect:
        destination_trust = TrustLevel.EXTERNAL_NETWORK
    elif network_access:
        destination_trust = TrustLevel.INTERNAL_NETWORK

    trust_boundary = external_effect or database_access or filesystem_access or identity_access or secret_access

    risk_reasons = []
    risk_score = 0.0
    if destructive == DestructiveRisk.LIKELY:
        risk_score += 35
        risk_reasons.append("operation is likely destructive")
    elif destructive == DestructiveRisk.POSSIBLE:
        risk_score += 15
        risk_reasons.append("operation may have destructive side effects")
    if sensitivity in (DataSensitivity.SECRETS, DataSensitivity.CREDENTIALS):
        risk_score += 30
        risk_reasons.append(f"touches {sensitivity.value} data")
    elif sensitivity in (DataSensitivity.PII, DataSensitivity.FINANCIAL, DataSensitivity.HEALTH):
        risk_score += 20
        risk_reasons.append(f"touches {sensitivity.value} data")
    if external_effect:
        risk_score += 15
        risk_reasons.append("has an external/irreversible effect")
    if authorization == "admin" or required_role == "admin":
        risk_score += 15
        risk_reasons.append("requires elevated authorization")
    if code_execution:
        risk_score += 20
        risk_reasons.append("performs code/query execution")
    risk_score = min(risk_score, 100.0)

    return CapabilityFrame(
        name=tool.tool_name,
        display_name=tool.tool_name.replace("_", " ").title(),
        category=category,
        operation=operation,
        source=tool.source,
        declared=True,
        observed=False,
        inferred=False,
        confidence=op_confidence,
        tool_name=tool.tool_name,
        tool_description=tool.tool_description,
        input_schema=tool.input_schema,
        output_schema=tool.output_schema,
        resources=resources,
        data_sensitivity=sensitivity,
        authorization=authorization,
        required_role=required_role,
        required_permissions=tool.declared_permissions,
        trust_boundary=trust_boundary,
        source_trust=TrustLevel.AGENT,
        destination_trust=destination_trust,
        side_effect=side_effect,
        reversible=(destructive == DestructiveRisk.NONE and not external_effect),
        destructive=destructive,
        external_effect=external_effect,
        network_access=network_access,
        filesystem_access=filesystem_access,
        database_access=database_access,
        secret_access=secret_access,
        code_execution=code_execution,
        identity_access=identity_access,
        risk_score=risk_score,
        risk_reasons=risk_reasons,
        metadata={"raw": tool.raw} if tool.raw else {},
    )


def classify_all(tool_frames: list[ToolFrame]) -> list[CapabilityFrame]:
    return [classify_tool_frame(t) for t in tool_frames]
