import json
from datetime import datetime, timedelta
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import Optimization, UsageLog
from backend.deps import get_current_user, audit, client_ip
from backend.ai_service import analyze_resume, tailor_resume, generate_cover_letter, generate_interview_prep
from backend.config import FREE_MONTHLY_LIMIT, MAX_TEXT_CHARS, RATE_LIMIT_AI
from backend.rate_limit import limiter

router = APIRouter(prefix="/api", tags=["optimize"])


class OptimizeIn(BaseModel):
    resume_text: str
    jd_text: str
    resume_id: int | None = None
    jd_id: int | None = None
    include_cover_letter: bool = True
    include_interview_prep: bool = False
    title: str = ""


def _monthly_usage(user_id: int, db: Session) -> int:
    start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return db.query(func.count(UsageLog.id)).filter(
        UsageLog.user_id == user_id,
        UsageLog.action == "optimize",
        UsageLog.created_at >= start,
    ).scalar() or 0


@router.post("/optimize")
@limiter.limit(RATE_LIMIT_AI)
def optimize(request: Request, data: OptimizeIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.rate_limit import limiter as _l  # noqa
    if not data.resume_text.strip() or not data.jd_text.strip():
        raise HTTPException(400, "Resume and job description are required")
    resume_text = data.resume_text[:MAX_TEXT_CHARS]
    jd_text = data.jd_text[:MAX_TEXT_CHARS]

    used = _monthly_usage(user.id, db)
    if user.plan != "premium" and used >= FREE_MONTHLY_LIMIT:
        raise HTTPException(402, f"Free plan limit reached ({FREE_MONTHLY_LIMIT}/month). Upgrade to Premium for unlimited optimizations.")

    try:
        analysis = analyze_resume(resume_text, jd_text)
        tailored = tailor_resume(resume_text, jd_text, analysis)
    except Exception as e:
        raise HTTPException(503, "AI service temporarily unavailable. Please try again.")

    cover = ""
    if data.include_cover_letter:
        try:
            cover = generate_cover_letter(resume_text, jd_text, analysis)
        except Exception:
            cover = ""

    interview = []
    if data.include_interview_prep:
        if user.plan != "premium":
            raise HTTPException(402, "Interview prep is a Premium feature. Upgrade to unlock.")
        try:
            interview = generate_interview_prep(resume_text, jd_text)
        except Exception:
            interview = []

    opt = Optimization(
        user_id=user.id,
        resume_id=data.resume_id,
        jd_id=data.jd_id,
        resume_text=resume_text,
        jd_text=jd_text,
        ats_score=analysis.get("ats_score", 0),
        analysis=analysis,
        tailored_resume=tailored,
        cover_letter=cover,
        interview_prep=__import__("json").dumps(interview) if interview else "",
    )
    db.add(opt)
    db.add(UsageLog(user_id=user.id, action="optimize"))
    db.commit()
    db.refresh(opt)
    audit(db, user, "resume.optimize", "optimization", opt.id, ip=client_ip(request))

    return {
        "id": opt.id,
        "ats_score": opt.ats_score,
        "analysis": analysis,
        "tailored_resume": tailored,
        "cover_letter": cover,
        "interview_prep": interview,
        "created_at": opt.created_at.isoformat(),
    }


@router.get("/optimizations")
def list_opts(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Optimization).filter(Optimization.user_id == user.id).order_by(Optimization.created_at.desc()).all()
    out = []
    for o in rows:
        iv = []
        try:
            iv = json.loads(o.interview_prep) if o.interview_prep else []
        except Exception:
            iv = []
        out.append({
            "id": o.id,
            "ats_score": o.ats_score,
            "analysis": o.analysis,
            "tailored_resume": o.tailored_resume,
            "cover_letter": o.cover_letter,
            "interview_prep": iv,
            "created_at": o.created_at.isoformat(),
        })
    return out


@router.get("/optimizations/{oid}")
def get_opt(oid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    o = db.query(Optimization).filter(Optimization.id == oid, Optimization.user_id == user.id).first()
    if not o:
        raise HTTPException(404, "Not found")
    iv = []
    try:
        iv = json.loads(o.interview_prep) if o.interview_prep else []
    except Exception:
        iv = []
    return {
        "id": o.id,
        "ats_score": o.ats_score,
        "analysis": o.analysis,
        "tailored_resume": o.tailored_resume,
        "cover_letter": o.cover_letter,
        "interview_prep": iv,
        "created_at": o.created_at.isoformat(),
    }


@router.delete("/optimizations/{oid}")
def delete_opt(oid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    o = db.query(Optimization).filter(Optimization.id == oid, Optimization.user_id == user.id).first()
    if not o:
        raise HTTPException(404, "Not found")
    db.delete(o)
    db.commit()
    return {"ok": True}


@router.get("/usage")
def usage(user=Depends(get_current_user), db: Session = Depends(get_db)):
    used = _monthly_usage(user.id, db)
    limit = None if user.plan == "premium" else FREE_MONTHLY_LIMIT
    return {"plan": user.plan, "used_this_month": used, "monthly_limit": limit}
