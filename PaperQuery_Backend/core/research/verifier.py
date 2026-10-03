"""Research Verifier：检查任务是否满足成功条件。"""
from __future__ import annotations

from core.research.schemas import StepResult, TaskPlan


class Verifier:
    def verify(
        self, plan: TaskPlan, step_results: list[StepResult], artifacts: list[dict]
    ) -> tuple[bool, dict]:
        """首版：所有步骤必须 SUCCESS 才算完成。"""
        all_success = all(r.status == "SUCCESS" for r in step_results)
        checks = {
            "all_steps_success": all_success,
            "completed_steps": sum(1 for r in step_results if r.status == "SUCCESS"),
            "total_steps": len(plan.steps),
        }
        return all_success, checks
