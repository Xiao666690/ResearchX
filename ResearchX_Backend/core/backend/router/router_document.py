import asyncio
import hashlib
from io import BytesIO
import os
import re
import fitz
from urllib.parse import urljoin, urlsplit
from datetime import timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
import requests

from core.agent.chatAgent import *
from core.agent.dataprocessAgent import *
from core.backend.crud.crud_document import *
from core.backend.crud.crud_knowledge import update_knowledge_content
from core.backend.crud.crud_note import create_note, del_note
from core.backend.crud.crud_tmpdocument import create_tmp_document, get_tmp_document_by_filename
from core.backend.db.models import Knowledge
from core.backend.router.req_res_schema import DeleteDocument
from core.backend.schema.noteschema import NoteCreate, NoteDelete
from core.backend.schema.schema import *
from core.backend.utils.utils import get_current_user, get_db, get_document_tags, get_filtered_documents, vector_paper_for_tmp
from core.backend.services.paper_inspection import MAX_PDF_BYTES, OCRUnavailable, inspect_pdf
from core.vectordb.chromadb import *
from datetime import datetime as PythonDateTime  # import after wildcard imports to avoid DateTime shadowing

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
router = APIRouter()


class ExternalPaperImport(BaseModel):
    pdf_url: str
    knowledgeID: str
    title: str | None = None


def _allowed_arxiv_pdf(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}
        and port in (None, 443)
        and not parsed.username
        and parsed.path.startswith("/pdf/")
    )


def _download_arxiv_pdf(url: str) -> tuple[bytes, str]:
    """Fetch a user-selected arXiv PDF without allowing arbitrary server URLs."""
    if not _allowed_arxiv_pdf(url):
        raise HTTPException(status_code=400, detail="当前仅支持直接导入 arXiv PDF；其他论文请下载后手动上传")
    current = url
    max_bytes = int(os.getenv("MAX_UPLOAD_MB", "25")) * 1024 * 1024
    for _ in range(4):
        try:
            response = requests.get(current, stream=True, allow_redirects=False, timeout=(8, 35))
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail="论文 PDF 下载失败，请稍后重试") from exc
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location", "")
            response.close()
            current = urljoin(current, location)
            if not _allowed_arxiv_pdf(current):
                raise HTTPException(status_code=502, detail="论文下载跳转到了不支持的地址")
            continue
        try:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                content.extend(chunk)
                if len(content) > max_bytes:
                    raise HTTPException(status_code=413, detail="论文 PDF 超过上传大小限制")
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail="论文 PDF 下载失败，请稍后重试") from exc
        finally:
            response.close()
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=502, detail="下载结果不是有效 PDF，请打开原文链接查看")
        filename = urlsplit(current).path.rsplit("/", 1)[-1]
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        return bytes(content), filename
    raise HTTPException(status_code=502, detail="论文 PDF 跳转次数过多")

@router.get("/document/getDocumentList")
async def get_documents_all(knowledgeID:str, token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):
    user = await get_current_user(token, db)
    knowledge = db.query(Knowledge).filter(
        Knowledge.knowledgeID == knowledgeID,
        Knowledge.lid == user.workspace_lid,
    ).first()
    if not knowledge:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status_code": 404, "msg": "知识库不存在"},
        )
    documents=get_document_by_knowledgeID(db, knowledgeID)
    
    filtered_documents = get_filtered_documents(documents)
    return {
            "status_code": 200, 
            "msg":"Get document list successfully", 
            "data":filtered_documents
            }

# 获取document的状态
@router.get("/document/Info")
async def get_document_info(documentID: str,knowledgeID:str,token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):
    user = await get_current_user(token,db)
    print(documentID,knowledgeID)
    document =db.query(Document).filter(
        Document.uid == documentID,
        Document.knowledgeID == knowledgeID,
        Document.lid == user.workspace_lid,
    ).first()
    if not document:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status_code": 404, "msg": "未找到指定文件"},
        )
    return {
        "status_code": 200,
        "msg": "Get document info successfully",
        "data": {
            "documentID": document.uid,
            "documentName": document.documentName,
            "documentStatus": document.documentStatus,
            "vectorNum": document.documentVector,
            "documentTags": get_document_tags(document) if (document.primaryClassification or document.secondaryClassification or document.tags) else [],
            "createTime":document.createTime_timestamp
        }
    }
# 获取文档的总结
@router.get("/document/summarize")
async def get_document_summarize(documentID: str,knowledgeID:str,token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):
    user = await get_current_user(token,db)
    document = db.query(Document).filter(
        Document.uid == documentID,
        Document.knowledgeID == knowledgeID,
        Document.lid == user.workspace_lid,
    ).first()
    if not document:
        return {
            "status_code": 404,
            "msg": "未找到指定文件",
        }
    return {
        "status_code": 200,
        "msg": "成功获取文档总结",
        "data": {
            "summarize": document.documentDescription,
        }
    }
## 根据documentID获取pdf文件
@router.get("/document/getFile")
async def get_document(
    documentID: str,
    knowledgeID: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = await get_current_user(token, db)
    document = db.query(Document).filter(
        Document.uid == documentID,
        Document.knowledgeID == knowledgeID,
        Document.lid == user.workspace_lid,
    ).first()
    if not document:
        return {
            "status_code": 404,
            "msg": "document not found",
        }
    file_path =os.getenv("AcadeAgent_DIR")+document.documentPath
    print("File_path",file_path) # 替换成你实际的 PDF 文件路径
    return FileResponse(file_path)

## 多文件对话-文件上传 
@router.post("/document/multi_file_chat_upload")
async def upload_document(
    request: Request,
    documentFile: UploadFile = File(...),
    addToLibrary: bool = Form(False),
    knowledgeID: str | None = Form(None),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = await get_current_user(token,db)
    createtime = PythonDateTime.now(timezone.utc)
    if addToLibrary:
        if not knowledgeID:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status_code": 400, "msg": "请选择要加入的知识库"},
            )
        knowledge = db.query(Knowledge).filter(
            Knowledge.knowledgeID == knowledgeID,
            Knowledge.lid == user.workspace_lid,
        ).first()
        if not knowledge:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status_code": 404, "msg": "目标知识库不存在"},
            )

    # 计算文件内容 MD5，作为跨临时上传和 Library 的统一 documentID。
    hasher = hashlib.md5()
    file_content = await documentFile.read()
    hasher.update(file_content)
    file_md5 = hasher.hexdigest()
    print("FILE_MD5",file_md5)

    if addToLibrary:
        existing = get_document_by_uid_kid(db, file_md5, knowledgeID)
    else:
        existing = get_tmp_document_by_filename(db, file_md5)
    if existing:
        return {
            "status_code": 200,
            "msg": "document already available",
            "data": {
                "documentID": existing.uid,
                "documentName": existing.documentName,
                "vectorNum": existing.documentVector or 0,
                "knowledgeID": knowledgeID if addToLibrary else None,
                "addedToLibrary": addToLibrary,
                "createTime": int(createtime.timestamp()),
            }
        }

    storage_path = os.getenv("PAPER_SAVE_DIR") if addToLibrary else os.getenv("TMP_PAPER_SAVE_DIR")
    os.makedirs(storage_path, exist_ok=True)
    stored_name = f"{file_md5}.pdf"
    file_path = os.path.join(storage_path, stored_name)
    print("saving ", documentFile.filename, "as", stored_name, "...")
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    index_knowledge_id = knowledgeID if addToLibrary else "THIS_IS_A_TMP_KID"
    vectornum = vector_paper_for_tmp(
        file_path, file_md5, index_knowledge_id, request.app.chroma_db
    )

    if addToLibrary:
        document = DocumentCreate(
            documentName=documentFile.filename,
            documentPath=os.path.join("/res/pdf/", stored_name),
            documentStatus=2,
            uid=file_md5,
            knowledgeID=knowledgeID,
            lid=user.workspace_lid,
            createTime=createtime,
        )
        db_document = create_document(db=db, document=document)
        db_document.documentVector = vectornum
        db.commit()
        create_note(db=db, info=NoteCreate(
            uid=file_md5, knowledgeID=knowledgeID, lid=user.workspace_lid
        ))
        update_knowledge_content(db, vectornum, 1, knowledgeID)
    else:
        document = TMPDocumentCreate(
            documentName=documentFile.filename,
            documentPath=os.path.join("/res/tmppdf/", stored_name),
            documentStatus=2,
            uid=file_md5,
            knowledgeID="THIS_IS_A_TMP_KID",
            lid=user.workspace_lid,
            createTime=createtime,
        )
        db_document = create_tmp_document(db=db, document=document)
        db_document.documentVector = vectornum
        db.commit()

    return {
        "status_code": 200,
        "msg": "upload successfully",
        "data": {
            "documentID": file_md5,
            "documentName": documentFile.filename,
            "vectorNum": vectornum,
            "knowledgeID": knowledgeID if addToLibrary else None,
            "addedToLibrary": addToLibrary,
            "createTime": int(createtime.timestamp()),
        }
    }


@router.post("/document/import_external")
async def import_external_paper(
    payload: ExternalPaperImport,
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Add a chosen search result to an owned Library using the upload path."""
    user = await get_current_user(token, db)
    owned = db.query(Knowledge).filter(
        Knowledge.knowledgeID == payload.knowledgeID,
        Knowledge.lid == user.workspace_lid,
    ).first()
    if owned is None:
        raise HTTPException(status_code=404, detail="目标知识库不存在")
    content, filename = await asyncio.to_thread(_download_arxiv_pdf, payload.pdf_url)
    if payload.title:
        title = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', payload.title).strip(' .')[:120]
        if title:
            filename = f"{title}.pdf"
    upload = UploadFile(file=BytesIO(content), filename=filename)
    return await upload_document(
        request=request,
        documentFile=upload,
        addToLibrary=True,
        knowledgeID=payload.knowledgeID,
        token=token,
        db=db,
    )


## 单文件上传
@router.post("/document/inspect")
async def inspect_library_pdf(
    documentFile: UploadFile = File(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    await get_current_user(token, db)
    content = await documentFile.read(MAX_PDF_BYTES + 1)
    try:
        assessment = await asyncio.to_thread(inspect_pdf, content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OCRUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status_code": 200, "data": assessment}


@router.post("/document/upload")
async def upload_library_document(
    knowledgeID: str = Form(...),
    documentFile: UploadFile = File(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    pdf_storage_path =os.getenv("PAPER_SAVE_DIR")
    user =await get_current_user(token,db)
    knowledge = db.query(Knowledge).filter(
        Knowledge.knowledgeID == knowledgeID,
        Knowledge.lid == user.workspace_lid,
    ).first()
    if not knowledge:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status_code": 404, "msg": "目标知识库不存在"},
        )

        # 计算文件的MD5哈希值
    hasher = hashlib.md5()
    file_content = await documentFile.read(MAX_PDF_BYTES + 1)
    if len(file_content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF 超过 25 MB 上传限制")
    if not file_content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="文件不是有效的 PDF")
    try:
        with fitz.open(stream=file_content, filetype="pdf") as pdf:
            if pdf.is_encrypted or len(pdf) == 0:
                raise HTTPException(status_code=422, detail="PDF 已加密或没有页面")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="PDF 已损坏或无法读取") from exc
    hasher.update(file_content)
    file_md5 = hasher.hexdigest()
    print("FILE_MD5",file_md5)
    document =get_document_by_uid_kid(db, file_md5, knowledgeID)
    if document:
        # 同一知识库内已存在该文件（按文件内容 MD5 判断），则不再重复上传
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=jsonable_encoder({                
                "status_code": status.HTTP_409_CONFLICT,
                "msg": "该知识库中已存在此文件",
                }),
        )
        
    # 重置文件内容读取位置，以便后续写入文件
    documentFile.file.seek(0)
    os.makedirs(pdf_storage_path, exist_ok=True)
    stored_name = f"{file_md5}.pdf"
    print("saving ",documentFile.filename,"as",stored_name,"...")
    file_path=os.path.join(pdf_storage_path,stored_name)
    with open(file_path, "wb") as buffer:
        buffer.write(documentFile.file.read())
    uid=cal_file_md5(file_path)

    print("UID",uid)
    createtime=PythonDateTime.now(timezone.utc)
    document = DocumentCreate(documentName=documentFile.filename,documentPath=os.path.join("/res/pdf/",stored_name),documentStatus=0,uid=uid,knowledgeID=knowledgeID,lid=user.workspace_lid,createTime=createtime)
    ### 增加创建笔记
    addnotedata=NoteCreate(
        uid=uid,knowledgeID=knowledgeID,lid=user.workspace_lid,
    )
    create_note(db=db,info=addnotedata)
    ###
    create_document(db=db, document=document)
    return {
        "status_code": 200,
        "msg": "upload successfully",
        "data": {
            "documentID": uid,
            "documentName": documentFile.filename,
            "documentStatus": 0,
            "documentTags": [],
            "knowledgeID": knowledgeID,
            "vectorNum": 0,
            "createTime": int(createtime.timestamp())
        }
    }

## 文件删除
@router.post("/document/delete")
async def delete_document(deleteDocument:DeleteDocument,request:Request,token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):
    user =await get_current_user(token,db)
    document = db.query(Document).filter(
        Document.uid == deleteDocument.documentID,
        Document.knowledgeID == deleteDocument.knowledgeID,
        Document.lid == user.workspace_lid,
    ).first()
    if not document:
        return {
            "status_code": 404,
            "msg": "文件不存在",
        }
    #在document表中删除
    db.delete(document)
    db.commit()
    #在向量数据库中删除
    request.app.chroma_db.delete_paper_from_layer1(deleteDocument.knowledgeID,deleteDocument.documentID)
    request.app.chroma_db.delete_paper_from_layer2(deleteDocument.knowledgeID,deleteDocument.documentID)
    #更新知识库状态 file -1  vector -N
    update_knowledge_content(db,-document.documentVector,-1,document.knowledgeID)
    ### 增加删除笔记
    delnotedata=NoteDelete(
        uid=deleteDocument.documentID,knowledgeID=deleteDocument.knowledgeID,lid=user.workspace_lid,
    )
    del_note(db=db,delNote=delnotedata)
    ###
    #删除文件
    doc =get_document_by_uid(db, deleteDocument.documentID)#检查其他知识中是否还有该文档,如果有就不需要删除向量和源文件
    if not doc: #如果没有则进行删除
        file_path =os.getenv("AcadeAgent_DIR")+document.documentPath
        os.remove(file_path)
    return {
        "status_code": 200,
        "msg": "文件删除成功",
    }
