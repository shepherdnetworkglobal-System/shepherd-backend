from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.database.session import get_db
from app.models.models import Scripture

router = APIRouter(prefix="/api/scripture", tags=["Spiritual Engine"])


class ScriptureCreate(BaseModel):
    reference: str
    translation: str = "ESV"
    text: str
    theme: str = "GENERAL"
    placement: str = "HOMEPAGE"
    is_active: bool = True
    is_featured: bool = False
    weight: int = 0
    notes: Optional[str] = None


class ScriptureUpdate(BaseModel):
    reference: Optional[str] = None
    translation: Optional[str] = None
    text: Optional[str] = None
    theme: Optional[str] = None
    placement: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    weight: Optional[int] = None
    notes: Optional[str] = None


def _serialize(s: Scripture) -> dict:
    return {
        "id": s.id,
        "reference": s.reference,
        "translation": s.translation,
        "text": s.text,
        "theme": s.theme,
        "placement": s.placement,
        "is_active": bool(s.is_active),
        "is_featured": bool(s.is_featured),
        "weight": int(s.weight or 0),
        "notes": s.notes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.get("")
@router.get("/")
def list_scriptures(
    placement: Optional[str] = None,
    theme: Optional[str] = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(Scripture)
    if placement:
        q = q.filter(Scripture.placement == placement.upper())
    if theme:
        q = q.filter(Scripture.theme == theme.upper())
    if active_only:
        q = q.filter(Scripture.is_active == True)
    rows = q.order_by(Scripture.weight.desc(), Scripture.id.desc()).all()
    return [_serialize(s) for s in rows]


@router.get("/public/featured")
def get_featured_public(
    placement: str = "HOMEPAGE",
    db: Session = Depends(get_db),
):
    """Public endpoint — one featured/active verse for a placement. Weighted random among featured."""
    placement = (placement or "HOMEPAGE").upper()
    rows = (
        db.query(Scripture)
        .filter(Scripture.is_active == True)
        .filter(Scripture.placement.in_([placement, "GLOBAL"]))
        .order_by(Scripture.is_featured.desc(), Scripture.weight.desc(), func.random())
        .limit(1)
        .all()
    )
    if not rows:
        # Graceful fallback — classic platform verse
        return {
            "id": 0,
            "reference": "2 Corinthians 8:21",
            "translation": "ESV",
            "text": "For we aim at what is honorable not only in the Lord's sight but also in the sight of man.",
            "theme": "TRANSPARENCY",
            "placement": placement,
            "is_active": True,
            "is_featured": True,
            "weight": 100,
            "notes": None,
            "created_at": None,
            "updated_at": None,
        }
    return _serialize(rows[0])


@router.get("/public/rotate")
def get_rotate_public(
    placement: str = "HOMEPAGE",
    limit: int = 5,
    db: Session = Depends(get_db),
):
    """Public endpoint — small pool of active verses for client-side rotation."""
    placement = (placement or "HOMEPAGE").upper()
    limit = max(1, min(limit, 20))
    rows = (
        db.query(Scripture)
        .filter(Scripture.is_active == True)
        .filter(Scripture.placement.in_([placement, "GLOBAL"]))
        .order_by(Scripture.weight.desc(), func.random())
        .limit(limit)
        .all()
    )
    if not rows:
        return [get_featured_public(placement=placement, db=db)]
    return [_serialize(s) for s in rows]


@router.get("/{scripture_id}")
def get_scripture(scripture_id: int, db: Session = Depends(get_db)):
    s = db.query(Scripture).filter(Scripture.id == scripture_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scripture not found")
    return _serialize(s)


@router.post("")
@router.post("/")
def create_scripture(payload: ScriptureCreate, db: Session = Depends(get_db)):
    s = Scripture(
        reference=payload.reference.strip(),
        translation=(payload.translation or "ESV").upper().strip(),
        text=payload.text.strip(),
        theme=(payload.theme or "GENERAL").upper().strip(),
        placement=(payload.placement or "HOMEPAGE").upper().strip(),
        is_active=payload.is_active,
        is_featured=payload.is_featured,
        weight=payload.weight or 0,
        notes=payload.notes,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _serialize(s)


@router.put("/{scripture_id}")
def update_scripture(scripture_id: int, payload: ScriptureUpdate, db: Session = Depends(get_db)):
    s = db.query(Scripture).filter(Scripture.id == scripture_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scripture not found")

    if payload.reference is not None:
        s.reference = payload.reference.strip()
    if payload.translation is not None:
        s.translation = payload.translation.upper().strip()
    if payload.text is not None:
        s.text = payload.text.strip()
    if payload.theme is not None:
        s.theme = payload.theme.upper().strip()
    if payload.placement is not None:
        s.placement = payload.placement.upper().strip()
    if payload.is_active is not None:
        s.is_active = payload.is_active
    if payload.is_featured is not None:
        s.is_featured = payload.is_featured
    if payload.weight is not None:
        s.weight = payload.weight
    if payload.notes is not None:
        s.notes = payload.notes

    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return _serialize(s)


@router.delete("/{scripture_id}")
def delete_scripture(scripture_id: int, db: Session = Depends(get_db)):
    s = db.query(Scripture).filter(Scripture.id == scripture_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scripture not found")
    db.delete(s)
    db.commit()
    return {"status": "success", "message": "Scripture deleted"}