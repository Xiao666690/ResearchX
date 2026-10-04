"""Research Mode 数据 Schema。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    step_id: str
    title: str
    skill: str
    depends_on: list[str] = Field(default_factory=list)
    input: dict = Field(default_factory=dict)
    success_criteria: list[str] = Field(default_factory=list)
    retry_of: Optional[str] = None


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


class AgentAction(BaseModel):
    action_id: str
    step_id: str
    skill: str
    input: dict = Field(default_factory=dict)
    reason: str = ""
    attempt: int = 1


class Observation(BaseModel):
    action_id: str
    step_id: str
    skill: str
    status: Literal["SUCCESS", "FAILED", "NEED_MORE_EVIDENCE"]
    output: dict = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    error_code: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0


class EvidenceSource(BaseModel):
    citation_id: str
    source_id: str
    title: str = ""
    excerpt: str = ""
    locator: str = ""
    source_type: str = ""


class EvidenceState(BaseModel):
    status: Literal["UNKNOWN", "SUFFICIENT", "PARTIAL", "MISSING_EXTERNAL", "CONFLICT", "UNSUPPORTED"] = "UNKNOWN"
    score: float = 0.0
    required_sources: int = 1
    sources: list[EvidenceSource] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(default_factory=list)
    reason: str = ""


class VerificationResult(BaseModel):
    decision: Literal["CONTINUE", "FINISH", "REPLAN", "RETRY", "EXPAND_EVIDENCE", "ABSTAIN"]
    goal_complete: bool = False
    evidence_sufficient: bool = False
    artifact_present: bool = False
    citations_valid: bool = False
    unsupported_claims: list[str] = Field(default_factory=list)
    reason: str = ""


class AgentEvent(BaseModel):
    sequence: int
    event_type: Literal["GOAL", "PLAN", "ACTION", "OBSERVATION", "EVIDENCE", "REPLAN", "VERIFICATION", "ARTIFACT", "FINISH", "STOP"]
    title: str
    detail: str = ""
    data: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchState(BaseModel):
    task_id: str
    goal: str
    status: Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"] = "PENDING"
    plan: TaskPlan
    current_step: Optional[str] = None
    evidence_state: EvidenceState = Field(default_factory=EvidenceState)
    observations: list[Observation] = Field(default_factory=list)
    tool_history: list[AgentAction] = Field(default_factory=list)
    step_results: list[StepResult] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    replan_count: int = 0
    turn_count: int = 0
    tool_calls: int = 0
    failure_count: int = 0
    stop_reason: Optional[str] = None
    events: list[AgentEvent] = Field(default_factory=list)
