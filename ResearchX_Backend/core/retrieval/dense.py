"""BGE-M3 Dense Retriever。

用 FlagEmbedding 加载 BGE-M3 作为语义召回，底层走 langchain_chroma。
"""
from __future__ import annotations

from typing import Optional

from langchain_core.embeddings import Embeddings

from core.common.types import EvidenceChunk


class BGE3Embeddings(Embeddings):
    """BGE-M3 的 langchain Embeddings 封装（dense 向量）。"""

    def __init__(self, model_path: str, use_fp16: bool = True):
        from FlagEmbedding import BGEM3FlagModel

        self._model = BGEM3FlagModel(model_path, use_fp16=use_fp16)

    def _encode(self, texts: list[str]):
        return self._model.encode(
            texts, batch_size=12, max_length=8192, return_dense=True
        )["dense_vecs"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._encode(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text])[0].tolist()


def build_document_filter(document_ids: Optional[list[str]]) -> Optional[dict]:
    """把 document_id 列表转成 chromadb 的 where 过滤条件。"""
    if not document_ids:
        return None
    if len(document_ids) == 1:
        return {"documentID": {"$eq": document_ids[0]}}
    return {"documentID": {"$in": list(document_ids)}}


def to_evidence(doc, score: float) -> EvidenceChunk:
    """把 langchain Document + score 转成 EvidenceChunk。"""
    m = doc.metadata or {}
    document_id = m.get("documentID") or m.get("document_id") or ""
    page_number = int(m.get("page_number", 0) or 0)
    return EvidenceChunk(
        chunk_id=m.get("chunk_id") or f"{document_id}:p{page_number}",
        document_id=document_id,
        knowledge_id=m.get("knowledge_name") or m.get("knowledgeID"),
        source=m.get("source", ""),
        page_number=page_number,
        text=doc.page_content,
        dense_score=float(score),
    )


class DenseRetriever:
    """BGE-M3 Dense 检索器，返回结构化 EvidenceChunk。"""

    def __init__(self, chroma_db):
        self.db = chroma_db

    def search(
        self, query: str, document_ids: Optional[list[str]] = None, k: int = 20
    ) -> list[EvidenceChunk]:
        where = build_document_filter(document_ids)
        docs_scores = self.db.similarity_search_with_score(query, k=k, filter=where)
        return [to_evidence(doc, score) for doc, score in docs_scores]
