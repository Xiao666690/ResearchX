from fastapi import APIRouter,Depends,BackgroundTasks, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from core.backend.crud.crud_commit import create_commit, query_all_commits_by_pid
from core.backend.crud.crud_post import query_post_by_pid
from core.backend.router.dependencies import get_db
from core.backend.router.router_user import get_current_user
from core.backend.schema.commitschema import CommitCreate, CommitCreateRequest, QueryCommitResponse
import uuid
oauth2_schema=OAuth2PasswordBearer(tokenUrl="/login")
router=APIRouter()

def post_answer_gpt(db:Session,postid:str, request:Request):
    ## 帖子内容获取
    post=query_post_by_pid(db,postid)
    createtime=datetime.now(timezone.utc)
    ## 调用大模型
    callresponse=request.app.chat_agent.chat_answer_post(post.title,post.content)
    commitdata=CommitCreate(
        lid="文心一言",
        postid=postid,
        commitid=str(uuid.uuid1()),
        username="文心一言小助手",
        content=callresponse,
        publishtime=int(createtime.timestamp())
    )
    ## 生成内容存储
    create_commit(db,commitdata)
#创建评论
@router.post("/forum/createcommit")
async def create_commit_handler(background_tasks: BackgroundTasks, request:Request,commitCreateRequest:CommitCreateRequest,token:str=Depends(oauth2_schema),db:Session=Depends(get_db),):
    #获取当前用户
    user =await get_current_user(token,db)
    createtime=datetime.now(timezone.utc)
    commitdata=CommitCreate(
        lid=user.workspace_lid,
        postid=commitCreateRequest.postid,
        username=user.username,
        commitid=str(uuid.uuid1()),
        content=commitCreateRequest.content,
        publishtime=int(createtime.timestamp())
    )
    create_commit(db,commitdata)
    #### 检查是否有关键字 `@文言一心 `
    if("@文心一言" in commitCreateRequest.content):
        print("检测到文心一言")
        background_tasks.add_task(post_answer_gpt,db,commitCreateRequest.postid,request)
    
    return{
            "status_code": 200, 
            "msg":"create commit suscessfully."
            }

#获取指定帖子对应的所有评论
@router.get("/forum/getpostcommit")
async def get_post_commit_handler(postid:str,token:str=Depends(oauth2_schema),db:Session=Depends(get_db)):
    
    commits=query_all_commits_by_pid(db,postid)
    post=query_post_by_pid(db,postid)
    commitsData=[QueryCommitResponse.model_validate(commit) for commit in commits]
    return {
            "status_code": 200, 
            "msg":"get commit suscessfully.",
            "data":{
            "postid":post.postid,
            "content": post.content,
            "updatetime_timestamp":post.updatetime_timestamp,
            "lid": post.lid,
            "username":post.username,
            "title": post.title,
            "publishtime_timestamp":post.publishtime_timestamp,
            "commits":commitsData
            }
        }