"""V2 配置。基于环境变量，提供默认值；后续可迁移到 pydantic-settings。"""
from __future__ import annotations

import os


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """集中读取 V2 相关配置。"""

    # 索引版本
    INDEX_VERSION: str = os.getenv("INDEX_VERSION", "v2-bge-m3-001")

    # 模型本地缓存路径
    BGE_M3_MODEL_PATH: str = os.getenv("BGE_M3_MODEL_PATH", "./models/bge-m3")
    RERANKER_MODEL_PATH: str = os.getenv("RERANKER_MODEL_PATH", "./models/bge-reranker-v2-m3")

    # 检索目录
    CHROMA_LAYER1_V2_DIR: str = os.getenv("CHROMA_LAYER1_V2_DIR", "./res/layer1_v2")
    BM25_INDEX_DIR: str = os.getenv("BM25_INDEX_DIR", "./res/bm25")

    # 检索参数
    DENSE_K: int = _get_int("DENSE_K", 20)
    SPARSE_K: int = _get_int("SPARSE_K", 20)
    RRF_C: int = _get_int("RRF_C", 60)
    RERANK_CANDIDATES: int = _get_int("RERANK_CANDIDATES", 24)
    FINAL_K: int = _get_int("FINAL_K", 8)
    EVIDENCE_THRESHOLD: float = _get_float("EVIDENCE_THRESHOLD", 0.65)
    MAX_RETRIEVAL_ROUNDS: int = _get_int("MAX_RETRIEVAL_ROUNDS", 2)

    # Research / Skill
    SKILL_SANDBOX_DIR: str = os.getenv("SKILL_SANDBOX_DIR", "./res/tasks")
    SKILL_DEFAULT_TIMEOUT: int = _get_int("SKILL_DEFAULT_TIMEOUT", 120)
    RESEARCH_MAX_STEPS: int = _get_int("RESEARCH_MAX_STEPS", 12)
    RESEARCH_MAX_RETRIES: int = _get_int("RESEARCH_MAX_RETRIES", 2)

    # Security / Web
    FRONTEND_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("FRONTEND_ORIGINS", "http://127.0.0.1:8080,http://localhost:8080").split(",")
        if o.strip()
    ]
    MAX_UPLOAD_MB: int = _get_int("MAX_UPLOAD_MB", 50)
    TMP_FILE_TTL_HOURS: int = _get_int("TMP_FILE_TTL_HOURS", 24)


settings = Settings()
