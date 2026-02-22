"""ORM models for FieldOps AI."""

from datetime import datetime, date

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from database import Base


class Job(Base):
    """A completed field service job."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False, index=True)
    job_type = Column(String, nullable=False)
    materials_used = Column(JSON, default=list)  # List of {item, quantity, unit}
    labor_hours = Column(Float, nullable=False, default=0.0)
    status = Column(String, default="completed")
    transcript = Column(Text, default="")
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="job", uselist=False)
    follow_up = relationship("FollowUp", back_populates="job", uselist=False)

    def __repr__(self):
        return f"<Job {self.id}: {self.customer_name} - {self.job_type}>"


class Invoice(Base):
    """An auto-generated invoice for a job."""

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    labor_cost = Column(Float, nullable=False, default=0.0)
    materials_cost = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="invoice")

    def __repr__(self):
        return f"<Invoice {self.id}: ${self.total_amount:.2f}>"


class Inventory(Base):
    """Material inventory tracking."""

    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String, nullable=False, unique=True, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    unit = Column(String, default="piece")
    unit_cost = Column(Float, default=10.0)  # Default cost per unit
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Inventory {self.item_name}: {self.quantity} {self.unit}>"


class FollowUp(Base):
    """Scheduled follow-up for a customer."""

    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    customer_name = Column(String, nullable=False, index=True)
    scheduled_date = Column(Date, nullable=False)
    reason = Column(String, default="")
    status = Column(String, default="pending")  # pending, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="follow_up")

    def __repr__(self):
        return f"<FollowUp {self.customer_name}: {self.scheduled_date}>"


class RevenueEntry(Base):
    """Daily revenue tracking."""

    __tablename__ = "revenue_entries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today, index=True)
    amount = Column(Float, nullable=False, default=0.0)
    source = Column(String, default="invoice")  # invoice, other
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Revenue {self.date}: ${self.amount:.2f}>"
