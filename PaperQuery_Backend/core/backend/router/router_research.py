"""V2 Research Mode 路由：创建/执行/查询科研任务并持久化。"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from langchain_core.callbacks import BaseCallbackHandler
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from core.backend.crud.crud_user import query_user
from core.backend.db.models import Artifact, Document, ResearchStep, ResearchTask
from core.backend.utils.utils import attach_workspace_lid, get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
router = APIRouter()
logger = logging.getLogger(__name__)
_research_slots = threading.BoundedSemaphore(2)


def _get_user(token: str, db: Session):
    """同步获取当前用户（供 sync 端点使用，避免 async 依赖注入）。"""
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        username = payload.get("username")
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    user = query_user(db, username=username)
    if user is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return attach_workspace_lid(db, user)


class ResearchTaskCreate(BaseModel):
    goal: str
    mode: str = "research"
    document_ids: list[str] = Field(default_factory=list)
    parent_task_id: str | None = None


def _json_safe(value: Any) -> Any:
    """把 Skill/第三方库结果递归转换成可持久化的 JSON 数据。"""
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, BaseModel):
        return _json_safe(value.model_dump())
    if isinstance(value, dict):
        return {
            str(key.value if isinstance(key, Enum) else key): _json_safe(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _json_dumps(value: Any) -> str:
    # default=str 是最后一道保护，避免某个新 Skill 返回第三方自定义对象时整项任务丢失。
    return json.dumps(_json_safe(value), ensure_ascii=False, default=str)


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None
            else value.astimezone(timezone.utc)).isoformat()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class _ResearchTokenHeartbeat(BaseCallbackHandler):
    """Streaming tokens refresh task activity without imposing a total deadline."""

    def __init__(self, touch):
        self.touch = touch
        self.last_touch = 0.0

    def on_llm_new_token(self, token: str, **kwargs):
        if not token or time.monotonic() - self.last_touch < 8:
            return
        self.last_touch = time.monotonic()
        try:
            self.touch()
        except Exception:
            logger.warning("Could not save research heartbeat", exc_info=True)


def _run_research_task(task_id: str, planning_goal: str, allowed_ids: list[str],
                       parent_task_id: str | None, prior_artifacts: list[dict],
                       orchestrator, llm_provider, db_factory,
                       workspace_lid: str | None = None,
                       available_documents: list[dict] | None = None):
    def touch():
        with db_factory() as session:
            task = session.query(ResearchTask).filter_by(task_id=task_id).first()
            if task and task.status == "RUNNING":
                task.updated_at = _utc_now()
                session.commit()

    def on_plan(plan):
        with db_factory() as session:
            task = session.query(ResearchTask).filter_by(task_id=task_id).one()
            task.plan_json = plan.model_dump_json()
            task.updated_at = _utc_now()
            session.commit()

    def on_step_start(step):
        with db_factory() as session:
            session.add(ResearchStep(
                step_id=step.step_id, task_id=task_id, skill_name=step.skill,
                status="RUNNING",
            ))
            task = session.query(ResearchTask).filter_by(task_id=task_id).one()
            task.updated_at = _utc_now()
            session.commit()

    def on_step(step, result):
        with db_factory() as session:
            row = session.query(ResearchStep).filter_by(task_id=task_id, step_id=result.step_id).first()
            if row is None:
                row = ResearchStep(step_id=result.step_id, task_id=task_id, skill_name=step.skill)
                session.add(row)
            row.status = result.status
            row.output_json = _json_dumps(result.output)
            row.error = result.error
            row.duration_ms = result.duration_ms
            task = session.query(ResearchTask).filter_by(task_id=task_id).one()
            task.updated_at = _utc_now()
            session.commit()

    with _research_slots:
        try:
            with db_factory() as session:
                task = session.query(ResearchTask).filter_by(task_id=task_id).one()
                task.status = "RUNNING"
                task.updated_at = _utc_now()
                session.commit()

            context = {
                "allowed_document_ids": allowed_ids,
                "workspace_lid": workspace_lid,
                "available_documents": available_documents,
                "parent_task_id": parent_task_id,
                "prior_artifacts": prior_artifacts,
                "_task_id": task_id,
                "_on_plan": on_plan,
                "_on_step_start": on_step_start,
                "_on_step": on_step,
            }
            if llm_provider is not None:
                research_llm = llm_provider.get_stream_llm("deepseek").with_config(
                    callbacks=[_ResearchTokenHeartbeat(touch)]
                )
                context["_research_llm"] = research_llm
                context["llm"] = research_llm
            state = orchestrator.run(planning_goal, context=context)

            with db_factory() as session:
                task = session.query(ResearchTask).filter_by(task_id=task_id).one()
                task.plan_json = state.plan.model_dump_json()
                for result in state.step_results:
                    if not session.query(ResearchStep).filter_by(task_id=task_id, step_id=result.step_id).first():
                        session.add(ResearchStep(
                            step_id=result.step_id, task_id=task_id,
                            skill_name=next((s.skill for s in state.plan.steps if s.step_id == result.step_id), ""),
                            status=result.status, output_json=_json_dumps(result.output),
                            error=result.error, duration_ms=result.duration_ms,
                        ))
                for artifact in state.artifacts:
                    safe_artifact = _json_safe(artifact)
                    artifact_id = safe_artifact.get("artifact_id") or uuid.uuid4().hex
                    safe_artifact["artifact_id"] = artifact_id
                    session.add(Artifact(
                        artifact_id=artifact_id, task_id=task_id,
                        type=safe_artifact.get("type", ""), title=safe_artifact.get("title", ""),
                        data_json=_json_dumps(safe_artifact),
                    ))
                task.status = state.status
                task.updated_at = _utc_now()
                session.commit()
        except Exception as exc:
            logger.exception("Research task %s failed", task_id)
            with db_factory() as session:
                task = session.query(ResearchTask).filter_by(task_id=task_id).first()
                if task:
                    task.status = "FAILED"
                    task.updated_at = _utc_now()
                    session.add(ResearchStep(
                        step_id="system_error", task_id=task_id, skill_name="research",
                        status="FAILED", error=str(exc)[:1200], duration_ms=0,
                    ))
                    session.commit()


@router.post("/research/tasks")
def create_task(
    req: ResearchTaskCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = _get_user(token, db)
    orchestrator = getattr(request.app, "research_orchestrator", None)
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Research 编排组件未初始化")

    owned_ids = {
        row.uid for row in db.query(Document.uid).filter(Document.lid == user.workspace_lid).all()
    }
    if req.document_ids and not set(req.document_ids).issubset(owned_ids):
        raise HTTPException(status_code=403, detail="部分论文不在当前账号的资料库中")
    allowed_ids = list(dict.fromkeys(req.document_ids)) if req.document_ids else list(owned_ids)
    available_documents = [
        {"document_id": row.uid, "title": row.documentName}
        for row in db.query(Document.uid, Document.documentName).filter(Document.lid == user.workspace_lid).all()
        if row.uid in allowed_ids
    ]

    parent = None
    prior_artifacts = []
    if req.parent_task_id:
        parent = db.query(ResearchTask).filter(ResearchTask.task_id == req.parent_task_id, ResearchTask.lid == user.workspace_lid).first()
        if parent is None:
            raise HTTPException(status_code=404, detail="上一轮研究任务不存在")
        prior_artifacts = [json.loads(item.data_json) for item in db.query(Artifact).filter(Artifact.task_id == parent.task_id).all() if item.data_json]
    prior_digest = "\n".join(f"- {item.get('title', '')}: {str(item.get('markdown') or item.get('report') or item.get('papers') or item.get('raw') or '')[:500]}" for item in prior_artifacts[:4])
    planning_goal = req.goal if not parent else f"{req.goal}\n\n上一轮研究目标：{parent.goal}\n上一轮结果：\n{prior_digest[:1800]}"

    task_id = uuid.uuid4().hex[:12]
    task = ResearchTask(
        task_id=task_id,
        lid=user.workspace_lid,
        goal=req.goal,
        mode=req.mode,
        parent_task_id=req.parent_task_id,
        status="PENDING",
    )
    try:
        db.add(task)

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Research 任务保存失败: {exc}") from exc
    db_factory = sessionmaker(bind=db.get_bind())
    background_tasks.add_task(
        _run_research_task, task_id, planning_goal, allowed_ids,
        req.parent_task_id, prior_artifacts, orchestrator,
        getattr(request.app, "llm", None), db_factory,
        user.workspace_lid, available_documents,
    )
    return {
        "status_code": 200,
        "msg": "Research task created",
        "data": {"task_id": task_id, "status": "PENDING"},
    }


@router.get("/research/tasks")
def list_tasks(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = _get_user(token, db)
    tasks = (
        db.query(ResearchTask)
        .filter(ResearchTask.lid == user.workspace_lid)
        .order_by(ResearchTask.created_at.desc())
        .all()
    )
    return {
        "status_code": 200,
        "msg": "ok",
        "data": [
            {
                "task_id": t.task_id,
                "goal": t.goal,
                "status": t.status,
                "mode": t.mode,
                "parent_task_id": t.parent_task_id,
                "created_at": _utc_iso(t.created_at),
                "updated_at": _utc_iso(t.updated_at),
            }
            for t in tasks
        ],
    }


@router.get("/research/tasks/{task_id}")
def get_task(
    task_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = _get_user(token, db)
    task = db.query(ResearchTask).filter(
        ResearchTask.task_id == task_id, ResearchTask.lid == user.workspace_lid
    ).first()
    if task is None:
        return {"status_code": 404, "msg": "任务不存在"}
    steps = db.query(ResearchStep).filter(ResearchStep.task_id == task_id).all()
    artifacts = db.query(Artifact).filter(Artifact.task_id == task_id).all()
    return {
        "status_code": 200,
        "msg": "ok",
        "data": {
            "task_id": task.task_id,
            "goal": task.goal,
            "status": task.status,
            "parent_task_id": task.parent_task_id,
            "created_at": _utc_iso(task.created_at),
            "updated_at": _utc_iso(task.updated_at),
            "plan": json.loads(task.plan_json) if task.plan_json else None,
            "steps": [
                {
                    "step_id": s.step_id,
                    "skill_name": s.skill_name,
                    "status": s.status,
                    "error": s.error,
                    "duration_ms": s.duration_ms,
                }
                for s in steps
            ],
            "artifacts": [
                {
                    "artifact_id": a.artifact_id,
                    "type": a.type,
                    "title": a.title,
                    "data": json.loads(a.data_json) if a.data_json else {},
                }
                for a in artifacts
            ],
        },
    }
