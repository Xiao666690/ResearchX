"""Account-scoped daily overview and note collection."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.backend.db.models import ActivityEvent, Document, Knowledge, Note, Post, ResearchTask
from core.backend.router.dependencies import get_db
from core.backend.utils.utils import get_current_user

router = APIRouter()


class ReadingPulse(BaseModel):
    knowledgeID: str
    documentID: str
    seconds: int = Field(ge=1, le=60)


def _today():
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


@router.post("/dashboard/reading")
async def record_reading(pulse: ReadingPulse, user=Depends(get_current_user), db: Session = Depends(get_db)):
    document = db.query(Document).filter(
        Document.lid == user.workspace_lid,
        Document.knowledgeID == pulse.knowledgeID,
        Document.uid == pulse.documentID,
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    db.add(ActivityEvent(lid=user.workspace_lid, event_type="reading", knowledge_id=pulse.knowledgeID,
                         document_id=pulse.documentID, duration_seconds=pulse.seconds))
    db.commit()
    return {"status_code": 200, "msg": "reading time recorded"}


@router.get("/notes/collection")
async def note_collection(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Note, Document, Knowledge)
            .join(Document, (Document.uid == Note.uid) & (Document.knowledgeID == Note.knowledgeID) & (Document.lid == Note.lid))
            .join(Knowledge, (Knowledge.knowledgeID == Note.knowledgeID) & (Knowledge.lid == Note.lid))
            .filter(Note.lid == user.workspace_lid, Note.note.isnot(None), Note.note != "")
            .order_by(Knowledge.knowledgeName, Document.documentName)
            .all())
    return {"status_code": 200, "data": [
        {"knowledgeID": knowledge.knowledgeID, "knowledgeName": knowledge.knowledgeName,
         "documentID": document.uid, "documentName": document.documentName,
         "preview": " ".join(note.note.split())[:160]}
        for note, document, knowledge in rows
    ]}


@router.get("/dashboard/overview")
async def overview(user=Depends(get_current_user), db: Session = Depends(get_db)):
    start = _today()
    start_epoch = int(start.timestamp())
    # Document and ResearchTask timestamps originate from SQLite/UTC; reading
    # events use local server time. Convert the account's local day boundary.
    local_start = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = (local_start + timedelta(days=1)).astimezone(timezone.utc).replace(tzinfo=None)
    libraries = db.query(Knowledge).filter(Knowledge.lid == user.workspace_lid).all()
    documents = db.query(Document).filter(Document.lid == user.workspace_lid).all()
    knowledge_names = {item.knowledgeID: item.knowledgeName for item in libraries}
    document_names = {(item.knowledgeID, item.uid): item for item in documents}
    note_keys = {(item.knowledgeID, item.uid) for item in db.query(Note).filter(
        Note.lid == user.workspace_lid, Note.note.isnot(None), Note.note != "").all()}

    ask_count = db.query(func.count(ActivityEvent.id)).filter(
        ActivityEvent.lid == user.workspace_lid, ActivityEvent.event_type == "ask", ActivityEvent.created_at >= start).scalar() or 0
    research = (db.query(ResearchTask).filter(ResearchTask.lid == user.workspace_lid,
                ResearchTask.created_at >= start_utc, ResearchTask.created_at < end_utc)
                .order_by(ResearchTask.created_at.desc()).all())
    posts = db.query(Post).order_by(Post.publishtime_timestamp.desc()).limit(30).all()
    today_posts = [item for item in posts if (item.publishtime_timestamp or 0) >= start_epoch]
    my_posts = [item for item in today_posts if item.lid == user.workspace_lid]
    uploads = [item for item in documents if item.createTime and start_utc <= item.createTime < end_utc]

    readings = {}
    pulses = db.query(ActivityEvent).filter(ActivityEvent.lid == user.workspace_lid,
        ActivityEvent.event_type == "reading", ActivityEvent.created_at >= start).all()
    for pulse in pulses:
        key = (pulse.knowledge_id, pulse.document_id)
        if key in document_names:
            readings[key] = readings.get(key, 0) + (pulse.duration_seconds or 0)

    return {"status_code": 200, "data": {
        "date": start.date().isoformat(),
        "stats": {"libraries": len(libraries), "documents": len(documents),
                  "vectors": sum(item.vectorNum or 0 for item in libraries),
                  "askCount": ask_count, "researchCount": len(research),
                  "uploadCount": len(uploads), "readingMinutes": round(sum(readings.values()) / 60, 1)},
        "researchGoals": [{"taskID": item.task_id, "goal": item.goal, "status": item.status}
                          for item in research[:8]],
        "myPosts": [{"postID": item.postid, "title": item.title,
                     "published": item.publishtime_timestamp} for item in my_posts[:8]],
        "newPosts": [{"postID": item.postid, "title": item.title, "author": item.username,
                      "published": item.publishtime_timestamp} for item in (today_posts or posts)[:8]],
        "uploadedPapers": [{"knowledgeID": item.knowledgeID, "knowledgeName": knowledge_names.get(item.knowledgeID, ""),
                            "documentID": item.uid, "documentName": item.documentName,
                            "topic": item.primaryClassification or item.secondaryClassification or item.tags or "未分类"}
                           for item in sorted(uploads, key=lambda item: item.createTime, reverse=True)[:8]],
        "readings": [{"knowledgeID": kid, "knowledgeName": knowledge_names.get(kid, ""),
                      "documentID": did, "documentName": document_names[(kid, did)].documentName,
                      "seconds": seconds, "hasNote": (kid, did) in note_keys}
                     for (kid, did), seconds in sorted(readings.items(), key=lambda pair: pair[1], reverse=True)[:8]],
    }}
