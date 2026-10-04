"""内置 Research Skills（首版）。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.skills.base import BaseSkill, SkillResult


class LocalRetrievalInput(BaseModel):
    query: str
    document_ids: list[str] = Field(default_factory=list)
    k: int = 8


class LocalRetrievalSkill(BaseSkill):
    name = "local_retrieval"
    description = "在用户论文库内使用 ChromaDB 向量检索，返回可追溯证据片段"
    input_model = LocalRetrievalInput

    async def execute(self, data: LocalRetrievalInput, ctx: dict) -> SkillResult:
        chroma_db = ctx.get("chroma_db")
        if chroma_db is None:
            return SkillResult(ok=False, error_code="NO_VECTOR_DB", error_message="向量库未初始化")
        allowed_ids = set(ctx.get("allowed_document_ids", []))
        if data.document_ids and not set(data.document_ids).issubset(allowed_ids):
            return SkillResult(ok=False, error_code="FORBIDDEN_DOCUMENT", error_message="论文不在当前任务的资料库范围内")
        selected_ids = data.document_ids or sorted(allowed_ids)
        if not selected_ids:
            return SkillResult(ok=True, output={"evidence": []})
        filter_by_document = {"documentID": {"$in": selected_ids}}
        evidence = chroma_db.search_evidence(data.query, filter_by_document, k=data.k)
        return SkillResult(
            ok=True,
            output={"evidence": [e.model_dump() for e in evidence]},
            evidence=[e.chunk_id for e in evidence],
        )


class ReportGenerateInput(BaseModel):
    topic: str
    context: str = ""
    citations: list[dict] = Field(default_factory=list)
    verification_feedback: str = ""


class ReportGenerateSkill(BaseSkill):
    name = "report_generate"
    description = "基于给定上下文与引用生成结构化研究报告（Markdown）"
    input_model = ReportGenerateInput

    async def execute(self, data: ReportGenerateInput, ctx: dict) -> SkillResult:
        llm = ctx.get("llm")
        if llm is None:
            return SkillResult(ok=False, error_code="NO_LLM", error_message="LLM 未初始化")
        prompt = (
            "你是科研报告撰写助手，请基于以下上下文生成一份 Markdown 研究报告，"
            "只使用给定来源支持事实性结论；每项关键事实用已有的 [C#] 标注引用。"
            "不能从摘要推断论文全文的实验结果；证据不足时明确写出限制。"
            "不得编造引用编号。\n\n"
            f"主题：{data.topic}\n\n上下文：{data.context}\n\n请输出 Markdown："
        )
        if data.verification_feedback:
            prompt += (
                "\n\n上一版报告未通过核验，请针对以下问题修订。"
                "无法由上述来源证明的结论必须删除，不能仅增加引用标记："
                f"{data.verification_feedback[:1500]}"
            )
        resp = llm.invoke(prompt)
        markdown = resp.content if hasattr(resp, "content") else str(resp)
        artifact = {
            "type": "research_report",
            "title": data.topic,
            "markdown": markdown,
        }
        return SkillResult(ok=True, output={"report": markdown}, artifacts=[artifact])


class PaperCompareInput(BaseModel):
    question: str
    context: str = ""
    columns: list[str] = Field(default_factory=list)
    verification_feedback: str = ""


class PaperCompareSkill(BaseSkill):
    name = "paper_compare"
    description = "跨多篇论文比较方法/数据集/指标，输出结构化对比表"
    input_model = PaperCompareInput

    async def execute(self, data: PaperCompareInput, ctx: dict) -> SkillResult:
        llm = ctx.get("llm")
        if llm is None:
            return SkillResult(ok=False, error_code="NO_LLM", error_message="LLM 未初始化")
        columns = data.columns or ["论文", "方法", "数据集", "指标"]
        prompt = (
            "你是一个论文对比助手。只依据以下来源生成 JSON 对比表，"
            "每条事实附上对应 [C#] 引用，不得编造结论或引用。\n"
            f"对比问题：{data.question}\n"
            f"对比列：{columns}\n"
            f"上下文：{data.context}\n"
            "输出 JSON：{\"columns\": [...], \"rows\": [{\"论文\": ..., ...}]}"
        )
        if data.verification_feedback:
            prompt += f"\n上一版未通过核验，请删除或修正无证据结论：{data.verification_feedback[:1500]}"
        resp = llm.invoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
        artifact = {"type": "comparison_table", "title": data.question, "raw": text}
        return SkillResult(ok=True, output={"comparison": text}, artifacts=[artifact])
