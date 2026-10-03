"""Offline hybrid retrieval over the existing ONNX Chroma collection.

The stored vectors remain 384-dimensional ONNX vectors. BGE-M3 scores the
retrieved passages at query time, so installing it does not invalidate papers
that were already indexed with ONNX.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

import numpy as np

from core.common.types import EvidenceChunk
from core.retrieval.fusion import reciprocal_rank_fusion
from core.retrieval.sparse import BM25Retriever

if TYPE_CHECKING:
    from langchain_chroma import Chroma


class LocalRetrievalEnhancer:
    """ONNX dense + BM25 candidates, BGE-M3 scoring, cross-encoder reranking."""

    def __init__(self, embedding_path: str, reranker_path: str):
        from sentence_transformers import CrossEncoder, SentenceTransformer

        self.embedder = SentenceTransformer(embedding_path, device="cpu")
        self.reranker = CrossEncoder(reranker_path, device="cpu", max_length=128)
        self._passage_vectors: OrderedDict[str, np.ndarray] = OrderedDict()

    def _embed_passages(self, passages: list[str]) -> np.ndarray:
        missing = list(dict.fromkeys(text for text in passages if text not in self._passage_vectors))
        if missing:
            vectors = self.embedder.encode(
                [text[:600] for text in missing],
                batch_size=4,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            for text, vector in zip(missing, vectors):
                self._passage_vectors[text] = np.asarray(vector)
                if len(self._passage_vectors) > 4096:
                    self._passage_vectors.popitem(last=False)
        return np.asarray([self._passage_vectors[text] for text in passages])

    @staticmethod
    def _chunk(doc_id: str, text: str, metadata: dict) -> EvidenceChunk:
        document_id = metadata.get("documentID") or metadata.get("document_id") or ""
        return EvidenceChunk(
            chunk_id=metadata.get("chunk_id") or doc_id,
            document_id=document_id,
            knowledge_id=metadata.get("knowledge_name") or metadata.get("knowledgeID"),
            source=metadata.get("source", ""),
            page_number=int(metadata.get("page_number", 0) or 0),
            text=text,
        )

    def search(
        self,
        chroma: "Chroma",
        query: str,
        where: dict | None,
        k: int,
    ) -> list[EvidenceChunk]:
        candidate_count = max(k, 8)
        dense_hits = chroma.similarity_search_with_score(query, k=candidate_count, filter=where)
        dense = [
            self._chunk(
                str(getattr(doc, "id", "") or f"dense:{index}"),
                doc.page_content,
                doc.metadata or {},
            ).model_copy(update={"dense_score": float(distance)})
            for index, (doc, distance) in enumerate(dense_hits)
        ]

        # Read only the scope supplied by the caller. The QA route validates
        # document ownership before passing its document filter here.
        stored = chroma._collection.get(where=where, include=["documents", "metadatas"])
        corpus = [
            self._chunk(doc_id, text, metadata or {})
            for doc_id, text, metadata in zip(
                stored.get("ids") or [],
                stored.get("documents") or [],
                stored.get("metadatas") or [],
            )
            if text
        ]
        sparse = BM25Retriever(corpus).search(query, k=candidate_count) if corpus else []
        candidates = reciprocal_rank_fusion([dense, sparse])[:candidate_count]
        if not candidates:
            return []

        query_vector = np.asarray(
            self.embedder.encode(query, normalize_embeddings=True, show_progress_bar=False)
        )
        passage_vectors = self._embed_passages([item.text for item in candidates])
        similarities = passage_vectors @ query_vector
        ordered = [
            candidates[index]
            for index in np.argsort(similarities)[::-1]
        ]
        shortlist = ordered[: min(len(ordered), 4)]
        scores = self.reranker.predict(
            [[query, item.text[:600]] for item in shortlist],
            batch_size=2,
            show_progress_bar=False,
        )
        reranked = [
            item.model_copy(update={"rerank_score": float(score)})
            for item, score in zip(shortlist, scores)
        ]
        best = sorted(reranked, key=lambda item: item.rerank_score or 0.0, reverse=True)
        return (best + ordered[len(shortlist):])[:k]
