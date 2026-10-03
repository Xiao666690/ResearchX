from sqlalchemy.orm import Session

from core.backend.db.models import *
from core.backend.schema.schema import *



## 临时聊天文件获取
def get_tmp_document_by_filename(db: Session, uid: str):
    return db.query(TMPDocument).filter(TMPDocument.uid == uid).first()


# 临时聊天文件创建
def create_tmp_document(db: Session, document: TMPDocumentCreate):
    db_document = TMPDocument(**document.model_dump())
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document
