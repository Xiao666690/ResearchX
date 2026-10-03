"""Research Planner：把科研目标拆解为有限技能集合中的计划。"""
from __future__ import annotations

import json
import re

from core.research.schemas import TaskPlan
from core.skills.registry import SkillRegistry

PLANNER_PROMPT = """你是科研任务规划器。根据用户的科研目标，把任务拆解为可执行的步骤序列。

可用技能（skill 只能是以下之一，不得凭空生成）：
{skills}

当前任务可读取的本地论文（document_id 必须使用这里的 ID）：
{documents}

严格输出 JSON，格式：
{{"goal": "...", "steps": [{{"step_id": "s1", "title": "...", "skill": "<可用技能名>", "depends_on": [], "input": {{}}, "success_criteria": ["..."]}}], "expected_artifacts": ["comparison_table", "report"]}}

用户目标：{goal}

数据流规则：
1. paper_search 已返回标题、作者、摘要和链接；如果后续要总结搜索结果，使用 report_generate，context 必须写成 "{{{{s1.result}}}}"（s1 替换成对应步骤 ID）。
2. paper_reader 只读取用户本地论文库中的 document_id，绝不能拿 paper_search 的外部搜索结果调用 paper_reader。
3. 依赖前一步数据时，必须在 input 字段中使用 "{{{{步骤ID.result}}}}"，不要使用 $s1、自然语言描述或不存在的 selected_document_id。
4. 计划应精简且可执行，一般不超过 4 步。
5. 每一步 input 必须符合技能的 input_schema；depends_on 只能引用此前已定义的步骤，引用结果时必须列入 depends_on。
"""

REFERENCE_PATTERN = re.compile(r"\{\{\s*([\w-]+)(?:\.(?:result|output))?\s*\}\}")


def _clean_json(text: str) -> str:
    text = re.sub(r"\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*", "", text)
    return text.strip()


class Planner:
    def __init__(self, llm, registry: SkillRegistry):
        self.llm = llm
        self.registry = registry

    def plan(self, goal: str, task_id: str | None = None, llm=None,
             allowed_document_ids: list[str] | None = None,
             available_documents: list[dict] | None = None) -> TaskPlan:
        skills_desc = json.dumps(self.registry.describe(), ensure_ascii=False)
        documents = available_documents if available_documents is not None else (
            [{"document_id": doc_id} for doc_id in allowed_document_ids]
            if allowed_document_ids is not None else [])
        prompt = PLANNER_PROMPT.format(skills=skills_desc, documents=json.dumps(documents, ensure_ascii=False), goal=goal)
        if not task_id:
            import uuid
            task_id = uuid.uuid4().hex[:12]
        for attempt in range(2):
            resp = (llm or self.llm).invoke(prompt)
            text = resp.content if hasattr(resp, "content") else str(resp)
            try:
                data = json.loads(_clean_json(text))
                data["task_id"] = task_id
                plan = TaskPlan.model_validate(data)
                self._validate_plan(plan, allowed_document_ids)
                return plan
            except (ValueError, TypeError, KeyError) as exc:
                if attempt:
                    raise ValueError(f"研究计划两次校验失败: {exc}") from exc
                prompt += f"\n\n上一份计划未通过校验：{str(exc)[:800]}。请只输出修正后的完整 JSON。"
        raise AssertionError("unreachable")

    def _validate_plan(self, plan: TaskPlan, allowed_document_ids: list[str] | None = None) -> None:
        """执行前验证输入、顺序依赖和本地论文权限。"""
        valid_skills = set(self.registry.names())
        previous_ids: set[str] = set()
        allowed_ids = set(allowed_document_ids) if allowed_document_ids is not None else None
        for s in plan.steps:
            if s.step_id in previous_ids:
                raise ValueError(f"重复的 step_id: {s.step_id}")
            if s.skill not in valid_skills:
                raise ValueError(f"未知技能 {s.skill}（step {s.step_id}）")
            for dep in s.depends_on:
                if dep not in previous_ids:
                    raise ValueError(f"step {s.step_id} 依赖尚未执行的 step {dep}")
            for ref in REFERENCE_PATTERN.findall(json.dumps(s.input, ensure_ascii=False)):
                if ref not in previous_ids or ref not in s.depends_on:
                    raise ValueError(f"step {s.step_id} 引用无效依赖 {ref}")
            skill = self.registry.get(s.skill)
            unknown = set(s.input) - set(skill.input_model.model_fields)
            if unknown:
                raise ValueError(f"step {s.step_id} 包含未知输入字段 {sorted(unknown)}")
            try:
                skill.validate(s.input)
            except ValueError as exc:
                raise ValueError(f"step {s.step_id} 输入类型错误: {exc}") from exc
            ids = ([s.input.get("document_id")] if "document_id" in skill.input_model.model_fields
                   else s.input.get("document_ids", []) if "document_ids" in skill.input_model.model_fields else [])
            if allowed_ids is not None and any(doc_id and doc_id not in allowed_ids for doc_id in ids):
                raise ValueError(f"step {s.step_id} 使用了当前任务不允许的 document_id")
            previous_ids.add(s.step_id)
