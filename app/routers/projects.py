from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.database.session import get_db
from app.models.models import (
    Mission, MissionBudgetItem, MissionCheckpoint, MissionFieldReport,
    MissionPayout, MissionRiskIncident, MissionPhoto, Receipt, Donation
)

router = APIRouter(prefix="/api/projects", tags=["Project Management (01.02)"])


# --- Schemas ---
class BudgetItemCreate(BaseModel):
    mission_id: int
    item_name: str
    category: str = "EQUIPMENT"
    quantity: float = 1.0
    unit_cost_usd: float
    vendor_name: Optional[str] = None
    notes: Optional[str] = None
    is_public: bool = True

class BudgetItemUpdate(BaseModel):
    item_name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit_cost_usd: Optional[float] = None
    actual_spent_usd: Optional[float] = None
    status: Optional[str] = None
    vendor_name: Optional[str] = None
    notes: Optional[str] = None
    is_public: Optional[bool] = None

class CheckpointCreate(BaseModel):
    mission_id: int
    title: str
    description: Optional[str] = None
    weight_percent: float = 0.0
    target_date: Optional[str] = None
    requires_photo: bool = True
    requires_report: bool = True
    is_public: bool = True

class CheckpointUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    weight_percent: Optional[float] = None
    status: Optional[str] = None
    target_date: Optional[str] = None
    completion_notes: Optional[str] = None
    photo_url: Optional[str] = None
    is_public: Optional[bool] = None

class FieldReportCreate(BaseModel):
    mission_id: int
    checkpoint_id: Optional[int] = None
    title: str
    body: str
    report_type: str = "WEEKLY"
    people_served_delta: int = 0
    is_public: bool = False
    author_name: Optional[str] = None

class PayoutCreate(BaseModel):
    mission_id: int
    budget_item_id: Optional[int] = None
    amount_usd: float
    recipient_wallet: Optional[str] = None
    recipient_name: Optional[str] = None
    stellar_tx_hash: Optional[str] = None
    purpose: Optional[str] = None
    status: str = "PENDING"
    is_public: bool = True

class RiskIncidentCreate(BaseModel):
    mission_id: int
    title: str
    description: str
    severity: str = "MEDIUM" # LOW, MEDIUM, HIGH
    resolution_plan: Optional[str] = None
    is_public: bool = False

class RiskIncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None # OPEN, MONITORING, RESOLVED, CLOSED
    resolution_plan: Optional[str] = None
    is_public: Optional[bool] = None

class PhotoUploadCreate(BaseModel):
    mission_id: int
    checkpoint_id: Optional[int] = None
    budget_item_id: Optional[int] = None
    image_url: str
    caption: Optional[str] = None
    category: str = "DURING"
    is_public: bool = True


# --- TAB 1: Dashboard Summary & Calculation Engine ---
@router.get("/summary/{mission_id}")
def get_project_summary(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Financial Meter Calculations
    total_raised = float(mission.raised_amount_usd or 0)
    
    budget_items = db.query(MissionBudgetItem).filter(MissionBudgetItem.mission_id == mission_id).all()
    total_budgeted = sum([float(b.total_cost_usd or 0) for b in budget_items])
    
    receipts = db.query(Receipt).filter(Receipt.mission_id == mission_id).all()
    total_verified_spent = sum([float(r.amount_spent_usd or 0) for r in receipts])

    payouts = db.query(MissionPayout).filter(MissionPayout.mission_id == mission_id).all()
    total_disbursed = sum([float(p.amount_usd or 0) for p in payouts if str(p.status).upper() in ("SENT", "CONFIRMED")])

    unallocated_balance = max(0.0, total_raised - total_budgeted)
    remaining_budget = max(0.0, total_budgeted - total_verified_spent)
    spend_rate_pct = round((total_verified_spent / total_budgeted * 100), 1) if total_budgeted > 0 else 0.0

    # Progress Checkpoint Weight Engine
    checkpoints = db.query(MissionCheckpoint).filter(MissionCheckpoint.mission_id == mission_id).all()
    completed_weight = sum([float(c.weight_percent or 0) for c in checkpoints if str(c.status).upper() == "COMPLETED"])
    total_weight = sum([float(c.weight_percent or 0) for c in checkpoints])
    progress_pct = min(100.0, round(completed_weight, 1))

    # Active Risk Alerts
    open_risks = db.query(MissionRiskIncident).filter(
        MissionRiskIncident.mission_id == mission_id,
        MissionRiskIncident.status != "RESOLVED"
    ).all()
    high_risk_count = sum(1 for r in open_risks if str(r.severity).upper() == "HIGH")

    return {
        "mission_id": mission_id,
        "title": mission.title,
        "target_country": mission.target_country,
        "status": str(mission.status),
        "donations_meter": {
            "total_raised_usd": total_raised,
            "total_budgeted_usd": total_budgeted,
            "total_verified_spent_usd": total_verified_spent,
            "total_disbursed_usd": total_disbursed,
            "unallocated_balance_usd": unallocated_balance,
            "remaining_budget_usd": remaining_budget,
            "spend_rate_pct": spend_rate_pct
        },
        "progress_meter": {
            "calculated_progress_pct": progress_pct,
            "checkpoints_total": len(checkpoints),
            "checkpoints_completed": sum(1 for c in checkpoints if str(c.status).upper() == "COMPLETED"),
            "total_weight_assigned": total_weight
        },
        "risk_alerts": {
            "open_risks_count": len(open_risks),
            "high_severity_count": high_risk_count,
            "has_critical_blocker": high_risk_count > 0
        },
        "counts": {
            "budget_items": len(budget_items),
            "receipts": len(receipts),
            "checkpoints": len(checkpoints),
            "photos": db.query(MissionPhoto).filter(MissionPhoto.mission_id == mission_id).count(),
            "field_reports": db.query(MissionFieldReport).filter(MissionFieldReport.mission_id == mission_id).count(),
            "payouts": len(payouts)
        }
    }


# --- TAB 2: Budget & Expenditure ---
@router.get("/budget/{mission_id}")
def list_budget_items(mission_id: int, db: Session = Depends(get_db)):
    items = db.query(MissionBudgetItem).filter(MissionBudgetItem.mission_id == mission_id).order_by(MissionBudgetItem.sort_order.asc(), MissionBudgetItem.id.asc()).all()
    return [
        {
            "id": b.id,
            "mission_id": b.mission_id,
            "item_name": b.item_name,
            "category": b.category,
            "quantity": float(b.quantity),
            "unit_cost_usd": float(b.unit_cost_usd),
            "total_cost_usd": float(b.total_cost_usd),
            "actual_spent_usd": float(b.actual_spent_usd),
            "variance_usd": float(b.actual_spent_usd) - float(b.total_cost_usd),
            "status": b.status,
            "vendor_name": b.vendor_name,
            "notes": b.notes,
            "is_public": b.is_public,
            "sort_order": b.sort_order,
            "created_at": b.created_at.isoformat() if b.created_at else None
        }
        for b in items
    ]

@router.post("/budget")
def create_budget_item(payload: BudgetItemCreate, db: Session = Depends(get_db)):
    total = float(payload.quantity) * float(payload.unit_cost_usd)
    item = MissionBudgetItem(
        mission_id=payload.mission_id,
        item_name=payload.item_name,
        category=payload.category,
        quantity=payload.quantity,
        unit_cost_usd=payload.unit_cost_usd,
        total_cost_usd=total,
        vendor_name=payload.vendor_name,
        notes=payload.notes,
        is_public=payload.is_public,
        status="PLANNED"
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"status": "success", "id": item.id, "total_cost_usd": total}

@router.put("/budget/{item_id}")
def update_budget_item(item_id: int, payload: BudgetItemUpdate, db: Session = Depends(get_db)):
    item = db.query(MissionBudgetItem).filter(MissionBudgetItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")

    if payload.item_name is not None: item.item_name = payload.item_name
    if payload.category is not None: item.category = payload.category
    if payload.quantity is not None: item.quantity = payload.quantity
    if payload.unit_cost_usd is not None: item.unit_cost_usd = payload.unit_cost_usd
    if payload.actual_spent_usd is not None: item.actual_spent_usd = payload.actual_spent_usd
    if payload.status is not None: item.status = payload.status
    if payload.vendor_name is not None: item.vendor_name = payload.vendor_name
    if payload.notes is not None: item.notes = payload.notes
    if payload.is_public is not None: item.is_public = payload.is_public

    item.total_cost_usd = float(item.quantity) * float(item.unit_cost_usd)
    db.commit()
    return {"status": "success", "id": item.id}

@router.delete("/budget/{item_id}")
def delete_budget_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MissionBudgetItem).filter(MissionBudgetItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    db.delete(item)
    db.commit()
    return {"status": "success", "message": "Budget item deleted"}


# --- TAB 4: Progress Checkpoints & Objectives Auto-Gen ---
@router.post("/checkpoints/autogen/{mission_id}")
def autogen_checkpoints_from_objectives(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission or not mission.mission_objectives:
        raise HTTPException(status_code=400, detail="Mission has no written objectives to generate from.")

    lines = [line.strip().lstrip("-•*1234567890. ") for line in mission.mission_objectives.split("\n") if line.strip()]
    if not lines:
        raise HTTPException(status_code=400, detail="No readable objective lines found.")

    default_weight = round(100.0 / len(lines), 1)
    created = []

    for idx, line in enumerate(lines):
        cp = MissionCheckpoint(
            mission_id=mission_id,
            title=line[:250],
            description=f"Objective #{idx + 1}: {line}",
            weight_percent=default_weight,
            status="PENDING",
            sort_order=idx,
            auto_generated=True
        )
        db.add(cp)
        created.append(line)

    db.commit()
    return {"status": "success", "count": len(created), "default_weight": default_weight}

@router.get("/checkpoints/{mission_id}")
def list_checkpoints(mission_id: int, db: Session = Depends(get_db)):
    checkpoints = db.query(MissionCheckpoint).filter(MissionCheckpoint.mission_id == mission_id).order_by(MissionCheckpoint.sort_order.asc(), MissionCheckpoint.id.asc()).all()
    return [
        {
            "id": c.id,
            "mission_id": c.mission_id,
            "title": c.title,
            "description": c.description,
            "weight_percent": float(c.weight_percent),
            "status": c.status,
            "target_date": c.target_date.isoformat() if c.target_date else None,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
            "requires_photo": c.requires_photo,
            "requires_report": c.requires_report,
            "completion_notes": c.completion_notes,
            "photo_url": c.photo_url,
            "is_public": c.is_public,
            "auto_generated": c.auto_generated,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in checkpoints
    ]

@router.post("/checkpoints")
def create_checkpoint(payload: CheckpointCreate, db: Session = Depends(get_db)):
    dt = datetime.fromisoformat(payload.target_date) if payload.target_date else None
    cp = MissionCheckpoint(
        mission_id=payload.mission_id,
        title=payload.title,
        description=payload.description,
        weight_percent=payload.weight_percent,
        target_date=dt,
        requires_photo=payload.requires_photo,
        requires_report=payload.requires_report,
        is_public=payload.is_public,
        status="PENDING"
    )
    db.add(cp)
    db.commit()
    db.refresh(cp)
    return {"status": "success", "id": cp.id}

@router.put("/checkpoints/{checkpoint_id}")
def update_checkpoint(checkpoint_id: int, payload: CheckpointUpdate, db: Session = Depends(get_db)):
    cp = db.query(MissionCheckpoint).filter(MissionCheckpoint.id == checkpoint_id).first()
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    if payload.title is not None: cp.title = payload.title
    if payload.description is not None: cp.description = payload.description
    if payload.weight_percent is not None: cp.weight_percent = payload.weight_percent
    if payload.status is not None:
        cp.status = payload.status
        if payload.status.upper() == "COMPLETED" and not cp.completed_at:
            cp.completed_at = datetime.utcnow()
    if payload.target_date is not None:
        cp.target_date = datetime.fromisoformat(payload.target_date) if payload.target_date else None
    if payload.completion_notes is not None: cp.completion_notes = payload.completion_notes
    if payload.photo_url is not None: cp.photo_url = payload.photo_url
    if payload.is_public is not None: cp.is_public = payload.is_public

    db.commit()
    return {"status": "success", "id": cp.id}

@router.delete("/checkpoints/{checkpoint_id}")
def delete_checkpoint(checkpoint_id: int, db: Session = Depends(get_db)):
    cp = db.query(MissionCheckpoint).filter(MissionCheckpoint.id == checkpoint_id).first()
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    db.delete(cp)
    db.commit()
    return {"status": "success", "message": "Checkpoint deleted"}


# --- TAB 5: Photos & Media ---
@router.get("/photos/{mission_id}")
def list_photos(mission_id: int, db: Session = Depends(get_db)):
    photos = db.query(MissionPhoto).filter(MissionPhoto.mission_id == mission_id).order_by(MissionPhoto.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "mission_id": p.mission_id,
            "checkpoint_id": p.checkpoint_id,
            "budget_item_id": p.budget_item_id,
            "image_url": p.image_url,
            "caption": p.caption,
            "category": p.category,
            "is_public": p.is_public,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in photos
    ]

@router.post("/photos")
def create_photo(payload: PhotoUploadCreate, db: Session = Depends(get_db)):
    photo = MissionPhoto(
        mission_id=payload.mission_id,
        checkpoint_id=payload.checkpoint_id,
        budget_item_id=payload.budget_item_id,
        image_url=payload.image_url,
        caption=payload.caption,
        category=payload.category,
        is_public=payload.is_public
    )
    db.add(photo)
    db.commit()
    return {"status": "success", "id": photo.id}


@router.delete("/photos/{photo_id}")
def delete_photo(photo_id: int, db: Session = Depends(get_db)):
    photo = db.query(MissionPhoto).filter(MissionPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    db.delete(photo)
    db.commit()
    return {"status": "success", "message": "Photo deleted"}


@router.delete("/reports/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(MissionFieldReport).filter(MissionFieldReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()
    return {"status": "success", "message": "Report deleted"}


# --- TAB 6: Field Reports ---
@router.get("/reports/{mission_id}")
def list_reports(mission_id: int, db: Session = Depends(get_db)):
    reports = db.query(MissionFieldReport).filter(MissionFieldReport.mission_id == mission_id).order_by(MissionFieldReport.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "mission_id": r.mission_id,
            "checkpoint_id": r.checkpoint_id,
            "title": r.title,
            "body": r.body,
            "report_type": r.report_type,
            "people_served_delta": r.people_served_delta,
            "is_public": r.is_public,
            "author_name": r.author_name,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in reports
    ]

@router.post("/reports")
def create_report(payload: FieldReportCreate, db: Session = Depends(get_db)):
    report = MissionFieldReport(
        mission_id=payload.mission_id,
        checkpoint_id=payload.checkpoint_id,
        title=payload.title,
        body=payload.body,
        report_type=payload.report_type,
        people_served_delta=payload.people_served_delta,
        is_public=payload.is_public,
        author_name=payload.author_name
    )
    db.add(report)
    db.commit()
    return {"status": "success", "id": report.id}


# --- TAB 7: Payouts ---
@router.get("/payouts/{mission_id}")
def list_payouts(mission_id: int, db: Session = Depends(get_db)):
    payouts = db.query(MissionPayout).filter(MissionPayout.mission_id == mission_id).order_by(MissionPayout.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "mission_id": p.mission_id,
            "budget_item_id": p.budget_item_id,
            "amount_usd": float(p.amount_usd),
            "recipient_wallet": p.recipient_wallet,
            "recipient_name": p.recipient_name,
            "stellar_tx_hash": p.stellar_tx_hash,
            "purpose": p.purpose,
            "status": p.status,
            "is_public": p.is_public,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in payouts
    ]

@router.post("/payouts")
def create_payout(payload: PayoutCreate, db: Session = Depends(get_db)):
    payout = MissionPayout(
        mission_id=payload.mission_id,
        budget_item_id=payload.budget_item_id,
        amount_usd=payload.amount_usd,
        recipient_wallet=payload.recipient_wallet,
        recipient_name=payload.recipient_name,
        stellar_tx_hash=payload.stellar_tx_hash,
        purpose=payload.purpose,
        status=payload.status,
        is_public=payload.is_public
    )
    db.add(payout)
    db.commit()
    return {"status": "success", "id": payout.id}


# --- TAB 8: Risk & Incidents ---
@router.get("/risks/{mission_id}")
def list_risks(mission_id: int, db: Session = Depends(get_db)):
    risks = db.query(MissionRiskIncident).filter(MissionRiskIncident.mission_id == mission_id).order_by(MissionRiskIncident.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "mission_id": r.mission_id,
            "title": r.title,
            "description": r.description,
            "severity": r.severity,
            "status": r.status,
            "resolution_plan": r.resolution_plan,
            "is_public": r.is_public,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in risks
    ]

@router.post("/risks")
def create_risk(payload: RiskIncidentCreate, db: Session = Depends(get_db)):
    risk = MissionRiskIncident(
        mission_id=payload.mission_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        resolution_plan=payload.resolution_plan,
        is_public=payload.is_public,
        status="OPEN"
    )
    db.add(risk)
    db.commit()
    return {"status": "success", "id": risk.id}

@router.put("/risks/{risk_id}")
def update_risk(risk_id: int, payload: RiskIncidentUpdate, db: Session = Depends(get_db)):
    risk = db.query(MissionRiskIncident).filter(MissionRiskIncident.id == risk_id).first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk incident not found")

    if payload.title is not None: risk.title = payload.title
    if payload.description is not None: risk.description = payload.description
    if payload.severity is not None: risk.severity = payload.severity
    if payload.status is not None:
        risk.status = payload.status
        if payload.status.upper() == "RESOLVED" and not risk.resolved_at:
            risk.resolved_at = datetime.utcnow()
    if payload.resolution_plan is not None: risk.resolution_plan = payload.resolution_plan
    if payload.is_public is not None: risk.is_public = payload.is_public

    db.commit()
    return {"status": "success", "id": risk.id}