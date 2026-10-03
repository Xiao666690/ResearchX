"""Research Executor：顺序执行计划中的步骤。"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from core.research.schemas import StepResult, TaskPlan
from core.skills.registry import SkillRegistry


class Executor:
    def __init__(self, registry: SkillRegistry, ctx: dict | None = None):
        self.registry = registry
        self.ctx = ctx or {}

    async def run(self, plan: TaskPlan, context: dict | None = None) -> list[StepResult]:
        results: list[StepResult] = []
        step_outputs: dict[str, dict] = {}
        step_statuses: dict[str, str] = {}
        run_context = {**self.ctx, **(context or {})}

        for step in plan.steps:
            failed_dependencies = [
                dep for dep in step.depends_on if step_statuses.get(dep) != "SUCCESS"
            ]
            if failed_dependencies:
                result = StepResult(
                    step_id=step.step_id,
                    status="FAILED",
                    error=f"前置步骤失败或缺失: {', '.join(failed_dependencies)}",
                    duration_ms=0,
                )
                results.append(result)
                step_outputs[step.step_id] = {}
                step_statuses[step.step_id] = result.status
                if callable(run_context.get("_on_step")):
                    run_context["_on_step"](step, result)
                continue

            skill = self.registry.get(step.skill)
            skill_input = self._resolve_references(step.input, step_outputs)
            if callable(run_context.get("_on_step_start")):
                run_context["_on_step_start"](step)

            start = time.time()
            result = await skill.run(skill_input, run_context)
            duration_ms = int((time.time() - start) * 1000)
            status = "SUCCESS" if result.ok else "FAILED"
            if result.error_code == "NEED_MORE_EVIDENCE":
                status = "NEED_MORE_EVIDENCE"

            step_result = StepResult(
                step_id=step.step_id,
                status=status,  # type: ignore[arg-type]
                output={**result.output, "artifacts": result.artifacts},
                evidence_ids=result.evidence,
                error=result.error_message,
                duration_ms=duration_ms,
            )
            step_outputs[step.step_id] = result.output
            step_statuses[step.step_id] = step_result.status
            results.append(step_result)
            if callable(run_context.get("_on_step")):
                run_context["_on_step"](step, step_result)

        return results

    @staticmethod
    def _resolve_references(value: Any, outputs: dict[str, dict]) -> Any:
        """把 Planner 生成的 {{s1.result}} / {{s1.output}} 引用替换为真实结果。"""
        if isinstance(value, dict):
            return {
                key: Executor._resolve_references(item, outputs)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [Executor._resolve_references(item, outputs) for item in value]
        if not isinstance(value, str):
            return value

        pattern = re.compile(r"\{\{\s*([\w-]+)(?:\.(?:result|output))?\s*\}\}")

        def replace(match: re.Match[str]) -> str:
            step_id = match.group(1)
            return json.dumps(outputs.get(step_id, {}), ensure_ascii=False, default=str)

        return pattern.sub(replace, value)
