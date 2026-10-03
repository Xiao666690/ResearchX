from contextlib import asynccontextmanager
import asyncio

import dotenv

dotenv.load_dotenv()

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from langchain_core.embeddings import Embeddings

from core.agent.chatAgent import ChatAgent
from core.backend.db.database import SessionLocal, engine
from core.backend.db.models import Base
from core.backend.router import (
    router_document,
    router_knowledge,
    router_llm,
    router_translate,
    router_user,
    router_note,
    router_post,
    router_commit,
    router_qa,
    router_research,
    router_system,
    router_dashboard,
    router_team,
)
from core.common.config import settings
from core.decision.engine import DecisionEngine
from core.llm.LLM import LLM
from core.vectordb.chromadb import AcadeChroma


Base.metadata.create_all(bind=engine)
with engine.begin() as connection:
    if "role" not in {row[1] for row in connection.execute(text("PRAGMA table_info(users)"))}:
        connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'user'"))
    if "category" not in {row[1] for row in connection.execute(text("PRAGMA table_info(posts)"))}:
        connection.execute(text("ALTER TABLE posts ADD COLUMN category VARCHAR(20) NOT NULL DEFAULT '技术'"))
    if "parent_task_id" not in {row[1] for row in connection.execute(text("PRAGMA table_info(research_tasks)"))}:
        connection.execute(text("ALTER TABLE research_tasks ADD COLUMN parent_task_id VARCHAR(64)"))


def _init_role_and_default_team():
    """幂等初始化：确保 admin 用户有 admin 角色 + 存在默认团队（owner 为 admin）。
    存量数据库也执行，保证老数据升级后同样具备团队能力。"""
    from core.backend.db.models import Team, TeamMember, User

    with SessionLocal() as session:
        # 1) admin 用户角色置为 admin（若已是则跳过）
        admin = session.query(User).filter(User.username == "admin").first()
        if admin and admin.role != "admin":
            admin.role = "admin"
            session.commit()
        # 2) 若不存在 admin 的默认团队则创建（team_id 复用 admin 的 lid）
        if admin:
            team = session.query(Team).filter(Team.owner_username == "admin").first()
            if not team:
                session.add(Team(team_id=admin.lid, owner_username="admin", team_name="默认团队"))
                session.commit()
            print(f"[team] 默认团队就绪 team_id={admin.lid}")


_init_role_and_default_team()


def _build_skill_registry():
    """注册全部内置 Research Skills。"""
    from core.skills.builtin import (
        LocalRetrievalSkill,
        PaperCompareSkill,
        ReportGenerateSkill,
    )
    from core.skills.citation_verify import CitationVerifySkill
    from core.skills.extract import ExperimentExtractSkill, MethodExtractSkill
    from core.skills.paper_reader import PaperReaderSkill
    from core.skills.paper_search import PaperSearchSkill
    from core.skills.registry import SkillRegistry

    registry = SkillRegistry()
    registry.register(LocalRetrievalSkill())
    registry.register(ReportGenerateSkill())
    registry.register(PaperCompareSkill())
    registry.register(PaperSearchSkill())
    registry.register(PaperReaderSkill())
    registry.register(MethodExtractSkill())
    registry.register(ExperimentExtractSkill())
    registry.register(CitationVerifySkill())
    return registry


def _build_research_orchestrator(registry, llm, ctx):
    """构建 Research Planner → Executor → Verifier → Orchestrator。"""
    from core.research.executor import Executor
    from core.research.orchestrator import ResearchOrchestrator
    from core.research.planner import Planner
    from core.research.verifier import Verifier

    planner = Planner(llm, registry)
    executor = Executor(registry, ctx)
    return ResearchOrchestrator(planner, executor, Verifier())


class ONNXEmbeddings(Embeddings):
    """使用 ChromaDB 内置 ONNX 模型，无需 API key，不依赖 sentence-transformers"""
    def __init__(self):
        cache_dir = os.getenv("CHROMA_ONNX_CACHE_DIR")
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            ONNXMiniLM_L6_V2.DOWNLOAD_PATH = cache_dir
        self._ef = ONNXMiniLM_L6_V2()

    def embed_documents(self, texts):
        return self._ef(texts)

    def embed_query(self, text):
        return self._ef([text])[0]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 离线模型首次加载和推理可能超过前端普通请求的 10 秒预算。
    # 启动时预热，后续选择论文文本可直接使用已缓存的翻译器。
    try:
        from core.backend.services.translate import Translator
        await asyncio.to_thread(Translator().translate, "This paper presents a research method.")
        print("[translate] 离线英中模型预热完成")
    except Exception as exc:
        print(f"[translate] 离线模型暂不可用：{exc}")
    app.llm = LLM()
    app.chroma_db = AcadeChroma(
        os.getenv("CHROMA_LAYER1_DIR"),
        os.getenv("CHROMA_LAYER2_DIR"),
        ONNXEmbeddings(),
        app.llm
    )

    # 为每个模型创建 ChatAgent
    # 非流式 LLM 使用 deepseek 作为默认
    app.chat_agent = ChatAgent(
        app.llm.get_llm('deepseek'),
        app.llm.get_stream_llm('deepseek'),
        app.chroma_db
    )

    # 只注册实际配置过的模型，避免未配置模型静默回退为 DeepSeek。
    app.chat_agents = {'deepseek': app.chat_agent}
    for model_name in ('kimi', 'zhipu'):
        if model_name in app.llm.get_all_llms():
            app.chat_agents[model_name] = ChatAgent(
                app.llm.get_llm(model_name),
                app.llm.get_stream_llm(model_name),
                app.chroma_db,
            )

    # V2: DecisionEngine（轻量，基于 LLM Judge）
    app.decision_engine = DecisionEngine(app.llm.get_llm('deepseek'))

    # 保留现有 ONNX 向量库；本地 BGE-M3 与重排模型用于二阶段混合检索。
    # 模型缺失或加载失败时继续使用原有 ONNX 检索，已上传论文无需重建索引。
    app.retrieval_pipeline = None
    embedding_path = settings.BGE_M3_MODEL_PATH
    reranker_path = settings.RERANKER_MODEL_PATH
    if (
        os.getenv("ENABLE_BGE_RETRIEVAL", "true").lower() in ("1", "true", "yes", "on")
        and os.path.isfile(os.path.join(embedding_path, "pytorch_model.bin"))
        and os.path.isfile(os.path.join(reranker_path, "model.safetensors"))
    ):
        try:
            from core.retrieval.local_enhancer import LocalRetrievalEnhancer

            app.retrieval_pipeline = LocalRetrievalEnhancer(embedding_path, reranker_path)
            app.chroma_db.retrieval_enhancer = app.retrieval_pipeline
            print("[retrieval] ONNX + BM25 + BGE-M3 + reranker 已就绪")
        except Exception as exc:
            print(f"[retrieval] 本地模型加载失败，继续使用 ONNX：{exc}")

    # V2: SkillRegistry + ResearchOrchestrator
    app.skill_registry = _build_skill_registry()
    research_ctx = {
        "chroma_db": app.chroma_db,
        "llm": app.llm.get_llm('deepseek'),
        "decision_engine": app.decision_engine,
        "db_factory": SessionLocal,
    }
    app.research_orchestrator = _build_research_orchestrator(
        app.skill_registry, app.llm.get_llm('deepseek'), research_ctx
    )
    print(f"[V2] Research Orchestrator 初始化完成（{len(app.skill_registry.names())} 个 Skills）")

    yield
    # Clean up the ML models and release resources
    print("shutdown!")


app = FastAPI(
    title="PaperAgent API",
    version="2.0.0",
    description="PaperAgent 论文问答、知识库与深度研究 API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router_user.router, tags=["router_user"])
app.include_router(router_team.router, tags=["team"])
app.include_router(router_knowledge.router, tags=["knowledge"])
app.include_router(router_document.router, tags=["router_document"])
app.include_router(router_llm.router, tags=["router_llm"])
app.include_router(router_translate.router, tags=["router_translate"])
app.include_router(router_note.router, tags=["router_note"])
app.include_router(router_post.router, tags=["router_post"])
app.include_router(router_commit.router, tags=["router_commit"])
app.include_router(router_qa.router, tags=["router_qa"])
app.include_router(router_research.router, tags=["router_research"])
app.include_router(router_system.router, tags=["system"])
app.include_router(router_dashboard.router, tags=["dashboard"])
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
