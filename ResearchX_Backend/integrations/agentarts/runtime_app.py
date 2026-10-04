"""AgentArts HTTP inbound protocol for the public-paper ResearchX Agent.

The Runtime container intentionally has no access to a user's local ChromaDB.
Only public paper tools are advertised to its planner. Local Library/Ask stay
on the existing FastAPI service until a shared data store is configured.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.decision.engine import DecisionEngine
from core.evidence.gate import ResearchEvidenceGate
from core.llm.LLM import LLM
from core.research.executor import Executor
from core.research.orchestrator import ResearchOrchestrator
from core.research.planner import Planner
from core.research.verifier import Verifier
from core.skills.builtin import PaperCompareSkill, ReportGenerateSkill
from core.skills.paper_search import PaperSearchSkill
from core.skills.registry import SkillRegistry


class Invocation(BaseModel):
    goal: str = Field(min_length=3, max_length=4000)
    model: Literal["deepseek", "kimi", "zhipu"] = "deepseek"
    document_ids: list[str] = Field(default_factory=list)


def public_tool_registry() -> SkillRegistry:
    registry = SkillRegistry()
    # Goal-level Verifier already checks citations and grounding. Exposing the
    # low-level citation skill here lets the planner pass incomplete inputs.
    for skill in (PaperSearchSkill(), PaperCompareSkill(), ReportGenerateSkill()):
        registry.register(skill)
    return registry


@lru_cache(maxsize=1)
def model_provider() -> LLM:
    return LLM()


app = FastAPI(title="ResearchX AgentArts Runtime", version="1.0.0")


@app.get("/ping")
def ping():
    return {"status": "Healthy"}


@app.post("/invocations")
async def invoke(request: Invocation):
    if request.document_ids:
        raise HTTPException(status_code=422, detail="云端运行时尚未接入本地论文库，请使用公开论文检索")

    provider = model_provider()
    if request.model not in provider.get_all_llms():
        raise HTTPException(status_code=503, detail=f"模型 {request.model} 未配置")

    llm = provider.get_llm(request.model)
    decision_engine = DecisionEngine(llm)
    registry = public_tool_registry()
    context = {"llm": llm, "decision_engine": decision_engine,
               "allowed_document_ids": [], "available_documents": []}
    orchestrator = ResearchOrchestrator(
        Planner(llm, registry), Executor(registry, context),
        Verifier(decision_engine), ResearchEvidenceGate(decision_engine),
    )
    state = await orchestrator._run(request.goal, context)
    return {"task_id": state.task_id, "status": state.status,
            "stop_reason": state.stop_reason, "state": state.model_dump(mode="json")}
