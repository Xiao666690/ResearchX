from fastapi import HTTPException
from pydantic import BaseModel, Field


class LoginException(HTTPException):
    def __init__(self, status_code: int, msg: str):
        self.status_code = status_code
        self.msg = msg

class Ref(BaseModel):
    knowledgeID: str
    documentID: str
    selectedText: str
    page: int

class Chat_Request(BaseModel):
    question: str
    ref: Ref
    context: str
    model: str = "deepseek"  # 可选: deepseek, kimi, zhipu


class DeleteDocument(BaseModel):
    documentID: str
    knowledgeID: str


class DeleteKnowledge(BaseModel):
    knowledgeIDs: list[str]


class TranslateRequest(BaseModel):
    text: str

class Summarise_Request(BaseModel):
    question: str
    answer: str
    context: str
#临时聊天的请求,包含 问题、上下文、临时文件的所有uid
class TMP_Chat_Request(BaseModel):
    question: str
    context: str
    uid: list
    model: str = "deepseek"  # 可选: deepseek, kimi, zhipu


# V2 Ask Mode 请求
class QARequest(BaseModel):
    question: str
    document_ids: list[str] = Field(default_factory=list)
    model: str = "deepseek"
    mode: str = "ask"  # ask / research / experiment
    conversation_context: str = ""
