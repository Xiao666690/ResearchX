from  pydantic import BaseModel
import datetime


class CommitCreateRequest(BaseModel):
    postid:str
    content:str

class QueryCommitResponse(BaseModel):
    lid:str
    postid:str
    username:str
    content:str
    commitid:str
    publishtime_timestamp:int
    class Config:
        from_attributes=True


class CommitCreate(BaseModel):
    lid:str
    postid:str
    username:str
    commitid:str
    content:str
    publishtime:datetime.datetime
