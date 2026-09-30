from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.session import Base, engine
from app.routers import verification, missions, donations, payouts, accountability

# Create SQLite tables on startup
Base.metadata.create_all(bind=engine)

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

# Register API Routers
app.include_router(verification.router)
app.include_router(missions.router)
app.include_router(donations.router)
app.include_router(payouts.router)
app.include_router(accountability.router)


@app.get("/")
def health_check():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "stellar_network": settings.STELLAR_NETWORK
    }