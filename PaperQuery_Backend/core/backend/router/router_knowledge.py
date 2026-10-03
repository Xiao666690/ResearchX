
import os
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.backend.crud.crud_knowledge import (
    create_knowledge,
    get_knowledge_by_lid,
    get_knowledge_by_name,
    get_knowledge_by_name_uid,
    get_knowledges_statistics,
)
from core.backend.crud.crud_note import del_note
from core.backend.router.dependencies import get_db
from core.backend.db.models import Document, Knowledge, TMPDocument
from core.backend.router.req_res_schema import DeleteKnowledge
from core.backend.schema.noteschema import NoteDelete
from core.backend.schema.schema import KnowledgeCreate, KnowledgeEdit
from core.backend.utils.utils import *

router = APIRouter()
##-----------------------------------------------------------
# 获取用户的知识库描述
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@router.get("/knowledges/getLibraryInfo")
async def describe_knowledge(token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):
    user =await get_current_user(token,db)
    Knowledgecount,filecount,vectorcount=get_knowledges_statistics(db, user.workspace_lid)
    return {
        "status_code": 200,
        "msg": "Get knowledge statistics successfully",
        "data": {
            "libraryID" : user.workspace_lid,
            "knowledgeNumSum": Knowledgecount,
            "documentNumSum": filecount,
            "vectorNumSum": vectorcount
        }
    }

# 获取用户拥有的所有 `知识`
@router.get("/knowledges/getKnowledgeList")
async def get_knowledges_all(token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):
    #获取当前用户
    user =await get_current_user(token,db)
    print(user.workspace_lid)
    knowledges=get_knowledge_by_lid(db, user.workspace_lid)
    filtered_documents = [{"knowledgeID": knowledge.knowledgeID,"knowledgeName":knowledge.knowledgeName, "knowledgeDescription":knowledge.knowledgeDescription,"documentNum":knowledge.documentNum,"vectorNum":knowledge.vectorNum} for knowledge in knowledges]
    
    print(filtered_documents)
    #根据用户lid获取其拥有的全部知识
    return {"status_code": 200, 
            "msg":"Get knowledge list successfully", 
            "data":{
                "knowledgeList": filtered_documents
            }
            }

# 用户创建新的知识
@router.post("/knowledges/createKnowledge")
async def create_knowledges(knowledge: KnowledgeCreate, token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):
    user =await get_current_user(token,db)
    # 查询是否有重复的知识名
    if get_knowledge_by_name_uid(db, knowledge.knowledgeName, user.workspace_lid):
        return {
            "status_code": 409,
            "msg": "Knowledge name already exists",
        }
    knowledge.lid = user.workspace_lid
    knowledge.knowledgeID = str(uuid.uuid1())
    created_k= create_knowledge(db, knowledge)

    return{
        "status_code": 200,
        "msg": "Create knowledge successfully",
        "data": {
            "knowledgeID": created_k.knowledgeID,
            "knowledgeName": created_k.knowledgeName,
            "knowledgeDescription": created_k.knowledgeDescription,
            "documentNum": created_k.documentNum,
            "vectorNum": created_k.vectorNum
        }
    }


@router.post("/knowledges/updateKnowledge")
async def update_knowledge(
    payload: KnowledgeEdit,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = await get_current_user(token, db)
    knowledge = db.query(Knowledge).filter(
        Knowledge.knowledgeID == payload.knowledgeID,
        Knowledge.lid == user.workspace_lid,
    ).first()
    if not knowledge:
        return {"status_code": 404, "msg": "Knowledge not found"}

    duplicate = db.query(Knowledge).filter(
        Knowledge.lid == user.workspace_lid,
        Knowledge.knowledgeName == payload.knowledgeName,
        Knowledge.knowledgeID != payload.knowledgeID,
    ).first()
    if duplicate:
        return {"status_code": 409, "msg": "Knowledge name already exists"}

    knowledge.knowledgeName = payload.knowledgeName
    knowledge.knowledgeDescription = payload.knowledgeDescription
    db.commit()
    db.refresh(knowledge)
    return {
        "status_code": 200,
        "msg": "Update knowledge successfully",
        "data": {
            "knowledgeID": knowledge.knowledgeID,
            "knowledgeName": knowledge.knowledgeName,
            "knowledgeDescription": knowledge.knowledgeDescription,
            "documentNum": knowledge.documentNum,
            "vectorNum": knowledge.vectorNum,
        },
    }


# 批量删除知识（级联删除其下文档的向量、笔记与源文件）
@router.post("/knowledges/deleteKnowledge")
async def delete_knowledges(
    payload: DeleteKnowledge,
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = await get_current_user(token, db)
    deleted = []
    failed = []
    for kid in payload.knowledgeIDs:
        knowledge = (
            db.query(Knowledge)
            .filter(Knowledge.knowledgeID == kid, Knowledge.lid == user.workspace_lid)
            .first()
        )
        if not knowledge:
            failed.append(kid)
            continue
        # 级联删除该知识下的文档
        docs = (
            db.query(Document)
            .filter(Document.knowledgeID == kid, Document.lid == user.workspace_lid)
            .all()
        )
        for doc in docs:
            # 删除向量（layer1 / layer2）
            try:
                request.app.chroma_db.delete_paper_from_layer1(kid, doc.uid)
                request.app.chroma_db.delete_paper_from_layer2(kid, doc.uid)
            except Exception:
                pass
            # 删除该文档的笔记
            try:
                del_note(
                    db=db,
                    delNote=NoteDelete(uid=doc.uid, knowledgeID=kid, lid=user.workspace_lid),
                )
            except Exception:
                pass
            # 若没有其他知识仍引用同一文档，则删除源文件
            try:
                other = (
                    db.query(Document)
                    .filter(
                        Document.uid == doc.uid,
                        Document.knowledgeID != kid,
                    )
                    .first()
                )
                if not other:
                    file_path = os.getenv("AcadeAgent_DIR") + doc.documentPath
                    if os.path.exists(file_path):
                        os.remove(file_path)
            except Exception:
                pass
            db.delete(doc)
        # 删除该知识下的临时文档记录
        db.query(TMPDocument).filter(
            TMPDocument.knowledgeID == kid,
            TMPDocument.lid == user.workspace_lid,
        ).delete(synchronize_session=False)
        # 删除知识本身
        db.delete(knowledge)
        db.commit()
        deleted.append(kid)
    return {
        "status_code": 200,
        "msg": "知识删除成功" if deleted else "未找到可删除的知识",
        "data": {"deleted": deleted, "failed": failed},
    }
