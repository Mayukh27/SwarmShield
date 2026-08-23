"""
Capability taxonomy — enums used throughout the Capability Intelligence
Engine. Spec sections 4-5, 10-13.

Every enum that classifies something extracted from an untrusted/unknown
target includes an UNKNOWN sentinel so extraction never has to discard
data it can't confidently categorize (spec section 5: "Unknown operations
must be represented as UNKNOWN_CAPABILITY rather than discarded.").
"""
import enum


class CapabilityOperation(str, enum.Enum):
    # DATA OPERATIONS
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    SEARCH = "search"
    EXPORT = "export"
    IMPORT = "import"
    TRANSFORM = "transform"
    # EXECUTION
    EXECUTE = "execute"
    RUN_CODE = "run_code"
    RUN_COMMAND = "run_command"
    SPAWN_PROCESS = "spawn_process"
    SCHEDULE = "schedule"
    DELEGATE = "delegate"
    # NETWORK
    HTTP_REQUEST = "http_request"
    HTTPS_REQUEST = "https_request"
    FETCH_URL = "fetch_url"
    WEB_SEARCH = "web_search"
    API_CALL = "api_call"
    INTERNAL_NETWORK_ACCESS = "internal_network_access"
    EXTERNAL_NETWORK_ACCESS = "external_network_access"
    # COMMUNICATION
    SEND_EMAIL = "send_email"
    SEND_MESSAGE = "send_message"
    CREATE_NOTIFICATION = "create_notification"
    POST = "post"
    PUBLISH = "publish"
    # FILESYSTEM
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    MOVE_FILE = "move_file"
    COPY_FILE = "copy_file"
    LIST_DIRECTORY = "list_directory"
    # DATABASE
    READ_DATABASE = "read_database"
    WRITE_DATABASE = "write_database"
    UPDATE_DATABASE = "update_database"
    DELETE_DATABASE = "delete_database"
    EXECUTE_QUERY = "execute_query"
    EXECUTE_PROCEDURE = "execute_procedure"
    # IDENTITY
    AUTHENTICATE = "authenticate"
    AUTHORIZE = "authorize"
    ASSUME_ROLE = "assume_role"
    IMPERSONATE = "impersonate"
    CREATE_USER = "create_user"
    MODIFY_USER = "modify_user"
    MODIFY_PERMISSION = "modify_permission"
    # SECRETS
    READ_SECRET = "read_secret"
    ACCESS_CREDENTIAL = "access_credential"
    ACCESS_TOKEN = "access_token"
    READ_ENVIRONMENT = "read_environment"
    ACCESS_PRIVATE_KEY = "access_private_key"
    # AGENTIC
    DELEGATE_TO_AGENT = "delegate_to_agent"
    CALL_AGENT = "call_agent"
    SPAWN_AGENT = "spawn_agent"
    PASS_CONTEXT = "pass_context"
    MODIFY_AGENT_STATE = "modify_agent_state"
    # fallback — never discard
    UNKNOWN_CAPABILITY = "unknown_capability"


class CapabilityCategory(str, enum.Enum):
    DATA = "data"
    EXECUTION = "execution"
    NETWORK = "network"
    COMMUNICATION = "communication"
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    IDENTITY = "identity"
    SECRETS = "secrets"
    AGENTIC = "agentic"
    UNKNOWN = "unknown"


# operation -> category, used by the deterministic classifier
OPERATION_CATEGORY: dict[CapabilityOperation, CapabilityCategory] = {
    **{op: CapabilityCategory.DATA for op in (
        CapabilityOperation.READ, CapabilityOperation.WRITE, CapabilityOperation.UPDATE,
        CapabilityOperation.DELETE, CapabilityOperation.LIST, CapabilityOperation.SEARCH,
        CapabilityOperation.EXPORT, CapabilityOperation.IMPORT, CapabilityOperation.TRANSFORM,
    )},
    **{op: CapabilityCategory.EXECUTION for op in (
        CapabilityOperation.EXECUTE, CapabilityOperation.RUN_CODE, CapabilityOperation.RUN_COMMAND,
        CapabilityOperation.SPAWN_PROCESS, CapabilityOperation.SCHEDULE, CapabilityOperation.DELEGATE,
    )},
    **{op: CapabilityCategory.NETWORK for op in (
        CapabilityOperation.HTTP_REQUEST, CapabilityOperation.HTTPS_REQUEST, CapabilityOperation.FETCH_URL,
        CapabilityOperation.WEB_SEARCH, CapabilityOperation.API_CALL,
        CapabilityOperation.INTERNAL_NETWORK_ACCESS, CapabilityOperation.EXTERNAL_NETWORK_ACCESS,
    )},
    **{op: CapabilityCategory.COMMUNICATION for op in (
        CapabilityOperation.SEND_EMAIL, CapabilityOperation.SEND_MESSAGE,
        CapabilityOperation.CREATE_NOTIFICATION, CapabilityOperation.POST, CapabilityOperation.PUBLISH,
    )},
    **{op: CapabilityCategory.FILESYSTEM for op in (
        CapabilityOperation.READ_FILE, CapabilityOperation.WRITE_FILE, CapabilityOperation.DELETE_FILE,
        CapabilityOperation.MOVE_FILE, CapabilityOperation.COPY_FILE, CapabilityOperation.LIST_DIRECTORY,
    )},
    **{op: CapabilityCategory.DATABASE for op in (
        CapabilityOperation.READ_DATABASE, CapabilityOperation.WRITE_DATABASE,
        CapabilityOperation.UPDATE_DATABASE, CapabilityOperation.DELETE_DATABASE,
        CapabilityOperation.EXECUTE_QUERY, CapabilityOperation.EXECUTE_PROCEDURE,
    )},
    **{op: CapabilityCategory.IDENTITY for op in (
        CapabilityOperation.AUTHENTICATE, CapabilityOperation.AUTHORIZE, CapabilityOperation.ASSUME_ROLE,
        CapabilityOperation.IMPERSONATE, CapabilityOperation.CREATE_USER, CapabilityOperation.MODIFY_USER,
        CapabilityOperation.MODIFY_PERMISSION,
    )},
    **{op: CapabilityCategory.SECRETS for op in (
        CapabilityOperation.READ_SECRET, CapabilityOperation.ACCESS_CREDENTIAL,
        CapabilityOperation.ACCESS_TOKEN, CapabilityOperation.READ_ENVIRONMENT,
        CapabilityOperation.ACCESS_PRIVATE_KEY,
    )},
    **{op: CapabilityCategory.AGENTIC for op in (
        CapabilityOperation.DELEGATE_TO_AGENT, CapabilityOperation.CALL_AGENT, CapabilityOperation.SPAWN_AGENT,
        CapabilityOperation.PASS_CONTEXT, CapabilityOperation.MODIFY_AGENT_STATE,
    )},
    CapabilityOperation.UNKNOWN_CAPABILITY: CapabilityCategory.UNKNOWN,
}


class ProvenanceState(str, enum.Enum):
    """A capability's declared/observed/inferred state is not exclusive —
    CapabilityFrame carries all three as independent booleans (spec
    section 7). This enum is used only where a single dominant label is
    needed (e.g. API summaries, event payloads)."""
    DECLARED_ONLY = "declared_only"
    OBSERVED_ONLY = "observed_only"          # undeclared-but-observed: the important case
    DECLARED_AND_OBSERVED = "declared_and_observed"
    INFERRED_ONLY = "inferred_only"


class DataSensitivity(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PII = "pii"
    CREDENTIALS = "credentials"
    SECRETS = "secrets"
    FINANCIAL = "financial"
    HEALTH = "health"
    SOURCE_CODE = "source_code"
    SYSTEM_CONFIG = "system_config"
    USER_DATA = "user_data"
    UNKNOWN = "unknown"


class ResourceType(str, enum.Enum):
    DATABASE = "database"
    FILESYSTEM = "filesystem"
    INTERNAL_NETWORK = "internal_network"
    EXTERNAL_NETWORK = "external_network"
    EXTERNAL_RECIPIENT = "external_recipient"
    UNKNOWN = "unknown"


class TrustLevel(str, enum.Enum):
    USER = "user"
    AGENT = "agent"
    EXTERNAL_CONTENT = "external_content"
    RAG_CONTENT = "rag_content"
    TOOL = "tool"
    DATABASE = "database"
    FILESYSTEM = "filesystem"
    EXTERNAL_NETWORK = "external_network"
    INTERNAL_NETWORK = "internal_network"
    OTHER_AGENT = "other_agent"
    UNKNOWN = "unknown"


class DestructiveRisk(str, enum.Enum):
    NONE = "none"
    POSSIBLE = "possible"
    LIKELY = "likely"
    UNKNOWN = "unknown"


class CapabilityStatus(str, enum.Enum):
    """Used for the declared-vs-observed diff (spec section 8)."""
    DECLARED = "declared"
    DECLARED_OBSERVED = "declared_observed"
    UNDECLARED_OBSERVED = "undeclared_observed"


class GraphNodeType(str, enum.Enum):
    AGENT = "agent"
    TOOL = "tool"
    CAPABILITY = "capability"
    RESOURCE = "resource"
    DATA = "data"
    ROLE = "role"
    PERMISSION = "permission"
    TRUST_BOUNDARY = "trust_boundary"
    EXTERNAL_ENDPOINT = "external_endpoint"
    INTERNAL_ENDPOINT = "internal_endpoint"
    OTHER_AGENT = "other_agent"


class GraphEdgeType(str, enum.Enum):
    CAN_READ = "can_read"
    CAN_WRITE = "can_write"
    CAN_DELETE = "can_delete"
    CAN_EXECUTE = "can_execute"
    CAN_ACCESS = "can_access"
    CAN_CALL = "can_call"
    CAN_TRIGGER = "can_trigger"
    CAN_CHAIN = "can_chain"
    REQUIRES_ROLE = "requires_role"
    REQUIRES_PERMISSION = "requires_permission"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    TRANSFORMS = "transforms"
    SENDS_TO = "sends_to"
    RECEIVES_FROM = "receives_from"
    CROSSES_BOUNDARY = "crosses_boundary"
    AUTHENTICATES_AS = "authenticates_as"
    DELEGATES_TO = "delegates_to"


class SecuritySpecialist(str, enum.Enum):
    """The five existing agents — Capability Intelligence maps hypotheses
    onto these, it never replaces them (spec sections 2, 19, 20)."""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    TOOL_ABUSE = "tool_abuse"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class HypothesisPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CoverageState(str, enum.Enum):
    TESTED = "tested"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    NOT_TESTED = "not_tested"
    NOT_APPLICABLE = "not_applicable"
