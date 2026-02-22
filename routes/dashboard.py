"""Dashboard and data API routes."""

import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.models import Job, Invoice, Inventory, FollowUp, RevenueEntry
from schemas.extraction import DashboardSummary, InventoryItem, FollowUpResponse
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get overview metrics for the dashboard."""
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Job counts
    total_jobs_today = db.query(func.count(Job.id)).filter(
        func.date(Job.created_at) == today
    ).scalar() or 0

    # Revenue
    total_revenue_today = db.query(func.coalesce(func.sum(RevenueEntry.amount), 0)).filter(
        RevenueEntry.date == today
    ).scalar() or 0.0

    total_revenue_week = db.query(func.coalesce(func.sum(RevenueEntry.amount), 0)).filter(
        RevenueEntry.date >= week_ago
    ).scalar() or 0.0

    total_revenue_month = db.query(func.coalesce(func.sum(RevenueEntry.amount), 0)).filter(
        RevenueEntry.date >= month_ago
    ).scalar() or 0.0

    # Low stock items
    low_stock = db.query(Inventory).filter(
        Inventory.quantity <= settings.LOW_STOCK_THRESHOLD
    ).all()
    low_stock_items = [
        {"item_name": i.item_name, "quantity": i.quantity, "unit": i.unit}
        for i in low_stock
    ]

    # Upcoming follow-ups (next 7 days)
    upcoming = db.query(FollowUp).filter(
        FollowUp.status == "pending",
        FollowUp.scheduled_date <= today + timedelta(days=7),
    ).order_by(FollowUp.scheduled_date).all()
    upcoming_followups = [
        {
            "customer_name": f.customer_name,
            "scheduled_date": f.scheduled_date.isoformat(),
            "reason": f.reason,
        }
        for f in upcoming
    ]

    # Recent jobs (last 10)
    recent = db.query(Job).order_by(Job.created_at.desc()).limit(10).all()
    recent_jobs = [
        {
            "id": j.id,
            "customer_name": j.customer_name,
            "job_type": j.job_type,
            "labor_hours": j.labor_hours,
            "created_at": j.created_at.isoformat() if j.created_at else "",
        }
        for j in recent
    ]

    return DashboardSummary(
        total_jobs_today=total_jobs_today,
        total_revenue_today=total_revenue_today,
        total_revenue_week=total_revenue_week,
        total_revenue_month=total_revenue_month,
        low_stock_items=low_stock_items,
        upcoming_followups=upcoming_followups,
        recent_jobs=recent_jobs,
    )


@router.get("/jobs")
def get_jobs(db: Session = Depends(get_db)):
    """Get all jobs, most recent first."""
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(50).all()
    return [
        {
            "id": j.id,
            "customer_name": j.customer_name,
            "job_type": j.job_type,
            "materials_used": j.materials_used or [],
            "labor_hours": j.labor_hours,
            "status": j.status,
            "confidence_score": j.confidence_score,
            "transcript": j.transcript,
            "created_at": j.created_at.isoformat() if j.created_at else "",
        }
        for j in jobs
    ]


@router.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    """Get all inventory items."""
    items = db.query(Inventory).order_by(Inventory.item_name).all()
    return [
        {
            "id": i.id,
            "item_name": i.item_name,
            "quantity": i.quantity,
            "unit": i.unit,
            "unit_cost": i.unit_cost,
            "is_low_stock": i.quantity <= settings.LOW_STOCK_THRESHOLD,
        }
        for i in items
    ]


@router.get("/followups")
def get_followups(db: Session = Depends(get_db)):
    """Get all pending follow-ups."""
    followups = db.query(FollowUp).filter(
        FollowUp.status == "pending"
    ).order_by(FollowUp.scheduled_date).all()
    return [
        {
            "id": f.id,
            "customer_name": f.customer_name,
            "scheduled_date": f.scheduled_date.isoformat(),
            "reason": f.reason,
            "status": f.status,
            "job_id": f.job_id,
            "created_at": f.created_at.isoformat() if f.created_at else "",
        }
        for f in followups
    ]


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    """Get active alerts for retention layer — low stock + overdue follow-ups."""
    today = date.today()
    alerts = []

    # Low stock alerts
    low_stock = db.query(Inventory).filter(
        Inventory.quantity <= settings.LOW_STOCK_THRESHOLD
    ).all()
    for item in low_stock:
        alerts.append({
            "type": "low_stock",
            "severity": "warning" if item.quantity > 0 else "critical",
            "message": f"Low stock: {item.item_name} ({item.quantity} {item.unit} remaining)",
            "item_name": item.item_name,
            "quantity": item.quantity,
        })

    # Overdue follow-ups
    overdue = db.query(FollowUp).filter(
        FollowUp.status == "pending",
        FollowUp.scheduled_date <= today,
    ).all()
    for fu in overdue:
        alerts.append({
            "type": "overdue_followup",
            "severity": "critical",
            "message": f"Overdue follow-up: {fu.customer_name} (was due {fu.scheduled_date.isoformat()})",
            "customer_name": fu.customer_name,
            "scheduled_date": fu.scheduled_date.isoformat(),
        })

    # Upcoming follow-ups (next 3 days)
    upcoming = db.query(FollowUp).filter(
        FollowUp.status == "pending",
        FollowUp.scheduled_date > today,
        FollowUp.scheduled_date <= today + timedelta(days=3),
    ).all()
    for fu in upcoming:
        alerts.append({
            "type": "upcoming_followup",
            "severity": "info",
            "message": f"Upcoming follow-up: {fu.customer_name} on {fu.scheduled_date.isoformat()}",
            "customer_name": fu.customer_name,
            "scheduled_date": fu.scheduled_date.isoformat(),
        })

    return alerts
