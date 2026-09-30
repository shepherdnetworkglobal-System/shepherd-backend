from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Donation, Mission, MissionaryProfile, DonationStatus
from app.services.payout_adapters import payout_router

router = APIRouter(prefix="/api/payouts", tags=["Payouts & Settlement"])


@router.get("/quote")
async def get_payout_quote(
    mission_id: int,
    amount_usd: Decimal,
    db: Session = Depends(get_db)
):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    profile = db.query(MissionaryProfile).filter(
        MissionaryProfile.id == mission.missionary_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Missionary profile not found")

    # Determine payout method from missionary config
    method = "mpesa" if profile.mpesa_phone_number else "cash_pickup"
    currency = "KES" if profile.country == "Kenya" else "USD"

    adapter = payout_router.get_adapter(profile.country, method)
    quote = await adapter.get_quote("USDC", currency, amount_usd)

    return {
        "mission_id": mission_id,
        "missionary_shepherd_id": profile.shepherd_id,
        "country": profile.country,
        "payout_method": method,
        "quote": quote.model_dump()
    }


@router.post("/initiate")
async def initiate_payout(
    donation_id: int,
    db: Session = Depends(get_db)
):
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")

    if donation.status != DonationStatus.CONFIRMED_ONCHAIN:
        raise HTTPException(
            status_code=400,
            detail="Donation must be CONFIRMED_ONCHAIN before payout"
        )

    mission = db.query(Mission).filter(Mission.id == donation.mission_id).first()
    profile = db.query(MissionaryProfile).filter(
        MissionaryProfile.id == mission.missionary_id
    ).first()

    method = "mpesa" if profile.mpesa_phone_number else "cash_pickup"
    currency = "KES" if profile.country == "Kenya" else "USD"
    recipient = profile.mpesa_phone_number or profile.stellar_payout_address

    adapter = payout_router.get_adapter(profile.country, method)
    result = await adapter.execute_payout(
        recipient_identifier=recipient,
        amount=donation.amount_usd,
        currency=currency,
        reference=f"DON-{donation.id}"
    )

    return {
        "donation_id": donation_id,
        "payout": result.model_dump()
    }


@router.get("/status/{provider_tx_id}")
async def get_payout_status(provider_tx_id: str):
    # Determine provider from transaction ID prefix
    if provider_tx_id.startswith("CP-"):
        adapter = payout_router.adapters["clickpesa"]
    elif provider_tx_id.startswith("MG-"):
        adapter = payout_router.adapters["moneygram"]
    else:
        raise HTTPException(status_code=400, detail="Unknown provider transaction ID")

    status = await adapter.check_status(provider_tx_id)
    return status.model_dump()