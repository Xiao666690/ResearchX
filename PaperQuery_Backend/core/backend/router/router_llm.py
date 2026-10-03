# 获取知识所拥有的所有文档
from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
import json
import os
from arxiv_client import PARAMS, ArxivClient
from core.backend.router.req_res_schema import Chat_Request, Summarise_Request, TMP_Chat_Request
from core.backend.services.translate import Translator
import re

from core.backend.utils.utils import format_uids_to_json
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
router = APIRouter()


def get_chat_agent(request: Request, model: str):
    """根据模型名称获取对应的 ChatAgent，默认使用 deepseek"""
    agents = request.app.chat_agents
    return agents.get(model, agents['deepseek'])


## 聊天对话
@router.post("/chat/generate")
def chat_with_paper_generate(chat: Chat_Request, request: Request, token: str = Depends(oauth2_scheme)):
    agent = get_chat_agent(request, chat.model)
    docs = request.app.chroma_db.query_paper_with_score_layer1_by_filter(
        chat.input,
        {"documentID": chat.ref.documentID}
    )
    print(docs)
    output, context = agent.chat_with_memory(chat.context, chat.ref.selectedText, chat.question, docs)
    return {
        "status_code": 200,
        "msg": "chat successfully",
        "data": {
            "question": chat.question,
            "output": output,
            "context": context
        }
    }


## 流式对话
def chunked_yield(data, chunk_size=3):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


def get_translators():
    secret_id = os.getenv("TENCENT_SECRET_ID", "")
    secret_key = os.getenv("TENCENT_SECRET_KEY", "")
    translator = Translator(from_lang="zh", to_lang="en", secret_id=secret_id, secret_key=secret_key)
    translator_rev = Translator(from_lang="en", to_lang="zh", secret_id=secret_id, secret_key=secret_key)
    return translator, translator_rev


@router.post("/chat/generate_flow")
def chat_with_paper_generate_flow(chat: Chat_Request, request: Request, token: str = Depends(oauth2_scheme)):
    agent = get_chat_agent(request, chat.model)
    translator, translator_rev = get_translators()
    translatedinput = translator.translate(re.sub(r'[\n\r\t]', '', chat.question))
    # 将用户的问题作为RAG进行检索
    docs = request.app.chroma_db.query_paper_with_score_layer1_by_filter(
        translatedinput,
        {"documentID": chat.ref.documentID}
    )
    judge_result = agent.chat_judge_relate(chat.context, chat.ref.selectedText, translatedinput, docs)
    print(docs)
    ret = None
    results = None
    if (not judge_result["is_relevant"]) and (judge_result["is_professional"] and len(judge_result["arxiv_query_keyword"]) > 0):
        fetch_params = [PARAMS.TITLE, PARAMS.PDF_URL, PARAMS.PUBLISHED]
        client = ArxivClient(max_results=10)
        results = client.fetch_results(judge_result["arxiv_query_keyword"], fetch_params)
    else:
        ret = agent.chat_with_memory_ret_tmp(chat.context, translatedinput, docs)

    def predict():
        text = ""
        try:
            for _token in ret:
                token = _token.content
                js_data = {"code": "200", "msg": "ok", "data": token}
                yield f"data: {json.dumps(js_data, ensure_ascii=False)}\n\n"
                text += token
        except Exception as e:
            js_data = {"code": "500", "msg": str(e), "data": f"\n\n模型调用失败：{e}"}
            yield f"data: {json.dumps(js_data, ensure_ascii=False)}\n\n"

    def arxiv_search():
        js_data = {"code": "200", "msg": "ok", "data": "**您的专业性问题似乎跟本篇论文无关,为您联网检索到如下论文:<br>** \r\n"}
        yield f"data: {json.dumps(js_data, ensure_ascii=False)}\n\n"
        count = 1
        for paper in results:
            datalist = f"**{count}**.<u> [{translator_rev.translate(paper.get(PARAMS.TITLE, 'N/A'))}]({paper.get(PARAMS.PDF_URL, 'N/A')})</u> <br><br>"
            count += 1
            for chunk in chunked_yield(datalist):
                js_data = {"code": "200", "msg": "ok", "data": chunk}
                yield f"data: {json.dumps(js_data, ensure_ascii=False)}\n\n"

    if ret:
        generate = predict()
    else:
        generate = arxiv_search()
    return StreamingResponse(generate, media_type="text/event-stream")


@router.post("/chat/mulit_file_chat_generate_flow")
def chat_multi_file_generate_flow(chat: TMP_Chat_Request, request: Request, token: str = Depends(oauth2_scheme)):
    agent = get_chat_agent(request, chat.model)
    translator, translator_rev = get_translators()
    translatedinput = translator.translate(re.sub(r'[\n\r\t]', '', chat.question))
    # 将用户的问题作为RAG进行检索
    docs = request.app.chroma_db.query_paper_with_score_layer1_by_filter(
        translatedinput,
        format_uids_to_json(chat.uid)
    )
    print(docs)
    judge_result = agent.chat_judge_relate(chat.context, "", translatedinput, docs)
    ret = None
    results = None
    if (not judge_result["is_relevant"]) and (judge_result["is_professional"] and len(judge_result["arxiv_query_keyword"]) > 0):
        fetch_params = [PARAMS.TITLE, PARAMS.PDF_URL, PARAMS.PUBLISHED]
        client = ArxivClient(max_results=10)
        results = client.fetch_results(judge_result["arxiv_query_keyword"], fetch_params)
    else:
        ret = agent.chat_with_memory_ret(chat.context, "", translatedinput, docs)

    def predict():
        text = ""
        try:
            for _token in ret:
                token = _token.content
                js_data = {"code": "200", "msg": "ok", "data": token}
                yield f"data: {json.dumps(js_data, ensure_ascii=False)}\n\n"
                text += token
        except Exception as e:
            js_data = {"code": "500", "msg": str(e), "data": f"\n\n模型调用失败：{e}"}
            yield f"data: {json.dumps(js_data, ensure_ascii=False)}\n\n"

    def arxiv_search():
        js_data = {"code": "200", "msg": "ok", "data": "**您的专业性问题似乎跟本篇论文无关,为您联网检索到如下论文:<br>** \r\n"}
        yield f"data: {json.dumps(js_data, ensure_ascii=False)}\n\n"
        count = 1
        for paper in results:
            datalist = f"**{count}**. [{translator_rev.translate(paper.get(PARAMS.TITLE, 'N/A'))}]({paper.get(PARAMS.PDF_URL, 'N/A')}) <br><br>"
            count += 1
            for chunk in chunked_yield(datalist):
                js_data = {"code": "200", "msg": "ok", "data": chunk}
                yield f"data: {json.dumps(js_data, ensure_ascii=False)}\n\n"

    if ret:
        generate = predict()
    else:
        generate = arxiv_search()
    return StreamingResponse(generate, media_type="text/event-stream")


## 对话总结
@router.post("/chat/summarize")
def chat_summarise(chat: Summarise_Request, request: Request, token: str = Depends(oauth2_scheme)):
    output = request.app.chat_agent.chat_summarise(chat.context, chat.question, chat.answer)
    return {
        "status_code": 200,
        "msg": "记忆更新成功",
        "data": {
            "context": output
        }
    }
