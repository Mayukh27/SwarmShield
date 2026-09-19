"""
BaseAgent: every Planner/Specialist/Sentinel agent subclasses this. It
just standardizes how a system prompt + input turns into a (typically
JSON) structured output via the Gemini client.
"""
from abc import ABC
from typing import Any

from app.services import gemini_client


class BaseAgent(ABC):
    #: Override in subclasses — this is the agent's fixed system instruction.
    SYSTEM_PROMPT: str = ""

    def __init__(self, temperature: float = 0.7):
        self.temperature = temperature

    def run(self, user_content: str, as_json: bool = True) -> Any:
        if not self.SYSTEM_PROMPT:
            raise NotImplementedError("Subclasses must set SYSTEM_PROMPT")
        return gemini_client.generate(
            system_instruction=self.SYSTEM_PROMPT,
            user_content=user_content,
            as_json=as_json,
            temperature=self.temperature,
        )
