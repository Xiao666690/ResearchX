"""Artifact 构建器：把 Skill 输出组装为结构化 Artifact。"""
from __future__ import annotations

import uuid

from core.artifact.models import Artifact


def build_artifact(
    artifact_type: str,
    title: str,
    data: dict,
    citations: list[dict] | None = None,
) -> Artifact:
    return Artifact(
        artifact_id=uuid.uuid4().hex[:12],
        type=artifact_type,  # type: ignore[arg-type]
        title=title,
        data=data,
        citations=citations or [],
    )


def build_comparison_table(rows: list[dict], columns: list[str], citations: list[dict] | None = None) -> Artifact:
    return build_artifact(
        "comparison_table",
        "论文对比表",
        {"columns": columns, "rows": rows},
        citations,
    )


def build_research_report(markdown: str, citations: list[dict] | None = None) -> Artifact:
    return build_artifact(
        "research_report",
        "研究报告",
        {"markdown": markdown},
        citations,
    )
