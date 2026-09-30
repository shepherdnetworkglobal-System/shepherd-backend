from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Donation, Mission, DonationStatus
from app.schemas.schemas import DonationCreate, DonationVerify, DonationResponse
from app.services.stellar import stellar_service

router = APIRouter(prefix="/api/donations", tags=["Donations & Payment Wall"])


@router.post("/create", response_model=DonationResponse)
def create_donation(
    payload: DonationCreate,
    db: Session = Depends(get_db)
):
    mission = db.query(Mission).filter(Mission.id == payload.mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    donation = Donation(
        mission_id=payload.mission_id,
        donor_email=payload.donor_email,
        amount_usd=payload.amount_usd,
        asset_type=payload.asset_type,
        status=DonationStatus.PENDING
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)
    return donation


@router.post("/verify-onchain", response_model=DonationResponse)
async def verify_onchain_donation(
    payload: DonationVerify,
    db: Session = Depends(get_db)
):
    donation = db.query(Donation).filter(Donation.id == payload.donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")

    is_valid = await stellar_service.verify_transaction(payload.stellar_tx_hash)
    if not is_valid:
        donation.status = DonationStatus.FAILED
        db.commit()
        db.refresh(donation)
        raise HTTPException(status_code=400, detail="Transaction verification failed on Stellar")

    donation.stellar_tx_hash = payload.stellar_tx_hash
    donation.status = DonationStatus.CONFIRMED_ONCHAIN

    # Update mission raised total
    mission = db.query(Mission).filter(Mission.id == donation.mission_id).first()
    if mission:
        mission.raised_amount_usd = Decimal(str(mission.raised_amount_usd)) + Decimal(str(donation.amount_usd))

    db.commit()
    db.refresh(donation)
    return donation


@router.get("/", response_model=list[DonationResponse])
def list_all_donations(db: Session = Depends(get_db)):
    return db.query(Donation).order_by(Donation.created_at.desc()).all()


@router.get("/{donation_id}/status", response_model=DonationResponse)
def get_donation_status(donation_id: int, db: Session = Depends(get_db)):
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    return donation