"""Skill Registry：统一注册与描述内置 Research Skills。"""
from __future__ import annotations

from core.skills.base import BaseSkill


class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        if skill.name in self._skills:
            raise ValueError(f"duplicated skill: {skill.name}")
        self._skills[skill.name] = skill

    def get(self, name: str) -> BaseSkill:
        return self._skills[name]

    def has(self, name: str) -> bool:
        return name in self._skills

    def describe(self) -> list[dict]:
        """供 Planner 注入 skill 清单。"""
        return [
            {
                "name": s.name,
                "description": s.description,
                "input_schema": s.input_model.model_json_schema(),
            }
            for s in self._skills.values()
        ]

    def names(self) -> list[str]:
        return list(self._skills.keys())
