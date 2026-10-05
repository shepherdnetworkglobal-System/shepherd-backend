from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import (
    MissionaryProfile,
    User,
    VerificationStatus,
    Mission,
    PastProject,
    Donation,
    DonationStatus,
    AffiliationPath,
    LayerStatus
)
from app.schemas.schemas import (
    MissionaryProfileCreate,
    MissionaryProfileUpdate,
    MissionaryDocumentUpload,
    AdminVerificationReview,
    MissionaryProfileResponse,
    PastProjectCreate,
    PastProjectResponse,
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
        affiliation_path=payload.affiliation_path,
        organization_name=payload.organization_name,
        stellar_payout_address=payload.stellar_payout_address,
        mpesa_phone_number=payload.mpesa_phone_number,
        profile_photo_url=payload.profile_photo_url,
        biography=payload.biography,
        years_of_service=payload.years_of_service,
        calling_description=payload.calling_description,
        verification_status=VerificationStatus.SUBMITTED,
        identity_layer_status=LayerStatus.PENDING
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
        profile.identity_layer_status = LayerStatus.PENDING
    if docs.selfie_url:
        profile.selfie_url = docs.selfie_url
    if docs.proof_of_address_url:
        profile.proof_of_address_url = docs.proof_of_address_url
        profile.address_layer_status = LayerStatus.PENDING

    profile.verification_status = VerificationStatus.UNDER_REVIEW
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/projects", response_model=PastProjectResponse)
def add_past_project(
    payload: PastProjectCreate,
    db: Session = Depends(get_db)
):
    profile = db.query(MissionaryProfile).filter(MissionaryProfile.id == payload.missionary_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Missionary profile not found")

    project = PastProject(
        missionary_id=payload.missionary_id,
        title=payload.title,
        description=payload.description,
        location=payload.location,
        year_completed=payload.year_completed,
        people_impacted=payload.people_impacted,
        media_urls=payload.media_urls
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/applications")
def list_verification_applications(db: Session = Depends(get_db)):
    profiles = db.query(MissionaryProfile).order_by(MissionaryProfile.created_at.desc()).all()
    results = []
    for profile in profiles:
        user = db.query(User).filter(User.id == profile.user_id).first()
        results.append({
            "id": profile.id,
            "user_id": profile.user_id,
            "full_name": user.full_name if user else "Unknown Operator",
            "email": user.email if user else None,
            "shepherd_id": profile.shepherd_id,
            "country": profile.country,
            "organization_name": profile.organization_name,
            "organization_id": profile.organization_id,
            "profile_photo_url": profile.profile_photo_url,
            "biography": profile.biography,
            "years_of_service": profile.years_of_service,
            "calling_description": profile.calling_description,
            "verification_status": profile.verification_status.value if hasattr(profile.verification_status, "value") else str(profile.verification_status),
            "affiliation_path": profile.affiliation_path.value if hasattr(profile.affiliation_path, "value") else str(profile.affiliation_path),
            "risk_tier": profile.risk_tier.value if hasattr(profile.risk_tier, "value") else str(profile.risk_tier),
            "badge_identity_verified": profile.badge_identity_verified,
            "badge_org_verified": profile.badge_org_verified,
            "badge_payout_verified": profile.badge_payout_verified,
            "badge_mission_verified": profile.badge_mission_verified,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
        })
    return results


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
    if review.admin_notes is not None:
        profile.admin_notes = review.admin_notes
    if review.shepherd_id is not None:
        profile.shepherd_id = review.shepherd_id
    if review.affiliation_path is not None:
        profile.affiliation_path = review.affiliation_path
    if review.risk_tier is not None:
        profile.risk_tier = review.risk_tier

    if review.identity_layer_status is not None:
        profile.identity_layer_status = review.identity_layer_status
    if review.address_layer_status is not None:
        profile.address_layer_status = review.address_layer_status
    if review.affiliation_layer_status is not None:
        profile.affiliation_layer_status = review.affiliation_layer_status
    if review.organization_layer_status is not None:
        profile.organization_layer_status = review.organization_layer_status
    if review.payout_layer_status is not None:
        profile.payout_layer_status = review.payout_layer_status
    if review.mission_layer_status is not None:
        profile.mission_layer_status = review.mission_layer_status
    if review.history_layer_status is not None:
        profile.history_layer_status = review.history_layer_status

    if review.badge_identity_verified is not None:
        profile.badge_identity_verified = review.badge_identity_verified
    if review.badge_org_verified is not None:
        profile.badge_org_verified = review.badge_org_verified
    if review.badge_payout_verified is not None:
        profile.badge_payout_verified = review.badge_payout_verified
    if review.badge_mission_verified is not None:
        profile.badge_mission_verified = review.badge_mission_verified

    profile.last_reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/public/{profile_id}")
def get_public_missionary_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(MissionaryProfile).filter(MissionaryProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Missionary not found")
    if profile.verification_status != VerificationStatus.APPROVED:
        raise HTTPException(status_code=403, detail="Profile not yet public")

    user = db.query(User).filter(User.id == profile.user_id).first()
    active_missions = db.query(Mission).filter(Mission.missionary_id == profile_id).all()
    past_projects = db.query(PastProject).filter(PastProject.missionary_id == profile_id).all()

    donations = db.query(Donation).join(Mission).filter(
        Mission.missionary_id == profile_id,
        Donation.status == DonationStatus.CONFIRMED_ONCHAIN
    ).all()
    total_funds = sum([float(d.amount_usd) for d in donations])
    total_people = sum([p.people_impacted for p in past_projects])

    return {
        "id": profile.id,
        "shepherd_id": profile.shepherd_id,
        "full_name": user.full_name if user else "Unknown",
        "country": profile.country,
        "organization_name": profile.organization_name,
        "profile_photo_url": profile.profile_photo_url,
        "biography": profile.biography,
        "years_of_service": profile.years_of_service,
        "calling_description": profile.calling_description,
        "verification_status": profile.verification_status.value,
        "affiliation_path": profile.affiliation_path.value,
        "risk_tier": profile.risk_tier.value,
        "badge_identity_verified": profile.badge_identity_verified,
        "badge_org_verified": profile.badge_org_verified,
        "badge_payout_verified": profile.badge_payout_verified,
        "badge_mission_verified": profile.badge_mission_verified,
        "active_missions": [
            {
                "id": m.id,
                "title": m.title,
                "goal_amount_usd": float(m.goal_amount_usd),
                "raised_amount_usd": float(m.raised_amount_usd),
                "status": m.status.value,
                "target_country": m.target_country
            }
            for m in active_missions
        ],
        "past_projects": [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "location": p.location,
                "year_completed": p.year_completed,
                "people_impacted": p.people_impacted,
                "media_urls": p.media_urls
            }
            for p in past_projects
        ],
        "total_funds_deployed": total_funds,
        "total_people_served": total_people
    }


@router.put("/profile/{profile_id}", response_model=MissionaryProfileResponse)
def update_missionary_profile(
    profile_id: int,
    payload: MissionaryProfileUpdate,
    db: Session = Depends(get_db)
):
    profile = db.query(MissionaryProfile).filter(MissionaryProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if payload.country is not None:
        profile.country = payload.country
    if payload.organization_name is not None:
        profile.organization_name = payload.organization_name
    if payload.profile_photo_url is not None:
        profile.profile_photo_url = payload.profile_photo_url
    if payload.biography is not None:
        profile.biography = payload.biography
    if payload.years_of_service is not None:
        profile.years_of_service = payload.years_of_service
    if payload.calling_description is not None:
        profile.calling_description = payload.calling_description
    if payload.stellar_payout_address is not None:
        profile.stellar_payout_address = payload.stellar_payout_address

    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/projects/{project_id}")
def delete_past_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    project = db.query(PastProject).filter(PastProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"message": "Past project removed"}