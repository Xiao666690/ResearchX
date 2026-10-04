"""Research Executor: execute one action and return an observation."""
from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

from core.research.schemas import AgentAction, Observation, ResearchState, StepResult, TaskPlan
from core.skills.registry import SkillRegistry


class Executor:
    def __init__(self, registry: SkillRegistry, ctx: dict | None = None):
        self.registry = registry
        self.ctx = ctx or {}

    async def execute_action(self, action: AgentAction, state: ResearchState,
                             context: dict | None = None) -> Observation:
        outputs = {item.step_id: item.output for item in state.observations}
        successful_steps = {item.step_id for item in state.observations if item.status == "SUCCESS"}
        # A successful retry fulfills references to its original plan step.
        for step in state.plan.steps:
            if step.retry_of and step.step_id in successful_steps:
                outputs[step.retry_of] = outputs[step.step_id]
        skill_input = self._resolve_references(action.input, outputs)
        run_context = {**self.ctx, **(context or {})}
        started = time.monotonic()
        if not self.registry.has(action.skill):
            return Observation(action_id=action.action_id, step_id=action.step_id,
                               skill=action.skill, status="FAILED", error_code="UNKNOWN_SKILL",
                               error=f"未知技能: {action.skill}")
        skill = self.registry.get(action.skill)
        try:
            skill.validate(skill_input)
            # Existing skills use blocking SDK calls. Keep the loop responsive and
            # bound how long it waits for each invocation.
            result = await asyncio.wait_for(
                asyncio.to_thread(lambda: asyncio.run(skill.run(skill_input, run_context))),
                timeout=max(1, int(getattr(skill, "timeout_s", 60))),
            )
            status = ("NEED_MORE_EVIDENCE" if result.error_code == "NEED_MORE_EVIDENCE"
                      else "SUCCESS" if result.ok else "FAILED")
            return Observation(
                action_id=action.action_id, step_id=action.step_id, skill=action.skill,
                status=status, output=result.output, evidence_ids=result.evidence,
                artifacts=result.artifacts, error_code=result.error_code,
                error=result.error_message,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        except asyncio.TimeoutError:
            error_code, error = "TIMEOUT", f"技能超时（{skill.timeout_s} 秒）"
        except Exception as exc:
            error_code, error = "INVALID_ACTION", str(exc)
        return Observation(
            action_id=action.action_id, step_id=action.step_id, skill=action.skill,
            status="FAILED", error_code=error_code, error=error,
            duration_ms=int((time.monotonic() - started) * 1000),
        )

    async def run(self, plan: TaskPlan, context: dict | None = None) -> list[StepResult]:
        """Compatibility entry point for the former sequential executor."""
        state = ResearchState(task_id=plan.task_id, goal=plan.goal, plan=plan)
        for step in plan.steps:
            observation = await self.execute_action(AgentAction(
                action_id=step.step_id, step_id=step.step_id, skill=step.skill,
                input=step.input), state, context)
            state.observations.append(observation)
            state.step_results.append(StepResult(
                step_id=step.step_id, status=observation.status,
                output={**observation.output, "artifacts": observation.artifacts},
                evidence_ids=observation.evidence_ids, error=observation.error,
                duration_ms=observation.duration_ms,
            ))
        return state.step_results

    @staticmethod
    def _resolve_references(value: Any, outputs: dict[str, dict]) -> Any:
        if isinstance(value, dict):
            return {key: Executor._resolve_references(item, outputs) for key, item in value.items()}
        if isinstance(value, list):
            return [Executor._resolve_references(item, outputs) for item in value]
        if not isinstance(value, str):
            return value
        pattern = re.compile(r"\{\{\s*([\w-]+)(?:\.(?:result|output))?\s*\}\}")

        def replace(match: re.Match[str]) -> str:
            return json.dumps(outputs.get(match.group(1), {}), ensure_ascii=False, default=str)

        return pattern.sub(replace, value)
