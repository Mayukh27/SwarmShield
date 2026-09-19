"""
Generic client used by attacker agents to send a payload to the target
agentic system and get its response back. Kept deliberately simple:
POSTs {"input": payload} and expects {"output": "..."} or similar — since
the whole point of SwarmShield is to work against arbitrary target agents,
this should be the thinnest possible adapter. Extend `_extract_output` if
a target uses a different response shape.
"""
from typing import Any, Optional

import httpx

from app.models.target import TargetProfile


class TargetClient:
    def __init__(self, target: TargetProfile, timeout: float = 30.0):
        self.target = target
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.target.auth_header_name and self.target.auth_header_value:
            headers[self.target.auth_header_name] = self.target.auth_header_value
        return headers

    async def send(self, payload: str) -> dict[str, Any]:
        """
        Sends `payload` to the target's endpoint and returns a normalized
        dict: {"raw": <full response json or text>, "output": <best-guess
        extracted text response>}.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    self.target.endpoint_url,
                    headers=self._headers(),
                    json={"input": payload},
                )
                resp.raise_for_status()
                try:
                    data = resp.json()
                except ValueError:
                    return {"raw": resp.text, "output": resp.text}
                return {"raw": data, "output": self._extract_output(data)}
            except httpx.HTTPError as e:
                return {"raw": str(e), "output": None, "error": str(e)}

    @staticmethod
    def _extract_output(data: Any) -> Optional[str]:
        """Best-effort extraction of a text response from common shapes."""
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            for key in ("output", "response", "text", "message", "reply", "content"):
                if key in data and isinstance(data[key], str):
                    return data[key]
        return str(data)
