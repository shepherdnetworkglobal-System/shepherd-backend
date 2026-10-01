"""
Seeds the database with a realistic demo missionary, active mission,
donations, field receipts, and milestone updates.
Run once: python seed_demo.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database.session import SessionLocal, Base, engine
from app.models.models import (
    User, UserRole, MissionaryProfile, VerificationStatus,
    Mission, MissionStatus, Donation, DonationStatus,
    Receipt, MilestoneUpdate, PastProject,
    AffiliationPath, RiskTier, LayerStatus,
    UnderfundingRule, OverfundingRule
)
from app.core.security import get_password_hash
from decimal import Decimal

Base.metadata.create_all(bind=engine)
db = SessionLocal()

def run_demo_seed(db_session=None):
    close_session_at_end = False
    if db_session is None:
        db_session = SessionLocal()
        close_session_at_end = True

    try:
        # ─── 1. Create or Get Missionary User ───
        missionary_email = "joseph.mwangi@shepherd.network"
        missionary_user = db_session.query(User).filter(User.email == missionary_email).first()
        if not missionary_user:
            missionary_user = User(
                email=missionary_email,
                hashed_password=get_password_hash("Missionary2026!"),
                full_name="Joseph Mwangi",
                role=UserRole.MISSIONARY,
                email_verified=True,
                phone_verified=True
            )
            db_session.add(missionary_user)
            db_session.commit()
            db_session.refresh(missionary_user)

        # ─── 2. Create or Update Verified Missionary Profile ───
        profile = db_session.query(MissionaryProfile).filter(MissionaryProfile.user_id == missionary_user.id).first()
        if not profile:
            profile = MissionaryProfile(user_id=missionary_user.id, country="Kenya")

        profile.shepherd_id = "JOSEPH-KENYA-1042"
        profile.country = "Kenya"
        profile.organization_name = "Turkana Hope Ministries"
        profile.organization_cert_url = "https://images.unsplash.com/photo-1532629345422-7515f3d16bb6?w=800"
        profile.government_id_url = "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=800"
        profile.selfie_url = "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400"
        profile.proof_of_address_url = "https://images.unsplash.com/photo-1489392191049-fc10c97e64b6?w=800"
        profile.profile_photo_url = "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600"
        profile.biography = (
            "Joseph Mwangi was born in Nakuru, Kenya, and raised in a family of seven children. "
            "After completing his degree in Community Development at Moi University in 2014, "
            "he felt a deep calling to serve the most marginalized communities in Northern Kenya. "
            "In 2016, Joseph moved to Lodwar in Turkana County — one of the driest and most "
            "underserved regions in East Africa. What began as a short-term mission trip became "
            "a lifelong commitment. He founded Turkana Hope Ministries in 2018 with a focus on "
            "clean water access, children's education, and community health. Joseph lives in Lodwar "
            "with his wife Grace and their two children. He speaks fluent Swahili, Turkana, and English. "
            "His life verse is Isaiah 58:11 — 'The Lord will guide you always; he will satisfy your "
            "needs in a sun-scorched land.'"
        )
        profile.years_of_service = 8
        profile.calling_description = "Clean water access and community development among the Turkana people of Northern Kenya."
        profile.stellar_payout_address = "GCEZWKCA5VLDNRLN3RPRJMRZOX3Z6G5CHCGSNFHEYVXM3XOJMDS674JZ"
        profile.mpesa_phone_number = "+254712345678"
        profile.verification_status = VerificationStatus.APPROVED
        profile.affiliation_path = AffiliationPath.ORG_AFFILIATED
        profile.risk_tier = RiskTier.STANDARD
        profile.identity_layer_status = LayerStatus.APPROVED
        profile.address_layer_status = LayerStatus.APPROVED
        profile.affiliation_layer_status = LayerStatus.APPROVED
        profile.organization_layer_status = LayerStatus.APPROVED
        profile.payout_layer_status = LayerStatus.APPROVED
        profile.mission_layer_status = LayerStatus.APPROVED
        profile.history_layer_status = LayerStatus.APPROVED
        profile.badge_identity_verified = True
        profile.badge_org_verified = True
        profile.badge_payout_verified = True
        profile.badge_mission_verified = True
        profile.admin_notes = "Verified by Shepherd Admin. Active in Turkana County since 2016. Partnered with Lodwar Diocese."

        db_session.add(profile)
        db_session.commit()
        db_session.refresh(profile)

        # ─── 3. Create or Update Active Mission ───
        mission = db_session.query(Mission).filter(Mission.missionary_id == profile.id).first()
        if not mission:
            mission = Mission(
                missionary_id=profile.id,
                title="Clean Water Wells — Turkana East, Kenya",
                goal_amount_usd=Decimal("18000.00"),
                target_country="Kenya"
            )

        mission.title = "Clean Water Wells — Turkana East, Kenya"
        mission.description = (
            "Turkana East is one of the most water-scarce regions in Kenya. "
            "Families walk 8-12 km daily to collect contaminated water from seasonal riverbeds. "
            "This mission aims to drill 3 solar-powered boreholes serving 5 villages "
            "with an estimated combined population of 4,200 people. "
            "Each borehole includes a solar pump, 10,000L storage tank, and community tap stand. "
            "Phase 1 (Well #1) is complete. Phase 2 (Well #2) is currently underway. "
            "Phase 3 (Well #3) begins once funding is secured."
        )
        mission.goal_amount_usd = Decimal("18000.00")
        mission.raised_amount_usd = Decimal("11240.00")
        mission.target_country = "Kenya"
        mission.location_granularity = "Turkana East Sub-County"
        mission.exact_location_hidden = False
        mission.local_partners = "Lodwar Diocese, Turkana Water Ministry, Kenya Red Cross"
        mission.underfunding_rule = UnderfundingRule.HOLD_UNTIL_THRESHOLD
        mission.overfunding_rule = OverfundingRule.EXPAND_SCOPE
        mission.reporting_plan = "Monthly photo evidence, bi-weekly water quality reports, quarterly audited receipts."
        mission.status = MissionStatus.ACTIVE

        db_session.add(mission)
        db_session.commit()
        db_session.refresh(mission)

        # ─── 4. Seed Donations (if none exist) ───
        existing_donations = db_session.query(Donation).filter(Donation.mission_id == mission.id).first()
        if not existing_donations:
            donors = [
                ("sarah.johnson@gmail.com", Decimal("250.00"), "USDC", "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"),
                ("mike.chen@yahoo.com", Decimal("500.00"), "USDC", "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3"),
                ("grace.obi@outlook.com", Decimal("1000.00"), "USDC", "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"),
                ("david.kim@gmail.com", Decimal("150.00"), "XLM", "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5"),
                ("rachel.smith@gmail.com", Decimal("2000.00"), "USDC", "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6"),
                ("emmanuel.adeyemi@gmail.com", Decimal("750.00"), "USDC", "f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1"),
                ("lisa.park@gmail.com", Decimal("100.00"), "USDC", "a1c2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2"),
                ("james.wilson@yahoo.com", Decimal("3500.00"), "USDC", "b2d3f4a5c6e7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3"),
                ("anna.mueller@gmail.com", Decimal("490.00"), "USDC", "c3e4a5b6d7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4"),
                ("peter.ngugi@gmail.com", Decimal("2500.00"), "USDC", "d4f5b6c7e8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5"),
            ]

            for email, amount, asset, tx_hash in donors:
                donation = Donation(
                    mission_id=mission.id,
                    donor_email=email,
                    amount_usd=amount,
                    asset_type=asset,
                    stellar_tx_hash=tx_hash,
                    status=DonationStatus.CONFIRMED_ONCHAIN
                )
                db_session.add(donation)
            db_session.commit()

        # ─── 5. Seed Field Receipts (if none exist) ───
        existing_receipts = db_session.query(Receipt).filter(Receipt.mission_id == mission.id).first()
        if not existing_receipts:
            receipts_data = [
                ("Borehole Drilling — Phase 1 (Well #1)", Decimal("4200.00"), "Equipment", "Lodwar Heavy Works Ltd", "Complete drilling to 120m depth including casing and gravel pack."),
                ("Solar Water Pump & Controller", Decimal("1850.00"), "Equipment", "Davis & Shirtliff Kenya", "Lorentz PS2-150 solar pump with 4x 330W panels."),
                ("10,000L Polyethylene Storage Tank", Decimal("680.00"), "Materials", "Roto Tanks Kenya", "Transported from Nairobi to Lodwar via flatbed truck."),
                ("PVC Piping & Fittings (2km)", Decimal("420.00"), "Materials", "Turkana Hardware Supplies", "110mm main line from borehole to village tap stand."),
                ("Community Tap Stand Construction", Decimal("350.00"), "Labor", "Local Turkana Masons", "4-tap concrete stand with drainage soak pit."),
                ("Fuel & Transport — Phase 1", Decimal("280.00"), "Transport", "Turkana Fuel Depot", "Diesel for drilling rig and supply truck over 14 days."),
                ("Water Quality Testing Kit", Decimal("120.00"), "Materials", "Nairobi Lab Services", "WHO-standard field testing for bacteria, fluoride, and salinity."),
            ]

            for title, amount, category, vendor, notes in receipts_data:
                receipt = Receipt(
                    mission_id=mission.id,
                    title=title,
                    amount_spent_usd=amount,
                    category=category,
                    receipt_image_url="https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=600",
                    vendor_name=vendor,
                    notes=notes
                )
                db_session.add(receipt)
            db_session.commit()

        # ─── 6. Seed Milestone Updates (if none exist) ───
        existing_milestones = db_session.query(MilestoneUpdate).filter(MilestoneUpdate.mission_id == mission.id).first()
        if not existing_milestones:
            milestones_data = [
                (
                    "Phase 1 Complete — Well #1 Flowing!",
                    "After 14 days of drilling, we hit clean water at 118 meters. The solar pump is installed and the community tap stand is operational. Over 800 people from Napetet village now have access to clean water within a 5-minute walk. The women who previously walked 10km daily are in tears of joy.",
                    "https://images.unsplash.com/photo-1541544181051-e46607bc22a4?w=800",
                    800
                ),
                (
                    "Phase 2 Groundbreaking — Well #2 Started",
                    "We broke ground on the second borehole at Kalokol village this week. The drilling rig arrived from Lodwar and the community has prepared the site. Expected completion in 10-14 days. This well will serve approximately 1,200 people across three sub-villages.",
                    "https://images.unsplash.com/photo-1594398901394-4e34939a02eb?w=800",
                    1200
                ),
                (
                    "Community Health Training Completed",
                    "Conducted a 3-day water sanitation and hygiene (WASH) training for 45 community health volunteers across Napetet and Kalokol. Topics covered: safe water storage, handwashing stations, and latrine maintenance. Each volunteer received a hygiene kit to distribute to 20 households.",
                    "https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?w=800",
                    900
                ),
            ]

            for title, desc, photo, people in milestones_data:
                update = MilestoneUpdate(
                    mission_id=mission.id,
                    title=title,
                    description=desc,
                    photo_url=photo,
                    people_served=people
                )
                db_session.add(update)
            db_session.commit()

        # ─── 7. Seed Past Projects (if none exist) ───
        existing_past_projects = db_session.query(PastProject).filter(PastProject.missionary_id == profile.id).first()
        if not existing_past_projects:
            past_projects_data = [
                (
                    "Lodwar Primary School Water Tank",
                    "Installed a 20,000L rainwater harvesting system at Lodwar Primary School serving 450 students. The school previously relied on a single hand-dug well that dried up every January. The new system captures rooftop rainwater during the two rainy seasons and stores enough to last through the dry months. Includes a first-flush diverter and biosand filter for safe drinking water.",
                    "Lodwar Town, Turkana County",
                    2019,
                    450,
                    "https://images.unsplash.com/photo-1594398901394-4e34939a02eb?w=600,https://images.unsplash.com/photo-1541544181051-e46607bc22a4?w=600"
                ),
                (
                    "Napetet Women's Microfinance Cooperative",
                    "Established a savings and loan cooperative for 60 Turkana women. Provided initial seed capital of $3,000 and 6 months of financial literacy training. The cooperative now runs independently and has funded 23 small businesses including beadwork, goat trading, and solar lantern resale. Average household income among members has increased by 40%.",
                    "Napetet Village, Turkana East",
                    2020,
                    320,
                    "https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?w=600,https://images.unsplash.com/photo-1532629345422-7515f3d16bb6?w=600"
                ),
                (
                    "Kalokol Health Clinic Solar Electrification",
                    "Partnered with Kenya Red Cross to install a 5kW solar power system at Kalokol Community Health Clinic. The clinic previously operated without electricity, making nighttime deliveries and vaccine storage impossible. The solar system powers lights, a vaccine refrigerator, and a water pump. The clinic now serves 2,000+ patients monthly and has reduced infant mortality in the area by an estimated 15%.",
                    "Kalokol, Turkana South",
                    2021,
                    2000,
                    "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=600,https://images.unsplash.com/photo-1559757175-5700dde675bc?w=600"
                ),
                (
                    "Turkana Children's Feeding Program",
                    "Launched a daily school feeding program across 4 primary schools during the 2022 drought crisis. Partnered with World Food Programme for grain supply and local Turkana women for cooking. At peak operation, the program provided 1,800 meals per day for 8 months. School attendance increased by 60% during the program period.",
                    "Turkana East Sub-County",
                    2022,
                    1800,
                    "https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?w=600,https://images.unsplash.com/photo-1509099836639-18ba1795216d?w=600"
                ),
            ]

            for title, desc, location, year, people, media in past_projects_data:
                project = PastProject(
                    missionary_id=profile.id,
                    title=title,
                    description=desc,
                    location=location,
                    year_completed=year,
                    people_impacted=people,
                    media_urls=media
                )
                db_session.add(project)
            db_session.commit()

        print(">>> Demo Data Seeded Successfully!")
    finally:
        if close_session_at_end:
            db_session.close()

if __name__ == "__main__":
    run_demo_seed()