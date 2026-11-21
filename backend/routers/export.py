from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.deps import get_current_user
from backend.models import Optimization
from backend.export import text_to_pdf, text_to_docx

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/{oid}/pdf")
def export_pdf(oid: int, kind: str = "tailored", user=Depends(get_current_user), db: Session = Depends(get_db)):
    o = db.query(Optimization).filter(Optimization.id == oid, Optimization.user_id == user.id).first()
    if not o:
        raise HTTPException(404, "Not found")
    if kind == "cover":
        text = o.cover_letter or ""
    elif kind == "resume":
        text = o.tailored_resume or ""
    else:
        text = o.tailored_resume or ""
    if not text.strip():
        raise HTTPException(400, "Nothing to export")
    pdf = text_to_pdf(text)
    return Response(content=pdf, media_type="application/pdf",
                   headers={"Content-Disposition": f'attachment; filename="resume_{oid}.pdf"'})


@router.get("/{oid}/docx")
def export_docx(oid: int, kind: str = "tailored", user=Depends(get_current_user), db: Session = Depends(get_db)):
    o = db.query(Optimization).filter(Optimization.id == oid, Optimization.user_id == user.id).first()
    if not o:
        raise HTTPException(404, "Not found")
    text = o.tailored_resume if kind != "cover" else o.cover_letter
    if not (text or "").strip():
        raise HTTPException(400, "Nothing to export")
    docx = text_to_docx(text)
    return Response(content=docx, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                   headers={"Content-Disposition": f'attachment; filename="resume_{oid}.docx"'})
