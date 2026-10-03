"""Quantum Experiment Skill 输入输出 Schema。

注意：字段需按真实工具接口调整；当前仅有软件著作权，未提供真实 CLI/API，
故此处仅定义可实施的接口骨架，算法/参数名必须白名单。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class QuantumExperimentInput(BaseModel):
    algorithm: str
    parameters: dict = Field(default_factory=dict)
    shots: Optional[int] = None
    backend: Optional[str] = "simulator"
    timeout_s: int = 120


class QuantumExperimentOutput(BaseModel):
    status: str
    normalized_metrics: dict = Field(default_factory=dict)
    raw_result_path: Optional[str] = None
    stdout_tail: Optional[str] = None
