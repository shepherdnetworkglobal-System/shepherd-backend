import os
from decimal import Decimal
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Donation, Mission, DonationStatus
from app.schemas.schemas import DonationCreate, DonationVerify, DonationResponse
from app.services.stellar import stellar_service

router = APIRouter(prefix="/api/donations", tags=["Donations & Payment Wall"])
webhook_router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
stripe.api_key = STRIPE_SECRET_KEY


@router.post("/create-stripe-checkout")
async def create_stripe_checkout(
    payload: dict,
    db: Session = Depends(get_db)
):
    mission_id = payload.get("mission_id")
    amount_usd = payload.get("amount_usd")
    donor_name = payload.get("donor_name")
    donor_email = payload.get("donor_email")
    progress_opt_in = payload.get("progress_opt_in", True)
    origin_url = payload.get("origin_url", "https://shepherd-frontend-two.vercel.app")

    if not mission_id or not amount_usd or float(amount_usd) <= 0:
        raise HTTPException(status_code=400, detail="Invalid mission ID or amount")

    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    donation = Donation(
        mission_id=mission_id,
        donor_name=donor_name,
        donor_email=donor_email,
        progress_opt_in=progress_opt_in,
        amount_usd=Decimal(str(amount_usd)),
        asset_type="USD_STRIPE",
        status=DonationStatus.PENDING
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)

    try:
        session = stripe.checkout.Session.create(
            customer_email=donor_email if donor_email else None,
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Donation to Mission #{mission.id}: {mission.title}",
                            "description": f"Transparent cross-border deployment via Shepherd Network to {mission.target_country or 'field missionary'}.",
                        },
                        "unit_amount": int(float(amount_usd) * 100),
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            metadata={
                "donation_id": str(donation.id),
                "mission_id": str(mission.id),
            },
            success_url=f"{origin_url}/missions/{mission_id}?donation=success&tx={donation.id}",
            cancel_url=f"{origin_url}/missions/{mission_id}?donation=cancelled",
        )
        return {"checkout_url": session.url, "donation_id": donation.id}
    except Exception as e:
        donation.status = DonationStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=f"Stripe Checkout error: {str(e)}")


@webhook_router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="stripe-signature"), db: Session = Depends(get_db)):
    payload = await request.body()
    event = None

    try:
        if STRIPE_WEBHOOK_SECRET and stripe_signature:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
        else:
            event = stripe.Event.construct_from(
                request.json(), stripe.api_key
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook signature error: {str(e)}")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        donation_id = metadata.get("donation_id")
        
        if donation_id:
            donation = db.query(Donation).filter(Donation.id == int(donation_id)).first()
            if donation and donation.status == DonationStatus.PENDING:
                donation.status = DonationStatus.CONFIRMED_ONCHAIN
                donation.stellar_tx_hash = f"STRIPE-{session.get('id')}"
                
                mission = db.query(Mission).filter(Mission.id == donation.mission_id).first()
                if mission:
                    mission.raised_amount_usd = Decimal(str(mission.raised_amount_usd)) + Decimal(str(donation.amount_usd))
                
                db.commit()

    return {"status": "success"}


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
        donor_name=payload.donor_name,
        donor_email=payload.donor_email,
        progress_opt_in=payload.progress_opt_in,
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