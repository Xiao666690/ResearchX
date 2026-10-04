"""citation_verify：批量校验 claim-evidence 支持情况。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.skills.base import BaseSkill, SkillResult


class CitationVerifyInput(BaseModel):
    question: str = ""
    answer: str
    evidence: dict[str, str] = Field(default_factory=dict)  # cid -> text


class CitationVerifySkill(BaseSkill):
    name = "citation_verify"
    description = "校验回答中的事实性结论是否有证据支持，输出 pass/unsupported"
    input_model = CitationVerifyInput

    async def execute(self, data: CitationVerifyInput, ctx: dict) -> SkillResult:
        verifier = ctx.get("grounding_verifier")
        if verifier is None:
            engine = ctx.get("decision_engine")
            if engine is None:
                return SkillResult(ok=False, error_code="NO_VERIFIER", error_message="Grounding 组件未初始化")
            from core.evidence.grounding import GroundingVerifier

            verifier = GroundingVerifier(engine)

        from core.common.types import Citation, EvidenceChunk

        citations = [
            Citation(citation_id=cid, document_id="", page_number=0, chunk_id="", quote=text[:200])
            for cid, text in data.evidence.items()
        ]
        evidence_map = {
            cid: EvidenceChunk(chunk_id="", document_id="", source="", page_number=0, text=text)
            for cid, text in data.evidence.items()
        }

        passed, report = verifier.verify(data.question, data.answer, citations, evidence_map)
        return SkillResult(ok=passed, output=report)
