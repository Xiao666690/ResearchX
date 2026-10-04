"""字符窗口 + overlap 文本切块。

V2 切块规则：为每个 chunk 生成稳定的页内序号，避免英文论文中单纯 split()
造成公式、标点和段落结构丢失。chunk_id 统一为 `{documentID}:p{page}:c{idx}`。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TextChunk:
    text: str
    index: int
    start_char: int
    end_char: int


def split_text(text: str, chunk_size: int = 1800, overlap: int = 250) -> list[TextChunk]:
    """按字符窗口切分文本，返回带页内序号的 chunk 列表。

    Args:
        text: 单页原始文本。
        chunk_size: 字符窗口大小。
        overlap: 相邻 chunk 的重叠字符数。
    """
    chunks: list[TextChunk] = []
    start, idx = 0, 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(TextChunk(chunk, idx, start, end))
            idx += 1
        if end == n:
            break
        start = max(end - overlap, start + 1)
    return chunks
