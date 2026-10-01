import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import Base, engine, SessionLocal
from app.models.models import User, UserRole
from app.core.security import get_password_hash
from app.routers import auth, verification, missions, donations, payouts, accountability, uploads

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

        # Missions table updates
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS location_granularity VARCHAR(100);",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS exact_location_hidden BOOLEAN DEFAULT FALSE NOT NULL;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS local_partners TEXT;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS underfunding_rule VARCHAR(50) DEFAULT 'HOLD_UNTIL_THRESHOLD' NOT NULL;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS overfunding_rule VARCHAR(50) DEFAULT 'EXPAND_SCOPE' NOT NULL;",
        "ALTER TABLE missions ADD COLUMN IF NOT EXISTS reporting_plan TEXT;"
    ]

    with engine.begin() as conn:
        for stmt in migration_statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                print(f"Migration note ({stmt}): {e}")


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


run_migrations()
seed_admin()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)

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