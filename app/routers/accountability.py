from typing import List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Mission, Receipt, MilestoneUpdate, Donation, DonationStatus
from app.schemas.schemas import (
    ReceiptCreate,
    ReceiptResponse,
    MilestoneUpdateCreate,
    MilestoneUpdateResponse,
)

router = APIRouter(prefix="/api/accountability", tags=["Accountability & Transparency"])


@router.post("/receipts", response_model=ReceiptResponse)
def upload_receipt(
    payload: ReceiptCreate,
    db: Session = Depends(get_db)
):
    mission = db.query(Mission).filter(Mission.id == payload.mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    receipt = Receipt(
        mission_id=payload.mission_id,
        title=payload.title,
        amount_spent_usd=payload.amount_spent_usd,
        category=payload.category,
        receipt_image_url=payload.receipt_image_url,
        vendor_name=payload.vendor_name,
        notes=payload.notes
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


@router.post("/updates", response_model=MilestoneUpdateResponse)
def post_milestone_update(
    payload: MilestoneUpdateCreate,
    db: Session = Depends(get_db)
):
    mission = db.query(Mission).filter(Mission.id == payload.mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    update = MilestoneUpdate(
        mission_id=payload.mission_id,
        title=payload.title,
        description=payload.description,
        photo_url=payload.photo_url,
        people_served=payload.people_served
    )
    db.add(update)
    db.commit()
    db.refresh(update)
    return update


@router.get("/receipts", response_model=list[ReceiptResponse])
def list_all_receipts(db: Session = Depends(get_db)):
    return db.query(Receipt).order_by(Receipt.created_at.desc()).all()


@router.get("/feed/{mission_id}")
def get_mission_transparency_feed(
    mission_id: int,
    db: Session = Depends(get_db)
):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    receipts = db.query(Receipt).filter(Receipt.mission_id == mission_id).all()
    updates = db.query(MilestoneUpdate).filter(MilestoneUpdate.mission_id == mission_id).all()
    donations = db.query(Donation).filter(
        Donation.mission_id == mission_id,
        Donation.status == DonationStatus.CONFIRMED_ONCHAIN
    ).all()

    total_spent = sum([Decimal(str(r.amount_spent_usd)) for r in receipts])
    total_received = sum([Decimal(str(d.amount_usd)) for d in donations])

    return {
        "mission_id": mission_id,
        "mission_title": mission.title,
        "financial_ledger": {
            "total_received_usd": total_received,
            "total_spent_usd": total_spent,
            "remaining_unallocated_usd": total_received - total_spent,
        },
        "receipts": receipts,
        "milestone_updates": updates,
        "confirmed_donations_count": len(donations),
    }