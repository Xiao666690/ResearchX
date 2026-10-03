"""统一异常类型。"""
from __future__ import annotations


class PaperAgentError(Exception):
    """所有业务异常的基类。"""


class RetrievalError(PaperAgentError):
    """检索失败。"""


class DecisionError(PaperAgentError):
    """决策引擎解析/调用失败。"""


class GroundingError(PaperAgentError):
    """Grounding 校验失败。"""


class SkillError(PaperAgentError):
    """Skill 执行失败。"""


class SkillValidationError(SkillError):
    """Skill 输入校验失败。"""


class QuantumToolError(SkillError):
    """量子工具调用失败。"""


class DocumentNotFoundError(PaperAgentError):
    """文档不存在。"""
