from sqlalchemy.orm import Session

from core.backend.db.models import Commit
from core.backend.schema.commitschema import CommitCreate

#创建评论
def create_commit(db:Session,commitCreate:CommitCreate):
    
    newdata=Commit(
    lid=commitCreate.lid,
    postid=commitCreate.postid,
    username=commitCreate.username,
    commitid=commitCreate.commitid,
    content=commitCreate.content,
    publishtime=commitCreate.publishtime,
    )
    db.add(newdata)
    db.commit()
    db.refresh(newdata)
    return newdata



#获取全部评论
def query_all_commits_by_pid(db:Session,postid):
    return db.query(Commit).filter(Commit.postid==postid).all()
