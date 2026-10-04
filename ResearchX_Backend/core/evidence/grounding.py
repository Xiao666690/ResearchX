"""Grounding Verify：回答事实性结论的证据核验。

首版采用「规则校验 + LLM Judge」组合：
- 规则1：回答中引用的 [C#] 必须存在于 citation 列表；
- 规则2：LLM Judge 输出 unsupported_claims。
"""
from __future__ import annotations

import re
from typing import Optional

from core.common.types import Citation, EvidenceChunk
from core.decision.engine import DecisionEngine


class GroundingVerifier:
    def __init__(self, decision_engine: Optional[DecisionEngine] = None):
        self.decision_engine = decision_engine

    def verify(
        self,
        question: str,
        answer: str,
        citations: list[Citation],
        evidence_map: dict[str, EvidenceChunk],
    ) -> tuple[bool, dict]:
        """返回 (passed, report)。"""
        # 规则1：引用 ID 必须存在
        used_ids = re.findall(r"\[(C\d+)\]", answer)
        valid_ids = {c.citation_id for c in citations}
        unknown_ids = [i for i in used_ids if i not in valid_ids]

        # 规则2：LLM Judge
        unsupported: list[str] = []
        confidence = 0.0
        judge_passed = True
        if self.decision_engine is not None:
            evidence_text = "\n\n".join(
                f"[{cid}] {e.text}" for cid, e in evidence_map.items()
            )
            judge = self.decision_engine.verify_grounding(
                question, answer, evidence_text
            )
            unsupported = judge.unsupported_claims
            confidence = judge.confidence
            judge_passed = judge.passed

        passed = judge_passed and not unknown_ids
        report = {
            "unknown_citations": unknown_ids,
            "unsupported_claims": unsupported,
            "confidence": confidence,
        }
        return passed, report
