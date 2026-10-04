
import datetime
from typing import List

from pydantic import BaseModel

# 获取note请求
class NoteRequest(BaseModel):
    knowledgeID: str 
    documentID: str 
# 更新note请求
class NoteUpdateRequest(BaseModel):
    knowledgeID: str 
    documentID: str 
    note: str
#curd
class NoteQuery(BaseModel):
    knowledgeID: str 
    lid: str
    uid: str 
class NoteCreate(BaseModel):
    knowledgeID: str 
    lid: str
    uid: str 
class NoteDelete(BaseModel):
    knowledgeID: str 
    lid: str
    uid: str 
class NoteUpdate(BaseModel):
    knowledgeID: str 
    lid: str
    uid: str 
    note: str