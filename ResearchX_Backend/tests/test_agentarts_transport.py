"""Contract checks for AgentArts HTTP ingress and gateway transport."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from integrations.agentarts.client import AgentArtsRuntimeClient
from integrations.agentarts.runtime_app import app, public_tool_registry


class AgentArtsTransportTests(unittest.TestCase):
    def test_runtime_protocol_and_public_tools(self):
        client = TestClient(app)
        self.assertEqual(client.get("/ping").json(), {"status": "Healthy"})
        self.assertEqual(
            client.post("/invocations", json={"goal": "Compare RAG papers", "document_ids": ["local-1"]}).status_code,
            422,
        )
        self.assertEqual(set(public_tool_registry().names()),
                         {"paper_search", "paper_compare", "report_generate"})

    def test_gateway_auth_and_state_contract(self):
        state = {
            "task_id": "remote", "goal": "Compare RAG papers", "status": "SUCCESS",
            "plan": {"task_id": "remote", "goal": "Compare RAG papers", "steps": []},
        }
        with patch("integrations.agentarts.client.requests.post") as post:
            post.return_value.json.return_value = {"state": state}
            result = AgentArtsRuntimeClient(
                "https://example.com/runtimes/researchx/invocations", "secret"
            ).run("Compare RAG papers", "task123")
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(post.call_args.kwargs["headers"]["x-hw-agentarts-session-id"], "task123")


if __name__ == "__main__":
    unittest.main()
