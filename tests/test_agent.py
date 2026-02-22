"""Tests for agent orchestrator — workflow execution and business rules."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from schemas.extraction import JobExtraction, MaterialUsed
from agent.orchestrator import execute_workflow, _determine_tools
from models.models import Inventory


@pytest.fixture
def db_session():
    """Create a fresh in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed inventory
    items = [
        Inventory(item_name="copper pipe", quantity=50, unit="piece", unit_cost=25.0),
        Inventory(item_name="wire", quantity=100, unit="meter", unit_cost=8.0),
    ]
    session.add_all(items)
    session.commit()

    yield session
    session.close()


class TestDetermineTools:
    """Test business rule-based tool selection."""

    def test_full_extraction_all_tools(self):
        extraction = JobExtraction(
            customer_name="Sharma",
            job_type="plumbing",
            materials_used=[MaterialUsed(item="pipe", quantity=3)],
            labor_hours=2.0,
            follow_up_date="6 months",
            invoice_required=True,
        )
        tools = _determine_tools(extraction)
        tool_names = [t["name"] for t in tools]

        assert "log_job" in tool_names
        assert "update_inventory" in tool_names
        assert "generate_invoice" in tool_names
        assert "update_revenue" in tool_names
        assert "schedule_followup" in tool_names

    def test_minimal_extraction(self):
        extraction = JobExtraction(
            customer_name="Test",
            job_type="inspection",
            labor_hours=1.0,
            invoice_required=False,
        )
        tools = _determine_tools(extraction)
        tool_names = [t["name"] for t in tools]

        assert "log_job" in tool_names
        assert "update_inventory" not in tool_names
        assert "generate_invoice" not in tool_names
        assert "schedule_followup" not in tool_names

    def test_no_materials_skips_inventory(self):
        extraction = JobExtraction(
            customer_name="Test",
            job_type="consulting",
            labor_hours=2.0,
            materials_used=[],
            invoice_required=True,
        )
        tools = _determine_tools(extraction)
        tool_names = [t["name"] for t in tools]

        assert "update_inventory" not in tool_names
        assert "generate_invoice" in tool_names

    def test_revenue_follows_invoice(self):
        extraction = JobExtraction(
            customer_name="Test",
            job_type="plumbing",
            labor_hours=1.0,
            invoice_required=True,
        )
        tools = _determine_tools(extraction)
        tool_names = [t["name"] for t in tools]

        invoice_idx = tool_names.index("generate_invoice")
        revenue_idx = tool_names.index("update_revenue")
        assert revenue_idx > invoice_idx  # Revenue must come after invoice


class TestExecuteWorkflow:
    """Test full workflow execution."""

    def test_full_workflow(self, db_session):
        extraction = JobExtraction(
            customer_name="Sharma",
            job_type="plumbing",
            materials_used=[MaterialUsed(item="copper pipe", quantity=3)],
            labor_hours=2.0,
            follow_up_date="6 months",
            follow_up_reason="Heater is old",
            invoice_required=True,
            confidence_score=0.92,
            raw_transcript="Finished the Sharma job.",
        )
        result = execute_workflow(extraction, db_session)

        assert result.success is True
        assert len(result.tools_executed) == 5
        assert "log_job" in result.tools_executed
        assert "update_inventory" in result.tools_executed
        assert "generate_invoice" in result.tools_executed
        assert "update_revenue" in result.tools_executed
        assert "schedule_followup" in result.tools_executed
        assert result.summary != ""

    def test_minimal_workflow(self, db_session):
        extraction = JobExtraction(
            customer_name="Test",
            job_type="inspection",
            labor_hours=0.5,
            invoice_required=False,
        )
        result = execute_workflow(extraction, db_session)

        assert result.success is True
        assert "log_job" in result.tools_executed
        assert "update_inventory" not in result.tools_executed
        assert "generate_invoice" not in result.tools_executed

    def test_reasoning_steps_logged(self, db_session):
        extraction = JobExtraction(
            customer_name="Kumar",
            job_type="electrical",
            materials_used=[MaterialUsed(item="wire", quantity=5, unit="meter")],
            labor_hours=3.0,
            invoice_required=True,
        )
        result = execute_workflow(extraction, db_session)

        assert len(result.steps) > 1  # At least analysis + tool executions
        assert result.steps[0].action == "analyze_extraction"
        for step in result.steps[1:]:
            assert step.reasoning != ""  # Every step has reasoning
