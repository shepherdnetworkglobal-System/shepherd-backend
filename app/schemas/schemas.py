from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.models import UserRole, VerificationStatus, MissionStatus, DonationStatus


# --- User Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.DONOR


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


# --- Missionary Profile / Verification Schemas ---
class MissionaryProfileCreate(BaseModel):
    user_id: int
    country: str
    organization_name: Optional[str] = None
    stellar_payout_address: Optional[str] = None
    mpesa_phone_number: Optional[str] = None


class MissionaryDocumentUpload(BaseModel):
    organization_cert_url: Optional[str] = None
    government_id_url: Optional[str] = None
    selfie_url: Optional[str] = None
    proof_of_address_url: Optional[str] = None


class AdminVerificationReview(BaseModel):
    status: VerificationStatus
    admin_notes: Optional[str] = None
    shepherd_id: Optional[str] = None


class MissionaryProfileResponse(BaseModel):
    id: int
    user_id: int
    shepherd_id: Optional[str]
    country: str
    organization_name: Optional[str]
    organization_cert_url: Optional[str]
    government_id_url: Optional[str]
    selfie_url: Optional[str]
    proof_of_address_url: Optional[str]
    stellar_payout_address: Optional[str]
    mpesa_phone_number: Optional[str]
    verification_status: VerificationStatus
    admin_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Mission Schemas ---
class MissionCreate(BaseModel):
    missionary_id: int
    title: str
    description: str
    goal_amount_usd: Decimal
    target_country: str


class MissionResponse(BaseModel):
    id: int
    missionary_id: int
    title: str
    description: str
    goal_amount_usd: Decimal
    raised_amount_usd: Decimal
    target_country: str
    status: MissionStatus
    created_at: datetime

    class Config:
        from_attributes = True


# --- Donation & Payment Wall Schemas ---
class DonationCreate(BaseModel):
    mission_id: int
    donor_email: EmailStr
    amount_usd: Decimal
    asset_type: str = "USDC"


class DonationVerify(BaseModel):
    donation_id: int
    stellar_tx_hash: str


class DonationResponse(BaseModel):
    id: int
    mission_id: int
    donor_email: str
    amount_usd: Decimal
    asset_type: str
    stellar_tx_hash: Optional[str]
    status: DonationStatus
    created_at: datetime

    class Config:
        from_attributes = True


# --- Accountability & Transparency Schemas ---
class ReceiptCreate(BaseModel):
    mission_id: int
    title: str
    amount_spent_usd: Decimal
    category: str
    receipt_image_url: str
    vendor_name: Optional[str] = None
    notes: Optional[str] = None


class ReceiptResponse(BaseModel):
    id: int
    mission_id: int
    title: str
    amount_spent_usd: Decimal
    category: str
    receipt_image_url: str
    vendor_name: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MilestoneUpdateCreate(BaseModel):
    mission_id: int
    title: str
    description: str
    photo_url: Optional[str] = None
    people_served: int = 0


class MilestoneUpdateResponse(BaseModel):
    id: int
    mission_id: int
    title: str
    description: str
    photo_url: Optional[str]
    people_served: int
    created_at: datetime

    class Config:
        from_attributes = True