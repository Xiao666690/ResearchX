"""证据 → LLM 上下文格式化。

在最后一步才把 EvidenceChunk 转成文本，同时保留 Citation 映射表，
供 Grounding 校验与前端 Citation 跳页使用。
"""
from __future__ import annotations

from core.common.types import Citation, EvidenceChunk


def format_evidence(chunks: list[EvidenceChunk]) -> tuple[str, dict[str, EvidenceChunk]]:
    """把证据片段格式化为带 [C#] 引用的文本，并返回 citation 映射表。"""
    parts: list[str] = []
    citation_map: dict[str, EvidenceChunk] = {}
    for i, e in enumerate(chunks, 1):
        cid = f"C{i}"
        parts.append(
            f"[{cid}] document={e.document_id} page={e.page_number} chunk={e.chunk_id}\n{e.text}"
        )
        citation_map[cid] = e
    return "\n\n".join(parts), citation_map


def build_citations(citation_map: dict[str, EvidenceChunk]) -> list[Citation]:
    """由 citation 映射表构造结构化 Citation 列表（供前端展示）。"""
    citations: list[Citation] = []
    for cid, e in citation_map.items():
        citations.append(Citation(
            citation_id=cid,
            document_id=e.document_id,
            page_number=e.page_number,
            chunk_id=e.chunk_id,
            quote=e.text[:200],
            knowledge_id=e.knowledge_id,
        ))
    return citations
