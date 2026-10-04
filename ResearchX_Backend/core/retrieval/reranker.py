"""bge-reranker-v2-m3 重排序器。"""
from __future__ import annotations

from core.common.types import EvidenceChunk


class BGEReranker:
    """基于 sentence-transformers CrossEncoder 的重排序。"""

    def __init__(self, model_path: str):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_path)

    def rerank(
        self, query: str, candidates: list[EvidenceChunk], top_n: int = 8
    ) -> list[EvidenceChunk]:
        if not candidates:
            return []
        pairs = [[query, c.text] for c in candidates]
        scores = self.model.predict(pairs)
        rescored = [
            c.model_copy(update={"rerank_score": float(s)})
            for c, s in zip(candidates, scores)
        ]
        return sorted(
            rescored, key=lambda x: x.rerank_score or 0.0, reverse=True
        )[:top_n]
