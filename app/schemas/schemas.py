from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from app.models.models import (
    UserRole,
    VerificationStatus,
    MissionStatus,
    DonationStatus,
    AffiliationPath,
    RiskTier,
    LayerStatus,
    CaseDecision,
    PayoutMethodType,
    UnderfundingRule,
    OverfundingRule
)


# --- User & Auth Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.DONOR


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: str
    role: UserRole


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    email_verified: bool = False
    phone_verified: bool = False
    mfa_enrolled: bool = False
    terms_consented_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Organization & Sub-entity Schemas ---
class OrganizationCreate(BaseModel):
    official_name: str
    registry_id: Optional[str] = None
    entity_type: Optional[str] = None
    official_domain: Optional[str] = None
    official_contact_email: Optional[EmailStr] = None
    gov_docs_url: Optional[str] = None
    auth_rep_name: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: int
    official_name: str
    registry_id: Optional[str]
    entity_type: Optional[str]
    official_domain: Optional[str]
    official_contact_email: Optional[str]
    gov_docs_url: Optional[str]
    auth_rep_name: Optional[str]
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MissionaryReferenceCreate(BaseModel):
    missionary_id: int
    ref_name: str
    ref_type: str
    email: Optional[str] = None
    phone: Optional[str] = None
    relationship: Optional[str] = None


class MissionaryReferenceResponse(BaseModel):
    id: int
    missionary_id: int
    ref_name: str
    ref_type: str
    email: Optional[str]
    phone: Optional[str]
    relationship: Optional[str]
    verification_notes: Optional[str]
    is_confirmed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PayoutDestinationCreate(BaseModel):
    missionary_id: int
    method_type: PayoutMethodType
    destination_account: str
    currency: str = "USD"
    is_primary: bool = False


class PayoutDestinationResponse(BaseModel):
    id: int
    missionary_id: int
    method_type: PayoutMethodType
    destination_account: str
    currency: str
    is_primary: bool
    is_verified: bool
    cooling_period_ends_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class VerificationCaseCreate(BaseModel):
    missionary_id: int
    layer: str
    reviewer_notes: Optional[str] = None
    structured_exceptions: Optional[str] = None
    decision: CaseDecision


class VerificationCaseResponse(BaseModel):
    id: int
    missionary_id: int
    layer: str
    reviewer_id: Optional[int]
    reviewer_notes: Optional[str]
    structured_exceptions: Optional[str]
    decision: CaseDecision
    created_at: datetime

    class Config:
        from_attributes = True


class RiskScreeningResponse(BaseModel):
    id: int
    missionary_id: int
    screening_type: str
    risk_score: int
    flags_json: Optional[str]
    reviewed_by: Optional[int]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Missionary Profile / Verification Schemas ---
class MissionaryProfileCreate(BaseModel):
    user_id: int
    country: str
    affiliation_path: AffiliationPath = AffiliationPath.INDEPENDENT
    organization_name: Optional[str] = None
    stellar_payout_address: Optional[str] = None
    mpesa_phone_number: Optional[str] = None
    profile_photo_url: Optional[str] = None
    biography: Optional[str] = None
    years_of_service: int = 0
    calling_description: Optional[str] = None


class PastProjectCreate(BaseModel):
    missionary_id: int
    title: str
    description: str
    location: Optional[str] = None
    year_completed: Optional[int] = None
    people_impacted: int = 0
    media_urls: Optional[str] = None


class PastProjectResponse(BaseModel):
    id: int
    missionary_id: int
    title: str
    description: str
    location: Optional[str]
    year_completed: Optional[int]
    people_impacted: int
    media_urls: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MissionaryDocumentUpload(BaseModel):
    organization_cert_url: Optional[str] = None
    government_id_url: Optional[str] = None
    selfie_url: Optional[str] = None
    proof_of_address_url: Optional[str] = None


class AdminVerificationReview(BaseModel):
    status: VerificationStatus
    admin_notes: Optional[str] = None
    shepherd_id: Optional[str] = None
    affiliation_path: Optional[AffiliationPath] = None
    risk_tier: Optional[RiskTier] = None
    identity_layer_status: Optional[LayerStatus] = None
    address_layer_status: Optional[LayerStatus] = None
    affiliation_layer_status: Optional[LayerStatus] = None
    organization_layer_status: Optional[LayerStatus] = None
    payout_layer_status: Optional[LayerStatus] = None
    mission_layer_status: Optional[LayerStatus] = None
    history_layer_status: Optional[LayerStatus] = None
    badge_identity_verified: Optional[bool] = None
    badge_org_verified: Optional[bool] = None
    badge_payout_verified: Optional[bool] = None
    badge_mission_verified: Optional[bool] = None


class MissionaryProfileResponse(BaseModel):
    id: int
    user_id: int
    shepherd_id: Optional[str]
    organization_id: Optional[int]
    country: str
    organization_name: Optional[str]
    organization_cert_url: Optional[str]
    government_id_url: Optional[str]
    selfie_url: Optional[str]
    proof_of_address_url: Optional[str]
    profile_photo_url: Optional[str]
    biography: Optional[str]
    years_of_service: int
    calling_description: Optional[str]
    stellar_payout_address: Optional[str]
    mpesa_phone_number: Optional[str]
    
    affiliation_path: AffiliationPath
    risk_tier: RiskTier
    
    identity_layer_status: LayerStatus
    address_layer_status: LayerStatus
    affiliation_layer_status: LayerStatus
    organization_layer_status: LayerStatus
    payout_layer_status: LayerStatus
    mission_layer_status: LayerStatus
    history_layer_status: LayerStatus

    badge_identity_verified: bool
    badge_org_verified: bool
    badge_payout_verified: bool
    badge_mission_verified: bool

    verification_status: VerificationStatus
    admin_notes: Optional[str]
    last_reviewed_at: Optional[datetime]
    next_review_due: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MissionaryPublicProfile(BaseModel):
    id: int
    shepherd_id: Optional[str]
    full_name: str
    country: str
    organization_name: Optional[str]
    profile_photo_url: Optional[str]
    biography: Optional[str]
    years_of_service: int
    calling_description: Optional[str]
    verification_status: VerificationStatus
    affiliation_path: AffiliationPath
    risk_tier: RiskTier
    badge_identity_verified: bool
    badge_org_verified: bool
    badge_payout_verified: bool
    badge_mission_verified: bool
    active_missions: list
    past_projects: List[PastProjectResponse]
    total_funds_deployed: Decimal
    total_people_served: int

    class Config:
        from_attributes = True


# --- Mission Schemas ---
class MissionCreate(BaseModel):
    missionary_id: int
    title: str
    description: str
    goal_amount_usd: Decimal
    target_country: str
    location_granularity: Optional[str] = None
    exact_location_hidden: bool = False
    local_partners: Optional[str] = None
    underfunding_rule: UnderfundingRule = UnderfundingRule.HOLD_UNTIL_THRESHOLD
    overfunding_rule: OverfundingRule = OverfundingRule.EXPAND_SCOPE
    reporting_plan: Optional[str] = None


class MissionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[MissionStatus] = None
    underfunding_rule: Optional[UnderfundingRule] = None
    overfunding_rule: Optional[OverfundingRule] = None
    exact_location_hidden: Optional[bool] = None
    location_granularity: Optional[str] = None
    reporting_plan: Optional[str] = None
    local_partners: Optional[str] = None


from pydantic import field_validator

class MissionResponse(BaseModel):
    id: int
    missionary_id: int
    title: str
    description: str
    goal_amount_usd: Decimal
    raised_amount_usd: Decimal
    target_country: str
    location_granularity: Optional[str] = None
    exact_location_hidden: Optional[bool] = False
    local_partners: Optional[str] = None
    underfunding_rule: Optional[str] = "HOLD_UNTIL_THRESHOLD"
    overfunding_rule: Optional[str] = "EXPAND_SCOPE"
    reporting_plan: Optional[str] = None
    status: str = "ACTIVE"
    created_at: datetime

    @field_validator("status", "underfunding_rule", "overfunding_rule", mode="before")
    def clean_enum_string(cls, v):
        if hasattr(v, "value"):
            return str(v.value)
        if isinstance(v, str) and "." in v:
            return v.split(".")[-1]
        return str(v) if v is not None else v

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