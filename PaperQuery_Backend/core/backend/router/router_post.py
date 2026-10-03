from fastapi import APIRouter,Depends,HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timezone
from core.backend.crud.crud_post import create_post, get_all_posts
from core.backend.router.dependencies import get_db
from core.backend.router.router_user import get_current_user
from core.backend.schema.postschema import PostCreate, PostCreateRequest, PostResponse

oauth2_schema=OAuth2PasswordBearer(tokenUrl="/login")
router=APIRouter()


@router.post("/forum/createpost")
async def create_user_post(postCreateRequest:PostCreateRequest,token:str=Depends(oauth2_schema),db:Session=Depends(get_db)):
    if postCreateRequest.category not in {'技术', '生活', '学习', '创意', '好玩', '问与答', '城市', '其他'}:
        raise HTTPException(422, '无效的帖子分类')
    #获取当前用户
    user =await get_current_user(token,db)
    createtime=datetime.now(timezone.utc)
    postdata=PostCreate(
        lid=user.workspace_lid,
        postid=str(uuid.uuid1()),
        title=postCreateRequest.title,
        category=postCreateRequest.category,
        content=postCreateRequest.content,
        username=user.username,
        publishtime=int(createtime.timestamp()),
        updatetime= int(createtime.timestamp())
    )
    create_post(db,postdata)
    return {
            "status_code": 200, 
            "msg":"create post suscessfully."
            }


#获取全部的post
@router.get("/forum/getallpost")
async def get_all_post_handler(token:str=Depends(oauth2_schema),db:Session=Depends(get_db)):
  posts=get_all_posts(db)
  post_data = [PostResponse.model_validate(post) for post in posts]
  return{
            "status_code": 200, 
            "msg":"get post suscessfully.",
            "data":post_data
            }
