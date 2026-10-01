from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Mission, MissionaryProfile, VerificationStatus
from app.schemas.schemas import MissionCreate, MissionResponse, MissionUpdate
from seed_demo import run_demo_seed

router = APIRouter(prefix="/api/missions", tags=["Missions"])


@router.post("/seed")
@router.get("/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    try:
        run_demo_seed(db)
        return {"status": "success", "message": "Demo missions seeded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/", response_model=List[MissionResponse])
def list_missions(db: Session = Depends(get_db)):
    missions = db.query(Mission).all()
    if not missions:
        try:
            run_demo_seed(db)
            missions = db.query(Mission).all()
        except Exception as e:
            print(f"Auto-seed note: {e}")
    return missions


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