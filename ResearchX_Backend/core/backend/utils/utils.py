# 使用Data 生成token
from datetime import datetime, timedelta, timezone
import re
import json
from typing import Annotated, Union
import fitz
from core.backend.services.paper_inspection import extract_page_text
from colorama import Fore, Style
import jwt,os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.backend.crud.crud_user import query_user
from core.backend.db.models import Team, TeamMember
from core.backend.router.dependencies import *

from core.utils.util import cal_file_md5, check_and_parse_json, split_text_into_chunks
from core.vectordb.chromadb import AcadeChroma


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=60000)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, os.getenv("SECRET_KEY"), algorithm=os.getenv("ALGORITHM"))
    return encoded_jwt




def generate_future_timestamp(minutes: int):
    """
    生成指定分钟以后的时间戳（以秒为单位的整数）

    :param minutes: 指定的分钟数
    :return: 指定分钟以后的时间戳（以秒为单位的整数）
    """
    now =datetime.now(timezone.utc)
    future_timestamp= now + timedelta(minutes=minutes)
     
    return int(future_timestamp.timestamp())

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_workspace_lid(db, user) -> str:
    """返回用户的有效工作空间 lid：
    - 管理员（默认团队 owner）→ 自己的 lid
    - 已加入团队的成员       → 该团队 owner 的 lid（共享管理员的）
    - 其他（未入团）         → 自己的 lid（个人空间，行为不变）
    """
    # 1) 查该用户是否作为成员加入某团队
    member = db.query(TeamMember).filter(TeamMember.member_username == user.username).first()
    if member:
        team = db.query(Team).filter(Team.team_id == member.team_id).first()
        if team:
            return team.team_id  # 共享管理员 lid
    # 2) 管理员/未入团用户：自己的 lid 即工作空间
    return user.lid


def attach_workspace_lid(db, user):
    """把解析出的有效工作空间挂到 user 对象上，供所有资源路由复用（避免各处遗漏）"""
    user.workspace_lid = get_workspace_lid(db, user)
    return user

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        username: str = payload.get("username") 
    except Exception:
        raise credentials_exception
    user = query_user(db, username=username)
    if user is None:
        raise credentials_exception
    return attach_workspace_lid(db, user)


def get_document_tags(doc):
    """
    从文档对象中提取并过滤分类和标签
    """
    tags = [doc.primaryClassification, doc.secondaryClassification] + (doc.tags.split(",") if doc.tags else [])
    # 使用列表推导式去除空字符串
    filtered_tags = [tag.strip() for tag in tags if tag and tag.strip()]
    return filtered_tags


def get_filtered_documents(documents):
    """
    从文档列表中创建过滤后的文档字典列表
    """
    filtered_documents = [{
        "documentID": doc.uid,
        "documentName": doc.documentName,
        "documentStatus": doc.documentStatus,
        "documentTags": get_document_tags(doc) if (doc.primaryClassification or doc.secondaryClassification or doc.tags) else [],
        "vectorNum": doc.documentVector,
        "createTime": doc.createTime_timestamp
    } for doc in documents]
    return filtered_documents


def clean_markdown_json_blocks(text):
    # 检查是否包含 ```json 块
    if '```json' in text:
        # 使用正则表达式匹配并去除 ```json ``` 块
        print(Fore.GREEN,text,Style.RESET_ALL)
        text = re.sub(r'\s*```json\s*', '', text, flags=re.DOTALL)
        # 第二步：去除 ``` 块
        text = re.sub(r'\s*```\s*', '', text, flags=re.DOTALL)
        return text.strip()
    else:
        # 如果没有 ```json 块，直接返回原始文本
        return text
    

def vector_paper_for_tmp(filepath,file_hash,knowledgeID,chromadb:AcadeChroma):
    doc = fitz.open(filepath)
    chunks = []
    chunksMetadataList = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text, _ = extract_page_text(page)
        if text:
            for chunk in split_text_into_chunks(text):
                chunks.append(chunk)
                metadata = {
                    'source': filepath,
                    'documentID': file_hash,
                    'knowledge_name': knowledgeID,#临时知识ID
                    'page_number': page_num + 1
                }
                chunksMetadataList.append(metadata)
    print(chunksMetadataList[0])
    chromadb.add_paper_to_layer1(chunks, chunksMetadataList)
    return len(chunksMetadataList)



def format_uids_to_json(uid_list):
    """
    将给定的 UID 列表格式化为特定的 JSON 格式。

    参数:
    uid_list (list): 包含 UID 字符串的列表。

    返回:
    str: 格式化的 JSON 字符串，其中包含 UID 列表中的每个 UID。

    示例:
    >>> uid_list = [
    >>>     "1ea21b3369043655250dd228a3e21486",
    >>>     "92557e08092fb856bca961e816f4110b"
    >>> ]
    >>> json_output = format_uids_to_json(uid_list)
    >>> print(json_output)
    {
        "$or": [
            {
                "documentID": {
                   "$eq": "1ea21b3369043655250dd228a3e21486"
                }
            },
            {
                "documentID": {
                    "$eq": "92557e08092fb856bca961e816f4110b"
                }
            }
        ]
    }
    """
    if(len(uid_list)==1):
        formatted_data= {"documentID": {
            "$eq": uid_list[0]
        }}
    elif len(uid_list) == 0:
        formatted_data = {}
    else:
        formatted_data = {
            "$or": [
                {
                    "documentID": {
                        "$eq": uid
                    }
                }
                for uid in uid_list
            ]
        }
    return formatted_data
