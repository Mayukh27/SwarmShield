"""SwarmShield: security middleware for agent-to-agent (A2A) communication."""

from swarmshield.exceptions import (
    SwarmShieldCircuitBreakerException,
    SwarmShieldError,
    SwarmShieldSecurityException,
    SwarmShieldUnavailableError,
)
from swarmshield.sdk import check, protect_agent

__version__ = "0.1.0"

__all__ = [
    "SwarmShieldError",
    "SwarmShieldSecurityException",
    "SwarmShieldCircuitBreakerException",
    "SwarmShieldUnavailableError",
    "protect_agent",
    "check",
    "__version__",
]
