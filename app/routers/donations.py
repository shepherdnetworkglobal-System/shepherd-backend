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
    origin_url = payload.get("origin_url", "https://shepherdnetwork.global")

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


def _confirm_donation_in_db(db: Session, donation_id: int, tx_hash: str):
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if donation and donation.status == DonationStatus.PENDING:
        donation.status = DonationStatus.CONFIRMED_ONCHAIN
        donation.stellar_tx_hash = tx_hash
        
        mission = db.query(Mission).filter(Mission.id == donation.mission_id).first()
        if mission:
            current_raised = Decimal(str(mission.raised_amount_usd or 0))
            donation_amt = Decimal(str(donation.amount_usd or 0))
            mission.raised_amount_usd = current_raised + donation_amt
        
        db.commit()
        db.refresh(donation)
        return donation
    return donation


from sqlalchemy import func

@router.post("/verify-stripe/{donation_id}")
async def verify_stripe_donation(donation_id: int, db: Session = Depends(get_db)):
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    
    mission = db.query(Mission).filter(Mission.id == donation.mission_id).first()
    
    # Perform automated Stellar hot wallet disbursement if donation was pending
    if str(donation.status).upper() in ["PENDING", "DONATIONSTATUS.PENDING"]:
        recipient_wallet = "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335WF2TZZS3FIEROSVC27J324L6" # Standard platform recipient address
        
        if mission and hasattr(mission, "missionary") and mission.missionary:
            recipient_wallet = getattr(mission.missionary, "payout_wallet", None) or recipient_wallet
        
        # Trigger on-chain hot wallet settlement
        tx_hash = await stellar_service.disburse_from_treasury(
            recipient_public_key=recipient_wallet,
            amount_usd=float(donation.amount_usd or 0),
            memo_text=f"SHEPHERD #{donation.id}"
        )
        
        donation.status = DonationStatus.CONFIRMED_ONCHAIN
        donation.stellar_tx_hash = tx_hash
        db.commit()

    # Recalculate true sum of all confirmed donations for this mission
    confirmed_total = db.query(func.sum(Donation.amount_usd))\
        .filter(Donation.mission_id == donation.mission_id, Donation.status == DonationStatus.CONFIRMED_ONCHAIN)\
        .scalar() or Decimal("0.00")

    if mission:
        mission.raised_amount_usd = confirmed_total
        db.commit()
        db.refresh(mission)

    return {
        "donation_id": donation.id,
        "status": str(donation.status),
        "stellar_tx_hash": donation.stellar_tx_hash,
        "amount_usd": float(donation.amount_usd or 0),
        "donor_name": donation.donor_name or "Generous Donor",
        "donor_email": donation.donor_email or "",
        "mission_id": donation.mission_id,
        "mission_title": mission.title if mission else "",
        "raised_amount_usd": float(confirmed_total)
    }


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
            req_json = await request.json()
            event = stripe.Event.construct_from(req_json, stripe.api_key)
    except Exception as e:
        print(f"Stripe Webhook Error: {e}")
        raise HTTPException(status_code=400, detail=f"Webhook signature error: {str(e)}")

    event_type = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
    
    if event_type == "checkout.session.completed":
        data_obj = event.get("data", {}).get("object", {}) if isinstance(event, dict) else getattr(getattr(event, "data", None), "object", {})
        metadata = data_obj.get("metadata", {}) if isinstance(data_obj, dict) else getattr(data_obj, "metadata", {})
        donation_id = metadata.get("donation_id") if isinstance(metadata, dict) else getattr(metadata, "donation_id", None)
        session_id = data_obj.get("id") if isinstance(data_obj, dict) else getattr(data_obj, "id", "")

        if donation_id:
            _confirm_donation_in_db(db, int(donation_id), f"STRIPE-{session_id}")

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