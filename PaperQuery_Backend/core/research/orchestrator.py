"""Research Orchestrator：编排 Planner → Executor → Verifier。"""
from __future__ import annotations

import asyncio

from core.research.executor import Executor
from core.research.planner import Planner
from core.research.schemas import TaskState
from core.research.verifier import Verifier


class ResearchOrchestrator:
    def __init__(self, planner: Planner, executor: Executor, verifier: Verifier):
        self.planner = planner
        self.executor = executor
        self.verifier = verifier

    def run(self, goal: str, context: dict | None = None) -> TaskState:
        context = context or {}
        plan = self.planner.plan(
            goal, task_id=context.get("_task_id"), llm=context.get("_research_llm"),
            allowed_document_ids=context.get("allowed_document_ids"),
            available_documents=context.get("available_documents"),
        )
        if callable(context.get("_on_plan")):
            context["_on_plan"](plan)
        step_results = asyncio.run(self.executor.run(plan, context=context))

        artifacts: list[dict] = []
        for r in step_results:
            for a in r.output.get("artifacts", []):
                if isinstance(a, dict):
                    artifacts.append(a)

        ok, _checks = self.verifier.verify(plan, step_results, artifacts)
        return TaskState(
            task_id=plan.task_id,
            goal=goal,
            status="SUCCESS" if ok else "FAILED",
            plan=plan,
            step_results=step_results,
            artifacts=artifacts,
        )
