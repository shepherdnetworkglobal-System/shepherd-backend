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

# Create SQLite tables on startup
Base.metadata.create_all(bind=engine)


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