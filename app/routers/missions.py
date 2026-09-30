from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Mission, MissionaryProfile, VerificationStatus
from app.schemas.schemas import MissionCreate, MissionResponse

router = APIRouter(prefix="/api/missions", tags=["Missions"])


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
    return db.query(Mission).all()


@router.get("/{mission_id}", response_model=MissionResponse)
def get_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission