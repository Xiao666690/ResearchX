"""Bounded observe → decide → act → evidence → verify research loop."""
from __future__ import annotations

import asyncio
import os
import time

from core.evidence.gate import ResearchEvidenceGate
from core.research.executor import Executor
from core.research.planner import Planner
from core.research.schemas import AgentAction, AgentEvent, PlanStep, ResearchState, StepResult
from core.research.verifier import Verifier


class ResearchOrchestrator:
    def __init__(self, planner: Planner, executor: Executor, verifier: Verifier,
                 evidence_gate: ResearchEvidenceGate | None = None):
        self.planner = planner
        self.executor = executor
        self.verifier = verifier
        self.evidence_gate = evidence_gate or ResearchEvidenceGate()

    @staticmethod
    def _limit(name: str, default: int) -> int:
        try:
            return max(1, int(os.getenv(name, str(default))))
        except ValueError:
            return default

    @staticmethod
    def _event(state: ResearchState, context: dict, event_type: str,
               title: str, detail: str = "", data: dict | None = None):
        event = AgentEvent(sequence=len(state.events) + 1, event_type=event_type,
                           title=title, detail=detail, data=data or {})
        state.events.append(event)
        callback = context.get("_on_event")
        if callable(callback):
            callback(event)

    @staticmethod
    def _checkpoint(state: ResearchState, context: dict):
        callback = context.get("_on_state")
        if callable(callback):
            callback(state)

    def run(self, goal: str, context: dict | None = None) -> ResearchState:
        return asyncio.run(self._run(goal, context or {}))

    async def _run(self, goal: str, context: dict) -> ResearchState:
        plan = self.planner.initial_plan(
            goal, task_id=context.get("_task_id"), llm=context.get("_research_llm"),
            allowed_document_ids=context.get("allowed_document_ids"),
            available_documents=context.get("available_documents"),
        )
        if not plan.steps:
            plan.steps.append(PlanStep(step_id="search_1", title="检索相关论文",
                                       skill="paper_search", input={"keywords": [goal[:100]]}))
        state = ResearchState(task_id=plan.task_id, goal=goal, plan=plan, status="RUNNING")
        self._event(state, context, "GOAL", "收到研究目标", goal[:500])
        self._event(state, context, "PLAN", "形成初始计划",
                    f"{len(plan.steps)} 个步骤", {"steps": [step.title for step in plan.steps]})
        if callable(context.get("_on_plan")):
            context["_on_plan"](plan)
        self._checkpoint(state, context)

        max_turns = self._limit("RESEARCH_MAX_TURNS", 12)
        max_replans = self._limit("RESEARCH_MAX_REPLANS", 3)
        max_tool_calls = self._limit("RESEARCH_MAX_TOOL_CALLS", 16)
        failure_budget = self._limit("RESEARCH_FAILURE_BUDGET", 2)
        deadline = time.monotonic() + self._limit("RESEARCH_TIMEOUT_S", 900)

        while state.turn_count < max_turns and state.tool_calls < max_tool_calls:
            if time.monotonic() >= deadline:
                state.stop_reason = "TIMEOUT"
                break
            previous_plan_size = len(state.plan.steps)
            action = self.planner.next_action(state)
            if len(state.plan.steps) != previous_plan_size and callable(context.get("_on_plan")):
                context["_on_plan"](state.plan)
            if action is None:
                verification = self.verifier.verify_state(state)
                self._event(state, context, "VERIFICATION", verification.decision,
                            verification.reason, verification.model_dump())
                if verification.decision == "FINISH":
                    state.status, state.stop_reason = "SUCCESS", "GOAL_COMPLETED"
                else:
                    state.stop_reason = verification.reason or "NO_NEXT_ACTION"
                break

            # Synthesis cannot precede the evidence gate, regardless of the
            # initial plan's ordering or an LLM-generated success claim.
            if action.skill in {"paper_compare", "report_generate"} and state.evidence_state.status != "SUFFICIENT":
                if state.replan_count >= max_replans:
                    state.stop_reason = "EVIDENCE_INSUFFICIENT"
                    break
                self._insert_search_before(state, action.step_id)
                self._event(state, context, "REPLAN", "先补充证据",
                            "生成结论前必须通过证据门控")
                if callable(context.get("_on_plan")):
                    context["_on_plan"](state.plan)
                self._checkpoint(state, context)
                continue

            state.current_step = action.step_id
            state.turn_count += 1
            state.tool_calls += 1
            state.tool_history.append(action)
            step = next(step for step in state.plan.steps if step.step_id == action.step_id)
            if callable(context.get("_on_step_start")):
                context["_on_step_start"](step)
            self._event(state, context, "ACTION", action.skill, action.reason,
                        {"step_id": action.step_id, "input": action.input})
            observation = await self.executor.execute_action(action, state, context)
            state.observations.append(observation)
            result = StepResult(
                step_id=action.step_id, status=observation.status,
                output={**observation.output, "artifacts": observation.artifacts},
                evidence_ids=observation.evidence_ids, error=observation.error,
                duration_ms=observation.duration_ms,
            )
            state.step_results.append(result)
            if callable(context.get("_on_step")):
                context["_on_step"](step, result)
            summary = (f"找到 {len(observation.output.get('papers', []))} 篇论文"
                       if action.skill == "paper_search" and observation.status == "SUCCESS"
                       else observation.error or observation.status)
            self._event(state, context, "OBSERVATION", summary,
                        f"{action.skill} · {observation.duration_ms} ms",
                        {"step_id": action.step_id, "status": observation.status,
                         "evidence_ids": observation.evidence_ids})

            if observation.status != "SUCCESS":
                state.failure_count += 1
                if state.failure_count <= failure_budget and observation.error_code in {
                    "SEARCH_ERROR", "TIMEOUT", "SKILL_ERROR", "NEED_MORE_EVIDENCE"}:
                    retry = PlanStep(step_id=f"retry_{state.turn_count}",
                                     title=f"重试 {action.skill}", skill=action.skill,
                                     input=action.input, retry_of=action.step_id)
                    index = state.plan.steps.index(step)
                    state.plan.steps.insert(index + 1, retry)
                    self._event(state, context, "REPLAN", "工具调用失败，准备恢复",
                                observation.error or observation.error_code or "")
                    if callable(context.get("_on_plan")):
                        context["_on_plan"](state.plan)
                    self._checkpoint(state, context)
                    continue
                state.stop_reason = observation.error_code or "TOOL_FAILURE"
                break

            state.artifacts.extend(observation.artifacts)
            if observation.artifacts:
                self._event(state, context, "ARTIFACT", "生成研究交付物",
                            ", ".join(item.get("title", "") for item in observation.artifacts))
            if action.skill in {"paper_search", "paper_reader", "local_retrieval"}:
                state.evidence_state = self.evidence_gate.evaluate(state)
                self._event(state, context, "EVIDENCE", state.evidence_state.status,
                            state.evidence_state.reason,
                            {"source_count": len(state.evidence_state.sources),
                             "required_sources": state.evidence_state.required_sources,
                             "missing_aspects": state.evidence_state.missing_aspects})
                if state.evidence_state.status != "SUFFICIENT":
                    if state.replan_count >= max_replans:
                        state.stop_reason = "EVIDENCE_INSUFFICIENT"
                        break
                    replanned = self.planner.replan(state, llm=context.get("_research_llm"))
                    state.replan_count += 1
                    self._event(state, context, "REPLAN", "调整检索策略",
                                state.evidence_state.reason,
                                {"step_id": replanned.step_id, "input": replanned.input})
                    if callable(context.get("_on_plan")):
                        context["_on_plan"](state.plan)
                    self._checkpoint(state, context)
                    continue

            verification = self.verifier.verify_state(state)
            self._event(state, context, "VERIFICATION", verification.decision,
                        verification.reason, verification.model_dump())
            if verification.decision == "FINISH":
                state.status, state.stop_reason = "SUCCESS", "GOAL_COMPLETED"
                self._checkpoint(state, context)
                break
            if verification.decision in {"RETRY", "REPLAN"}:
                if observation.artifacts:
                    artifact_ids = {id(item) for item in observation.artifacts}
                    state.artifacts = [item for item in state.artifacts if id(item) not in artifact_ids]
                if state.failure_count >= failure_budget:
                    state.stop_reason = "VERIFICATION_FAILED"
                    break
                state.failure_count += 1
                if action.skill in {"report_generate", "paper_compare"}:
                    revised = PlanStep(step_id=f"revise_{state.turn_count}",
                                       title="依据核验结果修正交付物", skill=action.skill,
                                       input={**action.input, "verification_feedback": (
                                           verification.reason + "；" +
                                           "；".join(verification.unsupported_claims[:5]))[:1500]})
                    index = state.plan.steps.index(step)
                    state.plan.steps.insert(index + 1, revised)
                    if callable(context.get("_on_plan")):
                        context["_on_plan"](state.plan)
                self._event(state, context, "REPLAN", "修正交付物", verification.reason)
            self._checkpoint(state, context)

        if state.status != "SUCCESS":
            state.status = "FAILED"
            state.stop_reason = state.stop_reason or (
                "MAX_TURNS" if state.turn_count >= max_turns else "MAX_TOOL_CALLS")
            self._event(state, context, "STOP", "研究任务已停止", state.stop_reason)
        else:
            self._event(state, context, "FINISH", "研究目标已完成", state.stop_reason or "")
        self._checkpoint(state, context)
        return state

    def _insert_search_before(self, state: ResearchState, step_id: str):
        previous = state.current_step
        state.current_step = step_id
        step = self.planner.replan(state)
        state.replan_count += 1
        state.plan.steps.remove(step)
        index = next(index for index, item in enumerate(state.plan.steps)
                     if item.step_id == step_id)
        state.plan.steps.insert(index, step)
        state.current_step = previous
