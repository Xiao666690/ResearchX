from sqlalchemy.orm import Session

from core.backend.db.models import Post
from core.backend.schema.postschema import PostUpdate, PostCreate
#创建帖子
def create_post(db:Session,postCreate:PostCreate):
    new_post=Post(
        lid=postCreate.lid,
        username=postCreate.username,
        postid=postCreate.postid,
        title=postCreate.title,
        category=postCreate.category,
        content=postCreate.content,
        publishtime=postCreate.publishtime,
        updatetime=postCreate.publishtime
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post
#获取全部帖子
def get_all_posts(db:Session):
    return db.query(Post).order_by(Post.publishtime_timestamp.desc()).all()

#更新帖子
def update_post(db:Session,postUpdate:PostUpdate):
    update_data = {k: v for k, v in postUpdate.model_dump(exclude_unset=True).items() if v is not None}
    db.query(Post).filter(
        Post.postid==postUpdate.postid
    ).update(update_data)

#根据postid获取帖子

def query_post_by_pid(db:Session,pid:str):
    return db.query(Post).filter(Post.postid==pid).first()
