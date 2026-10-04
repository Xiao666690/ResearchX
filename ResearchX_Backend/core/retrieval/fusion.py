"""Reciprocal Rank Fusion。

不比较原始分数，只比较排名，避免 Dense / Sparse 两个检索器分数尺度不一致。
"""
from __future__ import annotations

from collections import defaultdict

from core.common.types import EvidenceChunk


def reciprocal_rank_fusion(
    rank_lists: list[list[EvidenceChunk]], c: int = 60
) -> list[EvidenceChunk]:
    """对多个排序列表做 RRF 融合。

    Args:
        rank_lists: 各检索器返回的已排序 EvidenceChunk 列表。
        c: 平滑常数（默认 60）。
    """
    score: defaultdict[str, float] = defaultdict(float)
    item: dict[str, EvidenceChunk] = {}
    for ranked in rank_lists:
        for rank, e in enumerate(ranked, start=1):
            score[e.chunk_id] += 1.0 / (c + rank)
            item[e.chunk_id] = e

    merged: list[EvidenceChunk] = []
    for cid, s in sorted(score.items(), key=lambda x: x[1], reverse=True):
        merged.append(item[cid].model_copy(update={"fusion_score": s}))
    return merged
