"""Local OCR and explainable screening for uploaded research PDFs.

The result describes document structure; it cannot authenticate a publication.
"""

from functools import lru_cache
import re
from threading import Lock

import fitz
import numpy as np


MAX_PDF_BYTES = 25 * 1024 * 1024
_ocr_lock = Lock()


class OCRUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _ocr_engine():
    try:
        from rapidocr import RapidOCR
        return RapidOCR()
    except Exception as exc:
        raise OCRUnavailable("扫描版 PDF 需要 RapidOCR；请安装后重试") from exc


def extract_page_text(page: fitz.Page) -> tuple[str, bool]:
    """Read native text, falling back to OCR only on image-like pages."""
    native_text = page.get_text("text").strip()
    if len(native_text) >= 80:
        return native_text, False

    scale = min(1.7, 2000 / max(page.rect.width, page.rect.height, 1))
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    try:
        with _ocr_lock:
            result = _ocr_engine()(image)
    except OCRUnavailable:
        raise
    except Exception as exc:
        raise OCRUnavailable("扫描版 PDF 的 OCR 识别失败，请检查文件质量后重试") from exc
    lines = [line.strip() for line in (result.txts or ()) if line and line.strip()]
    ocr_text = "\n".join(lines)
    return (ocr_text if len(ocr_text) > len(native_text) else native_text), True


def inspect_pdf(content: bytes) -> dict:
    if len(content) > MAX_PDF_BYTES:
        raise ValueError("PDF 超过 25 MB 上传限制")
    if not content.startswith(b"%PDF-"):
        raise ValueError("文件不是有效的 PDF")
    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("PDF 已损坏或无法读取") from exc

    try:
        if pdf.is_encrypted or len(pdf) == 0:
            raise ValueError("PDF 已加密或没有页面，无法识别")
        indices = list(range(min(3, len(pdf))))
        if len(pdf) > 3:
            indices.append(len(pdf) - 1)
        snippets = []
        ocr_pages = []
        for index in indices:
            text, used_ocr = extract_page_text(pdf.load_page(index))
            snippets.append(text[:5000])
            if used_ocr:
                ocr_pages.append(index + 1)
        page_count = len(pdf)
    finally:
        pdf.close()

    text = "\n".join(snippets)
    patterns = {
        "摘要": r"\babstract\b|摘\s*要",
        "引言": r"\bintroduction\b|引\s*言|绪\s*论",
        "方法或实验": r"\bmethods?\b|\bmethodology\b|\bexperiments?\b|研究方法|实验设计",
        "参考文献": r"\breferences\b|参考文献",
        "学术标识": r"\bdoi\s*[:：]?\s*10\.\d{4,9}|\barxiv\s*[:：]?\s*\d{4}\.\d{4,5}|\bissn\b",
    }
    signals = [name for name, pattern in patterns.items() if re.search(pattern, text, re.IGNORECASE)]
    non_paper = re.search(r"发票|增值税|简历|劳动合同|invoice|curriculum vitae|purchase order", text, re.IGNORECASE)
    if non_paper and not signals:
        verdict, reason = "not_paper", "识别到发票、简历或合同等非论文内容"
    elif len(text.strip()) < 40:
        verdict, reason = "unreadable", "采样页面未识别到足够文字，无法判断或建立正文索引"
    elif len(text) >= 200 and ("摘要" in signals and len(signals) >= 2 or len(signals) >= 3):
        verdict, reason = "likely_paper", "识别到摘要、章节或学术标识等论文结构特征"
    else:
        verdict, reason = "review", "论文结构特征不足，建议人工核对封面和正文"
    return {
        "verdict": verdict,
        "reason": reason,
        "signals": signals,
        "page_count": page_count,
        "sampled_pages": [i + 1 for i in indices],
        "ocr_pages": ocr_pages,
        "scanned": bool(ocr_pages),
        "preview": re.sub(r"\s+", " ", text).strip()[:350],
    }
