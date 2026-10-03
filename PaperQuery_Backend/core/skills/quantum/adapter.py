"""Quantum Tool Adapter（接口骨架）。

⚠️ 事实约束：当前仅有「量子算法模拟性能优化工具软件 V1.0」软件著作权，
未提供源代码 / CLI 参数 / HTTP API。因此本 adapter 只定义可实施的接口与
白名单校验，不实现真实调用；待拿到真实工具接口后再补齐 execute。
"""
from __future__ import annotations

from core.common.errors import QuantumToolError
from core.skills.quantum.schemas import QuantumExperimentInput, QuantumExperimentOutput


class QuantumToolAdapter:
    """量子工具适配器骨架。"""

    # 算法/参数白名单，待真实工具确认后填充
    ALLOWED_ALGORITHMS: set[str] = set()
    ALLOWED_PARAM_KEYS: set[str] = set()

    def validate_input(self, data: QuantumExperimentInput) -> None:
        if data.algorithm not in self.ALLOWED_ALGORITHMS:
            raise QuantumToolError(f"不支持的算法: {data.algorithm}")
        for key in data.parameters:
            if key not in self.ALLOWED_PARAM_KEYS:
                raise QuantumToolError(f"不支持的参数: {key}")

    async def run(self, data: QuantumExperimentInput) -> QuantumExperimentOutput:
        """真实调用待工具接口确认后实现。"""
        self.validate_input(data)
        raise QuantumToolError("量子工具真实接口尚未接入，仅提供骨架")
