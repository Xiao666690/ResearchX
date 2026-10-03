
from sqlalchemy.orm import Session


from core.backend.db.models import *
from core.backend.schema.schema import *

#----------------------用户相关
def create_user(db: Session, user: UserCreate):
    db_user = User(user.model_dump())

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def query_user(db: Session, username: str) :
    return db.query(User).filter(User.username == username).first()