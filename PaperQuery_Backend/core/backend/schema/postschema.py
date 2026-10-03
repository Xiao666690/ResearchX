from pydantic import BaseModel
import datetime

class PostCreateRequest(BaseModel):
    title:str
    content:str
    category:str = '技术'
class PostResponse(BaseModel):
    lid:str
    postid:str
    title:str
    category:str
    content:str
    username:str
    publishtime_timestamp:int
    updatetime_timestamp:int

    class Config:
        from_attributes=True
class PostCreate(BaseModel):
    lid:str
    postid:str
    title:str
    category:str
    content:str
    username:str
    publishtime:datetime.datetime
    updatetime: datetime.datetime


class PostUpdate(BaseModel):
    postid:str 
    title:str | None=None
    content:str | None=None
    publishtime:datetime.datetime | None=None
    updatetime: datetime.datetime | None=None
