"""Hybrid Retrieval Pipeline：Dense + Sparse → RRF → Reranker。"""
from __future__ import annotations

from typing import Optional

from core.common.config import Settings, settings
from core.common.types import EvidenceChunk
from core.retrieval.fusion import reciprocal_rank_fusion


class RetrievalPipeline:
    """组合 BGE-M3 Dense、BM25 Sparse、RRF 与 Reranker 的统一检索入口。"""

    def __init__(
        self,
        dense,
        sparse,
        reranker,
        cfg: Optional[Settings] = None,
    ):
        self.dense = dense
        self.sparse = sparse
        self.reranker = reranker
        self.cfg = cfg or settings

    def search(
        self, query: str, document_ids: Optional[list[str]] = None
    ) -> list[EvidenceChunk]:
        dense = self.dense.search(query, document_ids, self.cfg.DENSE_K)
        sparse = self.sparse.search(query, document_ids, self.cfg.SPARSE_K)
        fused = reciprocal_rank_fusion([dense, sparse], c=self.cfg.RRF_C)

        if self.reranker is not None:
            return self.reranker.rerank(
                query, fused[: self.cfg.RERANK_CANDIDATES], self.cfg.FINAL_K
            )
        # 无 reranker 时直接返回融合结果前 FINAL_K
        return fused[: self.cfg.FINAL_K]
