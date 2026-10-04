"""Verify the research goal, evidence and artifact before declaring success."""
from __future__ import annotations

import json
import re

from core.research.schemas import ResearchState, StepResult, TaskPlan, VerificationResult


class Verifier:
    def __init__(self, decision_engine=None):
        self.decision_engine = decision_engine

    def verify_state(self, state: ResearchState) -> VerificationResult:
        evidence_ok = state.evidence_state.status == "SUFFICIENT"
        expected = {"research_report" if value in {"report", "research_report"} else value
                    for value in state.plan.expected_artifacts}
        known = {"research_report", "comparison_table", "paper_list"}
        expected &= known
        found = {item.get("type") for item in state.artifacts}
        artifact_ok = bool(state.artifacts) and expected.issubset(found)
        attempted = {item.step_id for item in state.observations}
        pending = [step for step in state.plan.steps if step.step_id not in attempted]

        if not evidence_ok:
            return VerificationResult(decision="EXPAND_EVIDENCE", evidence_sufficient=False,
                                      artifact_present=artifact_ok,
                                      reason=state.evidence_state.reason or "证据不足")
        if not artifact_ok:
            return VerificationResult(decision="CONTINUE", evidence_sufficient=True,
                                      artifact_present=False, reason="仍需生成预期交付物")
        if pending:
            return VerificationResult(decision="CONTINUE", evidence_sufficient=True,
                                      artifact_present=True, reason="计划中仍有待执行的步骤")

        valid_ids = {source.citation_id for source in state.evidence_state.sources}
        content = "\n\n".join(
            str(item.get("markdown") or item.get("raw") or "") for item in state.artifacts
            if item.get("type") in {"research_report", "comparison_table"}
        )
        used_ids = set(re.findall(r"\[(C\d+)\]", content))
        citations_ok = not content or bool(used_ids) and used_ids.issubset(valid_ids)
        if not citations_ok:
            return VerificationResult(decision="RETRY", evidence_sufficient=True,
                                      artifact_present=True, citations_valid=False,
                                      reason="交付物缺少有效引用或引用了未知来源")

        unsupported: list[str] = []
        goal_complete = True
        if self.decision_engine is not None and content:
            evidence_text = "\n\n".join(
                f"[{source.citation_id}] {source.title}: {source.excerpt[:1200]}"
                for source in state.evidence_state.sources[:16]
            )
            grounding = self.decision_engine.verify_grounding(state.goal, content, evidence_text)
            unsupported = grounding.unsupported_claims
            if not grounding.passed or unsupported:
                return VerificationResult(decision="RETRY", evidence_sufficient=True,
                                          artifact_present=True, citations_valid=True,
                                          unsupported_claims=unsupported,
                                          reason="结论未通过证据核验")
            # The evidence judge handles source relevance. This second question asks
            # whether the delivered result actually addresses the user's goal.
            prompt = (
                "判断研究交付物是否完成目标。只输出 JSON："
                '{"goal_complete": true/false, "reason": "..."}。\n'
                f"目标：{state.goal}\n预期交付物：{sorted(expected)}\n"
                f"交付物：{content[:8000]}"
            )
            try:
                response = self.decision_engine.llm.invoke(prompt)
                raw = response.content if hasattr(response, "content") else str(response)
                verdict = json.loads(re.sub(r"```(?:json)?|```", "", raw).strip())
                goal_complete = verdict.get("goal_complete") is True
                if not goal_complete:
                    return VerificationResult(decision="REPLAN", goal_complete=False,
                                              evidence_sufficient=True, artifact_present=True,
                                              citations_valid=True,
                                              reason=str(verdict.get("reason") or "研究目标尚未完成")[:500])
            except (ValueError, TypeError, KeyError):
                return VerificationResult(decision="RETRY", evidence_sufficient=True,
                                          artifact_present=True, citations_valid=True,
                                          reason="目标完成度判断未能解析")

        return VerificationResult(decision="FINISH", goal_complete=goal_complete,
                                  evidence_sufficient=True, artifact_present=True,
                                  citations_valid=citations_ok, reason="目标与证据核验通过")

    def verify(self, plan: TaskPlan, step_results: list[StepResult],
               artifacts: list[dict]) -> tuple[bool, dict]:
        """Compatibility API for older callers."""
        all_success = bool(step_results) and all(item.status == "SUCCESS" for item in step_results)
        return all_success and bool(artifacts), {
            "all_steps_success": all_success,
            "completed_steps": sum(item.status == "SUCCESS" for item in step_results),
            "total_steps": len(plan.steps),
            "artifact_present": bool(artifacts),
        }
