"""BM25 稀疏检索器。

首版使用内存 BM25 + 字符/词法切分，索引阶段同步生成可持久化 corpus；
后续可替换为 Elasticsearch / OpenSearch。
"""
from __future__ import annotations

import re
from typing import Optional

from rank_bm25 import BM25Okapi

from core.common.types import EvidenceChunk

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    """英文按词法切分，中文用 jieba 分词。"""
    if _CJK_RE.search(text):
        try:
            import jieba

            return [t for t in jieba.cut(text) if t.strip()]
        except ImportError:
            return list(text)
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


class BM25Retriever:
    """基于内存 corpus 的 BM25 检索。"""

    def __init__(self, corpus: Optional[list[EvidenceChunk]] = None):
        self.corpus: list[EvidenceChunk] = list(corpus or [])

    def set_corpus(self, corpus: list[EvidenceChunk]) -> None:
        """索引阶段同步写入 corpus。"""
        self.corpus = list(corpus)

    def search(
        self, query: str, document_ids: Optional[list[str]] = None, k: int = 20
    ) -> list[EvidenceChunk]:
        scoped = [
            c for c in self.corpus
            if (not document_ids or c.document_id in set(document_ids))
        ]
        if not scoped:
            return []

        tokenized = [tokenize(c.text) for c in scoped]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(tokenize(query))
        top = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [
            scoped[i].model_copy(update={"sparse_score": float(scores[i])})
            for i in top
        ]
