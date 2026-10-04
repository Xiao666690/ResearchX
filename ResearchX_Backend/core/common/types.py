"""V2 公共数据类型。

检索结果与回答结果全程保持结构化对象，避免将 docs 转成字符串后再解析，
这是 Citation、Grounding、RRF 融合与三组实验可复现的共同基础。
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class EvidenceChunk(BaseModel):
    """一条可追溯的证据片段。"""

    chunk_id: str
    document_id: str
    knowledge_id: Optional[str] = None
    source: str
    page_number: int
    text: str
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None
    fusion_score: Optional[float] = None
    rerank_score: Optional[float] = None
    section_title: Optional[str] = None


class Citation(BaseModel):
    """回答中引用的一条证据，前端据此跳页与高亮。"""

    citation_id: str  # 如 C1
    document_id: str
    page_number: int
    chunk_id: str
    quote: str
    knowledge_id: Optional[str] = None
    support_score: Optional[float] = None


class AnswerPackage(BaseModel):
    """经过 Grounding 校验后的最终回答包。"""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    evidence_sufficient: bool = True
    grounding_passed: bool = True
    route: str = "LOCAL_RAG"
    trace_id: Optional[str] = None


# 兼容旧字符串上下文（逐步废弃）
EvidenceContext = str
