"""V2 Ask Mode 可信问答路由。

流程：Intent → Retrieval → Evidence Judge → Answer → Grounding → SSE 分片输出。
旧 /chat/* 作为兼容接口保留，新前端走 /qa/stream。
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.backend.db.models import ActivityEvent, Document, TMPDocument
from core.backend.router.dependencies import get_db
from core.backend.utils.utils import get_current_user
from core.backend.router.req_res_schema import QARequest
from core.decision.engine import DecisionEngine
from core.decision.external_search import (
    classify_external_request,
    is_broad_paper_recommendation,
    make_research_prompt,
    make_search_keywords,
    normalize_papers,
    wants_recent_papers,
)
from core.decision.prompts import ANSWER_PROMPT, GENERAL_CHAT_PROMPT
from core.decision.schemas import EvidenceDecision, IntentType
from core.evidence.formatter import build_citations, format_evidence
from core.skills.paper_search import PaperSearchSkill

router = APIRouter()

_PAPER_REFERENCE = re.compile(
    r"这(?:篇|些|两篇|几篇|多篇)(?:论文|文章|文献)|该(?:篇)?(?:论文|文章|文献)|"
    r"本(?:篇|文|论文)|所选(?:论文|文献)|当前(?:论文|文献)|上述(?:论文|文献)|"
    r"(?:选中|选定|上传|绑定)(?:的)?(?:论文|文章|文献|PDF)|"
    r"(?:这|当前)(?:个|份)?PDF|"
    r"(?:论文|文章|文献)(?:的|中|里|讲|介绍|总结|主要|核心)|"
    r"\b(?:this|selected|attached|uploaded|current)\s+papers?\b",
    re.IGNORECASE,
)
_PAPER_OVERVIEW = re.compile(
    r"讲一下|介绍一下|概述|概括|总结|摘要|主要内容|核心内容|解读|"
    r"(?:overview|summari[sz]e|introduce|explain)\b",
    re.IGNORECASE,
)


def _targets_selected_paper(question: str, names: list[str]) -> bool:
    query = question.strip()
    if _PAPER_REFERENCE.search(query):
        return True
    if any(name.casefold() in query.casefold() for name in names if name):
        return True
    # A short deictic prompt after the user bound a PDF also targets that PDF.
    return bool(re.fullmatch(r"(?:帮我|请|先)?(?:讲一下|介绍一下|总结一下|概括一下|解读一下)[。！？?\s]*", query))


def _is_paper_overview(question: str) -> bool:
    if re.search(r"实验|消融|公式|参数|数据集|评估|指标|具体结果|局限|缺点|细节", question):
        return False
    return bool(_PAPER_OVERVIEW.search(question))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_model_text(agent, prompt: str):
    """统一提取 LangChain 流式消息中的文本 token。"""
    stream = (
        agent.chat_simple(prompt)
        if hasattr(agent, "chat_simple")
        else agent.get_llm().stream(prompt)
    )
    for chunk in stream:
        content = chunk.content if hasattr(chunk, "content") else str(chunk)
        if isinstance(content, str) and content:
            yield content


@router.post("/qa/stream")
def qa_stream(
    qa: QARequest,
    request: Request,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    selected_papers = []
    if qa.document_ids:
        selected_ids = set(qa.document_ids)
        owned_papers = {
            row.uid: row for row in db.query(Document).filter(
                Document.lid == user.workspace_lid, Document.uid.in_(selected_ids)
            ).all()
        }
        owned_papers.update(
            (row.uid, row) for row in db.query(TMPDocument).filter(
                TMPDocument.lid == user.workspace_lid, TMPDocument.uid.in_(selected_ids)
            ).all()
        )
        if not selected_ids.issubset(owned_papers):
            raise HTTPException(status_code=403, detail="部分论文不在当前账号的资料库中")
        selected_papers = [owned_papers[document_id] for document_id in dict.fromkeys(qa.document_ids)]
    selected_names = [paper.documentName for paper in selected_papers]
    selected_paper_text = "、".join(selected_names) if selected_names else "无"

    # Count submitted Ask requests for this account. The event contains no question text.
    db.add(ActivityEvent(lid=user.workspace_lid, event_type="ask"))
    db.commit()

    trace_id = uuid.uuid4().hex[:12]
    agent = getattr(request.app, "chat_agents", {}).get(qa.model)
    if agent is None:
        agent = getattr(request.app, "chat_agents", {}).get("deepseek")
    decision_engine = (
        DecisionEngine(agent.get_llm())
        if agent is not None
        else getattr(request.app, "decision_engine", None)
    )
    chroma_db = getattr(request.app, "chroma_db", None)

    def generate():
        # 1. Intent 判断
        external_kind = classify_external_request(qa.question)
        intent = None
        if external_kind:
            yield _sse("meta", {
                "trace_id": trace_id,
                "route": "EXTERNAL_RESEARCH",
                "intent": IntentType.RESEARCH_TASK.value,
            })
        elif not qa.document_ids:
            yield _sse("meta", {
                "trace_id": trace_id,
                "route": "GENERAL_CHAT",
                "intent": IntentType.GENERAL_CHAT.value,
            })
        elif _targets_selected_paper(qa.question, selected_names):
            yield _sse("meta", {
                "trace_id": trace_id,
                "route": "LOCAL_RAG",
                "intent": IntentType.MULTI_PAPER_QA.value if len(selected_papers) > 1 else IntentType.PAPER_QA.value,
            })
        elif decision_engine is not None:
            intent = decision_engine.decide_intent(
                qa.question,
                f"当前已选论文：{selected_paper_text}\n{qa.conversation_context}",
            )
            route = "GENERAL_CHAT" if intent.intent == IntentType.GENERAL_CHAT else "LOCAL_RAG"
            yield _sse("meta", {
                "trace_id": trace_id,
                "route": route,
                "intent": intent.intent.value,
            })
        else:
            yield _sse("meta", {
                "trace_id": trace_id,
                "route": "LOCAL_RAG",
                "intent": IntentType.PAPER_QA.value,
            })

        # 普通聊天不需要论文证据，直接交给当前模型自然回答。
        if not external_kind and (not qa.document_ids or (intent is not None and intent.intent == IntentType.GENERAL_CHAT)):
            fallback_answer = "当前问答模型暂时不可用，请稍后重试。"
            if agent is not None:
                prompt = GENERAL_CHAT_PROMPT.format(
                    question=qa.question,
                    conversation_context=qa.conversation_context or "（暂无）",
                    selected_papers=selected_paper_text,
                )
            yield _sse("decision", {
                "decision": "GENERAL_CHAT",
                "evidence_score": 1.0,
                "confidence": intent.confidence if intent is not None else 1.0,
            })
            streamed = False
            if agent is not None:
                try:
                    for text in _stream_model_text(agent, prompt):
                        streamed = True
                        yield _sse("delta", {"text": text})
                except Exception:
                    # 模型暂时不可用时仍给出友好的问候，不回退到证据不足提示。
                    pass
            if not streamed:
                yield _sse("delta", {"text": fallback_answer})
            yield _sse("grounding", {
                "passed": True,
                "confidence": 1.0,
                "skipped": True,
                "reason": "GENERAL_CHAT",
            })
            yield _sse("citations", {"items": []})
            return

        # 2. 检索
        evidence = []
        if chroma_db is not None and qa.document_ids:
            overview = _is_paper_overview(qa.question)
            if overview and hasattr(chroma_db, "get_opening_evidence"):
                evidence.extend(chroma_db.get_opening_evidence(qa.document_ids))
            retrieved = chroma_db.search_evidence(
                "paper abstract introduction main method contributions and results" if overview else qa.question,
                {"documentID": {"$in": qa.document_ids}},
                k=4 if overview else 8,
            )
            seen_chunks = {item.chunk_id for item in evidence}
            seen_texts = {(item.document_id, item.text) for item in evidence}
            for item in retrieved:
                if item.chunk_id not in seen_chunks and (item.document_id, item.text) not in seen_texts:
                    evidence.append(item)
                    seen_chunks.add(item.chunk_id)
                    seen_texts.add((item.document_id, item.text))
            evidence = evidence[:8 if overview else 12]

        if qa.document_ids and not evidence and not external_kind:
            yield _sse("decision", {"decision": "ABSTAIN", "evidence_score": 0.0, "confidence": 1.0})
            yield _sse("delta", {
                "text": f"已选定 {selected_paper_text}，但当前尚未读取到可用于问答的论文文本。请确认论文处理状态为“完成”后重试。"
            })
            yield _sse("citations", {"items": []})
            return

        # 3. 证据格式化 + 引用映射
        evidence_text, citation_map = format_evidence(evidence)

        # 4. Evidence Judge
        if decision_engine is not None or external_kind:
            if external_kind:
                ev = EvidenceDecision(decision="SEARCH_EXTERNAL", confidence=1.0, evidence_score=0.0)
            elif _is_paper_overview(qa.question) and evidence:
                ev = EvidenceDecision(decision="ANSWER", confidence=1.0, evidence_score=1.0)
            else:
                ev = decision_engine.decide_evidence(qa.question, evidence_text)
            search_external = ev.decision == "SEARCH_EXTERNAL"
            yield _sse("decision", {
                "decision": "SEARCH_EXTERNAL" if search_external else ev.decision,
                "evidence_score": ev.evidence_score,
                "confidence": ev.confidence,
            })
            if search_external:
                broad_request = is_broad_paper_recommendation(qa.question)
                yield _sse("search_status", {
                    "state": "preparing",
                    "text": "正在准备近期论文检索…" if broad_request else "正在结合所选论文和目标领域提取检索词…",
                })
                keywords = (
                    make_search_keywords(
                        decision_engine.llm if decision_engine is not None else None,
                        qa.question,
                        evidence_text,
                        kind=external_kind or "literature",
                    )
                    if not ev.search_keywords
                    else ev.search_keywords[:3]
                )
                yield _sse("search_status", {
                    "state": "searching",
                    "text": "正在检索 arXiv / OpenAlex：" + "、".join(keywords),
                })
                result = asyncio.run(PaperSearchSkill().run(
                    {"keywords": keywords, "max_results": 8, "recent": wants_recent_papers(qa.question)}
                ))
                papers = normalize_papers(result.output.get("papers", [])) if result.ok else []
                yield _sse("external_papers", {
                    "items": papers,
                    "keywords": keywords,
                    "provider": result.output.get("provider", "") if result.ok else "",
                    "warning": result.output.get("warning", "") if result.ok else result.error_message,
                })
                if papers:
                    yield _sse("search_status", {
                        "state": "answering",
                        "text": f"从 {result.output.get('provider', '学术来源')} 找到 {len(papers)} 篇论文，正在对照摘要整理建议…",
                    })
                    if agent is not None:
                        prompt = make_research_prompt(
                            qa.question, evidence_text, papers, kind=external_kind or "literature"
                        )
                        try:
                            for text in _stream_model_text(agent, prompt):
                                yield _sse("delta", {"text": text})
                        except Exception:
                            yield _sse("delta", {"text": "已找到相关论文，请先查看下方题目和摘要，再选择需要核查的 PDF。"})
                    else:
                        yield _sse("delta", {"text": "已找到相关论文，请查看下方结果并选择需要进一步阅读的 PDF。"})
                else:
                    yield _sse("search_status", {
                        "state": "answering", "text": "学术来源暂未返回可核实的论文，正在整理下一步建议…",
                    })
                    fallback = (
                        "我可以推荐近期论文，但目前学术检索源没有返回可核实的题录，因此不能编造具体篇名。"
                        "你想关注哪个方向？例如大模型、计算机视觉、联邦学习或医学影像。"
                        "指定领域后，我会重新检索并列出真实论文供你选择。"
                    ) if broad_request else (
                        "目前外部学术检索没有返回可核实的论文题录。"
                        "我可以先帮你梳理这个问题的研究关键词和筛选思路；"
                        "如果你给出更具体的领域、方法或时间范围，我会继续检索。"
                    )
                    streamed = False
                    if agent is not None:
                        prompt = (
                            "你是 PaperAgent 学术助手。用户提出了下面的问题，但实时学术搜索没有返回可核实的论文题录。"
                            "请先直接回应用户能做什么，给出简短、有用的研究方向或筛选建议，"
                            "并询问最关键的领域偏好。不可编造具体论文标题、作者或最新发表事实；"
                            "明确说明当前未取得可核实题录。\n用户问题：" + qa.question[:1000]
                        )
                        try:
                            for text in _stream_model_text(agent, prompt):
                                streamed = True
                                yield _sse("delta", {"text": text})
                        except Exception:
                            pass
                    if not streamed:
                        yield _sse("delta", {"text": fallback})
                yield _sse("search_status", {"state": "done", "text": "外部学术检索已完成"})
                yield _sse("grounding", {"passed": False, "confidence": ev.confidence, "reason": "EXTERNAL_METADATA_ONLY"})
                yield _sse("citations", {
                    "items": [
                        {
                            "id": c.citation_id,
                            "documentID": c.document_id,
                            "knowledgeID": c.knowledge_id,
                            "page": c.page_number,
                            "chunk_id": c.chunk_id,
                        }
                        for c in build_citations(citation_map)
                    ]
                })
                return
            if ev.decision == "ABSTAIN":
                yield _sse("delta", {"text": "当前所选论文没有足够证据回答该问题。"})
                yield _sse("grounding", {"passed": False, "confidence": ev.confidence})
                return

        # 5. Answer 生成（带引用）
        answer = ""
        if agent is not None:
            prompt = ANSWER_PROMPT.format(
                question=qa.question,
                evidence=evidence_text,
                selected_papers=selected_paper_text,
            )
            for text in _stream_model_text(agent, prompt):
                answer += text
                yield _sse("delta", {"text": text})

        # 6. Grounding Verify
        citations = build_citations(citation_map)
        if decision_engine is not None:
            from core.evidence.grounding import GroundingVerifier
            verifier = GroundingVerifier(decision_engine)
            grounding_passed, report = verifier.verify(
                qa.question, answer, citations, citation_map
            )
            yield _sse("grounding", {"passed": grounding_passed, "confidence": report["confidence"]})

        # 7. Citations
        yield _sse("citations", {
            "items": [
                {
                    "id": c.citation_id,
                    "documentID": c.document_id,
                    "knowledgeID": c.knowledge_id,
                    "page": c.page_number,
                    "chunk_id": c.chunk_id,
                }
                for c in citations
            ]
        })

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
