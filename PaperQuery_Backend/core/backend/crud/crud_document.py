from sqlalchemy.orm import Session

from core.backend.db.models import *
from core.backend.schema.schema import *


# 获取用户指定知识下所有文档信息
def get_document_by_knowledgeID(db: Session, knowledgeID: str) :
    return db.query(Document).filter(Document.knowledgeID == knowledgeID).all()

def get_document_by_uid(db: Session, uid: str):
    return db.query(Document).filter(Document.uid == uid).first()

def get_document_by_filename(db: Session, filename: str):
    return db.query(Document).filter(Document.filename == filename).first()
def get_document_by_uid_kid(db: Session, uid: str,knowledgeID:str):
    return db.query(Document).filter(Document.uid == uid,Document.knowledgeID==knowledgeID).first()
def get_document_status_equal_zero(db: Session):
    return db.query(Document).filter(Document.documentStatus == 0).first()

def reset_stuck_documents(db: Session):
    """将处理中(状态1)的文档重置为排队(状态0)，用于 worker 启动时清理因进程中断而残留的文档"""
    db.query(Document).filter(Document.documentStatus == 1).update({Document.documentStatus: 0})
    db.commit()
    return 1

def update_document_status(db: Session,document: Document):
    db.query(Document).filter(Document.uid == document.uid).update({Document.documentStatus: document.documentStatus})
    db.commit()
    return 1

def update_document_content(db: Session,result: dict):
    db.query(Document).filter(Document.uid == result["uid"]).update({Document.documentVector: result["documentVector"],
                                                           Document.primaryClassification: result["Primary Classification"],
                                                           Document.secondaryClassification: result["Secondary Classification"],
                                                           Document.tags: ','.join(result["Research Direction Tags"]),
                                                           Document.documentDescription: result["Abstract"],
                                                           Document.documentStatus: 2
                                                           })
    db.commit()
    return 1
# 增
def create_document(db: Session, document: DocumentCreate):
    db_document = Document(**document.model_dump())
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

# 改
def update_document(db: Session, document: DocumentUpdate):
    db.query(Document).filter(document.filename == Document.filename).update(**document.model_dump())
    db.commit()
    return db.query(Document).filter(Document.filename == document.filename).first()

def get_documents(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Document).offset(skip).limit(limit).all()

