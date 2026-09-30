from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import MissionaryProfile, User, VerificationStatus, Mission, PastProject, Donation, DonationStatus
from app.schemas.schemas import (
    MissionaryProfileCreate,
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
        organization_name=payload.organization_name,
        stellar_payout_address=payload.stellar_payout_address,
        mpesa_phone_number=payload.mpesa_phone_number,
        verification_status=VerificationStatus.SUBMITTED
    )
    db.add(profile)
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