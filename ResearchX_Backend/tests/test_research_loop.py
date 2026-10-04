"""Behavioral acceptance tests for the local Research Agent loop."""
import unittest
from types import SimpleNamespace

from pydantic import BaseModel, Field

from core.evidence.gate import ResearchEvidenceGate
from core.research.executor import Executor
from core.research.orchestrator import ResearchOrchestrator
from core.research.planner import Planner
from core.research.schemas import Observation, ResearchState, TaskPlan
from core.research.verifier import Verifier
from core.skills.base import BaseSkill, SkillResult
from core.skills.registry import SkillRegistry


class FakeLLM:
    def invoke(self, prompt):
        if "先前检索" in prompt:
            return '{"keywords": ["adaptive retrieval evaluation"], "max_results": 10}'
        return ('{"goal": "比较检索方法", "steps": ['
                '{"step_id":"s1","title":"检索论文","skill":"paper_search",'
                '"input":{"keywords":["retrieval"]}},'
                '{"step_id":"s2","title":"生成报告","skill":"report_generate",'
                '"depends_on":["s1"],"input":{"topic":"比较检索方法"}}],'
                '"expected_artifacts":["report"]}')


class SearchInput(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    max_results: int = 10


class FakeSearch(BaseSkill):
    name = "paper_search"
    description = "Search fixture"
    input_model = SearchInput

    def __init__(self, counts, fail_first=False):
        self.counts = counts
        self.fail_first = fail_first
        self.calls = []

    async def execute(self, data, ctx):
        self.calls.append(data.keywords)
        if self.fail_first and len(self.calls) == 1:
            return SkillResult(ok=False, error_code="SEARCH_ERROR", error_message="temporary outage")
        count = self.counts[min(len(self.calls) - 1, len(self.counts) - 1)]
        return SkillResult(ok=True, output={"papers": [
            {"title": f"Paper {index}", "summary": f"Relevant abstract {index}",
             "pdf_url": f"https://example.org/{index}"}
            for index in range(count)
        ]})


class ReportInput(BaseModel):
    topic: str
    context: str = ""
    citations: list[dict] = Field(default_factory=list)


class FakeReport(BaseSkill):
    name = "report_generate"
    description = "Report fixture"
    input_model = ReportInput

    async def execute(self, data, ctx):
        return SkillResult(ok=True, artifacts=[{
            "type": "research_report", "title": data.topic,
            "markdown": "方法 A 有相关研究 [C1]，方法 B 也有相关研究 [C2]。",
        }])


class ResearchLoopTests(unittest.TestCase):
    def make_agent(self, counts, fail_first=False):
        registry = SkillRegistry()
        search = FakeSearch(counts, fail_first)
        registry.register(search)
        registry.register(FakeReport())
        planner = Planner(FakeLLM(), registry)
        return ResearchOrchestrator(planner, Executor(registry), Verifier(),
                                    ResearchEvidenceGate()), search

    def test_partial_evidence_causes_new_search_before_report(self):
        agent, search = self.make_agent([2, 5])
        events = []
        checkpoints = []
        state = agent.run("比较检索方法", context={
            "_on_event": lambda event: events.append(event.event_type),
            "_on_state": lambda value: checkpoints.append(value.turn_count),
        })
        self.assertEqual(state.status, "SUCCESS")
        self.assertEqual(state.replan_count, 1)
        self.assertEqual(len(search.calls), 2)
        self.assertNotEqual(search.calls[0], search.calls[1])
        self.assertEqual([action.skill for action in state.tool_history],
                         ["paper_search", "paper_search", "report_generate"])
        self.assertEqual(state.stop_reason, "GOAL_COMPLETED")
        self.assertIn("PARTIAL", [event.title for event in state.events])
        self.assertIn("REPLAN", events)
        self.assertEqual(events[-1], "FINISH")
        self.assertEqual(checkpoints[-1], 3)

    def test_insufficient_evidence_stops_without_report(self):
        agent, _ = self.make_agent([0])
        state = agent.run("比较检索方法")
        self.assertEqual(state.status, "FAILED")
        self.assertEqual(state.stop_reason, "EVIDENCE_INSUFFICIENT")
        self.assertFalse(any(item.get("type") == "research_report" for item in state.artifacts))

    def test_transient_tool_error_is_retried(self):
        agent, search = self.make_agent([3, 3], fail_first=True)
        state = agent.run("比较检索方法")
        self.assertEqual(state.status, "SUCCESS")
        self.assertEqual(len(search.calls), 2)
        self.assertTrue(any(event.event_type == "REPLAN" for event in state.events))

    def test_conflicting_sources_block_synthesis(self):
        class ConflictLLM:
            def invoke(self, prompt):
                return '{"conflict": true, "reason": "同一指标的结论相反"}'

        engine = SimpleNamespace(
            llm=ConflictLLM(),
            decide_evidence=lambda *_: SimpleNamespace(
                decision="ANSWER", evidence_score=0.95,
                missing_aspects=[], search_keywords=[],
            ),
        )
        state = ResearchState(task_id="conflict", goal="比较检索方法",
                              plan=TaskPlan(task_id="conflict", goal="比较检索方法", steps=[]))
        state.observations.append(Observation(
            action_id="search", step_id="search", skill="paper_search", status="SUCCESS",
            output={"papers": [
                {"title": f"Paper {index}", "summary": "互相矛盾的测试结论",
                 "pdf_url": f"https://example.org/{index}"}
                for index in range(3)
            ]},
        ))
        evidence = ResearchEvidenceGate(engine).evaluate(state)
        self.assertEqual(evidence.status, "CONFLICT")
        self.assertIn("结论相反", evidence.reason)


if __name__ == "__main__":
    unittest.main()
