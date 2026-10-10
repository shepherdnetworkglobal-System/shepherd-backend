from typing import List, Optional
import traceback
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text

from app.database.session import get_db
from app.models.models import Mission, MissionaryProfile, MissionCoalitionPartner, User
from app.schemas.schemas import MissionCreate, MissionUpdate
from pydantic import BaseModel

router = APIRouter(prefix="/api/missions", tags=["Missions"])


def _serialize_mission(m: Mission) -> dict:
    """Safely convert SQLAlchemy Mission model to dict without Pydantic serialization crashes."""
    status_str = str(getattr(m.status, "value", m.status) or "ACTIVE").upper()
    underfunding_str = str(getattr(m.underfunding_rule, "value", m.underfunding_rule) or "HOLD_UNTIL_THRESHOLD").upper()

    missionary_data = None
    try:
        if m.missionary:
            missionary_data = {
                "name": m.missionary.user.full_name if m.missionary.user else "Verified Operator",
                "shepherd_id": m.missionary.shepherd_id,
                "organization_name": m.missionary.organization_name,
                "profile_photo_url": m.missionary.profile_photo_url,
                "years_of_service": m.missionary.years_of_service,
                "affiliation": str(getattr(m.missionary.affiliation_path, "value", m.missionary.affiliation_path) or "INDEPENDENT")
            }
    except Exception:
        pass
    overfunding_str = str(getattr(m.overfunding_rule, "value", m.overfunding_rule) or "EXPAND_SCOPE").upper()

    coalition = []
    try:
        if hasattr(m, "coalition_partners") and m.coalition_partners:
            coalition = [
                {
                    "id": c.id,
                    "mission_id": c.mission_id,
                    "organization_id": c.organization_id,
                    "missionary_id": c.missionary_id,
                    "partner_role": str(c.partner_role),
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in m.coalition_partners
            ]
    except Exception:
        coalition = []

    budget = []
    try:
        if hasattr(m, "budget_items") and m.budget_items:
            budget = [
                {
                    "id": b.id,
                    "mission_id": b.mission_id,
                    "item_name": b.item_name,
                    "category": str(b.category),
                    "quantity": float(b.quantity),
                    "unit_cost_usd": float(b.unit_cost_usd),
                    "total_cost_usd": float(b.total_cost_usd),
                    "notes": b.notes,
                    "created_at": b.created_at.isoformat() if b.created_at else None
                }
                for b in m.budget_items
            ]
    except Exception:
        budget = []

    photos = []
    try:
        if hasattr(m, "photos") and m.photos:
            public_photos = [p for p in m.photos if getattr(p, "is_public", True)]
            public_photos = sorted(public_photos, key=lambda p: p.created_at or datetime.min, reverse=True)
            photos = [
                {
                    "id": p.id,
                    "url": p.image_url,
                    "image_url": p.image_url,
                    "caption": p.caption,
                    "category": str(p.category) if p.category else "DURING",
                    "checkpoint_id": p.checkpoint_id,
                    "is_public": bool(p.is_public),
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in public_photos
            ]
    except Exception:
        photos = []

    reports = []
    try:
        if hasattr(m, "field_reports") and m.field_reports:
            public_reports = [r for r in m.field_reports if getattr(r, "is_public", False)]
            public_reports = sorted(public_reports, key=lambda r: r.created_at or datetime.min, reverse=True)
            reports = [
                {
                    "id": r.id,
                    "title": r.title,
                    "summary": (r.body or "")[:280],
                    "body": r.body,
                    "report_type": str(r.report_type) if r.report_type else "WEEKLY",
                    "checkpoint_id": r.checkpoint_id,
                    "people_served_delta": int(r.people_served_delta or 0),
                    "author_name": r.author_name,
                    "is_public": bool(r.is_public),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in public_reports
            ]
    except Exception:
        reports = []

    checkpoints = []
    try:
        if hasattr(m, "checkpoints") and m.checkpoints:
            public_cps = [c for c in m.checkpoints if getattr(c, "is_public", True)]
            public_cps = sorted(public_cps, key=lambda c: c.sort_order or 0)
            checkpoints = [
                {
                    "id": c.id,
                    "title": c.title,
                    "description": c.description,
                    "status": str(c.status) if c.status else "PENDING",
                    "weight_percent": float(c.weight_percent or 0),
                    "sort_order": int(c.sort_order or 0),
                    "photo_url": c.photo_url,
                    "is_public": bool(c.is_public),
                }
                for c in public_cps
            ]
    except Exception:
        checkpoints = []

    cover_image = None
    if photos:
        cover_image = photos[0].get("url")
    elif getattr(m, "before_gallery_images", None):
        raw = m.before_gallery_images
        if isinstance(raw, str) and raw.strip():
            cover_image = raw.split(",")[0].strip()

    latest_update = None
    if reports:
        latest_update = reports[0].get("summary") or reports[0].get("title")

    return {
        "id": m.id,
        "missionary_id": m.missionary_id,
        "missionary": missionary_data,
        "missionary_profile": missionary_data,
        "title": m.title,
        "description": m.description,
        "goal_amount_usd": float(m.goal_amount_usd or 0.0),
        "raised_amount_usd": float(m.raised_amount_usd or 0.0),
        "target_country": m.target_country,
        "map_location": m.map_location,
        "location_granularity": m.location_granularity,
        "exact_location_hidden": bool(m.exact_location_hidden),
        "problem_statement": m.problem_statement,
        "mission_objectives": m.mission_objectives,
        "proposed_process": m.proposed_process,
        "before_gallery_images": m.before_gallery_images,
        "beneficiary_group": m.beneficiary_group,
        "expected_duration": m.expected_duration,
        "start_date": m.start_date.isoformat() if m.start_date else None,
        "expected_end_date": m.expected_end_date.isoformat() if m.expected_end_date else None,
        "estimated_total_cost": float(m.estimated_total_cost) if m.estimated_total_cost else None,
        "local_partners": m.local_partners,
        "underfunding_rule": underfunding_str,
        "overfunding_rule": overfunding_str,
        "reporting_plan": m.reporting_plan,
        "status": status_str,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "coalition_partners": coalition,
        "budget_items": budget,
        "photos": photos,
        "reports": reports,
        "field_reports": reports,
        "checkpoints": checkpoints,
        "cover_image": cover_image,
        "latest_update": latest_update,
    }


@router.get("/debug")
def debug_database_state(db: Session = Depends(get_db)):
    try:
        users_count = db.query(User).count()
        profiles_count = db.query(MissionaryProfile).count()
        missions = db.query(Mission).all()
        return {
            "status": "connected",
            "users_count": users_count,
            "profiles_count": profiles_count,
            "missions_count": len(missions),
            "missions": [_serialize_mission(m) for m in missions]
        }
    except Exception as e:
        return {"status": "error", "detail": str(e), "traceback": traceback.format_exc()}


@router.post("")
@router.post("/")
def create_mission(
    payload: MissionCreate,
    db: Session = Depends(get_db)
):
    try:
        profile = db.query(MissionaryProfile).filter(MissionaryProfile.id == payload.missionary_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Missionary profile not found")

        profile_status = str(getattr(profile.verification_status, "value", profile.verification_status) or "").upper()
        if profile_status != "APPROVED":
            raise HTTPException(
                status_code=403,
                detail="Missionary must be APPROVED before launching a public mission"
            )

        underfunding = payload.underfunding_rule.value if hasattr(payload.underfunding_rule, "value") else str(payload.underfunding_rule)
        overfunding = payload.overfunding_rule.value if hasattr(payload.overfunding_rule, "value") else str(payload.overfunding_rule)

        mission = Mission(
            missionary_id=payload.missionary_id,
            title=payload.title,
            description=payload.description,
            goal_amount_usd=payload.goal_amount_usd,
            target_country=payload.target_country,
            map_location=payload.map_location,
            location_granularity=payload.location_granularity,
            exact_location_hidden=payload.exact_location_hidden,
            problem_statement=payload.problem_statement,
            mission_objectives=payload.mission_objectives,
            proposed_process=payload.proposed_process,
            before_gallery_images=payload.before_gallery_images,
            beneficiary_group=payload.beneficiary_group,
            expected_duration=payload.expected_duration,
            start_date=payload.start_date,
            expected_end_date=payload.expected_end_date,
            estimated_total_cost=payload.estimated_total_cost,
            local_partners=payload.local_partners,
            underfunding_rule=underfunding,
            overfunding_rule=overfunding,
            reporting_plan=payload.reporting_plan,
            status="ACTIVE"
        )

        db.add(mission)
        db.commit()
        db.refresh(mission)
        return _serialize_mission(mission)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print("CREATE MISSION ERROR:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("")
@router.get("/")
def list_missions(db: Session = Depends(get_db)):
    missions = (
        db.query(Mission)
        .options(
            joinedload(Mission.missionary).joinedload(MissionaryProfile.user),
            joinedload(Mission.photos),
            joinedload(Mission.field_reports),
            joinedload(Mission.checkpoints),
            joinedload(Mission.budget_items),
            joinedload(Mission.coalition_partners),
        )
        .order_by(Mission.created_at.desc())
        .all()
    )
    return [_serialize_mission(m) for m in missions]


@router.get("/{mission_id}")
def get_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = (
        db.query(Mission)
        .options(
            joinedload(Mission.missionary).joinedload(MissionaryProfile.user),
            joinedload(Mission.photos),
            joinedload(Mission.field_reports),
            joinedload(Mission.checkpoints),
            joinedload(Mission.budget_items),
            joinedload(Mission.coalition_partners),
        )
        .filter(Mission.id == mission_id)
        .first()
    )
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return _serialize_mission(mission)


@router.put("/{mission_id}")
def update_mission(
    mission_id: int,
    payload: MissionUpdate,
    db: Session = Depends(get_db)
):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    if payload.title is not None:
        mission.title = payload.title
    if payload.description is not None:
        mission.description = payload.description
    if payload.status is not None:
        mission.status = getattr(payload.status, "value", str(payload.status))
    if payload.underfunding_rule is not None:
        mission.underfunding_rule = getattr(payload.underfunding_rule, "value", str(payload.underfunding_rule))
    if payload.overfunding_rule is not None:
        mission.overfunding_rule = getattr(payload.overfunding_rule, "value", str(payload.overfunding_rule))
    if payload.exact_location_hidden is not None:
        mission.exact_location_hidden = payload.exact_location_hidden
    if payload.location_granularity is not None:
        mission.location_granularity = payload.location_granularity
    if payload.reporting_plan is not None:
        mission.reporting_plan = payload.reporting_plan
    if payload.local_partners is not None:
        mission.local_partners = payload.local_partners
    if payload.goal_amount_usd is not None:
        mission.goal_amount_usd = payload.goal_amount_usd
    if payload.target_country is not None:
        mission.target_country = payload.target_country
    if payload.map_location is not None:
        mission.map_location = payload.map_location
    if payload.problem_statement is not None:
        mission.problem_statement = payload.problem_statement
    if payload.mission_objectives is not None:
        mission.mission_objectives = payload.mission_objectives
    if payload.proposed_process is not None:
        mission.proposed_process = payload.proposed_process

    db.commit()
    db.refresh(mission)
    return _serialize_mission(mission)


# --- Coalition Partner Management ---
class CoalitionPartnerAdd(BaseModel):
    missionary_id: int
    partner_role: str = "SUPPORT"

@router.post("/{mission_id}/partners")
def add_coalition_partner(
    mission_id: int,
    payload: CoalitionPartnerAdd,
    db: Session = Depends(get_db)
):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    profile = db.query(MissionaryProfile).filter(MissionaryProfile.id == payload.missionary_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Missionary profile not found")

    existing = db.query(MissionCoalitionPartner).filter(
        MissionCoalitionPartner.mission_id == mission_id,
        MissionCoalitionPartner.missionary_id == payload.missionary_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This missionary is already a partner on this mission")

    partner = MissionCoalitionPartner(
        mission_id=mission_id,
        missionary_id=payload.missionary_id,
        partner_role=payload.partner_role
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return {"status": "success", "id": partner.id}


@router.delete("/{mission_id}/partners/{partner_id}")
def remove_coalition_partner(
    mission_id: int,
    partner_id: int,
    db: Session = Depends(get_db)
):
    partner = db.query(MissionCoalitionPartner).filter(
        MissionCoalitionPartner.id == partner_id,
        MissionCoalitionPartner.mission_id == mission_id
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    db.delete(partner)
    db.commit()
    return {"status": "success", "message": "Partner removed"}