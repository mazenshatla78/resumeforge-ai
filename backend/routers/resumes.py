from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Resume, JobDescription
from backend.deps import get_current_user, audit, client_ip
from backend.file_parser import extract_text_from_bytes, clean_text
from backend.config import MAX_UPLOAD_BYTES, MAX_TEXT_CHARS
from backend.rate_limit import limiter

router = APIRouter(prefix="/api", tags=["resumes"])


class TextIn(BaseModel):
    title: str = ""
    content: str


@router.post("/resumes")
def create_resume(data: TextIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not data.content.strip():
        raise HTTPException(400, "Resume content is empty")
    content = clean_text(data.content)[:MAX_TEXT_CHARS]
    r = Resume(user_id=user.id, title=(data.title or "Untitled Resume")[:255], content=content)
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "title": r.title, "created_at": r.created_at.isoformat()}


@router.post("/resumes/upload")
@limiter.limit("20/minute")
async def upload_resume(request: Request, file: UploadFile = File(...), title: str = Form(""), user=Depends(get_current_user), db: Session = Depends(get_db)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File too large (max {MAX_UPLOAD_BYTES//1024//1024}MB)")
    # content-type / magic-byte validation
    name = (file.filename or "").lower()
    allowed_ext = (".pdf", ".docx", ".txt", ".md")
    if not name.endswith(allowed_ext):
        raise HTTPException(400, "Unsupported file type")
    # magic bytes
    if name.endswith(".pdf") and not data.startswith(b"%PDF"):
        raise HTTPException(400, "File content does not match PDF format")
    if name.endswith(".docx") and not data.startswith(b"PK"):
        raise HTTPException(400, "File content does not match DOCX format")
    text = clean_text(extract_text_from_bytes(data, file.filename or ""))
    if not text.strip():
        raise HTTPException(400, "Could not extract text from file")
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
    r = Resume(user_id=user.id, title=(title or (file.filename or "Uploaded Resume"))[:255], content=text)
    db.add(r)
    db.commit()
    db.refresh(r)
    audit(db, user, "resume.upload", "resume", r.id, ip=client_ip(request))
    return {"id": r.id, "title": r.title, "chars": len(text), "preview": text[:500]}


@router.get("/resumes")
def list_resumes(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.created_at.desc()).all()
    return [{"id": r.id, "title": r.title, "preview": (r.content or "")[:200], "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/resumes/{rid}")
def get_resume(rid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(Resume).filter(Resume.id == rid, Resume.user_id == user.id).first()
    if not r:
        raise HTTPException(404, "Resume not found")
    return {"id": r.id, "title": r.title, "content": r.content, "created_at": r.created_at.isoformat()}


@router.delete("/resumes/{rid}")
def delete_resume(rid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(Resume).filter(Resume.id == rid, Resume.user_id == user.id).first()
    if not r:
        raise HTTPException(404, "Resume not found")
    db.delete(r)
    db.commit()
    return {"ok": True}


@router.post("/job-descriptions")
def create_jd(data: TextIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not data.content.strip():
        raise HTTPException(400, "Job description is empty")
    jd = JobDescription(user_id=user.id, title=(data.title or "")[:255], content=clean_text(data.content)[:MAX_TEXT_CHARS])
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return {"id": jd.id, "title": jd.title, "created_at": jd.created_at.isoformat()}


@router.get("/job-descriptions/{jid}")
def get_jd(jid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    j = db.query(JobDescription).filter(JobDescription.id == jid, JobDescription.user_id == user.id).first()
    if not j:
        raise HTTPException(404, "Job description not found")
    return {"id": j.id, "title": j.title, "company": j.company, "content": j.content, "created_at": j.created_at.isoformat()}


@router.get("/job-descriptions")
def list_jd(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(JobDescription).filter(JobDescription.user_id == user.id).order_by(JobDescription.created_at.desc()).all()
    return [{"id": j.id, "title": j.title, "company": j.company, "preview": (j.content or "")[:200], "created_at": j.created_at.isoformat()} for j in rows]
