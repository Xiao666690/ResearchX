'''
@Description: 
@Author: qwrdxer
@Date: 2024-07-22 21:31:52
@LastEditTime: 2024-07-23 15:46:14
@LastEditors: qwrdxer
'''
import datetime
from typing import List

from pydantic import BaseModel


class Response(BaseModel):
    status_code: int
    msg: str

# 知识创建
class KnowledgeCreate(BaseModel):
    knowledgeID: str | None = None #
    lid: str | None = None # 
    knowledgeName: str 
    knowledgeDescription: str  | None = None # 
    documentNum:int =0
    vectorNum:int  =0


# 知识更新
class KnowledgeUpdate(KnowledgeCreate):
    documentNum: int | None = None
    vectorNum: int | None = None


class KnowledgeEdit(BaseModel):
    knowledgeID: str
    knowledgeName: str
    knowledgeDescription: str | None = None
# 用户所有知识描述

# 知识获取
class KnowledgeGet(KnowledgeCreate):
    documentNum: int | None = None
    vectorNum: int | None = None
    
# 返回知识
class KnowledgeQuery(Response):
    data: List[KnowledgeGet] | None = None

class LoginRequest(BaseModel):
    username: str
    password: str

# 注册请求：团队名为可选字段，填了=提交加入申请（团队名=管理员名字，待管理员审批）
class RegisterRequest(BaseModel):
    username: str
    password: str
    team_name: str = ''   # 可选；填了即提交加入该团队的申请

# 审批通过加入申请（管理员操作）
class TeamApproveRequest(BaseModel):
    username: str

# 拒绝加入申请（管理员操作）
class TeamRejectRequest(BaseModel):
    username: str

# 删除成员（管理员操作）
class TeamRemoveRequest(BaseModel):
    username: str


class TeamRenameRequest(BaseModel):
    team_name: str

# 文件Document创建
class DocumentCreate(BaseModel):
    uid : str 
    knowledgeID : str 
    lid: str 
    documentName: str
    documentPath: str
    documentStatus: int
    createTime: datetime.datetime | None = None
# 临时document创建
class TMPDocumentCreate(BaseModel):
    uid : str 
    knowledgeID : str 
    lid: str 
    documentName: str
    documentPath: str
    documentStatus: int
    createTime: datetime.datetime | None = None

# 向量相关更新
class DocumentUpdate(DocumentCreate):
    fvector: int | None =None
    
    primary_classification: str | None = None
    secondary_classification: str | None = None
    tags: str | None = None
    fdesc: str | None = None

#文件查询
class DocumentQuery(DocumentCreate):
    fvector: int
    primary_classification: str | None = None
    secondary_classification: str | None = None
    tags: str | None = None
    description: str | None = None




class UserCreate(BaseModel):
    username: str
    password: str

class UserQuery(BaseModel):
    username: str | None = None
    password: str | None = None

##------------

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
    lid: str | None = None
    exp: datetime.datetime | None = None
