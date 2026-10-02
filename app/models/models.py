import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship

from app.database.session import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MISSIONARY = "MISSIONARY"
    DONOR = "DONOR"


class VerificationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    INFO_REQUESTED = "INFO_REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AffiliationPath(str, enum.Enum):
    ORG_AFFILIATED = "ORG_AFFILIATED"
    INDEPENDENT = "INDEPENDENT"


class RiskTier(str, enum.Enum):
    LOW = "LOW"
    STANDARD = "STANDARD"
    ELEVATED = "ELEVATED"
    RESTRICTED = "RESTRICTED"


class LayerStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    INFO_REQUESTED = "INFO_REQUESTED"
    ESCALATED = "ESCALATED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


class CaseDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    INFO_REQUESTED = "INFO_REQUESTED"
    ESCALATED = "ESCALATED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class PayoutMethodType(str, enum.Enum):
    STELLAR_USDC = "STELLAR_USDC"
    MPESA = "MPESA"
    BANK_TRANSFER = "BANK_TRANSFER"
    MONEYGRAM = "MONEYGRAM"


class UnderfundingRule(str, enum.Enum):
    HOLD_UNTIL_THRESHOLD = "HOLD_UNTIL_THRESHOLD"
    REFUND = "REFUND"
    REDIRECT_APPROVED_MISSION = "REDIRECT_APPROVED_MISSION"


class OverfundingRule(str, enum.Enum):
    EXPAND_SCOPE = "EXPAND_SCOPE"
    NEXT_MISSION_POOL = "NEXT_MISSION_POOL"
    RESERVE_FUND = "RESERVE_FUND"


class MissionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FUNDED = "FUNDED"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"


class DonationStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED_ONCHAIN = "CONFIRMED_ONCHAIN"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.DONOR, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    mfa_enrolled = Column(Boolean, default=False, nullable=False)
    terms_consented_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    missionary_profile = relationship("MissionaryProfile", back_populates="user", uselist=False)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    official_name = Column(String(255), nullable=False)
    registry_id = Column(String(100), nullable=True)
    entity_type = Column(String(100), nullable=True)
    official_domain = Column(String(255), nullable=True)
    official_contact_email = Column(String(255), nullable=True)
    gov_docs_url = Column(String(500), nullable=True)
    auth_rep_name = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    missionaries = relationship("MissionaryProfile", back_populates="organization")


class MissionaryProfile(Base):
    __tablename__ = "missionary_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    shepherd_id = Column(String(50), unique=True, index=True, nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    country = Column(String(100), nullable=False)
    organization_name = Column(String(255), nullable=True)
    organization_cert_url = Column(String(500), nullable=True)
    government_id_url = Column(String(500), nullable=True)
    selfie_url = Column(String(500), nullable=True)
    proof_of_address_url = Column(String(500), nullable=True)
    profile_photo_url = Column(String(500), nullable=True)
    biography = Column(Text, nullable=True)
    years_of_service = Column(Integer, default=0, nullable=False)
    calling_description = Column(Text, nullable=True)
    stellar_payout_address = Column(String(56), nullable=True)
    mpesa_phone_number = Column(String(20), nullable=True)
    
    # Layered Verification Architecture
    affiliation_path = Column(Enum(AffiliationPath), default=AffiliationPath.INDEPENDENT, nullable=False)
    risk_tier = Column(Enum(RiskTier), default=RiskTier.STANDARD, nullable=False)
    
    identity_layer_status = Column(Enum(LayerStatus), default=LayerStatus.NOT_STARTED, nullable=False)
    address_layer_status = Column(Enum(LayerStatus), default=LayerStatus.NOT_STARTED, nullable=False)
    affiliation_layer_status = Column(Enum(LayerStatus), default=LayerStatus.NOT_STARTED, nullable=False)
    organization_layer_status = Column(Enum(LayerStatus), default=LayerStatus.NOT_STARTED, nullable=False)
    payout_layer_status = Column(Enum(LayerStatus), default=LayerStatus.NOT_STARTED, nullable=False)
    mission_layer_status = Column(Enum(LayerStatus), default=LayerStatus.NOT_STARTED, nullable=False)
    history_layer_status = Column(Enum(LayerStatus), default=LayerStatus.NOT_STARTED, nullable=False)

    badge_identity_verified = Column(Boolean, default=False, nullable=False)
    badge_org_verified = Column(Boolean, default=False, nullable=False)
    badge_payout_verified = Column(Boolean, default=False, nullable=False)
    badge_mission_verified = Column(Boolean, default=False, nullable=False)

    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.DRAFT, nullable=False)
    admin_notes = Column(Text, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_due = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="missionary_profile")
    organization = relationship("Organization", back_populates="missionaries")
    missions = relationship("Mission", back_populates="missionary")
    past_projects = relationship("PastProject", back_populates="missionary", cascade="all, delete-orphan")
    references = relationship("MissionaryReference", back_populates="missionary", cascade="all, delete-orphan")
    payout_destinations = relationship("PayoutDestination", back_populates="missionary", cascade="all, delete-orphan")
    verification_cases = relationship("VerificationCase", back_populates="missionary", cascade="all, delete-orphan")
    risk_screenings = relationship("RiskScreening", back_populates="missionary", cascade="all, delete-orphan")


class MissionaryReference(Base):
    __tablename__ = "missionary_references"

    id = Column(Integer, primary_key=True, index=True)
    missionary_id = Column(Integer, ForeignKey("missionary_profiles.id"), nullable=False)
    ref_name = Column(String(255), nullable=False)
    ref_type = Column(String(50), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    ref_relationship = Column(String(255), nullable=True)
    verification_notes = Column(Text, nullable=True)
    is_confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    missionary = relationship("MissionaryProfile", back_populates="references")


class PayoutDestination(Base):
    __tablename__ = "payout_destinations"

    id = Column(Integer, primary_key=True, index=True)
    missionary_id = Column(Integer, ForeignKey("missionary_profiles.id"), nullable=False)
    method_type = Column(Enum(PayoutMethodType), nullable=False)
    destination_account = Column(String(255), nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    cooling_period_ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    missionary = relationship("MissionaryProfile", back_populates="payout_destinations")


class VerificationCase(Base):
    __tablename__ = "verification_cases"

    id = Column(Integer, primary_key=True, index=True)
    missionary_id = Column(Integer, ForeignKey("missionary_profiles.id"), nullable=False)
    layer = Column(String(50), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    structured_exceptions = Column(Text, nullable=True)
    decision = Column(Enum(CaseDecision), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    missionary = relationship("MissionaryProfile", back_populates="verification_cases")


class RiskScreening(Base):
    __tablename__ = "risk_screenings"

    id = Column(Integer, primary_key=True, index=True)
    missionary_id = Column(Integer, ForeignKey("missionary_profiles.id"), nullable=False)
    screening_type = Column(String(50), nullable=False)
    risk_score = Column(Integer, default=0, nullable=False)
    flags_json = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(50), default="CLEARED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    missionary = relationship("MissionaryProfile", back_populates="risk_screenings")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    target_resource = Column(String(255), nullable=False)
    old_value_json = Column(Text, nullable=True)
    new_value_json = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PastProject(Base):
    __tablename__ = "past_projects"

    id = Column(Integer, primary_key=True, index=True)
    missionary_id = Column(Integer, ForeignKey("missionary_profiles.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(200), nullable=True)
    year_completed = Column(Integer, nullable=True)
    people_impacted = Column(Integer, default=0, nullable=False)
    media_urls = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    missionary = relationship("MissionaryProfile", back_populates="past_projects")


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    missionary_id = Column(Integer, ForeignKey("missionary_profiles.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    goal_amount_usd = Column(Numeric(12, 2), nullable=False)
    raised_amount_usd = Column(Numeric(12, 2), default=0.00, nullable=False)
    target_country = Column(String(100), nullable=False)
    location_granularity = Column(String(100), nullable=True)
    exact_location_hidden = Column(Boolean, default=False, nullable=False)
    local_partners = Column(Text, nullable=True)
    underfunding_rule = Column(String(100), default="HOLD_UNTIL_THRESHOLD", nullable=False)
    overfunding_rule = Column(String(100), default="EXPAND_SCOPE", nullable=False)
    reporting_plan = Column(Text, nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    missionary = relationship("MissionaryProfile", back_populates="missions")
    donations = relationship("Donation", back_populates="mission")
    receipts = relationship("Receipt", back_populates="mission")
    updates = relationship("MilestoneUpdate", back_populates="mission")


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False)
    title = Column(String(255), nullable=False)
    amount_spent_usd = Column(Numeric(12, 2), nullable=False)
    category = Column(String(100), nullable=False)
    receipt_image_url = Column(String(500), nullable=False)
    vendor_name = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    mission = relationship("Mission", back_populates="receipts")


class MilestoneUpdate(Base):
    __tablename__ = "milestone_updates"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    photo_url = Column(String(500), nullable=True)
    people_served = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    mission = relationship("Mission", back_populates="updates")


class Donation(Base):
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False)
    donor_email = Column(String(255), nullable=False)
    amount_usd = Column(Numeric(12, 2), nullable=False)
    asset_type = Column(String(10), default="USDC", nullable=False)
    stellar_tx_hash = Column(String(64), unique=True, index=True, nullable=True)
    status = Column(Enum(DonationStatus), default=DonationStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    mission = relationship("Mission", back_populates="donations")