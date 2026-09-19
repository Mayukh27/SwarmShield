"""SwarmShield: security middleware for agent-to-agent (A2A) communication."""

from swarmshield.exceptions import (
    SwarmShieldCircuitBreakerException,
    SwarmShieldError,
    SwarmShieldSecurityException,
    SwarmShieldUnavailableError,
)

__version__ = "0.1.0"

__all__ = [
    "SwarmShieldError",
    "SwarmShieldSecurityException",
    "SwarmShieldCircuitBreakerException",
    "SwarmShieldUnavailableError",
    "__version__",
]
