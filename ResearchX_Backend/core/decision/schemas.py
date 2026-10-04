"""Typed Decision Schema。

把 Intent / Evidence / Grounding 等高频控制节点从自由文本生成中解耦，
统一输出带置信度的结构化决策。
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    PAPER_QA = "PAPER_QA"
    MULTI_PAPER_QA = "MULTI_PAPER_QA"
    RESEARCH_TASK = "RESEARCH_TASK"
    EXPERIMENT_TASK = "EXPERIMENT_TASK"
    GENERAL_CHAT = "GENERAL_CHAT"


class IntentDecision(BaseModel):
    intent: IntentType
    confidence: float = Field(ge=0, le=1)
    reason_code: str = ""


class EvidenceDecision(BaseModel):
    decision: Literal["ANSWER", "EXPAND_LOCAL", "SEARCH_EXTERNAL", "ABSTAIN"]
    confidence: float = Field(ge=0, le=1)
    evidence_score: float = Field(ge=0, le=1)
    missing_aspects: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(default_factory=list)


class RelatednessDecision(BaseModel):
    """兼容旧 chat_judge_relate 的结构化结果。"""

    is_relevant: bool
    is_professional: bool
    arxiv_query_keyword: list[str] = Field(default_factory=list)


class GroundingDecision(BaseModel):
    passed: bool
    confidence: float = Field(ge=0, le=1)
    unsupported_claims: list[str] = Field(default_factory=list)
