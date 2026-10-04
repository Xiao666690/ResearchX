"""Backend transport for an AgentArts deployed Runtime gateway."""
from __future__ import annotations

import os

import requests

from core.research.schemas import ResearchState


class AgentArtsRuntimeClient:
    def __init__(self, endpoint: str | None = None, api_key: str | None = None):
        self.endpoint = endpoint or os.getenv("AGENTARTS_INVOCATION_URL", "")
        self.api_key = api_key or os.getenv("AGENTARTS_API_KEY", "")
        if not self.endpoint.startswith("https://") or not self.endpoint.endswith("/invocations"):
            raise ValueError("AGENTARTS_INVOCATION_URL 必须是 HTTPS /invocations 地址")
        if not self.api_key:
            raise ValueError("AGENTARTS_API_KEY 未配置")

    def run(self, goal: str, session_id: str, model: str = "deepseek") -> ResearchState:
        response = requests.post(
            self.endpoint,
            json={"goal": goal, "model": model},
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "x-hw-agentarts-session-id": session_id,
            },
            timeout=(15, int(os.getenv("RESEARCH_TIMEOUT_S", "900")) + 30),
        )
        response.raise_for_status()
        payload = response.json()
        return ResearchState.model_validate(payload["state"])
