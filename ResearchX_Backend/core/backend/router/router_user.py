from datetime import timedelta
import hashlib
import hmac
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer

from core.backend.schema.schema import LoginRequest, RegisterRequest
from core.backend.db.models import Team, TeamMember, TeamRequest, User
from core.backend.utils.utils import *

router = APIRouter()


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return f"pbkdf2_sha256$260000${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    if not stored.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(password, stored)  # Existing accounts are upgraded at login.
    try:
        _, rounds, salt, digest = stored.split("$", 3)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    username = request.username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_\-]{3,50}", username):
        raise HTTPException(422, "用户名需为 3–50 位字母、数字、下划线或连字符")
    if len(request.password) < 8 or len(request.password) > 128:
        raise HTTPException(422, "密码长度需为 8–128 位")
    if query_user(db, username=username):
        raise HTTPException(409, "用户名已存在：该用户名可能曾被使用或曾被移出团队，请更换一个新用户名")
    user = User(username=username, password=_hash_password(request.password), lid=str(uuid.uuid4()))
    db.add(user)
    db.commit()
    # 注册成功：若填写了团队名则提交加入申请（待管理员审批），团队不存在/无效也不阻塞注册
    if request.team_name and request.team_name.strip():
        team_name = request.team_name.strip()
        # Keep the owner's username as a legacy join code, while also allowing the
        # name shown on the team page to be used for new registration requests.
        team = db.query(Team).filter(Team.owner_username == team_name).first()
        if not team:
            matching_teams = db.query(Team).filter(Team.team_name == team_name).limit(2).all()
            if len(matching_teams) > 1:
                return {"status_code": 201, "msg": "注册成功，但有多个同名团队，未提交加入申请；请联系管理员"}
            team = matching_teams[0] if matching_teams else None
        if team:
            exists_pending = db.query(TeamRequest).filter(
                TeamRequest.applicant_username == user.username,
                TeamRequest.status == 'pending').first()
            if not exists_pending:
                db.add(TeamRequest(team_id=team.team_id, applicant_username=user.username, status='pending'))
                db.commit()
            return {"status_code": 201, "msg": "注册成功，已提交加入团队申请，待管理员审批"}
        else:
            return {"status_code": 201, "msg": "注册成功，团队不存在，未提交申请"}
    return {"status_code": 201, "msg": "注册成功，请登录"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        username: str = payload.get("username") 
    except Exception:
        raise credentials_exception
    user = query_user(db, username=username)
    if user is None:
        raise credentials_exception
    return attach_workspace_lid(db, user)


@router.post("/login")
def login_for_access_token(loginrequest: LoginRequest,db: Session = Depends(get_db)):
    user = query_user(db, loginrequest.username)
    if not user or not _verify_password(loginrequest.password, user.password):
            return  JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=jsonable_encoder({"status_code": status.HTTP_401_UNAUTHORIZED, "msg": "用户名或密码错误"}),
        )
    if not user.password.startswith("pbkdf2_sha256$"):
        user.password = _hash_password(loginrequest.password)
        db.commit()
    access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))
    access_token = create_access_token(
        data={"username": loginrequest.username,"lid":user.lid}, expires_delta=access_token_expires
    )
    return {
        "status_code": 200,
        "msg": "登录成功",
        "data":{"access_token": access_token, "token_type": "Bearer","expire":generate_future_timestamp(int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))),
                "role": user.role, "workspace_lid": get_workspace_lid(db, user)}
    }

# 当前登录用户信息（供前端刷新角色与工作空间）
@router.get("/user/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "status_code": 200,
        "msg": "ok",
        "data": {
            "username": current_user.username,
            "role": current_user.role,
            "workspace_lid": current_user.workspace_lid,
        },
    }
