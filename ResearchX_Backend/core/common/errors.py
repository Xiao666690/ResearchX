"""统一异常类型。"""
from __future__ import annotations


class ResearchXError(Exception):
    """所有业务异常的基类。"""


class RetrievalError(ResearchXError):
    """检索失败。"""


class DecisionError(ResearchXError):
    """决策引擎解析/调用失败。"""


class GroundingError(ResearchXError):
    """Grounding 校验失败。"""


class SkillError(ResearchXError):
    """Skill 执行失败。"""


class SkillValidationError(SkillError):
    """Skill 输入校验失败。"""


class QuantumToolError(SkillError):
    """量子工具调用失败。"""


class DocumentNotFoundError(ResearchXError):
    """文档不存在。"""
