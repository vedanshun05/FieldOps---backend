"""Tests for Pydantic schemas — extraction validation and edge cases."""

import pytest
from schemas.extraction import JobExtraction, MaterialUsed, ToolResult, AgentStep, AgentResult


class TestMaterialUsed:
    """Test MaterialUsed schema validation."""

    def test_valid_material(self):
        m = MaterialUsed(item="copper pipe", quantity=3, unit="piece")
        assert m.item == "copper pipe"
        assert m.quantity == 3
        assert m.unit == "piece"

    def test_default_unit(self):
        m = MaterialUsed(item="wire", quantity=5)
        assert m.unit == "piece"

    def test_invalid_quantity_zero(self):
        with pytest.raises(Exception):
            MaterialUsed(item="pipe", quantity=0)

    def test_invalid_quantity_negative(self):
        with pytest.raises(Exception):
            MaterialUsed(item="pipe", quantity=-1)


class TestJobExtraction:
    """Test JobExtraction schema validation."""

    def test_full_extraction(self):
        extraction = JobExtraction(
            customer_name="Sharma",
            job_type="plumbing",
            materials_used=[
                MaterialUsed(item="copper pipe", quantity=3, unit="piece"),
            ],
            labor_hours=2.0,
            follow_up_date="2025-08-15",
            follow_up_reason="Heater is old",
            invoice_required=True,
            confidence_score=0.92,
            raw_transcript="Finished the Sharma job...",
        )
        assert extraction.customer_name == "Sharma"
        assert extraction.job_type == "plumbing"
        assert len(extraction.materials_used) == 1
        assert extraction.labor_hours == 2.0
        assert extraction.invoice_required is True
        assert extraction.confidence_score == 0.92

    def test_minimal_extraction(self):
        extraction = JobExtraction(
            customer_name="Test Customer",
            job_type="general maintenance",
            labor_hours=1.0,
        )
        assert extraction.materials_used == []
        assert extraction.follow_up_date is None
        assert extraction.invoice_required is True  # default
        assert extraction.confidence_score == 0.85  # default

    def test_confidence_score_bounds(self):
        # Valid bounds
        e1 = JobExtraction(customer_name="A", job_type="B", labor_hours=1, confidence_score=0.0)
        assert e1.confidence_score == 0.0

        e2 = JobExtraction(customer_name="A", job_type="B", labor_hours=1, confidence_score=1.0)
        assert e2.confidence_score == 1.0

        # Invalid: above 1.0
        with pytest.raises(Exception):
            JobExtraction(customer_name="A", job_type="B", labor_hours=1, confidence_score=1.5)

        # Invalid: below 0.0
        with pytest.raises(Exception):
            JobExtraction(customer_name="A", job_type="B", labor_hours=1, confidence_score=-0.1)

    def test_negative_labor_hours_rejected(self):
        with pytest.raises(Exception):
            JobExtraction(customer_name="A", job_type="B", labor_hours=-1)

    def test_multiple_materials(self):
        extraction = JobExtraction(
            customer_name="Kumar",
            job_type="electrical",
            materials_used=[
                MaterialUsed(item="wire", quantity=10, unit="meter"),
                MaterialUsed(item="circuit breaker", quantity=1),
                MaterialUsed(item="switch", quantity=4),
            ],
            labor_hours=3.5,
        )
        assert len(extraction.materials_used) == 3


class TestToolResult:
    """Test ToolResult schema."""

    def test_success_result(self):
        result = ToolResult(
            tool_name="log_job",
            success=True,
            message="Job logged",
            data={"job_id": 1},
        )
        assert result.success is True
        assert result.data["job_id"] == 1

    def test_failure_result(self):
        result = ToolResult(
            tool_name="update_inventory",
            success=False,
            message="DB error",
        )
        assert result.success is False
        assert result.data is None


class TestAgentResult:
    """Test AgentResult schema."""

    def test_agent_result(self):
        extraction = JobExtraction(
            customer_name="Test", job_type="plumbing", labor_hours=2.0
        )
        result = AgentResult(
            extraction=extraction,
            steps=[
                AgentStep(step_number=1, action="analyze", reasoning="Testing"),
            ],
            tools_executed=["log_job"],
            success=True,
            summary="Test complete",
        )
        assert result.success is True
        assert len(result.steps) == 1
        assert "log_job" in result.tools_executed
