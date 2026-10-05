import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import Base, engine, SessionLocal
from app.models.models import User, UserRole
from app.core.security import get_password_hash
from app.routers import auth, verification, missions, donations, payouts, accountability, uploads, platform

from sqlalchemy import text

# Create missing tables on startup
Base.metadata.create_all(bind=engine)


def run_migrations():
    """Safely append missing columns to existing tables in PostgreSQL without dropping data."""
    migration_statements = [
        # Users table updates
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE NOT NULL;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE NOT NULL;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enrolled BOOLEAN DEFAULT FALSE NOT NULL;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_consented_at TIMESTAMP;",

        # Missionary profiles table updates
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS organization_id INTEGER;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS affiliation_path VARCHAR(50) DEFAULT 'INDEPENDENT' NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS risk_tier VARCHAR(50) DEFAULT 'STANDARD' NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS identity_layer_status VARCHAR(50) DEFAULT 'NOT_STARTED' NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS address_layer_status VARCHAR(50) DEFAULT 'NOT_STARTED' NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS affiliation_layer_status VARCHAR(50) DEFAULT 'NOT_STARTED' NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS organization_layer_status VARCHAR(50) DEFAULT 'NOT_STARTED' NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS payout_layer_status VARCHAR(50) DEFAULT 'NOT_STARTED' NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS mission_layer_status VARCHAR(50) DEFAULT 'NOT_STARTED' NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS history_layer_status VARCHAR(50) DEFAULT 'NOT_STARTED' NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS badge_identity_verified BOOLEAN DEFAULT FALSE NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS badge_org_verified BOOLEAN DEFAULT FALSE NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS badge_payout_verified BOOLEAN DEFAULT FALSE NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS badge_mission_verified BOOLEAN DEFAULT FALSE NOT NULL;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS last_reviewed_at TIMESTAMP;",
        "ALTER TABLE missionary_profiles ADD COLUMN IF NOT EXISTS next_review_due TIMESTAMP;",

        # Organization table updates
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS country VARCHAR(100);",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500);",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS website VARCHAR(255);",

        # Donations table updates
        "ALTER TABLE donations ADD COLUMN IF NOT EXISTS donor_name VARCHAR(255);",
        "ALTER TABLE donations ALTER COLUMN donor_email DROP NOT NULL;",
        "ALTER TABLE donations ADD COLUMN IF NOT EXISTS progress_opt_in BOOLEAN DEFAULT FALSE NOT NULL;",

        # Convert legacy PostgreSQL native Enum columns to standard VARCHAR
        "ALTER TABLE missions ALTER COLUMN status TYPE VARCHAR(50) USING status::text;",
        "ALTER TABLE missions ALTER COLUMN underfunding_rule TYPE VARCHAR(100) USING underfunding_rule::text;",
        "ALTER TABLE missions ALTER COLUMN overfunding_rule TYPE VARCHAR(100) USING overfunding_rule::text;",

        # Mission table updates
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS map_location VARCHAR(255);",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS location_granularity VARCHAR(100);",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS exact_location_hidden BOOLEAN DEFAULT FALSE NOT NULL;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS problem_statement TEXT;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS mission_objectives TEXT;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS proposed_process TEXT;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS before_gallery_images TEXT;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS beneficiary_group VARCHAR(255);",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS expected_duration VARCHAR(100);",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS start_date TIMESTAMP;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS expected_end_date TIMESTAMP;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS estimated_total_cost NUMERIC(12,2);",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS local_partners TEXT;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS underfunding_rule VARCHAR(50) DEFAULT 'HOLD_UNTIL_THRESHOLD' NOT NULL;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS overfunding_rule VARCHAR(50) DEFAULT 'EXPAND_SCOPE' NOT NULL;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS reporting_plan TEXT;",

        # Coalition & Budget Tables Safeguard
        """
        CREATE TABLE IF NOT EXISTS mission_coalition_partners (
            id SERIAL PRIMARY KEY,
            mission_id INTEGER NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
            organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
            missionary_id INTEGER REFERENCES missionary_profiles(id) ON DELETE SET NULL,
            partner_role VARCHAR(50) DEFAULT 'CO_SPONSOR' NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS mission_budget_items (
            id SERIAL PRIMARY KEY,
            mission_id INTEGER NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
            item_name VARCHAR(255) NOT NULL,
            category VARCHAR(100) DEFAULT 'EQUIPMENT' NOT NULL,
            quantity NUMERIC(12, 2) DEFAULT 1.0 NOT NULL,
            unit_cost_usd NUMERIC(12, 2) NOT NULL,
            total_cost_usd NUMERIC(12, 2) NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,

        # Database Sanitization (Clean corrupted Enum prefixes in PostgreSQL)
        "UPDATE missions SET status = 'ACTIVE' WHERE status LIKE '%ACTIVE%' OR status IS NULL;",
        "UPDATE missions SET status = 'COMPLETED' WHERE status LIKE '%COMPLETED%';",
        "UPDATE missions SET status = 'PAUSED' WHERE status LIKE '%PAUSED%';",
        "UPDATE missions SET underfunding_rule = 'HOLD_UNTIL_THRESHOLD' WHERE underfunding_rule LIKE '%HOLD%' OR underfunding_rule IS NULL;",
        "UPDATE missions SET overfunding_rule = 'EXPAND_SCOPE' WHERE overfunding_rule LIKE '%EXPAND%' OR overfunding_rule IS NULL;",
        "UPDATE missionary_profiles SET verification_status = 'APPROVED' WHERE verification_status LIKE '%APPROVED%' OR verification_status IS NULL;"
    ]

    for stmt in migration_statements:
        with engine.begin() as conn:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                print(f"Migration note ({stmt[:40]}...): {e}")


def seed_admin():
    db: Session = SessionLocal()
    try:
        admin_email = "admin@shepherd.network"
        existing = db.query(User).filter(User.email == admin_email).first()
        if not existing:
            admin_user = User(
                email=admin_email,
                hashed_password=get_password_hash("ShepherdAdmin2026!"),
                full_name="System Administrator",
                role=UserRole.ADMIN
            )
            db.add(admin_user)
            db.commit()
            print(">>> Default Admin Seeded: admin@shepherd.network / ShepherdAdmin2026!")
    finally:
        db.close()


# Demo seeder removed for production live-data mode
run_migrations()
seed_admin()

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    redirect_slashes=False
)

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all Routers
app.include_router(auth.router)
app.include_router(verification.router)
app.include_router(missions.router)
app.include_router(donations.router)
app.include_router(payouts.router)
app.include_router(accountability.router)
app.include_router(uploads.router)
app.include_router(platform.router)

# Serve uploaded files
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def health_check():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "stellar_network": settings.STELLAR_NETWORK
    }