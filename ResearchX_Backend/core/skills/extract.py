"""extract：从论文文本结构化抽取方法 / 实验配置。"""
from __future__ import annotations

import json
import re

from pydantic import BaseModel

from core.skills.base import BaseSkill, SkillResult


def _parse_json(text: str):
    text = re.sub(r"\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*", "", text)
    return json.loads(text.strip())


class ExtractInput(BaseModel):
    context: str
    document_id: str = ""


class MethodExtractSkill(BaseSkill):
    name = "method_extract"
    description = "从论文文本抽取研究方法，输出结构化 MethodCard"
    input_model = ExtractInput

    async def execute(self, data: ExtractInput, ctx: dict) -> SkillResult:
        llm = ctx.get("llm")
        if llm is None:
            return SkillResult(ok=False, error_code="NO_LLM", error_message="LLM 未初始化")
        prompt = (
            "从以下论文内容抽取研究方法，严格输出 JSON，不要多余内容：\n"
            '{"method_name": "", "description": "", "key_innovations": [], "algorithm": "", "assumptions": []}\n\n'
            f"论文内容：{data.context}\n"
        )
        resp = llm.invoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
        try:
            card = _parse_json(text)
        except Exception:
            return SkillResult(ok=False, error_code="PARSE_ERROR", error_message="方法抽取解析失败")
        artifact = {"type": "evidence_table", "title": "方法抽取", "method": card}
        return SkillResult(ok=True, output={"method": card}, artifacts=[artifact])


class ExperimentExtractSkill(BaseSkill):
    name = "experiment_extract"
    description = "从论文文本抽取实验配置，输出结构化 ExperimentConfig"
    input_model = ExtractInput

    async def execute(self, data: ExtractInput, ctx: dict) -> SkillResult:
        llm = ctx.get("llm")
        if llm is None:
            return SkillResult(ok=False, error_code="NO_LLM", error_message="LLM 未初始化")
        prompt = (
            "从以下论文内容抽取实验配置，严格输出 JSON，不要多余内容：\n"
            '{"datasets": [], "metrics": [], "baselines": [], "hyperparameters": {}, "hardware": ""}\n\n'
            f"论文内容：{data.context}\n"
        )
        resp = llm.invoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
        try:
            config = _parse_json(text)
        except Exception:
            return SkillResult(ok=False, error_code="PARSE_ERROR", error_message="实验配置抽取解析失败")
        artifact = {"type": "experiment_report", "title": "实验配置", "config": config}
        return SkillResult(ok=True, output={"experiment_config": config}, artifacts=[artifact])
