"""paper_reader：按 documentID / page 读取论文原文。"""
from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict

from core.skills.base import BaseSkill, SkillResult


class PaperReaderInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    document_id: str
    page: int = 1


class PaperReaderSkill(BaseSkill):
    name = "paper_reader"
    description = "按 documentID 与页码读取论文原文"
    input_model = PaperReaderInput

    async def execute(self, data: PaperReaderInput, ctx: dict) -> SkillResult:
        if data.document_id not in ctx.get("allowed_document_ids", []):
            return SkillResult(ok=False, error_code="FORBIDDEN_DOCUMENT", error_message="论文不在当前任务允许的范围内")
        db_factory = ctx.get("db_factory")
        if db_factory is None:
            return SkillResult(ok=False, error_code="NO_DB", error_message="数据库未注入")
        from core.backend.db.models import Document

        db = db_factory()
        try:
            query = db.query(Document).filter(Document.uid == data.document_id)
            if ctx.get("workspace_lid"):
                query = query.filter(Document.lid == ctx["workspace_lid"])
            doc = query.first()
            if doc is None:
                return SkillResult(ok=False, error_code="NOT_FOUND", error_message="文档不存在")
            path = (doc.documentPath if os.path.exists(doc.documentPath)
                    else os.getenv("AcadeAgent_DIR", ".") + doc.documentPath)
        finally:
            db.close()

        if not os.path.exists(path):
            return SkillResult(ok=False, error_code="FILE_NOT_FOUND", error_message=f"文件不存在: {path}")

        import fitz

        pdf = fitz.open(path)
        try:
            if data.page < 1 or data.page > len(pdf):
                return SkillResult(ok=False, error_code="BAD_PAGE", error_message=f"页码越界: {data.page}")
            text = pdf.load_page(data.page - 1).get_text("text")
        finally:
            pdf.close()

        return SkillResult(
            ok=True,
            output={"text": text, "page": data.page, "document_id": data.document_id},
        )
