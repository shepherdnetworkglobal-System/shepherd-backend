from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import MissionaryProfile, User, VerificationStatus
from app.schemas.schemas import (
    MissionaryProfileCreate,
    MissionaryDocumentUpload,
    AdminVerificationReview,
    MissionaryProfileResponse,
)

router = APIRouter(prefix="/api/verification", tags=["Missionary Verification"])


@router.post("/apply", response_model=MissionaryProfileResponse)
def apply_for_verification(
    payload: MissionaryProfileCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_profile = db.query(MissionaryProfile).filter(MissionaryProfile.user_id == payload.user_id).first()
    if existing_profile:
        raise HTTPException(status_code=400, detail="Application already submitted")

    profile = MissionaryProfile(
        user_id=payload.user_id,
        country=payload.country,
        organization_name=payload.organization_name,
        stellar_payout_address=payload.stellar_payout_address,
        mpesa_phone_number=payload.mpesa_phone_number,
        verification_status=VerificationStatus.SUBMITTED
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/documents/{profile_id}", response_model=MissionaryProfileResponse)
def upload_documents(
    profile_id: int,
    docs: MissionaryDocumentUpload,
    db: Session = Depends(get_db)
):
    profile = db.query(MissionaryProfile).filter(MissionaryProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if docs.organization_cert_url:
        profile.organization_cert_url = docs.organization_cert_url
    if docs.government_id_url:
        profile.government_id_url = docs.government_id_url
    if docs.selfie_url:
        profile.selfie_url = docs.selfie_url
    if docs.proof_of_address_url:
        profile.proof_of_address_url = docs.proof_of_address_url

    profile.verification_status = VerificationStatus.UNDER_REVIEW
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/applications", response_model=list[MissionaryProfileResponse])
def list_verification_applications(db: Session = Depends(get_db)):
    return db.query(MissionaryProfile).order_by(MissionaryProfile.created_at.desc()).all()


@router.get("/status/{user_id}", response_model=MissionaryProfileResponse)
def get_verification_status(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(MissionaryProfile).filter(MissionaryProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Verification profile not found")
    return profile


@router.put("/admin/review/{profile_id}", response_model=MissionaryProfileResponse)
def admin_review_verification(
    profile_id: int,
    review: AdminVerificationReview,
    db: Session = Depends(get_db)
):
    profile = db.query(MissionaryProfile).filter(MissionaryProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.verification_status = review.status
    if review.admin_notes:
        profile.admin_notes = review.admin_notes
    if review.shepherd_id:
        profile.shepherd_id = review.shepherd_id

    db.commit()
    db.refresh(profile)
    return profile