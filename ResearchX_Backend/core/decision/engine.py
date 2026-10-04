"""Research Decision Engine。

把 Intent / Evidence / Relatedness 等判断从 ChatAgent 解耦为独立决策层，
统一输出 typed decision；解析失败时 Fail-closed（保守策略）。
"""
from __future__ import annotations

import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel

from core.decision.prompts import (
    EVIDENCE_PROMPT,
    GROUNDING_PROMPT,
    INTENT_PROMPT,
    RELATEDNESS_PROMPT,
)
from core.decision.schemas import (
    EvidenceDecision,
    GroundingDecision,
    IntentDecision,
    IntentType,
    RelatednessDecision,
)

T = TypeVar("T", bound=BaseModel)


_CASUAL_CHAT_PHRASES = {
    "hello",
    "hello there",
    "hi",
    "hey",
    "how are you",
    "你好",
    "您好",
    "嗨",
    "哈喽",
    "在吗",
    "早上好",
    "上午好",
    "中午好",
    "下午好",
    "晚上好",
}


def is_obvious_general_chat(query: str) -> bool:
    """识别无需论文证据的简短问候，避免分类模型异常时误入 RAG。"""
    normalized = re.sub(r"[\s\W_]+", " ", query, flags=re.UNICODE).strip().lower()
    compact = normalized.replace(" ", "")
    return normalized in _CASUAL_CHAT_PHRASES or compact in {
        phrase.replace(" ", "") for phrase in _CASUAL_CHAT_PHRASES
    }


def _clean_json(text: str) -> str:
    """去掉 markdown 代码块与多余空白。"""
    text = re.sub(r"\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*", "", text)
    return text.strip()


class DecisionEngine:
    """基于 LLM Judge 的决策引擎。

    Args:
        llm: langchain ChatOpenAI 实例（支持 .invoke()）。
    """

    def __init__(self, llm):
        self.llm = llm

    def _invoke(self, prompt: str) -> str:
        resp = self.llm.invoke(prompt)
        return resp.content if hasattr(resp, "content") else str(resp)

    def _parse(self, text: str, model_cls: Type[T]) -> T:
        return model_cls.model_validate(json.loads(_clean_json(text)))

    def decide_intent(self, query: str, context_meta: str = "") -> IntentDecision:
        if is_obvious_general_chat(query):
            return IntentDecision(
                intent=IntentType.GENERAL_CHAT,
                confidence=1.0,
                reason_code="CASUAL_GREETING",
            )
        prompt = INTENT_PROMPT.format(question=query, context_meta=context_meta)
        try:
            return self._parse(self._invoke(prompt), IntentDecision)
        except Exception:
            # Fail-safe：复杂请求宁可进入 PAPER_QA 检查，也不直接胡答
            return IntentDecision(
                intent=IntentType.PAPER_QA, confidence=0.0, reason_code="PARSER_FALLBACK"
            )

    def decide_evidence(self, query: str, evidence: str) -> EvidenceDecision:
        if not evidence:
            return EvidenceDecision(
                decision="SEARCH_EXTERNAL", confidence=1.0, evidence_score=0.0
            )
        prompt = EVIDENCE_PROMPT.format(question=query, evidence=evidence)
        try:
            return self._parse(self._invoke(prompt), EvidenceDecision)
        except Exception:
            return EvidenceDecision(
                decision="EXPAND_LOCAL", confidence=0.0, evidence_score=0.0
            )

    def relatedness(self, paper_content: str, question: str) -> RelatednessDecision:
        """兼容旧 chat_judge_relate 的相关性判断。"""
        prompt = RELATEDNESS_PROMPT.format(
            paper_content=paper_content, question=question
        )
        try:
            return self._parse(self._invoke(prompt), RelatednessDecision)
        except Exception:
            # Fail-closed：异常时不确定是否相关，不默认"相关可答"
            return RelatednessDecision(
                is_relevant=False, is_professional=False, arxiv_query_keyword=[]
            )

    def verify_grounding(
        self, question: str, answer: str, evidence: str
    ) -> GroundingDecision:
        prompt = GROUNDING_PROMPT.format(
            question=question, answer=answer, evidence=evidence
        )
        try:
            return self._parse(self._invoke(prompt), GroundingDecision)
        except Exception:
            return GroundingDecision(passed=False, confidence=0.0, unsupported_claims=[])


def relatedness_to_dict(d: RelatednessDecision) -> dict:
    return {
        "is_relevant": d.is_relevant,
        "is_professional": d.is_professional,
        "arxiv_query_keyword": d.arxiv_query_keyword,
    }
