from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Mission, MissionaryProfile, VerificationStatus
from app.schemas.schemas import MissionCreate, MissionResponse, MissionUpdate
from seed_demo import run_demo_seed

from app.models.models import User, MissionaryProfile

router = APIRouter(prefix="/api/missions", tags=["Missions"])


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
            "missions": [
                {
                    "id": m.id,
                    "title": m.title,
                    "status": str(m.status),
                    "raised": float(m.raised_amount_usd),
                    "goal": float(m.goal_amount_usd)
                }
                for m in missions
            ]
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


import traceback

@router.post("/seed")
@router.get("/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    try:
        run_demo_seed(db)
        missions_count = db.query(Mission).count()
        return {"status": "success", "message": "Demo missions seeded successfully", "total_missions": missions_count}
    except Exception as e:
        print("SEED ERROR TRACEBACK:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Seed error: {str(e)}")


@router.post("/", response_model=MissionResponse)
def create_mission(
    payload: MissionCreate,
    db: Session = Depends(get_db)
):
    profile = db.query(MissionaryProfile).filter(MissionaryProfile.id == payload.missionary_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Missionary profile not found")

    if profile.verification_status != VerificationStatus.APPROVED:
        raise HTTPException(
            status_code=403,
            detail="Missionary must be APPROVED before launching a public mission"
        )

    mission = Mission(
        missionary_id=payload.missionary_id,
        title=payload.title,
        description=payload.description,
        goal_amount_usd=payload.goal_amount_usd,
        target_country=payload.target_country
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


@router.get("/")
def list_missions(db: Session = Depends(get_db)):
    missions = db.query(Mission).all()
    if not missions:
        try:
            run_demo_seed(db)
            missions = db.query(Mission).all()
        except Exception as e:
            print(f"Seed note: {e}")

    result = []
    for m in missions:
        raw_status = m.status.value if hasattr(m.status, "value") else str(m.status or "ACTIVE")
        clean_status = raw_status.replace("MissionStatus.", "")

        raw_under = m.underfunding_rule.value if hasattr(m.underfunding_rule, "value") else str(m.underfunding_rule or "HOLD_UNTIL_THRESHOLD")
        clean_under = raw_under.replace("UnderfundingRule.", "")

        raw_over = m.overfunding_rule.value if hasattr(m.overfunding_rule, "value") else str(m.overfunding_rule or "EXPAND_SCOPE")
        clean_over = raw_over.replace("OverfundingRule.", "")

        result.append({
            "id": m.id,
            "missionary_id": m.missionary_id,
            "title": m.title,
            "description": m.description,
            "goal_amount_usd": float(m.goal_amount_usd or 0),
            "raised_amount_usd": float(m.raised_amount_usd or 0),
            "target_country": m.target_country,
            "location_granularity": m.location_granularity,
            "exact_location_hidden": bool(m.exact_location_hidden),
            "local_partners": m.local_partners,
            "underfunding_rule": clean_under,
            "overfunding_rule": clean_over,
            "reporting_plan": m.reporting_plan,
            "status": clean_status,
            "created_at": m.created_at.isoformat() if m.created_at else None
        })
    return result


@router.get("/{mission_id}", response_model=MissionResponse)
def get_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.put("/{mission_id}", response_model=MissionResponse)
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
        mission.status = payload.status
    if payload.underfunding_rule is not None:
        mission.underfunding_rule = payload.underfunding_rule
    if payload.overfunding_rule is not None:
        mission.overfunding_rule = payload.overfunding_rule
    if payload.exact_location_hidden is not None:
        mission.exact_location_hidden = payload.exact_location_hidden
    if payload.location_granularity is not None:
        mission.location_granularity = payload.location_granularity
    if payload.reporting_plan is not None:
        mission.reporting_plan = payload.reporting_plan
    if payload.local_partners is not None:
        mission.local_partners = payload.local_partners

    db.commit()
    db.refresh(mission)
    return mission