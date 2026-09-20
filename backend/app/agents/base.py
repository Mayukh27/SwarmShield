"""
BaseAgent: every Planner/Specialist/Sentinel agent subclasses this. It
just standardizes how a system prompt + input turns into a (typically
JSON) structured output via the Gemini client.
"""
import re
from abc import ABC
from typing import Any

from app.services import context_manager, gemini_client


class BaseAgent(ABC):
    #: Override in subclasses — this is the agent's fixed system instruction.
    SYSTEM_PROMPT: str = ""
    #: Optional override of the label used to attribute LLM token usage to
    #: this agent. By default it is derived from the class name, e.g.
    #: PlannerAgent -> "planner", PromptInjectionSpecialist ->
    #: "prompt_injection_specialist" (the same vocabulary as AgentType).
    AGENT_LABEL: str | None = None

    def __init__(self, temperature: float = 0.7):
        self.temperature = temperature

    def run(self, user_content: str, as_json: bool = True) -> Any:
        if not self.SYSTEM_PROMPT:
            raise NotImplementedError("Subclasses must set SYSTEM_PROMPT")
        # Attribution only: tags the active scan context (if any) so real token
        # usage recorded during this call is credited to this agent. The call
        # itself and its return value are unchanged.
        with context_manager.agent_scope(self.agent_label()):
            return gemini_client.generate(
                system_instruction=self.SYSTEM_PROMPT,
                user_content=user_content,
                as_json=as_json,
                temperature=self.temperature,
            )

    @classmethod
    def agent_label(cls) -> str:
        if cls.AGENT_LABEL:
            return cls.AGENT_LABEL
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return snake.removesuffix("_agent")
