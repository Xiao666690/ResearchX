"""Skill Framework 基础契约。

所有工具遵守统一生命周期：Schema 校验 → 权限判断 → execute → 结果标准化 → 记录 SkillRun。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field


class SkillResult(BaseModel):
    ok: bool
    output: dict = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class BaseSkill(ABC):
    """所有 Research Skill 的基类。"""

    name: str
    description: str
    input_model: type[BaseModel]
    permission: str = "read"
    timeout_s: int = 60

    def validate(self, raw: dict) -> BaseModel:
        return self.input_model.model_validate(raw)

    @abstractmethod
    async def execute(self, data: BaseModel, ctx: dict) -> SkillResult:
        """执行技能，返回标准化结果。ctx 传入运行上下文（如 RetrievalPipeline 等）。"""

    async def run(self, raw: dict, ctx: Optional[dict] = None) -> SkillResult:
        ctx = ctx or {}
        try:
            data = self.validate(raw)
            return await self.execute(data, ctx)
        except Exception as e:
            return SkillResult(ok=False, error_code="SKILL_ERROR", error_message=str(e))
