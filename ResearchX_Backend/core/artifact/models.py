"""Artifact 数据模型。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ArtifactType = Literal[
    "paper_list",
    "comparison_table",
    "research_report",
    "evidence_table",
    "experiment_report",
]


class Artifact(BaseModel):
    artifact_id: str
    type: ArtifactType
    title: str
    data: dict = Field(default_factory=dict)
    citations: list[dict] = Field(default_factory=list)
    created_at: Optional[str] = None
