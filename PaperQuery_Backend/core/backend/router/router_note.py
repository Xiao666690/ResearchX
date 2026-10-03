from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from core.backend.crud.crud_note import get_note, update_note
from core.backend.schema.noteschema import NoteQuery, NoteRequest, NoteUpdate,NoteUpdateRequest
from core.backend.utils.utils import *
from core.backend.router.dependencies import get_db
from core.backend.db.models import Document, Note
from fastapi import HTTPException
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
router = APIRouter()

## 因为笔记是跟用户和知识库唯一绑定的,因此创建和删除笔记的部分都跟创建删除文档绑定到一起了。

#获取笔记
@router.get("/note/getnote")
async def get_current_note(token: str=Depends(oauth2_scheme),db:Session=Depends(get_db),noteRequest:NoteRequest=Depends()):
    #获取当前用户
    user =await get_current_user(token,db)
    document = db.query(Document).filter(
        Document.uid == noteRequest.documentID,
        Document.knowledgeID == noteRequest.knowledgeID,
        Document.lid == user.workspace_lid,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    request_data = NoteQuery(knowledgeID=noteRequest.knowledgeID, lid=user.workspace_lid, uid=noteRequest.documentID)
    notequeryresult = get_note(db, request_data)
    if not notequeryresult:
        notequeryresult = Note(knowledgeID=noteRequest.knowledgeID, lid=user.workspace_lid, uid=noteRequest.documentID, note="")
        db.add(notequeryresult)
        db.commit()
    #根据条件进行查询
    return{
        "status_code":200,
        "msg":"get note sucessfully",
        "data":{
            "note":notequeryresult.note
        }
    }

# 更新
@router.post("/note/updatenote")
async def update_current_note(noteUpdateRequest:NoteUpdateRequest,token:str=Depends(oauth2_scheme),db:Session=Depends(get_db)):
    #获取当前用户
    user =await get_current_user(token,db)
    document = db.query(Document).filter(
        Document.uid == noteUpdateRequest.documentID,
        Document.knowledgeID == noteUpdateRequest.knowledgeID,
        Document.lid == user.workspace_lid,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    request_data = NoteQuery(knowledgeID=noteUpdateRequest.knowledgeID, lid=user.workspace_lid, uid=noteUpdateRequest.documentID)
    if not get_note(db, request_data):
        db.add(Note(knowledgeID=noteUpdateRequest.knowledgeID, lid=user.workspace_lid, uid=noteUpdateRequest.documentID, note=noteUpdateRequest.note))
        db.commit()
        return {"status_code": 200, "msg": "update note successfully"}
    #更新笔记
    updateQueryData=NoteUpdate(
        knowledgeID=noteUpdateRequest.knowledgeID,
        lid=user.workspace_lid,
        uid=noteUpdateRequest.documentID,
        note=noteUpdateRequest.note
    )
    update_note(db,updateQueryData)
    db.commit()
    #响应
    
    return{
        "status_code":200,
        "msg":"update note sucessfully",
    }


@router.delete("/note/{knowledge_id}/{document_id}")
async def delete_current_note(knowledge_id: str, document_id: str,
                              token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = await get_current_user(token, db)
    note = (db.query(Note)
            .join(Document, (Document.uid == Note.uid)
                  & (Document.knowledgeID == Note.knowledgeID)
                  & (Document.lid == Note.lid))
            .filter(Note.lid == user.workspace_lid, Note.knowledgeID == knowledge_id,
                    Note.uid == document_id)
            .first())
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"status_code": 200, "msg": "note deleted"}
