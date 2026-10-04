from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.backend.db.models import Team, TeamMember, TeamRequest, User
from core.backend.router.dependencies import get_db
from core.backend.schema.schema import TeamApproveRequest, TeamRejectRequest, TeamRemoveRequest, TeamRenameRequest
from core.backend.utils.utils import get_current_user

router = APIRouter()


def require_admin_owner(user, db) -> Team:
    """管理员 + 默认团队 owner 权限校验；普通用户一律返回 403"""
    if user.role != 'admin':
        raise HTTPException(403, "仅管理员可操作")
    team = db.query(Team).filter(Team.owner_username == user.username).first()
    if not team:
        raise HTTPException(404, "未找到团队")
    return team


@router.get("/team/info")
def get_team_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team = require_admin_owner(current_user, db)
    members = db.query(TeamMember).filter(TeamMember.team_id == team.team_id).all()
    return {
        "status_code": 200,
        "msg": "ok",
        "data": {
            "team_id": team.team_id,
            "team_name": team.team_name,
            "owner_username": team.owner_username,
            "members": [{"username": m.member_username, "joined_at": str(m.joined_at)} for m in members],
        },
    }


@router.post("/team/rename")
def rename_team(request: TeamRenameRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team = require_admin_owner(current_user, db)
    name = request.team_name.strip()
    if not name or len(name) > 50:
        raise HTTPException(422, "团队名称需为 1–50 个字符")
    if name != team.team_name:
        # Registration still accepts the owner's username for existing users. A team
        # name must not collide with that identifier or another team's display name.
        conflict = db.query(Team).filter(
            Team.team_id != team.team_id,
            (Team.team_name == name) | (Team.owner_username == name),
        ).first()
        if conflict:
            raise HTTPException(409, "团队名称已被使用")
        team.team_name = name
        db.commit()
    return {"status_code": 200, "msg": "团队名称已更新", "data": {"team_id": team.team_id, "team_name": team.team_name}}


@router.get("/team/members")
def get_team_members(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team = require_admin_owner(current_user, db)
    members = db.query(TeamMember).filter(TeamMember.team_id == team.team_id).order_by(TeamMember.joined_at).all()
    return {
        "status_code": 200,
        "msg": "ok",
        "data": [{"username": m.member_username, "joined_at": str(m.joined_at)} for m in members],
    }


@router.get("/team/requests")
def get_team_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """管理员查看当前团队所有待审批的加入申请"""
    team = require_admin_owner(current_user, db)
    requests = db.query(TeamRequest).filter(
        TeamRequest.team_id == team.team_id,
        TeamRequest.status == 'pending').order_by(TeamRequest.created_at).all()
    return {
        "status_code": 200,
        "msg": "ok",
        "data": [{"username": r.applicant_username, "created_at": str(r.created_at)} for r in requests],
    }


@router.post("/team/approve")
def approve_team_request(request: TeamApproveRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """通过加入申请：写入 TeamMember，申请状态置为 approved"""
    team = require_admin_owner(current_user, db)
    username = request.username.strip()
    req = db.query(TeamRequest).filter(
        TeamRequest.team_id == team.team_id,
        TeamRequest.applicant_username == username,
        TeamRequest.status == 'pending').first()
    if not req:
        raise HTTPException(404, "未找到该用户的待审批申请")
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(404, "用户不存在")
    if target.role == 'admin':
        raise HTTPException(400, "不能将管理员加入团队成员")
    if db.query(TeamMember).filter(TeamMember.member_username == username).first():
        raise HTTPException(400, "该用户已在团队中")
    req.status = 'approved'
    db.add(TeamMember(team_id=team.team_id, member_username=target.username, member_lid=target.lid))
    db.commit()
    return {"status_code": 200, "msg": f"已通过 {username} 的加入申请，{username} 现可共享团队知识库与对话"}


@router.post("/team/reject")
def reject_team_request(request: TeamRejectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """拒绝加入申请：只置状态为 rejected，不写入 TeamMember"""
    team = require_admin_owner(current_user, db)
    username = request.username.strip()
    req = db.query(TeamRequest).filter(
        TeamRequest.team_id == team.team_id,
        TeamRequest.applicant_username == username,
        TeamRequest.status == 'pending').first()
    if not req:
        raise HTTPException(404, "未找到该用户的待审批申请")
    req.status = 'rejected'
    db.commit()
    return {"status_code": 200, "msg": f"已拒绝 {username} 的加入申请"}


@router.post("/team/remove")
def remove_team_member(request: TeamRemoveRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team = require_admin_owner(current_user, db)
    username = request.username.strip()
    if username == current_user.username:
        raise HTTPException(400, "不能移除管理员本人")
    member = db.query(TeamMember).filter(TeamMember.team_id == team.team_id, TeamMember.member_username == username).first()
    if not member:
        raise HTTPException(404, "该用户不在当前团队中")
    db.delete(member)
    db.commit()
    return {"status_code": 200, "msg": f"已移除成员 {username}，该用户工作空间已回落为个人空间"}
