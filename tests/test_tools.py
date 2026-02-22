"""Tests for tool handlers — job logging, inventory, invoice, followup, revenue."""

import pytest
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from schemas.extraction import JobExtraction, MaterialUsed
from tools.job_logger import log_job
from tools.inventory import update_inventory
from tools.invoice import generate_invoice
from tools.followup import schedule_followup, _parse_follow_up_date
from tools.revenue import update_revenue
from models.models import Job, Inventory, Invoice, FollowUp, RevenueEntry


@pytest.fixture
def db_session():
    """Create a fresh in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed some inventory
    items = [
        Inventory(item_name="copper pipe", quantity=50, unit="piece", unit_cost=25.0),
        Inventory(item_name="wire", quantity=100, unit="meter", unit_cost=8.0),
        Inventory(item_name="faucet", quantity=3, unit="piece", unit_cost=45.0),
    ]
    session.add_all(items)
    session.commit()

    yield session
    session.close()


@pytest.fixture
def sample_extraction():
    """Standard extraction for testing."""
    return JobExtraction(
        customer_name="Sharma",
        job_type="plumbing",
        materials_used=[
            MaterialUsed(item="copper pipe", quantity=3, unit="piece"),
        ],
        labor_hours=2.0,
        follow_up_date="6 months",
        follow_up_reason="Heater is old",
        invoice_required=True,
        confidence_score=0.92,
        raw_transcript="Finished the Sharma job. Used 3 copper pipes, worked 2 hours.",
    )


class TestLogJob:
    """Test log_job tool."""

    def test_log_job_success(self, db_session, sample_extraction):
        result = log_job(sample_extraction, db_session)
        assert result.success is True
        assert result.data["job_id"] is not None

        # Verify in DB
        job = db_session.query(Job).first()
        assert job.customer_name == "Sharma"
        assert job.job_type == "plumbing"
        assert job.labor_hours == 2.0

    def test_log_job_stores_transcript(self, db_session, sample_extraction):
        log_job(sample_extraction, db_session)
        job = db_session.query(Job).first()
        assert "Sharma" in job.transcript


class TestUpdateInventory:
    """Test update_inventory tool."""

    def test_decrement_existing_item(self, db_session, sample_extraction):
        result = update_inventory(sample_extraction, db_session)
        db_session.flush()
        assert result.success is True

        item = db_session.query(Inventory).filter_by(item_name="copper pipe").first()
        assert item.quantity == 47  # 50 - 3

    def test_no_materials(self, db_session):
        extraction = JobExtraction(
            customer_name="Test", job_type="inspection", labor_hours=1.0, materials_used=[]
        )
        result = update_inventory(extraction, db_session)
        assert result.success is True
        assert result.message == "No materials to update"

    def test_new_material_created(self, db_session):
        extraction = JobExtraction(
            customer_name="Test",
            job_type="HVAC",
            labor_hours=1.0,
            materials_used=[
                MaterialUsed(item="thermostat", quantity=1, unit="piece"),
            ],
        )
        result = update_inventory(extraction, db_session)
        db_session.flush()
        assert result.success is True

        item = db_session.query(Inventory).filter_by(item_name="thermostat").first()
        assert item is not None
        assert item.quantity == 99  # 100 - 1


class TestGenerateInvoice:
    """Test generate_invoice tool."""

    def test_invoice_generated(self, db_session, sample_extraction):
        # First log the job
        job_result = log_job(sample_extraction, db_session)
        job_id = job_result.data["job_id"]

        result = generate_invoice(sample_extraction, job_id, db_session)
        assert result.success is True
        assert result.data["total_amount"] > 0
        assert result.data["labor_cost"] == 150.0  # 2h * $75
        assert result.data["materials_cost"] == 75.0  # 3 * $25

    def test_invoice_not_required(self, db_session):
        extraction = JobExtraction(
            customer_name="Test", job_type="inspection", labor_hours=1.0,
            invoice_required=False,
        )
        result = generate_invoice(extraction, 1, db_session)
        assert result.success is True
        assert result.message == "Invoice not required"


class TestScheduleFollowup:
    """Test schedule_followup tool and date parsing."""

    def test_relative_months(self):
        result = _parse_follow_up_date("6 months")
        expected = date.today() + relativedelta(months=6)
        assert result == expected

    def test_relative_weeks(self):
        result = _parse_follow_up_date("2 weeks")
        expected = date.today() + timedelta(weeks=2)
        assert result == expected

    def test_iso_date(self):
        result = _parse_follow_up_date("2027-06-15")
        assert result == date(2027, 6, 15)

    def test_followup_created(self, db_session, sample_extraction):
        job_result = log_job(sample_extraction, db_session)
        job_id = job_result.data["job_id"]

        result = schedule_followup(sample_extraction, job_id, db_session)
        assert result.success is True
        assert result.data["scheduled_date"] is not None

    def test_no_followup_needed(self, db_session):
        extraction = JobExtraction(
            customer_name="Test", job_type="plumbing", labor_hours=1.0,
            follow_up_date=None,
        )
        result = schedule_followup(extraction, 1, db_session)
        assert result.success is True
        assert result.message == "No follow-up needed"


class TestUpdateRevenue:
    """Test update_revenue tool."""

    def test_revenue_recorded(self, db_session):
        result = update_revenue(1, 225.0, db_session)
        assert result.success is True
        assert result.data["amount"] == 225.0

    def test_zero_amount(self, db_session):
        result = update_revenue(1, 0, db_session)
        assert result.success is True
        assert result.message == "No revenue to record"
