import os
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.models import User, MissionaryProfile, Mission, Donation, Receipt, MilestoneUpdate, PastProject, UserRole

def wipe_all_except_admin():
    db: Session = SessionLocal()
    try:
        print("Wiping demo data...")
        db.query(Donation).delete()
        db.query(Receipt).delete()
        db.query(MilestoneUpdate).delete()
        db.query(PastProject).delete()
        db.query(Mission).delete()
        db.query(MissionaryProfile).delete()
        # Delete all users EXCEPT the admin
        db.query(User).filter(User.role != UserRole.ADMIN).delete()
        
        db.commit()
        print("Wipe complete! The database is now empty and ready for live data.")
    except Exception as e:
        db.rollback()
        print(f"Error wiping data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    wipe_all_except_admin()