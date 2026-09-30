import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Enum
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
    created_at = Column(DateTime, default=datetime.utcnow)

    missionary_profile = relationship("MissionaryProfile", back_populates="user", uselist=False)


class MissionaryProfile(Base):
    __tablename__ = "missionary_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    shepherd_id = Column(String(50), unique=True, index=True, nullable=True)
    country = Column(String(100), nullable=False)
    organization_name = Column(String(255), nullable=True)
    organization_cert_url = Column(String(500), nullable=True)
    government_id_url = Column(String(500), nullable=True)
    selfie_url = Column(String(500), nullable=True)
    proof_of_address_url = Column(String(500), nullable=True)
    stellar_payout_address = Column(String(56), nullable=True)
    mpesa_phone_number = Column(String(20), nullable=True)
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.DRAFT, nullable=False)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="missionary_profile")
    missions = relationship("Mission", back_populates="missionary")


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    missionary_id = Column(Integer, ForeignKey("missionary_profiles.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    goal_amount_usd = Column(Numeric(12, 2), nullable=False)
    raised_amount_usd = Column(Numeric(12, 2), default=0.00, nullable=False)
    target_country = Column(String(100), nullable=False)
    status = Column(Enum(MissionStatus), default=MissionStatus.ACTIVE, nullable=False)
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