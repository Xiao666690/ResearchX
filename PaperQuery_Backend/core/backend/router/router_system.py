"""运行状态检查接口。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.backend.router.dependencies import get_db

router = APIRouter()


def component_status(app) -> dict:
    llm_manager = getattr(app, "llm", None)
    configured_models = (
        sorted(llm_manager.get_all_llms().keys())
        if llm_manager is not None
        else []
    )
    return {
        "database": False,  # 由 ready 端点执行真实 SQL 后覆盖
        "deepseek": "deepseek" in configured_models,
        "kimi": "kimi" in configured_models,
        "zhipu": "zhipu" in configured_models,
        "vector_database": getattr(app, "chroma_db", None) is not None,
        "hybrid_retrieval": getattr(app, "retrieval_pipeline", None) is not None,
        "research": getattr(app, "research_orchestrator", None) is not None,
    }


@router.get("/health/live", summary="进程存活检查")
def health_live():
    return {
        "status": "ok",
        "service": "paperagent-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready", summary="依赖就绪检查")
def health_ready(request: Request, db: Session = Depends(get_db)):
    components = component_status(request.app)
    try:
        db.execute(text("SELECT 1"))
        components["database"] = True
    except Exception:
        components["database"] = False

    required = ("database", "deepseek", "vector_database", "research")
    is_ready = all(components[name] for name in required)
    payload = {
        "status": "ready" if is_ready else "not_ready",
        "components": components,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(payload, status_code=200 if is_ready else 503)
