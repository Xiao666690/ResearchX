"""Research Mode 数据 Schema。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    step_id: str
    title: str
    skill: str
    depends_on: list[str] = Field(default_factory=list)
    input: dict = Field(default_factory=dict)
    success_criteria: list[str] = Field(default_factory=list)


class TaskPlan(BaseModel):
    task_id: str
    goal: str
    steps: list[PlanStep]
    expected_artifacts: list[str] = Field(default_factory=list)


class StepResult(BaseModel):
    step_id: str
    status: Literal["SUCCESS", "FAILED", "NEED_MORE_EVIDENCE"]
    output: dict = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class TaskState(BaseModel):
    task_id: str
    goal: str
    status: Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"]
    plan: TaskPlan
    step_results: list[StepResult] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
