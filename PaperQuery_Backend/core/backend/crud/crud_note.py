
from sqlalchemy.orm import Session
from core.backend.schema.noteschema import *
from core.backend.db.models import *
#笔记创建 ,在pdf处理完成后调用
def create_note(db:Session,info:NoteCreate):
    new_note=Note(
        knowledgeID=info.knowledgeID,
        lid=info.lid,
        uid=info.uid,
        note=None
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note

#笔记获取
def get_note(db: Session,userNote: NoteRequest):
    return db.query(Note).filter(
        Note.knowledgeID==userNote.knowledgeID,
        Note.lid==userNote.lid,
        Note.uid==userNote.uid).first()

#笔记更新
def update_note(db:Session ,updateNote:NoteUpdate):
    db.query(Note).filter(
        Note.knowledgeID==updateNote.knowledgeID,
        Note.lid==updateNote.lid,
        Note.uid==updateNote.uid).update({
            Note.note:updateNote.note
        })
#笔记删除

def del_note(db:Session,delNote:NoteDelete):
    note_to_delete = db.query(Note).filter(
        Note.knowledgeID==delNote.knowledgeID,
        Note.lid==delNote.lid,
        Note.uid==delNote.uid
    ).first()
    if note_to_delete:
        print(note_to_delete.__dict__)
        db.delete(note_to_delete)
        db.commit()  # 提交事务，执行删除操作
    else:
        # 如果没有找到记录，可以根据需求返回错误信息或处理逻辑
        raise ValueError("Note with the specified ID does not exist.")